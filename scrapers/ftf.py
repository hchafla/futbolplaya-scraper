# ftf.py

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://www.ftf.es"

START_URL = (
    "https://www.ftf.es/pnfg/NNws_LstNews"
    "?cod_primaria=3001822&cod_secundaria=3001822"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}

# La web dice "Página 2/58" (864 registros) solo en la
# segunda página que nos enseñaron; recorremos como máximo
# MAX_PAGINAS páginas manteniendo sesión (cookies) entre
# peticiones, como en rffpa.py / rfmf.py.
MAX_PAGINAS = 20


def limpiar_texto(texto):
    return " ".join(texto.split()).strip()


def construir_url_pagina(pagina):
    """Construye la URL de una página concreta."""

    if pagina == 1:
        return START_URL

    return (
        f"{BASE_URL}/pnfg/NNws_LstNews"
        f"?cod_primaria=3001822"
        f"&buscar="
        f"&cod_secundaria=3001822"
        f"&NPcd_PageAnt={pagina - 1}"
        f"&NPcd_PageNext={pagina + 1}"
        f"&NPcd_Page={pagina}"
    )


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


def convertir_fecha(fecha):
    """
    Convierte DD/MM/YYYY a YYYY-MM-DD para que main.py
    pueda ordenar correctamente las noticias.
    """

    match = re.match(
        r"^(\d{2})/(\d{2})/(\d{4})$",
        fecha
    )

    if not match:
        return fecha

    dia, mes, anio = match.groups()

    return f"{anio}-{mes}-{dia}"


def extraer_noticias(html):
    """Extrae las noticias de una página de FTF."""

    soup = BeautifulSoup(html, "html.parser")

    noticias = []

    for bloque in soup.select("td.td_not"):

        enlace = bloque.select_one("a.titulo_noticia")

        if not enlace:
            continue

        titulo = limpiar_texto(
            enlace.get_text(" ", strip=True)
        )

        if not titulo:
            continue

        href = enlace.get("href")

        if not href:
            continue

        url = urljoin(BASE_URL, href)

        # -------------------------------------------------
        # Fecha
        # -------------------------------------------------

        fecha_original = ""

        span = bloque.find("span")

        if span:

            texto_span = span.get_text(" ", strip=True)

            match = re.search(
                r"\b\d{2}/\d{2}/\d{4}\b",
                texto_span
            )

            if match:
                fecha_original = match.group(0)

        fecha = convertir_fecha(fecha_original)

        # -------------------------------------------------
        # Imagen
        # -------------------------------------------------

        imagen = ""

        img = bloque.select_one("img")

        if img:

            src = (
                img.get("src")
                or img.get("data-src")
                or ""
            )

            if src:
                imagen = urljoin(BASE_URL, src)

        # -------------------------------------------------
        # Resumen
        # -------------------------------------------------

        resumen = ""

        p = bloque.find("p")

        if p:
            resumen = limpiar_texto(
                p.get_text(" ", strip=True)
            )

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha,
            "summary": resumen,
            "image": imagen,
            "source": "FTF",
        })

    return noticias


def obtener_noticias_pagina(sesion, url):
    """Descarga y procesa una página usando una sesión persistente."""

    response = sesion.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return extraer_noticias(response.text)


def scrape():
    """
    Obtiene noticias de fútbol playa de la Federación
    Interinsular de Fútbol de Tenerife (FTF).

    La web mezcla todas las categorías en "Noticias
    generales", así que hace falta filtrar por título o
    resumen. Se recorren como máximo MAX_PAGINAS páginas,
    manteniendo sesión (cookies) entre peticiones.
    """

    print(f"FTF: procesando {START_URL}")

    noticias_futbol_playa = []
    urls_vistas = set()

    with requests.Session() as sesion:

        for pagina in range(1, MAX_PAGINAS + 1):

            url = construir_url_pagina(pagina)

            print(f"FTF: procesando página {pagina}: {url}")

            try:
                noticias = obtener_noticias_pagina(sesion, url)

            except requests.RequestException as e:

                print(f"FTF: error descargando página {pagina}: {e}")
                continue

            except Exception as e:

                print(f"FTF: error procesando página {pagina}: {e}")
                continue

            if not noticias:
                print(f"FTF: no se encontraron noticias en página {pagina}")
                continue

            print(f"FTF: {len(noticias)} noticias en bruto en página {pagina}")

            encontradas_pagina = 0

            for noticia in noticias:

                url_noticia = noticia.get("url")

                if not url_noticia or url_noticia in urls_vistas:
                    continue

                es_playa = (
                    es_futbol_playa(noticia["title"])
                    or es_futbol_playa(noticia.get("summary", ""))
                )

                if not es_playa:
                    continue

                urls_vistas.add(url_noticia)

                encontradas_pagina += 1

                noticias_futbol_playa.append(noticia)

                print(f"FTF: fútbol playa -> {noticia['title']}")

            print(
                f"FTF: {encontradas_pagina} noticias de "
                f"fútbol playa en página {pagina}"
            )

    # -----------------------------------------------------
    # Ordenar las noticias de FTF
    # -----------------------------------------------------

    noticias_futbol_playa.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(
        f"FTF: {len(noticias_futbol_playa)} noticias de "
        f"fútbol playa encontradas en total"
    )

    return noticias_futbol_playa


if __name__ == "__main__":

    noticias = scrape()

    print()
    print("=== NOTICIAS FÚTBOL PLAYA (FTF) ===")

    for noticia in noticias:

        print(
            f"{noticia['date']} | "
            f"{noticia['title']} | "
            f"{noticia['url']}"
        )
