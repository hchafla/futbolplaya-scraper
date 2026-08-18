import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from datetime import datetime
import re


BASE_URL = "https://www.fcf.cat"
URL = "https://www.fcf.cat/ca/noticies-fcf"


def limpiar_texto(texto):
    return " ".join(texto.split()).strip()


def extraer_fecha(texto):
    """
    Convierte una fecha FCF del tipo:

    22/07/2026

    en:

    2026-07-22
    """

    texto = limpiar_texto(texto)

    match = re.search(
        r"\b(\d{2})/(\d{2})/(\d{4})\b",
        texto
    )

    if not match:
        return None

    dia, mes, anio = match.groups()

    try:
        fecha = datetime.strptime(
            f"{dia}/{mes}/{anio}",
            "%d/%m/%Y"
        )

        return fecha.strftime("%Y-%m-%d")

    except ValueError:
        return None


def extraer_imagen(img):
    """
    Extrae la URL original de la imagen de FCF.

    La web utiliza Next.js y genera URLs como:

    /_next/image?url=https%3A%2F%2Ffiles.fcf.cat%2Fimg%2Fnoticies%2F...png&w=1200&q=75

    Nos interesa la imagen original de files.fcf.cat.
    """

    if not img:
        return None

    # Primero intentamos src
    src = img.get("src")

    if src:
        parsed = urlparse(src)

        if parsed.path == "/_next/image":

            parametros = parse_qs(parsed.query)

            if "url" in parametros:
                return unquote(parametros["url"][0])

        if src.startswith("http"):
            return src

    # Fallback a srcset
    srcset = img.get("srcset")

    if srcset:
        # Cogemos el último candidato, normalmente el de mayor resolución
        candidatos = [
            parte.strip().split(" ")[0]
            for parte in srcset.split(",")
            if parte.strip()
        ]

        if candidatos:

            src = candidatos[-1]

            parsed = urlparse(src)

            if parsed.path == "/_next/image":

                parametros = parse_qs(parsed.query)

                if "url" in parametros:
                    return unquote(parametros["url"][0])

            return urljoin(BASE_URL, src)

    return None


def es_noticia_fcf(url):
    """
    Comprueba que la URL tenga la estructura:

    https://www.fcf.cat/ca/noticies-fcf/1036803
    """

    parsed = urlparse(url)

    if parsed.netloc not in (
        "www.fcf.cat",
        "fcf.cat",
    ):
        return False

    partes = [
        parte
        for parte in parsed.path.strip("/").split("/")
        if parte
    ]

    if len(partes) != 3:
        return False

    if partes[0] != "ca":
        return False

    if partes[1] != "noticies-fcf":
        return False

    # El último componente debe ser numérico
    if not partes[2].isdigit():
        return False

    return True


def obtener_titulo(tarjeta):
    """
    El título de las tarjetas FCF está directamente en h3.
    """

    titulo = tarjeta.find("h3")

    if not titulo:
        return None

    texto = limpiar_texto(
        titulo.get_text(" ", strip=True)
    )

    return texto or None


def obtener_fecha(tarjeta):
    """
    Busca la fecha DD/MM/YYYY dentro de la tarjeta.
    """

    # Primero buscamos spans, que es donde aparece actualmente.
    for span in tarjeta.find_all("span"):

        texto = limpiar_texto(
            span.get_text(" ", strip=True)
        )

        fecha = extraer_fecha(texto)

        if fecha:
            return fecha

    # Fallback: buscar en todo el texto de la tarjeta.
    return extraer_fecha(
        tarjeta.get_text(" ", strip=True)
    )


def obtener_imagen(tarjeta):
    img = tarjeta.find("img")

    return extraer_imagen(img)


def scrape():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36"
        )
    }

    print(f"FCF: procesando {URL}")

    try:

        response = requests.get(
            URL,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

    except requests.RequestException as error:

        print(
            f"FCF: error al descargar la página: {error}"
        )

        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    noticias = []
    urls_vistas = set()

    # ---------------------------------------------------------
    # Las noticias están directamente en enlaces <a>.
    # ---------------------------------------------------------

    for enlace in soup.find_all(
        "a",
        href=True
    ):

        href = enlace.get("href", "").strip()

        if not href:
            continue

        url = urljoin(
            BASE_URL,
            href
        )

        if not es_noticia_fcf(url):
            continue

        if url in urls_vistas:
            continue

        # -----------------------------------------------------
        # Título
        # -----------------------------------------------------

        titulo = obtener_titulo(enlace)

        if not titulo:
            continue

        # -----------------------------------------------------
        # Fecha
        # -----------------------------------------------------

        fecha = obtener_fecha(enlace)

        if not fecha:
            continue

        # -----------------------------------------------------
        # Imagen
        # -----------------------------------------------------

        imagen = obtener_imagen(enlace)

        # -----------------------------------------------------
        # Guardar
        # -----------------------------------------------------

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha,
            "source": "FCF",
            "category": "Fútbol playa",
            "image": imagen,
        })

        urls_vistas.add(url)

    # ---------------------------------------------------------
    # Ordenar de más reciente a más antigua
    # ---------------------------------------------------------

    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(
        f"FCF: {len(noticias)} noticias encontradas"
    )

    return noticias
