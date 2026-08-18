import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


BASE_URL = "https://rfaf.es"

URL = (
    "https://rfaf.es/pnfg/NNws_LstNews"
    "?cod_primaria=140&cod_secundaria=5002366"
)


def limpiar_texto(texto):
    return " ".join(texto.split()).strip()


def extraer_fecha(texto):
    """
    Convierte una fecha de RFAF del tipo:

    12/08/2026

    a:

    2026-08-12
    """

    texto = limpiar_texto(texto)

    match = re.search(
        r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b",
        texto
    )

    if not match:
        return None

    dia = int(match.group(1))
    mes = int(match.group(2))
    anio = int(match.group(3))

    return f"{anio:04d}-{mes:02d}-{dia:02d}"


def obtener_imagen(noticia):
    """
    Obtiene la imagen principal de la noticia desde el <img>.
    """

    imagen = noticia.find("img")

    if not imagen:
        return None

    src = (
        imagen.get("src")
        or imagen.get("data-src")
        or imagen.get("data-lazy-src")
    )

    if not src:
        return None

    return urljoin(BASE_URL, src)


def extraer_noticias_pagina(soup):
    """
    Extrae las noticias del listado de RFAF.

    La estructura actual utiliza:

    <table class="table">
        <td class="td_not">
            ...
            <a class="titulo_noticia">Título</a>
            ...
            <span>12/08/2026 ...</span>
            ...
            <img src="...">
    """

    noticias = []

    tabla = soup.find("table", class_="table")

    if not tabla:
        print("RFAF: no se encontró la tabla de noticias.")
        return noticias

    for noticia in tabla.find_all(
        "td",
        class_="td_not"
    ):

        enlace_titulo = noticia.find(
            "a",
            class_="titulo_noticia",
            href=True
        )

        if not enlace_titulo:
            continue

        titulo = limpiar_texto(
            enlace_titulo.get_text(" ", strip=True)
        )

        if not titulo:
            continue

        url = urljoin(
            BASE_URL,
            enlace_titulo.get("href", "")
        )

        # Buscar la fecha dentro de la tarjeta.
        texto_tarjeta = noticia.get_text(
            " ",
            strip=True
        )

        fecha = extraer_fecha(texto_tarjeta)

        if not fecha:
            continue

        imagen = obtener_imagen(noticia)

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha,
            "source": "RFAF",
            "category": "Fútbol playa",
            "image": imagen,
        })

    return noticias


def obtener_siguiente_pagina(soup, pagina_actual):
    """
    Intenta localizar un enlace de paginación para la siguiente página.

    Si RFAF no muestra paginación o cambia su estructura,
    devuelve None y el scraper termina normalmente.
    """

    # Buscar enlaces cuyo texto indique siguiente página.
    textos_siguiente = {
        "siguiente",
        "siguiente >",
        ">",
        "next",
        "next page",
    }

    for enlace in soup.find_all("a", href=True):

        texto = limpiar_texto(
            enlace.get_text(" ", strip=True)
        ).lower()

        if texto in textos_siguiente:
            return urljoin(
                BASE_URL,
                enlace.get("href")
            )

    # Algunas versiones de la web utilizan parámetros
    # numéricos en la paginación. Si no encontramos un
    # enlace explícito, no inventamos la URL.
    return None


def scrape():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36"
        )
    }

    noticias = []
    urls_vistas = set()

    url_actual = URL
    pagina = 1

    while url_actual:

        print(
            f"RFAF: procesando página {pagina}: "
            f"{url_actual}"
        )

        try:
            response = requests.get(
                url_actual,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()

        except requests.RequestException as error:
            print(
                f"RFAF: error al descargar la página: {error}"
            )
            break

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        noticias_pagina = extraer_noticias_pagina(
            soup
        )

        nuevas = 0

        for noticia in noticias_pagina:

            url = noticia.get("url")

            if not url:
                continue

            if url in urls_vistas:
                continue

            urls_vistas.add(url)
            noticias.append(noticia)
            nuevas += 1

        print(
            f"RFAF: {nuevas} noticias nuevas "
            f"en página {pagina}"
        )

        # Si la página no contiene noticias nuevas,
        # evitamos continuar indefinidamente.
        if nuevas == 0:
            break

        siguiente = obtener_siguiente_pagina(
            soup,
            pagina
        )

        if not siguiente or siguiente == url_actual:
            break

        url_actual = siguiente
        pagina += 1

        # Medida de seguridad.
        if pagina > 50:
            print(
                "RFAF: límite de 50 páginas alcanzado."
            )
            break

    # Ordenar de más reciente a más antigua.
    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(
        f"RFAF: {len(noticias)} noticias encontradas en total"
    )

    return noticias
