import requests
from urllib.parse import urljoin
from datetime import datetime


BASE_URL = "https://www.fcf.cat"

API_URL = (
    "https://www.fcf.cat/api/news/list/1"
    "?page={page}&categories=3000208"
)

NOTICIA_BASE_URL = "https://www.fcf.cat/ca/noticies-fcf/"


def limpiar_texto(texto):
    if not texto:
        return ""

    return " ".join(str(texto).split()).strip()


def convertir_fecha(fecha):
    """
    Convierte:

    2026-07-22T09:37:40.000Z

    en:

    2026-07-22
    """

    if not fecha:
        return None

    try:
        fecha_dt = datetime.fromisoformat(
            fecha.replace("Z", "+00:00")
        )

        return fecha_dt.strftime("%Y-%m-%d")

    except (ValueError, TypeError):
        return None


def construir_url_noticia(noticia):
    """
    La API devuelve NOTICIA_URL con esta estructura:

    alba-arija-.../22/07/2026

    La URL pública es:

    https://www.fcf.cat/ca/noticies-fcf/alba-arija-.../22/07/2026
    """

    noticia_url = noticia.get("NOTICIA_URL")

    if not noticia_url:
        return None

    noticia_url = str(noticia_url).strip()

    if noticia_url.startswith("http"):
        return noticia_url

    return urljoin(
        NOTICIA_BASE_URL,
        noticia_url
    )


def extraer_imagen(noticia):
    """
    La API proporciona IMAGEHOME con la URL original.

    Ejemplo:

    https://files.fcf.cat/img/noticies/....png
    """

    imagen = noticia.get("IMAGEHOME")

    if not imagen:
        return None

    imagen = str(imagen).strip()

    if not imagen:
        return None

    return imagen


def convertir_noticia(noticia):
    """
    Convierte una noticia de la API FCF al formato utilizado
    por el resto del scraper.
    """

    titulo = limpiar_texto(
        noticia.get("TITULO")
    )

    if not titulo:
        return None

    url = construir_url_noticia(
        noticia
    )

    if not url:
        return None

    fecha = convertir_fecha(
        noticia.get("FECHA")
    )

    if not fecha:
        return None

    imagen = extraer_imagen(
        noticia
    )

    return {
        "title": titulo,
        "url": url,
        "date": fecha,
        "source": "FCF",
        "category": "Fútbol playa",
        "image": imagen,
    }


def descargar_pagina(page, headers):
    """
    Descarga una página de la API FCF.

    Devuelve:

    - lista de noticias
    - número total de noticias indicado por la API
    """

    url = API_URL.format(
        page=page
    )

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        datos = response.json()

    except requests.RequestException as error:

        print(
            f"FCF: error al descargar página {page}: {error}"
        )

        return [], None

    except ValueError as error:

        print(
            f"FCF: respuesta JSON inválida en página {page}: {error}"
        )

        return [], None

    noticias_api = datos.get(
        "data",
        []
    )

    meta = datos.get(
        "meta",
        {}
    )

    total = meta.get(
        "total"
    )

    noticias = []

    for noticia_api in noticias_api:

        noticia = convertir_noticia(
            noticia_api
        )

        if noticia:
            noticias.append(
                noticia
            )

    return noticias, total


def scrape():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Referer": "https://www.fcf.cat/ca/noticies-fcf",
    }

    print(
        "FCF: procesando API de noticias de fútbol playa"
    )

    noticias = []

    urls_vistas = set()

    page = 1
    total_api = None

    while True:

        print(
            f"FCF: procesando página {page}"
        )

        nuevas_noticias, total = descargar_pagina(
            page,
            headers
        )

        # Si es la primera página guardamos el total.
        if total_api is None and total is not None:
            total_api = total

            print(
                f"FCF: la API indica {total_api} noticias"
            )

        # Si la API no devuelve datos, hemos terminado.
        if not nuevas_noticias:

            print(
                f"FCF: página {page} sin noticias. "
                "Fin de la paginación."
            )

            break

        nuevas = 0

        for noticia in nuevas_noticias:

            url = noticia.get("url")

            if not url:
                continue

            if url in urls_vistas:
                continue

            noticias.append(
                noticia
            )

            urls_vistas.add(
                url
            )

            nuevas += 1

        print(
            f"FCF: {nuevas} noticias nuevas en página {page}"
        )

        # -----------------------------------------------------
        # Si ya hemos alcanzado el total indicado por la API,
        # no necesitamos seguir haciendo peticiones.
        # -----------------------------------------------------

        if total_api is not None and len(noticias) >= total_api:

            print(
                "FCF: total de noticias alcanzado."
            )

            break

        page += 1

        # -----------------------------------------------------
        # Protección por si la API se comporta mal y empieza
        # a devolver siempre las mismas páginas.
        # -----------------------------------------------------

        if page > 1000:

            print(
                "FCF: límite de seguridad de 1000 páginas alcanzado."
            )

            break

    # ---------------------------------------------------------
    # Ordenar de más reciente a más antigua
    # ---------------------------------------------------------

    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(
        f"FCF: {len(noticias)} noticias encontradas en total"
    )

    return noticias
