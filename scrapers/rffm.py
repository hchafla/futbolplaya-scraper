# rffm.py

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://www.rffm.es"

START_URL = "https://www.rffm.es/actualidad/federacion?_start=0"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}

ITEMS_POR_PAGINA = 12
MIN_PAGES = 20
MAX_PAGES = 50


def limpiar_texto(texto):
    return " ".join(texto.split()).strip()


def construir_url_pagina(pagina):
    """Construye la URL de una página según el parámetro _start."""

    start = (pagina - 1) * ITEMS_POR_PAGINA

    return f"{BASE_URL}/actualidad/federacion?_start={start}"


def es_futbol_playa(texto):
    """Determina si un texto pertenece a fútbol playa."""

    if not texto:
        return False

    texto = limpiar_texto(texto).lower()

    texto = texto.replace("-", " ")
    texto = texto.replace("–", " ")
    texto = texto.replace("—", " ")

    patrones = [
        r"\bfútbol\s+playa\b",
        r"\bfutbol\s+playa\b",
        r"\bbeach\s+soccer\b",
        r"\bbeachsoccer\b",
    ]

    return any(
        re.search(patron, texto)
        for patron in patrones
    )


def extraer_fecha(texto):
    """
    Convierte una fecha de RFFM del tipo DD/MM/YYYY
    a YYYY-MM-DD.
    """

    match = re.search(
        r"\b(\d{2})/(\d{2})/(\d{4})\b",
        texto
    )

    if not match:
        return None

    dia, mes, anio = match.groups()

    return f"{anio}-{mes}-{dia}"


def obtener_imagen(card):
    """
    Obtiene la imagen de la noticia a partir del estilo
    background: url("...") del primer <a> del card.
    """

    enlace_imagen = card.find("a", style=True)

    if not enlace_imagen:
        return None

    style = enlace_imagen.get("style", "")

    match = re.search(r'url\("([^"]+)"\)', style)

    if not match:
        match = re.search(r"url\('([^']+)'\)", style)

    if not match:
        return None

    return urljoin(BASE_URL, match.group(1))


def obtener_categoria(card):
    """
    Obtiene el badge de categoría que RFFM pinta sobre la
    imagen (ej. "Federación, Fútbol Sala").
    """

    enlace_imagen = card.find("a", style=True)

    if not enlace_imagen:
        return ""

    badge = enlace_imagen.find("p")

    if not badge:
        return ""

    return limpiar_texto(badge.get_text(" ", strip=True))


def obtener_resumen(card):
    """
    Obtiene el párrafo de resumen de la noticia (el <p> que
    no está dentro del <h4> del título ni es el badge de
    categoría).
    """

    enlace_imagen = card.find("a", style=True)
    badge = enlace_imagen.find("p") if enlace_imagen else None

    for p in card.find_all("p"):

        if p.find_parent("h4"):
            continue

        if badge is not None and p is badge:
            continue

        texto = limpiar_texto(p.get_text(" ", strip=True))

        if texto:
            return texto

    return None


def extraer_noticias(html):
    """Extrae las noticias de una página de RFFM."""

    soup = BeautifulSoup(html, "html.parser")

    noticias = []

    for card in soup.select("div.noticiacard"):

        enlace = card.find("a", href=True)

        if not enlace:
            continue

        href = enlace.get("href")

        if not href or href.startswith("#"):
            continue

        url = urljoin(BASE_URL, href)

        h4 = card.find("h4")

        if not h4:
            continue

        titulo = limpiar_texto(h4.get_text(" ", strip=True))

        if not titulo:
            continue

        # La fecha vive en el div que también contiene el
        # icono del escudo (MuiBox-root ...).
        fecha = None

        for div in card.find_all(
            "div",
            class_=re.compile(r"\bMuiBox-root\b")
        ):

            texto_div = div.get_text(" ", strip=True)

            fecha = extraer_fecha(texto_div)

            if fecha:
                break

        if not fecha:
            continue

        imagen = obtener_imagen(card)
        categoria = obtener_categoria(card)
        resumen = obtener_resumen(card)

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha,
            "summary": resumen or "",
            "image": imagen,
            "category": categoria,
            "source": "RFFM",
        })

    return noticias


def obtener_noticias_pagina(url):
    """Descarga y procesa una página."""

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return extraer_noticias(response.text)


def scrape():
    """
    Obtiene noticias de fútbol playa de RFFM.

    RFFM mezcla todas las categorías en /actualidad/federacion,
    así que hace falta filtrar por título, resumen o badge de
    categoría. La paginación usa el parámetro _start (12
    noticias por página). Se recorren al menos MIN_PAGES
    páginas.
    """

    print(f"RFFM: procesando {START_URL}")

    noticias_futbol_playa = []
    urls_vistas = set()

    paginas_sin_noticias_seguidas = 0

    for pagina in range(1, MAX_PAGES + 1):

        url = construir_url_pagina(pagina)

        print(f"RFFM: procesando página {pagina}: {url}")

        try:
            noticias = obtener_noticias_pagina(url)

        except requests.RequestException as e:

            print(f"RFFM: error descargando página {pagina}: {e}")

            if pagina < MIN_PAGES:
                continue

            break

        except Exception as e:

            print(f"RFFM: error procesando página {pagina}: {e}")

            if pagina < MIN_PAGES:
                continue

            break

        if not noticias:

            paginas_sin_noticias_seguidas += 1

            print(f"RFFM: no se encontraron noticias en página {pagina}")

            # Si ya hemos cubierto el mínimo y dos páginas
            # seguidas vienen vacías, asumimos que se acabó
            # la paginación real.
            if pagina >= MIN_PAGES and paginas_sin_noticias_seguidas >= 2:
                break

            continue

        paginas_sin_noticias_seguidas = 0

        encontradas_pagina = 0

        for noticia in noticias:

            url_noticia = noticia.get("url")

            if not url_noticia or url_noticia in urls_vistas:
                continue

            es_playa = (
                es_futbol_playa(noticia["title"])
                or es_futbol_playa(noticia.get("summary", ""))
                or es_futbol_playa(noticia.get("category", ""))
            )

            if not es_playa:
                continue

            urls_vistas.add(url_noticia)

            encontradas_pagina += 1

            noticias_futbol_playa.append(noticia)

            print(f"RFFM: fútbol playa -> {noticia['title']}")

        print(
            f"RFFM: {encontradas_pagina} noticias de "
            f"fútbol playa en página {pagina}"
        )

    # -----------------------------------------------------
    # Ordenar las noticias de RFFM
    # -----------------------------------------------------

    noticias_futbol_playa.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(
        f"RFFM: {len(noticias_futbol_playa)} noticias de "
        f"fútbol playa encontradas en total"
    )

    return noticias_futbol_playa


if __name__ == "__main__":

    noticias = scrape()

    print()
    print("=== NOTICIAS FÚTBOL PLAYA (RFFM) ===")

    for noticia in noticias:

        print(
            f"{noticia['date']} | "
            f"{noticia['title']} | "
            f"{noticia['url']}"
        )
