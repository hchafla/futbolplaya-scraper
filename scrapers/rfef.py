import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
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


def es_url_noticia(url):
    """
    Determina si una URL tiene estructura de noticia individual.

    Las noticias de RFEF aparecen como:
        /es/noticias/nombre-de-la-noticia

    Las categorías/secciones suelen tener rutas adicionales:
        /es/noticias/futbol-sala/...
        /es/noticias/institucional/...
        /es/noticias/selecciones-de-futbol-playa/...
    """

    parsed = urlparse(url)

    if parsed.netloc != "rfef.es":
        return False

    partes = [
        parte
        for parte in parsed.path.strip("/").split("/")
        if parte
    ]

    # Debe ser exactamente:
    # es / noticias / slug
    if len(partes) != 3:
        return False

    if partes[0] != "es":
        return False

    if partes[1] != "noticias":
        return False

    return True


def encontrar_tarjeta(enlace):
    """
    Sube por los padres del enlace hasta encontrar el bloque
    que contiene título, fecha e imagen.
    """

    actual = enlace

    for _ in range(8):

        if not actual.parent:
            break

        actual = actual.parent

        texto = limpiar_texto(
            actual.get_text(" ", strip=True)
        )

        fecha = extraer_fecha(texto)

        if fecha:
            return actual, fecha

    return None, None


def obtener_titulo(tarjeta, url):
    """
    Busca el título dentro de la tarjeta.
    """

    # Primero intentamos encontrar encabezados.
    for etiqueta in tarjeta.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6"]
    ):
        texto = limpiar_texto(
            etiqueta.get_text(" ", strip=True)
        )

        if texto:
            return texto

    # Si no hay encabezado, buscamos el enlace de la propia noticia.
    for enlace in tarjeta.find_all("a", href=True):

        enlace_url = urljoin(URL, enlace.get("href", ""))

        if enlace_url != url:
            continue

        texto = limpiar_texto(
            enlace.get_text(" ", strip=True)
        )

        if texto:
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
    # Buscar enlaces que aparecen en la página de fútbol playa
    # ---------------------------------------------------------

    for enlace in soup.find_all("a", href=True):

        href = enlace.get("href", "").strip()

        if not href:
            continue

        url = urljoin(URL, href)

        # Solo aceptamos URLs de noticias individuales.
        if not es_url_noticia(url):
            continue

        # Evitar duplicados.
        if url in urls_vistas:
            continue

        # -----------------------------------------------------
        # Encontrar tarjeta de la noticia
        # -----------------------------------------------------

        tarjeta, fecha = encontrar_tarjeta(enlace)

        if not tarjeta or not fecha:
            continue

        # -----------------------------------------------------
        # Título
        # -----------------------------------------------------

        titulo = obtener_titulo(tarjeta, url)

        if not titulo:
            continue

        # -----------------------------------------------------
        # Evitar falsos positivos obvios
        # -----------------------------------------------------

        titulo_lower = titulo.lower()

        if titulo_lower in (
            "fútbol playa",
            "institucional",
            "presidencia",
            "juntas directivas",
            "igualdad",
            "responsabilidad social y sostenibilidad",
            "integridad",
            "protección de la infancia",
            "área médica",
            "labor federativa",
            "competiciones masculinas",
            "competiciones femeninas",
            "fútbol sala",
            "grassroots",
            "árbitros",
            "entrenadores",
            "formación",
            "selección absoluta",
            "selecciones masculinas",
            "selecciones femeninas",
            "selecciones de fútbol playa",
            "e-sports",
            "leyendas",
        ):
            continue

        # -----------------------------------------------------
        # Imagen
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
    # Ordenar
    # ---------------------------------------------------------

    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(f"RFEF: {len(noticias)} noticias encontradas")

    return noticias
