import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import re


BASE_URL = "https://ffcv.es"

URL = (
    "https://ffcv.es/wp/blog/category/"
    "noticias-arbitros/noticias-futbol-playa/"
)


def limpiar_texto(texto):
    if not texto:
        return ""

    return " ".join(texto.split()).strip()


def extraer_fecha(texto):
    """
    Busca fechas en formatos habituales de WordPress/FFCV.

    Ejemplos:
        18/08/2026
        18-08-2026
        18.08.2026
    """

    texto = limpiar_texto(texto)

    match = re.search(
        r"\b(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})\b",
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


def extraer_fecha_noticia(url, headers):
    """
    Descarga la noticia individual y busca su fecha.

    FFCV utiliza URLs del tipo:

    /wp/blog/2026/06/titulo-de-la-noticia/
    """

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

    except requests.RequestException:

        return None

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # ---------------------------------------------------------
    # Primero buscamos elementos habituales de fecha
    # ---------------------------------------------------------

    selectores = [
        ".post_date",
        ".meta_date",
        ".date",
        ".entry-date",
        "time",
    ]

    for selector in selectores:

        elemento = soup.select_one(
            selector
        )

        if elemento:

            fecha = extraer_fecha(
                elemento.get_text(
                    " ",
                    strip=True
                )
            )

            if fecha:
                return fecha

            # <time datetime="...">
            datetime_attr = elemento.get(
                "datetime"
            )

            if datetime_attr:

                match = re.search(
                    r"(\d{4})-(\d{2})-(\d{2})",
                    datetime_attr
                )

                if match:

                    anio, mes, dia = match.groups()

                    return (
                        f"{anio}-{mes}-{dia}"
                    )

    # ---------------------------------------------------------
    # Fallback: buscar fechas DD/MM/YYYY en toda la noticia
    # ---------------------------------------------------------

    texto = soup.get_text(
        " ",
        strip=True
    )

    fecha = extraer_fecha(
        texto
    )

    if fecha:
        return fecha

    # ---------------------------------------------------------
    # Último fallback: fecha de la URL
    #
    # /wp/blog/2026/06/titulo/
    # ---------------------------------------------------------

    match = re.search(
        r"/blog/(\d{4})/(\d{2})/",
        url
    )

    if match:

        anio, mes = match.groups()

        return f"{anio}-{mes}-01"

    return None


def extraer_imagen(enlace):
    """
    Extrae la imagen principal de la tarjeta.

    FFCV utiliza normalmente:

    <img src="https://ffcv.es/wp/wp-content/uploads/...">
    """

    img = enlace.find(
        "img"
    )

    if not img:
        return None

    # src normal
    src = img.get(
        "src"
    )

    if src:
        return urljoin(
            BASE_URL,
            src
        )

    # Fallback para lazy loading
    src = img.get(
        "data-src"
    )

    if src:
        return urljoin(
            BASE_URL,
            src
        )

    return None


def obtener_pagina(url, headers):
    """
    Descarga y analiza una página de la categoría.
    """

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

    except requests.RequestException as error:

        print(
            f"FFCV: error al descargar {url}: {error}"
        )

        return None

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


def extraer_noticias(soup):
    """
    Extrae las noticias del listado de FFCV.

    La estructura actual es:

    <li class="post latest_posts2-post">
        ...
        <h4 class="latest_posts2-title">
            <a href="...">Título</a>
        </h4>
        ...
    </li>
    """

    noticias = []

    elementos = soup.select(
        "li.latest_posts2-post"
    )

    for elemento in elementos:

        # -----------------------------------------------------
        # Enlace y título
        # -----------------------------------------------------

        enlace_titulo = elemento.select_one(
            "h4.latest_posts2-title a[href]"
        )

        if not enlace_titulo:
            continue

        href = enlace_titulo.get(
            "href"
        )

        if not href:
            continue

        url = urljoin(
            BASE_URL,
            href
        )

        titulo = limpiar_texto(
            enlace_titulo.get_text(
                " ",
                strip=True
            )
        )

        if not titulo:
            continue

        # -----------------------------------------------------
        # Imagen
        # -----------------------------------------------------

        imagen = extraer_imagen(
            elemento
        )

        noticias.append({
            "title": titulo,
            "url": url,
            "image": imagen,
        })

    return noticias


def encontrar_siguiente_pagina(soup):
    """
    Busca el enlace de siguiente página de WordPress.

    Se prueban varios patrones porque los temas de WordPress
    tienen la maravillosa costumbre de cambiar nombres de clases.
    """

    selectores = [
        "a.next",
        "a.nextpostslink",
        "a.page-numbers.next",
        "a[rel='next']",
        ".pagination a.next",
        ".pagination a.nextpostslink",
        ".wp-pagenavi a.nextpostslink",
    ]

    for selector in selectores:

        enlace = soup.select_one(
            selector
        )

        if enlace:

            href = enlace.get(
                "href"
            )

            if href:
                return urljoin(
                    BASE_URL,
                    href
                )

    # ---------------------------------------------------------
    # Fallback: buscar cualquier enlace cuyo texto indique
    # siguiente página.
    # ---------------------------------------------------------

    for enlace in soup.find_all(
        "a",
        href=True
    ):

        texto = limpiar_texto(
            enlace.get_text(
                " ",
                strip=True
            )
        ).lower()

        if texto in (
            "next",
            "siguiente",
            "›",
            "»",
            "→",
        ):

            return urljoin(
                BASE_URL,
                enlace["href"]
            )

    return None


def scrape():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
    }

    print(
        f"FFCV: procesando {URL}"
    )

    noticias = []

    urls_vistas = set()

    url_actual = URL

    pagina = 1

    while url_actual:

        print(
            f"FFCV: procesando página {pagina}: {url_actual}"
        )

        soup = obtener_pagina(
            url_actual,
            headers
        )

        if soup is None:
            break

        noticias_pagina = extraer_noticias(
            soup
        )

        if not noticias_pagina:

            print(
                f"FFCV: no se encontraron noticias "
                f"en página {pagina}"
            )

            break

        nuevas = 0

        # -----------------------------------------------------
        # Procesar noticias
        # -----------------------------------------------------

        for noticia in noticias_pagina:

            url = noticia["url"]

            if url in urls_vistas:
                continue

            print(
                f"FFCV: obteniendo fecha: "
                f"{noticia['title']}"
            )

            fecha = extraer_fecha_noticia(
                url,
                headers
            )

            if not fecha:

                print(
                    "FFCV: no se pudo obtener fecha, "
                    "se omite noticia"
                )

                continue

            noticia["date"] = fecha
            noticia["source"] = "FFCV"
            noticia["category"] = "Fútbol playa"

            noticias.append(
                noticia
            )

            urls_vistas.add(
                url
            )

            nuevas += 1

        print(
            f"FFCV: {nuevas} noticias nuevas "
            f"en página {pagina}"
        )

        # -----------------------------------------------------
        # Siguiente página
        # -----------------------------------------------------

        siguiente = encontrar_siguiente_pagina(
            soup
        )

        if not siguiente:
            break

        if siguiente in urls_vistas:
            break

        # Protección contra bucles
        if siguiente == url_actual:
            break

        url_actual = siguiente
        pagina += 1

        # Límite de seguridad
        if pagina > 100:
            print(
                "FFCV: límite de 100 páginas alcanzado."
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
        f"FFCV: {len(noticias)} noticias encontradas en total"
    )

    return noticias
