import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


URL = "https://rfef.es/es/noticias/futbol-playa"


MESES = {
    "enero": "01",
    "febrero": "02",
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "octubre": "10",
    "noviembre": "11",
    "diciembre": "12",
}


def limpiar_texto(texto):
    return " ".join(texto.split()).strip()


def extraer_fecha(texto):
    """
    Busca fechas como:
    11 Agosto 2026
    10 Agosto 2026
    """

    texto = limpiar_texto(texto).lower()

    patron = (
        r"\b(\d{1,2})\s+"
        r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
        r"septiembre|octubre|noviembre|diciembre)\s+"
        r"(\d{4})\b"
    )

    match = re.search(patron, texto)

    if not match:
        return None

    dia = int(match.group(1))
    mes = MESES[match.group(2)]
    anio = match.group(3)

    return f"{anio}-{mes}-{dia:02d}"


def obtener_imagen(contenedor):
    imagen = contenedor.find("img")

    if not imagen:
        return None

    src = (
        imagen.get("src")
        or imagen.get("data-src")
        or imagen.get("data-lazy-src")
    )

    if not src:
        return None

    return urljoin(URL, src)


def obtener_titulo(contenedor):
    """
    Obtiene el título real de la noticia.
    """

    # El título suele estar dentro del enlace principal
    # de la noticia.
    enlaces = contenedor.find_all("a", href=True)

    for enlace in enlaces:

        href = enlace.get("href", "")

        if "/es/noticias/" not in href:
            continue

        texto = limpiar_texto(
            enlace.get_text(" ", strip=True)
        )

        if not texto:
            continue

        # Evitamos enlaces de categorías
        # que aparecen dentro del bloque de la noticia.
        if texto.lower() == "fútbol playa":
            continue

        if texto.lower() == "galería de imágenes en el interior":
            continue

        return texto

    return None


def scrape():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36"
        )
    }

    response = requests.get(
        URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    noticias = []
    urls_vistas = set()

    # ---------------------------------------------------------
    # 1. Localizar el bloque de resultados
    # ---------------------------------------------------------

    texto_resultados = soup.find(
        string=re.compile(
            r"Resultados de Fútbol playa",
            re.IGNORECASE
        )
    )

    if not texto_resultados:
        print("No se encontró el bloque de resultados de RFEF.")
        return []

    # Subimos hasta encontrar un contenedor suficientemente
    # grande que contenga el listado de resultados.
    contenedor_resultados = texto_resultados.parent

    for _ in range(8):

        if not contenedor_resultados.parent:
            break

        enlaces = contenedor_resultados.find_all(
            "a",
            href=True
        )

        # El listado de resultados actual contiene bastantes
        # enlaces, mientras que el nodo inicial no.
        if len(enlaces) >= 10:
            break

        contenedor_resultados = contenedor_resultados.parent

    # ---------------------------------------------------------
    # 2. Buscar noticias SOLO dentro de ese bloque
    # ---------------------------------------------------------

    enlaces = contenedor_resultados.find_all(
        "a",
        href=True
    )

    for enlace in enlaces:

        href = enlace.get("href", "")

        if not href:
            continue

        url = urljoin(URL, href)

        # Tiene que ser una URL de noticia
        if "/es/noticias/" not in url:
            continue

        # No queremos categorías que estén dentro del listado
        # como enlaces secundarios.
        texto_enlace = limpiar_texto(
            enlace.get_text(" ", strip=True)
        )

        if texto_enlace.lower() in (
            "fútbol playa",
            "galería de imágenes en el interior",
            "cargar más",
        ):
            continue

        # -----------------------------------------------------
        # 3. Encontrar el contenedor individual de la noticia
        # -----------------------------------------------------

        tarjeta = enlace

        for _ in range(6):

            if not tarjeta.parent:
                break

            tarjeta = tarjeta.parent

            texto_tarjeta = limpiar_texto(
                tarjeta.get_text(" ", strip=True)
            )

            fecha = extraer_fecha(texto_tarjeta)

            if fecha:
                break
        else:
            fecha = None

        # Si no tiene fecha, no es una noticia.
        if not fecha:
            continue

        # Evitar duplicados
        if url in urls_vistas:
            continue

        # -----------------------------------------------------
        # 4. Título
        # -----------------------------------------------------

        titulo = obtener_titulo(tarjeta)

        if not titulo:
            continue

        # -----------------------------------------------------
        # 5. Imagen
        # -----------------------------------------------------

        imagen = obtener_imagen(tarjeta)

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha,
            "source": "RFEF",
            "category": "Fútbol playa",
            "image": imagen,
        })

        urls_vistas.add(url)

    # ---------------------------------------------------------
    # 6. Ordenar
    # ---------------------------------------------------------

    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    return noticias
