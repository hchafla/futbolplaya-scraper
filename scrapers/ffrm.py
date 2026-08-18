import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import unicodedata


BASE_URL = "https://www.ffrm.es"

URL_BASE = (
    "https://www.ffrm.es/pnfg/NNws_LstNews"
)

COD_PRIMARIA = "1000057"
COD_SECUNDARIA = "1000057"


def limpiar_texto(texto):
    if not texto:
        return ""

    return " ".join(texto.split()).strip()


def normalizar_texto(texto):
    """
    Normaliza el texto para poder comparar sin tener en cuenta
    mayúsculas/minúsculas ni acentos.

    Ejemplo:
        "Fútbol Playa" -> "futbol playa"
    """

    texto = limpiar_texto(texto).lower()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return texto


def contiene_futbol_playa(titulo):
    """
    Comprueba si el título contiene exactamente la expresión
    "futbol playa", ignorando mayúsculas y acentos.
    """

    titulo_normalizado = normalizar_texto(
        titulo
    )

    return "futbol playa" in titulo_normalizado


def extraer_fecha(texto):
    """
    Extrae fechas en formato DD/MM/YYYY.
    """

    texto = limpiar_texto(texto)

    import re

    match = re.search(
        r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b",
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

        return fecha.strftime(
            "%Y-%m-%d"
        )

    except ValueError:

        return None


def construir_url_pagina(pagina):
    """
    Construye directamente la URL de cada página.

    FFRM utiliza:
        NPcd_PageAnt
        NPcd_PageNext
        NPcd_Page

    No necesitamos ejecutar elegirPag().
    """

    pagina_anterior = max(
        pagina - 1,
        0
    )

    pagina_siguiente = pagina + 1

    parametros = (
        f"?cod_primaria={COD_PRIMARIA}"
        f"&buscar="
        f"&cod_secundaria={COD_SECUNDARIA}"
        f"&NPcd_PageAnt={pagina_anterior}"
        f"&NPcd_PageNext={pagina_siguiente}"
        f"&NPcd_Page={pagina}"
    )

    return URL_BASE + parametros


def obtener_pagina(url, headers):
    """
    Descarga una página de noticias.
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
            f"FFRM: error al descargar {url}: {error}"
        )

        return None

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


def extraer_noticias(soup):
    """
    Extrae todas las noticias de la página.

    La estructura observada por FFRM es:

        table.table
            tr
                td.td_not
                    h3
                        a.titulo_noticia
                    span fecha
                    img

    Después filtramos únicamente aquellas cuyo título
    contiene "fútbol playa".
    """

    noticias = []

    elementos = soup.select(
        "td.td_not"
    )

    for elemento in elementos:

        # -----------------------------------------------------
        # Título y enlace
        # -----------------------------------------------------

        enlace = elemento.select_one(
            "a.titulo_noticia[href]"
        )

        if not enlace:
            continue

        titulo = limpiar_texto(
            enlace.get_text(
                " ",
                strip=True
            )
        )

        if not titulo:
            continue

        # -----------------------------------------------------
        # FILTRO FÚTBOL PLAYA
        # -----------------------------------------------------

        if not contiene_futbol_playa(
            titulo
        ):
            continue

        href = enlace.get(
            "href"
        )

        if not href:
            continue

        url = urljoin(
            BASE_URL,
            href
        )

        # -----------------------------------------------------
        # Fecha
        # -----------------------------------------------------

        fecha_elemento = elemento.select_one(
            "span"
        )

        fecha = None

        if fecha_elemento:

            fecha = extraer_fecha(
                fecha_elemento.get_text(
                    " ",
                    strip=True
                )
            )

        # -----------------------------------------------------
        # Imagen
        # -----------------------------------------------------

        imagen = None

        img = elemento.select_one(
            "img[src]"
        )

        if img:

            src = img.get(
                "src"
            )

            if src:

                imagen = urljoin(
                    BASE_URL,
                    src
                )

        # -----------------------------------------------------
        # Guardar
        # -----------------------------------------------------

        noticias.append({
            "title": titulo,
            "url": url,
            "image": imagen,
            "date": fecha,
            "source": "FFRM",
            "category": "Fútbol playa"
        })

    return noticias


def obtener_total_paginas(soup):
    """
    Intenta obtener el número total de páginas a partir
    del texto:

        Página 1/87, Total registros: 1296
    """

    import re

    texto = soup.get_text(
        " ",
        strip=True
    )

    match = re.search(
        r"Página\s+\d+\s*/\s*(\d+)",
        texto,
        re.IGNORECASE
    )

    if match:

        try:
            return int(
                match.group(1)
            )
        except ValueError:
            pass

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
        f"FFRM: procesando {URL_BASE}"
    )

    noticias = []

    urls_vistas = set()

    pagina = 1

    total_paginas = None

    while True:

        url = construir_url_pagina(
            pagina
        )

        print(
            f"FFRM: procesando página {pagina}: {url}"
        )

        soup = obtener_pagina(
            url,
            headers
        )

        if soup is None:
            break

        # -----------------------------------------------------
        # Primera página: obtener total de páginas
        # -----------------------------------------------------

        if pagina == 1:

            total_paginas = obtener_total_paginas(
                soup
            )

            if total_paginas:

                print(
                    f"FFRM: {total_paginas} páginas "
                    f"en total"
                )

        # -----------------------------------------------------
        # Extraer noticias
        # -----------------------------------------------------

        noticias_pagina = extraer_noticias(
            soup
        )

        print(
            f"FFRM: {len(noticias_pagina)} "
            f"noticias de fútbol playa "
            f"en página {pagina}"
        )

        # -----------------------------------------------------
        # Añadir evitando duplicados
        # -----------------------------------------------------

        nuevas = 0

        for noticia in noticias_pagina:

            url_noticia = noticia["url"]

            if url_noticia in urls_vistas:
                continue

            urls_vistas.add(
                url_noticia
            )

            noticias.append(
                noticia
            )

            nuevas += 1

        # -----------------------------------------------------
        # Fin de paginación
        # -----------------------------------------------------

        if total_paginas:

            if pagina >= total_paginas:
                break

        else:

            # Si no hemos podido detectar el total,
            # paramos cuando una página venga vacía.
            if not noticias_pagina:
                break

        pagina += 1

        # Protección de seguridad
        if pagina > 200:

            print(
                "FFRM: límite de 200 páginas alcanzado."
            )

            break

    # ---------------------------------------------------------
    # Ordenar por fecha
    # ---------------------------------------------------------

    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(
        f"FFRM: {len(noticias)} noticias de "
        f"fútbol playa encontradas en total"
    )

    return noticias
