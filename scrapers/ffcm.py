import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import re


BASE_URL = "https://www.ffcm.es"

URL = (
    "https://www.ffcm.es/pnfg/NNws_LstNews"
    "?cod_primaria=5000210&cod_secundaria="
)


def limpiar_texto(texto):
    if not texto:
        return ""

    return " ".join(texto.split()).strip()


def extraer_fecha(texto):
    """
    Extrae fechas con formato DD/MM/YYYY.
    """

    texto = limpiar_texto(texto)

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

        return fecha.strftime("%Y-%m-%d")

    except ValueError:
        return None


def obtener_pagina(url, headers):
    """
    Descarga una página del listado de noticias.
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


def extraer_noticias(soup):
    """
    Extrae las noticias del listado FFCM.

    La página ya está filtrada por la categoría
    FÚTBOL PLAYA, por lo que NO se aplica ningún
    filtro adicional por título.
    """

    noticias = []

    elementos = soup.select(
        "td.td_not"
    )

    for elemento in elementos:

        # -----------------------------------------------------
        # Título y enlace
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
        # Fecha
        # -----------------------------------------------------

        fecha = None

        elementos_fecha = elemento.select(
            "span"
        )

        for span in elementos_fecha:

            fecha = extraer_fecha(
                span.get_text(
                    " ",
                    strip=True
                )
            )

            if fecha:
                break

        if not fecha:
            print(
                f"FFCM: no se pudo obtener fecha: {titulo}"
            )
            continue

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
        # Guardar noticia
        # -----------------------------------------------------

        noticias.append({
            "title": titulo,
            "url": url,
            "image": imagen,
            "date": fecha,
            "source": "FFCM",
            "category": "Fútbol playa"
        })

    return noticias


def encontrar_siguiente_pagina(soup):
    """
    Busca el botón 'Siguiente' del sistema NovaNet.

    El HTML utiliza:

        javascript:elegirPag(3);

    para pasar a la página siguiente.

    También se utiliza el campo oculto
    NPcd_PageNext, que nos permite obtener
    directamente el número de página.
    """

    # ---------------------------------------------------------
    # Método principal: input NPcd_PageNext
    # ---------------------------------------------------------

    siguiente = soup.select_one(
        "input[name='NPcd_PageNext']"
    )

    if siguiente:

        pagina = siguiente.get(
            "value"
        )

        if pagina and pagina.isdigit():

            pagina = int(pagina)

            # Página actual
            actual = soup.select_one(
                "input[name='NPcd_Page']"
            )

            if actual:

                actual_valor = actual.get(
                    "value"
                )

                if (
                    actual_valor
                    and actual_valor.isdigit()
                    and int(actual_valor) >= pagina
                ):
                    return None

            return pagina

    # ---------------------------------------------------------
    # Fallback: botón Siguiente
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

        if "siguiente" not in texto:
            continue

        href = enlace.get(
            "href"
        )

        match = re.search(
            r"elegirPag\((\d+)\)",
            href
        )

        if match:
            return int(
                match.group(1)
            )

    return None


def construir_url_pagina(pagina):
    """
    Construye la URL de una página concreta.

    Página 1:
        ...&cod_secundaria=

    Página 2+:
        ...&buscar=&cod_secundaria=5000210
        &NPcd_PageAnt=X
        &NPcd_PageNext=Y
        &NPcd_Page=Y
    """

    if pagina == 1:

        return URL

    pagina_anterior = pagina - 1
    pagina_siguiente = pagina + 1

    return (
        "https://www.ffcm.es/pnfg/NNws_LstNews"
        "?cod_primaria=5000210"
        "&buscar="
        "&cod_secundaria=5000210"
        f"&NPcd_PageAnt={pagina_anterior}"
        f"&NPcd_PageNext={pagina_siguiente}"
        f"&NPcd_Page={pagina}"
    )


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
        f"FFCM: procesando {URL}"
    )

    noticias = []

    urls_vistas = set()

    pagina = 1

    while True:

        url_actual = construir_url_pagina(
            pagina
        )

        print(
            f"FFCM: procesando página {pagina}: "
            f"{url_actual}"
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
                f"FFCM: no se encontraron noticias "
                f"en página {pagina}"
            )

            break

        nuevas = 0

        for noticia in noticias_pagina:

            url = noticia["url"]

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
            f"FFCM: {nuevas} noticias nuevas "
            f"en página {pagina}"
        )

        # -----------------------------------------------------
        # Comprobar si existe siguiente página
        # -----------------------------------------------------

        siguiente = encontrar_siguiente_pagina(
            soup
        )

        if siguiente is None:
            break

        if siguiente <= pagina:
            break

        pagina = siguiente

        # -----------------------------------------------------
        # Protección contra bucles
        # -----------------------------------------------------

        if pagina > 100:
            print(
                "FFCM: límite de 100 páginas alcanzado."
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
        f"FFCM: {len(noticias)} noticias encontradas "
        f"en total"
    )

    return noticias
