# rfgf.py

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus


BASE_URL = "https://futgal.es"

# La propia web filtra por título usando su buscador interno
# (clave="Fútbol Praia", checkbox "titulo" activado), así que
# no hace falta filtrar los resultados en el cliente, igual
# que en rfaf.py.
#
# OJO: esta web codifica los parámetros de búsqueda en
# Latin-1 (ISO-8859-1), no en UTF-8. Por eso "ú" se codifica
# como %FA y no como %C3%BA. Si se codifica en UTF-8 la
# búsqueda no devuelve resultados.
CLAVE_BUSQUEDA = "Fútbol Praia"

MAX_PAGINAS = 15


def limpiar_texto(texto):
    return " ".join(texto.split()).strip()


def construir_url_pagina(pagina):
    """Construye la URL de una página de resultados de búsqueda."""

    clave_codificada = quote_plus(
        CLAVE_BUSQUEDA,
        encoding="latin-1"
    )

    return (
        f"{BASE_URL}/pnfg/NNws_LstNews"
        f"?opcion=0"
        f"&codigo=0"
        f"&cod_primaria=5000289"
        f"&cod_secundaria=5000289"
        f"&buscar=1"
        f"&NPcd_PageAnt={pagina - 1}"
        f"&NPcd_PageNext={pagina + 1}"
        f"&NPcd_Page={pagina}"
        f"&clave={clave_codificada}"
        f"&titulo=1"
        f"&fecha_desde_input="
        f"&fecha_desde="
        f"&fecha_hasta_input="
        f"&fecha_hasta="
    )


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}


def extraer_fecha(texto):
    """Convierte una fecha DD/MM/YYYY a YYYY-MM-DD."""

    match = re.search(
        r"\b(\d{2})/(\d{2})/(\d{4})\b",
        texto
    )

    if not match:
        return None

    dia, mes, anio = match.groups()

    return f"{anio}-{mes}-{dia}"


def extraer_noticias(html):
    """Extrae las noticias de una página de resultados de RFGF."""

    soup = BeautifulSoup(html, "html.parser")

    noticias = []

    for item in soup.select("li.mt-list-item"):

        contenido = item.select_one("div.list-item-content")

        if not contenido:
            continue

        enlace = contenido.find("h3")

        enlace = enlace.find("a", href=True) if enlace else None

        if not enlace:
            continue

        titulo = limpiar_texto(
            enlace.get_text(" ", strip=True)
        )

        if not titulo:
            continue

        url = urljoin(BASE_URL, enlace.get("href"))

        # -------------------------------------------------
        # Fecha
        # -------------------------------------------------

        fecha = None

        fecha_div = item.select_one("div.list-datetime")

        if fecha_div:
            fecha = extraer_fecha(
                fecha_div.get_text(" ", strip=True)
            )

        if not fecha:
            continue

        # -------------------------------------------------
        # Imagen
        # -------------------------------------------------

        imagen = None

        img = item.select_one("div.list-thumb img")

        if img:

            src = img.get("src") or img.get("data-src")

            if src:
                imagen = urljoin(BASE_URL, src)

        # -------------------------------------------------
        # Resumen (normalmente viene vacío en esta web)
        # -------------------------------------------------

        resumen = ""

        p = contenido.find("p")

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
            "source": "RFGF",
            "category": "Fútbol Praia",
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
    Obtiene noticias de fútbol playa de la Real Federación
    Galega de Fútbol (RFGF), usando el buscador propio de la
    web filtrado por título ("Fútbol Praia"). No hace falta
    filtrar en el cliente porque el servidor ya devuelve solo
    resultados relevantes.
    """

    url_pagina_1 = construir_url_pagina(1)

    print(f"RFGF: procesando {url_pagina_1}")

    noticias = []
    urls_vistas = set()

    for pagina in range(1, MAX_PAGINAS + 1):

        url = construir_url_pagina(pagina)

        print(f"RFGF: procesando página {pagina}: {url}")

        try:
            noticias_pagina = obtener_noticias_pagina(url)

        except requests.RequestException as e:

            print(f"RFGF: error descargando página {pagina}: {e}")
            break

        except Exception as e:

            print(f"RFGF: error procesando página {pagina}: {e}")
            break

        nuevas = 0

        for noticia in noticias_pagina:

            url_noticia = noticia.get("url")

            if not url_noticia or url_noticia in urls_vistas:
                continue

            urls_vistas.add(url_noticia)

            noticias.append(noticia)

            nuevas += 1

        print(f"RFGF: {nuevas} noticias nuevas en página {pagina}")

        # Al ser una búsqueda ya filtrada por el servidor, si
        # una página no trae noticias nuevas asumimos que se
        # acabaron los resultados.
        if nuevas == 0:
            break

    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(f"RFGF: {len(noticias)} noticias de fútbol playa encontradas en total")

    return noticias


if __name__ == "__main__":

    noticias = scrape()

    print()
    print("=== NOTICIAS FÚTBOL PLAYA (RFGF) ===")

    for noticia in noticias:

        print(
            f"{noticia['date']} | "
            f"{noticia['title']} | "
            f"{noticia['url']}"
        )
