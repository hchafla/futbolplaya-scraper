# ffib.py

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://www.ffib.es"

# OJO: esta web usa /Fed/ en vez de /pnfg/ (a diferencia del
# resto de federaciones con este mismo motor).
START_URL = (
    "https://www.ffib.es/Fed/NNws_LstNews"
    "?cod_primaria=5001212&cod_secundaria="
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}

# La web dice "Página 1/4" (46 registros). No hace falta
# filtrar por título: la sección ya viene pre-filtrada por la
# propia web ("Noticias Futbol Playa"), igual que RFAF.
MAX_PAGINAS = 6


def limpiar_texto(texto):
    return " ".join(texto.split()).strip()


def construir_url_pagina(pagina):
    """Construye la URL de una página concreta."""

    if pagina == 1:
        return START_URL

    return (
        f"{BASE_URL}/Fed/NNws_LstNews"
        f"?cod_primaria=5001212"
        f"&buscar="
        f"&cod_secundaria=5001212"
        f"&NPcd_PageAnt={pagina - 1}"
        f"&NPcd_PageNext={pagina + 1}"
        f"&NPcd_Page={pagina}"
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
    """Extrae las noticias de una página de FFIB."""

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
            "source": "FFIB",
            "category": "Fútbol Playa",
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
    Obtiene noticias de fútbol playa de la Federació de
    Futbol de les Illes Balears (FFIB).

    La sección ya viene pre-filtrada por categoría ("Noticias
    Futbol Playa"), así que no hace falta filtrar por título,
    igual que en rfaf.py. Se recorren como máximo MAX_PAGINAS
    páginas, manteniendo sesión (cookies) entre peticiones.
    """

    print(f"FFIB: procesando {START_URL}")

    noticias = []
    urls_vistas = set()

    with requests.Session() as sesion:

        for pagina in range(1, MAX_PAGINAS + 1):

            url = construir_url_pagina(pagina)

            print(f"FFIB: procesando página {pagina}: {url}")

            try:
                noticias_pagina = obtener_noticias_pagina(sesion, url)

            except requests.RequestException as e:

                print(f"FFIB: error descargando página {pagina}: {e}")
                break

            except Exception as e:

                print(f"FFIB: error procesando página {pagina}: {e}")
                break

            nuevas = 0

            for noticia in noticias_pagina:

                url_noticia = noticia.get("url")

                if not url_noticia or url_noticia in urls_vistas:
                    continue

                urls_vistas.add(url_noticia)

                noticias.append(noticia)

                nuevas += 1

            print(f"FFIB: {nuevas} noticias nuevas en página {pagina}")

            # Si una página no trae noticias nuevas, asumimos
            # que se acabaron los resultados.
            if nuevas == 0:
                break

    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(f"FFIB: {len(noticias)} noticias de fútbol playa encontradas en total")

    return noticias


if __name__ == "__main__":

    noticias = scrape()

    print()
    print("=== NOTICIAS FÚTBOL PLAYA (FFIB) ===")

    for noticia in noticias:

        print(
            f"{noticia['date']} | "
            f"{noticia['title']} | "
            f"{noticia['url']}"
        )
