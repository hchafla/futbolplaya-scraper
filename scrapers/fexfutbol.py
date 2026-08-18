# fexfutbol.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


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

# Número mínimo de páginas que se procesan.
MIN_PAGES = 5

# Límite de seguridad.
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
    """
    Determina si una noticia pertenece a fútbol playa
    utilizando únicamente el título.
    """

    titulo = " ".join(titulo.split()).lower()

    # Normalizamos guiones para detectar:
    # fútbol playa
    # fútbol-playa
    # futbol playa
    # futbol-playa
    titulo = titulo.replace("-", " ")

    patrones = [
        r"\bfútbol\s+playa\b",
        r"\bfutbol\s+playa\b",
        r"\bbeach\s+soccer\b",
    ]

    return any(
        re.search(patron, titulo, re.IGNORECASE)
        for patron in patrones
    )


def extraer_noticias(html):
    """Extrae las noticias de una página de FEXFUTBOL."""

    soup = BeautifulSoup(html, "html.parser")

    noticias = []

    # La estructura observada en FEXFUTBOL es:
    #
    # <td class="td_not">
    #   ...
    #   <a class="titulo_noticia">Título</a>
    #   <span>fecha</span>
    #   <p>resumen</p>
    #
    for bloque in soup.select("td.td_not"):

        enlace = bloque.select_one("a.titulo_noticia")

        if not enlace:
            continue

        titulo = enlace.get_text(" ", strip=True)

        if not titulo:
            continue

        href = enlace.get("href")

        if not href:
            continue

        url = urljoin(BASE_URL, href)

        # Fecha
        fecha = ""

        span = bloque.find("span")

        if span:
            texto_span = span.get_text(" ", strip=True)

            match = re.search(
                r"\b\d{2}/\d{2}/\d{4}\b",
                texto_span
            )

            if match:
                fecha = match.group(0)

        # Resumen
        resumen = ""

        p = bloque.find("p")

        if p:
            resumen = p.get_text(" ", strip=True)

        noticias.append({
            "titulo": titulo,
            "url": url,
            "fecha": fecha,
            "resumen": resumen
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


def obtener_noticias():
    """
    Obtiene noticias de fútbol playa de FEXFUTBOL.

    Se procesan como mínimo las 5 primeras páginas.
    Se continúa hasta que no haya noticias o se alcance
    MAX_PAGES.
    """

    print(f"FEXFUTBOL: procesando {START_URL}")

    noticias_futbol_playa = []

    paginas_vistas = set()

    for pagina in range(1, MAX_PAGES + 1):

        # Como mínimo procesamos 5 páginas.
        # Después podemos terminar cuando una página esté vacía.
        url = construir_url_pagina(pagina)

        if url in paginas_vistas:
            print(
                f"FEXFUTBOL: URL repetida en página {pagina}, "
                f"deteniendo"
            )
            break

        paginas_vistas.add(url)

        print(
            f"FEXFUTBOL: procesando página "
            f"{pagina}: {url}"
        )

        try:
            noticias = obtener_noticias_pagina(url)

        except requests.RequestException as e:
            print(
                f"FEXFUTBOL: error descargando página "
                f"{pagina}: {e}"
            )

            # Si todavía no hemos llegado a las 5 páginas,
            # continuamos intentando las siguientes.
            if pagina < MIN_PAGES:
                continue

            break

        except Exception as e:
            print(
                f"FEXFUTBOL: error procesando página "
                f"{pagina}: {e}"
            )

            if pagina < MIN_PAGES:
                continue

            break

        if not noticias:

            print(
                f"FEXFUTBOL: no se encontraron noticias "
                f"en página {pagina}"
            )

            # Las 5 primeras páginas son obligatorias.
            if pagina >= MIN_PAGES:
                break

            continue

        encontradas_pagina = 0

        for noticia in noticias:

            if not es_futbol_playa(noticia["titulo"]):
                continue

            encontradas_pagina += 1
            noticias_futbol_playa.append(noticia)

            print(
                "FEXFUTBOL: fútbol playa -> "
                f"{noticia['titulo']}"
            )

        print(
            f"FEXFUTBOL: {encontradas_pagina} "
            f"noticias de fútbol playa en página {pagina}"
        )

    # Eliminar duplicados por URL.
    noticias_unicas = []
    urls = set()

    for noticia in noticias_futbol_playa:

        if noticia["url"] in urls:
            continue

        urls.add(noticia["url"])
        noticias_unicas.append(noticia)

    print(
        f"FEXFUTBOL: {len(noticias_unicas)} "
        f"noticias de fútbol playa encontradas en total"
    )

    return noticias_unicas


if __name__ == "__main__":
    noticias = obtener_noticias()

    print()
    print("=== NOTICIAS FÚTBOL PLAYA ===")

    for noticia in noticias:
        print(
            f"{noticia['fecha']} | "
            f"{noticia['titulo']} | "
            f"{noticia['url']}"
        )
