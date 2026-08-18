# fexfutbol.py

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://www.fexfutbol.com"

START_URL = (
    "https://www.fexfutbol.com/pnfg/NNws_LstNews"
    "?cod_primaria=3000205"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}

MIN_PAGES = 5
MAX_PAGES = 50


def construir_url_pagina(pagina):
    """Construye la URL de una página concreta."""

    if pagina == 1:
        return START_URL

    return (
        f"{BASE_URL}/pnfg/NNws_LstNews"
        f"?cod_primaria=3000205"
        f"&buscar="
        f"&cod_secundaria=3000205"
        f"&NPcd_PageAnt={pagina - 1}"
        f"&NPcd_PageNext={pagina + 1}"
        f"&NPcd_Page={pagina}"
    )


def es_futbol_playa(titulo):
    """Determina si una noticia pertenece a fútbol playa."""

    titulo = " ".join(titulo.split()).lower()

    titulo = titulo.replace("-", " ")
    titulo = titulo.replace("–", " ")
    titulo = titulo.replace("—", " ")

    patrones = [
        r"\bfútbol\s+playa\b",
        r"\bfutbol\s+playa\b",
        r"\bbeach\s+soccer\b",
        r"\bbeachsoccer\b",
    ]

    return any(
        re.search(patron, titulo)
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

    dia, mes, año = match.groups()

    return f"{año}-{mes}-{dia}"


def extraer_noticias(html):
    """Extrae las noticias de una página de FEXFUTBOL."""

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    noticias = []

    for bloque in soup.select("td.td_not"):

        enlace = bloque.select_one(
            "a.titulo_noticia"
        )

        if not enlace:
            continue

        titulo = enlace.get_text(
            " ",
            strip=True
        )

        if not titulo:
            continue

        href = enlace.get("href")

        if not href:
            continue

        url = urljoin(
            BASE_URL,
            href
        )

        # -------------------------------------------------
        # Fecha
        # -------------------------------------------------

        fecha_original = ""

        span = bloque.find("span")

        if span:

            texto_span = span.get_text(
                " ",
                strip=True
            )

            match = re.search(
                r"\b\d{2}/\d{2}/\d{4}\b",
                texto_span
            )

            if match:
                fecha_original = match.group(0)

        fecha = convertir_fecha(
            fecha_original
        )

        # -------------------------------------------------
        # Imagen
        # -------------------------------------------------

        imagen = ""

        img = bloque.select_one(
            "img"
        )

        if img:

            src = (
                img.get("src")
                or img.get("data-src")
                or ""
            )

            if src:
                imagen = urljoin(
                    BASE_URL,
                    src
                )

        # -------------------------------------------------
        # Resumen
        # -------------------------------------------------

        resumen = ""

        p = bloque.find("p")

        if p:
            resumen = p.get_text(
                " ",
                strip=True
            )

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha,
            "summary": resumen,
            "image": imagen,
            "source": "FEXFútbol"
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

    return extraer_noticias(
        response.text
    )


def scrape():
    """
    Obtiene noticias de fútbol playa de FEXFútbol.

    Se procesan al menos las 5 primeras páginas.
    """

    print(
        f"FEXFútbol: procesando {START_URL}"
    )

    noticias_futbol_playa = []

    urls_vistas = set()

    for pagina in range(
        1,
        MAX_PAGES + 1
    ):

        url = construir_url_pagina(
            pagina
        )

        if url in urls_vistas:

            print(
                f"FEXFútbol: URL repetida "
                f"en página {pagina}, deteniendo"
            )

            break

        urls_vistas.add(url)

        print(
            f"FEXFútbol: procesando página "
            f"{pagina}: {url}"
        )

        try:

            noticias = obtener_noticias_pagina(
                url
            )

        except requests.RequestException as e:

            print(
                f"FEXFútbol: error descargando "
                f"página {pagina}: {e}"
            )

            if pagina < MIN_PAGES:
                continue

            break

        except Exception as e:

            print(
                f"FEXFútbol: error procesando "
                f"página {pagina}: {e}"
            )

            if pagina < MIN_PAGES:
                continue

            break

        if not noticias:

            print(
                f"FEXFútbol: no se encontraron "
                f"noticias en página {pagina}"
            )

            if pagina >= MIN_PAGES:
                break

            continue

        encontradas_pagina = 0

        for noticia in noticias:

            if not es_futbol_playa(
                noticia["title"]
            ):
                continue

            encontradas_pagina += 1

            noticias_futbol_playa.append(
                noticia
            )

            print(
                "FEXFútbol: fútbol playa -> "
                f"{noticia['title']}"
            )

        print(
            f"FEXFútbol: "
            f"{encontradas_pagina} noticias de "
            f"fútbol playa en página {pagina}"
        )

    # -----------------------------------------------------
    # Eliminar duplicados por URL
    # -----------------------------------------------------

    noticias_unicas = []
    urls = set()

    for noticia in noticias_futbol_playa:

        url = noticia.get("url")

        if not url or url in urls:
            continue

        urls.add(url)

        noticias_unicas.append(
            noticia
        )

    # -----------------------------------------------------
    # Ordenar las noticias de FEXFútbol
    # -----------------------------------------------------

    noticias_unicas.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(
        f"FEXFútbol: "
        f"{len(noticias_unicas)} noticias de "
        f"fútbol playa encontradas en total"
    )

    return noticias_unicas


if __name__ == "__main__":

    noticias = scrape()

    print()
    print(
        "=== NOTICIAS FÚTBOL PLAYA ==="
    )

    for noticia in noticias:

        print(
            f"{noticia['date']} | "
            f"{noticia['title']} | "
            f"{noticia['url']}"
        )
