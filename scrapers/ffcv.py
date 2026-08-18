import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import re


BASE_URL = "https://ffcv.es"
URL = "https://ffcv.es/wp/futbol-playa/"


def limpiar_texto(texto):
    if not texto:
        return ""

    return " ".join(texto.split()).strip()


def extraer_fecha(url, headers):
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

    except requests.RequestException as error:
        print(
            f"FFCV: error obteniendo fecha de {url}: {error}"
        )
        return None

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # ---------------------------------------------------------
    # <time datetime="2026-06-28T...">
    # ---------------------------------------------------------

    for time in soup.find_all("time"):

        datetime_attr = time.get("datetime")

        if datetime_attr:

            match = re.search(
                r"(\d{4})-(\d{2})-(\d{2})",
                datetime_attr
            )

            if match:

                anio, mes, dia = match.groups()

                return f"{anio}-{mes}-{dia}"

        fecha = time.get_text(
            " ",
            strip=True
        )

        match = re.search(
            r"\b(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})\b",
            fecha
        )

        if match:

            dia, mes, anio = match.groups()

            try:

                return datetime.strptime(
                    f"{dia}/{mes}/{anio}",
                    "%d/%m/%Y"
                ).strftime("%Y-%m-%d")

            except ValueError:
                pass

    # ---------------------------------------------------------
    # Buscar fecha DD/MM/YYYY en la página
    # ---------------------------------------------------------

    texto = soup.get_text(
        " ",
        strip=True
    )

    match = re.search(
        r"\b(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})\b",
        texto
    )

    if match:

        dia, mes, anio = match.groups()

        try:

            return datetime.strptime(
                f"{dia}/{mes}/{anio}",
                "%d/%m/%Y"
            ).strftime("%Y-%m-%d")

        except ValueError:
            pass

    # ---------------------------------------------------------
    # Fallback: fecha incluida en la URL
    #
    # /blog/2026/06/titulo/
    # ---------------------------------------------------------

    match = re.search(
        r"/blog/(\d{4})/(\d{2})/",
        url
    )

    if match:

        anio, mes = match.groups()

        return f"{anio}-{mes}-01"

    return None


def extraer_imagen(elemento):
    """
    FFCV utiliza lazy loading.

    Puede aparecer como:

        data-src
        src
        data-lazy-src
        srcset
        data-srcset

    Se intenta siempre obtener la URL real de la imagen.
    """

    img = elemento.find("img")

    if not img:
        return None

    # ---------------------------------------------------------
    # Prioridad: atributos que contienen la imagen real
    # ---------------------------------------------------------

    atributos = [
        "data-src",
        "data-lazy-src",
        "data-original",
        "src",
    ]

    for atributo in atributos:

        valor = img.get(atributo)

        if not valor:
            continue

        valor = valor.strip()

        if not valor:
            continue

        # Evitar placeholders
        if (
            "placeholder" in valor.lower()
            or valor.startswith("data:image")
        ):
            continue

        return urljoin(
            BASE_URL,
            valor
        )

    # ---------------------------------------------------------
    # srcset
    # ---------------------------------------------------------

    for atributo in (
        "data-srcset",
        "srcset",
    ):

        srcset = img.get(atributo)

        if not srcset:
            continue

        candidatos = []

        for parte in srcset.split(","):

            parte = parte.strip()

            if not parte:
                continue

            url = parte.split()[0]

            if url:
                candidatos.append(url)

        if candidatos:

            return urljoin(
                BASE_URL,
                candidatos[-1]
            )

    return None


def extraer_noticias(soup):

    noticias = []

    # ---------------------------------------------------------
    # Estructura actual de la página de Fútbol Playa
    # ---------------------------------------------------------

    elementos = soup.select(
        "li.latest_posts2-post"
    )

    for elemento in elementos:

        enlace = elemento.select_one(
            "h4.latest_posts2-title a[href]"
        )

        if not enlace:
            continue

        url = enlace.get(
            "href"
        )

        if not url:
            continue

        url = urljoin(
            BASE_URL,
            url
        )

        titulo = limpiar_texto(
            enlace.get_text(
                " ",
                strip=True
            )
        )

        if not titulo:
            continue

        imagen = extraer_imagen(
            elemento
        )

        noticias.append({
            "title": titulo,
            "url": url,
            "image": imagen,
        })

    return noticias


def scrape():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36"
        ),
        "Accept-Language": (
            "es-ES,es;q=0.9,en;q=0.8"
        ),
    }

    print(
        f"FFCV: procesando {URL}"
    )

    try:

        response = requests.get(
            URL,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

    except requests.RequestException as error:

        print(
            f"FFCV: error al descargar la página: {error}"
        )

        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    noticias_base = extraer_noticias(
        soup
    )

    if not noticias_base:

        print(
            "FFCV: no se encontraron noticias"
        )

        return []

    print(
        f"FFCV: {len(noticias_base)} noticias encontradas "
        "en el listado"
    )

    noticias = []

    urls_vistas = set()

    for noticia in noticias_base:

        url = noticia["url"]

        if url in urls_vistas:
            continue

        print(
            f"FFCV: procesando: "
            f"{noticia['title']}"
        )

        fecha = extraer_fecha(
            url,
            headers
        )

        if not fecha:

            print(
                "FFCV: no se pudo obtener la fecha"
            )

            continue

        imagen = noticia.get(
            "image"
        )

        # -----------------------------------------------------
        # Mostrar la imagen detectada para poder comprobarla
        # -----------------------------------------------------

        if imagen:

            print(
                f"FFCV: imagen: {imagen}"
            )

        else:

            print(
                "FFCV: imagen: NO ENCONTRADA"
            )

        noticias.append({
            "title": noticia["title"],
            "url": url,
            "date": fecha,
            "source": "FFCV",
            "category": "Fútbol playa",
            "image": imagen,
        })

        urls_vistas.add(
            url
        )

    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(
        f"FFCV: {len(noticias)} noticias encontradas en total"
    )

    return noticias
