import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import re


BASE_URL = "https://www.ffcm.es"

URL_BASE = (
    "https://www.ffcm.es/pnfg/NNws_LstNews"
)

COD_PRIMARIA = "5000210"
COD_SECUNDARIA = "5000210"


def limpiar_texto(texto):
    if not texto:
        return ""

    return " ".join(texto.split()).strip()


def extraer_fecha(texto):
    """
    Extrae fechas en formato:

    DD/MM/YYYY
    DD-MM-YYYY
    DD.MM.YYYY
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
            f"FFCM: error obteniendo noticia {url}: {error}"
        )

        return None

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # ---------------------------------------------------------
    # Selectores habituales
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

        if not elemento:
            continue

        fecha = extraer_fecha(
            elemento.get_text(
                " ",
                strip=True
            )
        )

        if fecha:
            return fecha

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
    # Buscar fecha en toda la página
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
    # Último recurso: buscar fecha en la URL
    # ---------------------------------------------------------

    match = re.search(
        r"/(\d{4})/(\d{2})/",
        url
    )

    if match:

        anio, mes = match.groups()

        return f"{anio}-{mes}-01"

    return None


def extraer_imagen(elemento):
    """
    Extrae la imagen de la noticia.
    """

    img = elemento.find(
        "img"
    )

    if not img:
        return None

    # ---------------------------------------------------------
    # src normal
    # ---------------------------------------------------------

    src = img.get(
        "src"
    )

    if src:
        return urljoin(
            BASE_URL,
            src
        )

    # ---------------------------------------------------------
    # Lazy loading
    # ---------------------------------------------------------

    for atributo in (
        "data-src",
        "data-lazy-src",
        "data-original",
    ):

        src = img.get(
            atributo
        )

        if src:
            return urljoin(
                BASE_URL,
                src
            )

    return None


def construir_url_pagina(pagina):
    """
    Construye directamente la URL de una página concreta.

    La FFCM utiliza:

    NPcd_PageAnt
    NPcd_PageNext
    NPcd_Page
    """

    if pagina == 1:

        return (
            f"{URL_BASE}"
            f"?cod_primaria={COD_PRIMARIA}"
            f"&cod_secundaria="
        )

    pagina_anterior = pagina - 1
    pagina_siguiente = pagina + 1

    return (
        f"{URL_BASE}"
        f"?cod_primaria={COD_PRIMARIA}"
        f"&buscar="
        f"&cod_secundaria={COD_SECUNDARIA}"
        f"&NPcd_PageAnt={pagina_anterior}"
        f"&NPcd_PageNext={pagina_siguiente}"
        f"&NPcd_Page={pagina}"
    )


def obtener_pagina(url, headers):
    """
    Descarga una página del listado.
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
            f"FFCM: error al descargar {url}: {error}"
        )

        return None

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


def obtener_total_paginas(soup):
    """
    Busca el número total de páginas.

    Ejemplo:

    Página 2/10, Total registros: 140
    """

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


def extraer_noticias(soup):
    """
    Extrae las noticias del listado FFCM.

    La estructura es:

    <td class="td_not">
        ...
        <a class="titulo_noticia">
            Título
        </a>
        ...
    """

    noticias = []

    elementos = soup.select(
        "td.td_not"
    )

    for elemento in elementos:

        # -----------------------------------------------------
        # Título y URL
        # -----------------------------------------------------

        enlace_titulo = elemento.select_one(
            "a.titulo_noticia[href]"
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

        # -----------------------------------------------------
        # Fecha
        #
        # En FFCM la fecha aparece directamente en el listado:
        #
        # 21/08/2025 Autor: FFCM
        # -----------------------------------------------------

        fecha = None

        texto_elemento = elemento.get_text(
            " ",
            strip=True
        )

        fecha = extraer_fecha(
            texto_elemento
        )

        noticias.append({
            "title": titulo,
            "url": url,
            "image": imagen,
            "date": fecha,
            "source": "FFCM",
            "category": "Fútbol playa",
        })

    return noticias


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
        f"FFCM: procesando {construir_url_pagina(1)}"
    )

    noticias = []

    urls_vistas = set()

    # ---------------------------------------------------------
    # Primera página
    # ---------------------------------------------------------

    soup = obtener_pagina(
        construir_url_pagina(1),
        headers
    )

    if soup is None:
        return noticias

    total_paginas = obtener_total_paginas(
        soup
    )

    if total_paginas is None:
        total_paginas = 1

    print(
        f"FFCM: total de páginas detectadas: "
        f"{total_paginas}"
    )

    # ---------------------------------------------------------
    # Recorrer TODAS las páginas
    # ---------------------------------------------------------

    for pagina in range(
        1,
        total_paginas + 1
    ):

        url_actual = construir_url_pagina(
            pagina
        )

        print(
            f"FFCM: procesando página "
            f"{pagina}/{total_paginas}: "
            f"{url_actual}"
        )

        # Para la página 1 ya tenemos el HTML
        if pagina == 1:

            soup_pagina = soup

        else:

            soup_pagina = obtener_pagina(
                url_actual,
                headers
            )

            if soup_pagina is None:

                print(
                    f"FFCM: no se pudo descargar "
                    f"la página {pagina}"
                )

                continue

        noticias_pagina = extraer_noticias(
            soup_pagina
        )

        if not noticias_pagina:

            print(
                f"FFCM: no se encontraron noticias "
                f"en página {pagina}"
            )

            continue

        nuevas = 0

        # -----------------------------------------------------
        # Guardar noticias
        # -----------------------------------------------------

        for noticia in noticias_pagina:

            url = noticia["url"]

            if url in urls_vistas:
                continue

            urls_vistas.add(
                url
            )

            # -------------------------------------------------
            # Si por alguna razón el listado no tiene fecha,
            # intentamos obtenerla desde la noticia.
            # -------------------------------------------------

            if not noticia.get("date"):

                print(
                    f"FFCM: obteniendo fecha: "
                    f"{noticia['title']}"
                )

                fecha = extraer_fecha_noticia(
                    url,
                    headers
                )

                if not fecha:

                    print(
                        "FFCM: no se pudo obtener fecha, "
                        "se omite noticia"
                    )

                    continue

                noticia["date"] = fecha

            noticias.append(
                noticia
            )

            nuevas += 1

        print(
            f"FFCM: {nuevas} noticias nuevas "
            f"en página {pagina}"
        )

    # ---------------------------------------------------------
    # Ordenar de más reciente a más antigua
    # ---------------------------------------------------------

    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(
        f"FFCM: {len(noticias)} noticias "
        f"encontradas en total"
    )

    return noticias
