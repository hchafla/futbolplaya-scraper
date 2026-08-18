import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re


BASE_URL = "https://rfef.es"
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


# URLs que pertenecen a secciones/categorías y no a noticias individuales.
SLUGS_BLOQUEADOS = {
    "futbol-playa",
    "selecciones-de-futbol-playa",
    "futbol-sala",
    "institucional",
    "competiciones-masculinas",
    "competiciones-femeninas",
    "arbitros",
    "entrenadores",
    "formacion",
    "seleccion-absoluta",
    "selecciones-masculinas",
    "selecciones-femeninas",
    "e-sports",
    "leyendas",
    "grassroots",
    "area-medica",
    "proteccion-de-la-infancia",
}


TEXTOS_NO_TITULO = {
    "fútbol playa",
    "galería de imágenes en el interior",
    "cargar más",
}


def limpiar_texto(texto):
    return " ".join(texto.split()).strip()


def extraer_fecha(texto):
    """
    Busca fechas del tipo:

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

    return urljoin(BASE_URL, src)


def es_url_noticia(url):
    """
    Determina si una URL pertenece a una noticia individual de RFEF.

    Debe tener exactamente esta estructura:

    https://rfef.es/es/noticias/slug
    """

    parsed = urlparse(url)

    if parsed.netloc not in ("rfef.es", "www.rfef.es"):
        return False

    partes = [
        parte
        for parte in parsed.path.strip("/").split("/")
        if parte
    ]

    if len(partes) != 3:
        return False

    if partes[0] != "es":
        return False

    if partes[1] != "noticias":
        return False

    slug = partes[2].lower()

    if slug in SLUGS_BLOQUEADOS:
        return False

    return True


def encontrar_tarjeta(enlace):
    """
    Sube desde el enlace hasta encontrar el contenedor individual
    de la noticia.

    Se detiene si llega a elementos estructurales grandes para evitar
    capturar todo el listado de noticias como una única tarjeta.
    """

    actual = enlace

    for _ in range(5):

        if not actual.parent:
            break

        actual = actual.parent

        if actual.name in {
            "main",
            "body",
            "header",
            "nav",
            "footer",
            "section",
        }:
            break

        texto = limpiar_texto(
            actual.get_text(" ", strip=True)
        )

        fecha = extraer_fecha(texto)

        if fecha:
            return actual, fecha

    return None, None


def obtener_titulo(tarjeta, url):
    """
    Obtiene el título real de la noticia.

    La RFEF puede incluir dentro de la misma tarjeta:
    - enlace a la noticia
    - enlace a la galería
    - enlace a la categoría

    Por eso no basta con coger el primer <a> o el primer <h>.
    """

    candidatos = []

    for enlace in tarjeta.find_all("a", href=True):

        enlace_url = urljoin(
            BASE_URL,
            enlace.get("href", "")
        )

        if enlace_url != url:
            continue

        texto = limpiar_texto(
            enlace.get_text(" ", strip=True)
        )

        if not texto:
            continue

        texto_lower = texto.lower()

        if texto_lower in TEXTOS_NO_TITULO:
            continue

        candidatos.append(texto)

    # Preferimos el texto del enlace que apunta exactamente
    # a la noticia.
    if candidatos:

        # Normalmente el título real es el texto más largo.
        # Esto evita quedarnos con etiquetas secundarias.
        candidatos.sort(
            key=len,
            reverse=True
        )

        return candidatos[0]

    # Fallback: buscar encabezados.
    for etiqueta in tarjeta.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6"]
    ):

        texto = limpiar_texto(
            etiqueta.get_text(" ", strip=True)
        )

        if not texto:
            continue

        if texto.lower() in TEXTOS_NO_TITULO:
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

    noticias = []
    urls_vistas = set()

    # ---------------------------------------------------------
    # Recorremos la paginación de la etiqueta Fútbol playa.
    # ---------------------------------------------------------

    pagina = 0

    while True:

        if pagina == 0:
            url_pagina = URL
        else:
            url_pagina = f"{URL}?page={pagina}"

        print(f"RFEF: procesando {url_pagina}")

        response = requests.get(
            url_pagina,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # -----------------------------------------------------
        # Buscar el contenido principal.
        # -----------------------------------------------------

        contenedor_principal = (
            soup.find("main")
            or soup.find("div", role="main")
        )

        if not contenedor_principal:

            # Fallback por si cambia ligeramente el HTML.
            for etiqueta in soup.find_all(
                ["header", "nav", "footer"]
            ):
                etiqueta.decompose()

            contenedor_principal = soup

        enlaces_noticias_pagina = 0

        # -----------------------------------------------------
        # Buscar enlaces únicamente dentro de la página de
        # resultados de Fútbol playa.
        # -----------------------------------------------------

        for enlace in contenedor_principal.find_all(
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

            if not es_url_noticia(url):
                continue

            if url in urls_vistas:
                continue

            tarjeta, fecha = encontrar_tarjeta(enlace)

            if not tarjeta or not fecha:
                continue

            titulo = obtener_titulo(
                tarjeta,
                url
            )

            if not titulo:
                continue

            # Evitar cualquier falso positivo que haya conseguido
            # atravesar los filtros anteriores.
            if titulo.lower() in TEXTOS_NO_TITULO:
                continue

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
            enlaces_noticias_pagina += 1

        print(
            f"RFEF: {enlaces_noticias_pagina} noticias "
            f"nuevas en página {pagina}"
        )

        # -----------------------------------------------------
        # Si una página no aporta noticias nuevas, dejamos de
        # paginar.
        # -----------------------------------------------------

        if enlaces_noticias_pagina == 0:
            break

        pagina += 1

        # Medida de seguridad para evitar un bucle infinito
        # si la web cambia su paginación.
        if pagina > 50:
            print(
                "RFEF: límite de 50 páginas alcanzado."
            )
            break

    # ---------------------------------------------------------
    # Ordenar de más reciente a más antigua.
    # ---------------------------------------------------------

    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(
        f"RFEF: {len(noticias)} noticias encontradas en total"
    )

    return noticias
