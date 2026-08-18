import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


BASE_URL = "https://www.fcf.cat"

# Página que contiene el listado de noticias.
# No dependemos de una URL de categoría que pueda dar 404.
URL = "https://www.fcf.cat/ca/noticies-fcf"

CATEGORIA = "F. Platja"


def limpiar_texto(texto):
    return " ".join(texto.split()).strip()


def extraer_fecha(texto):
    """
    Busca fechas del tipo:

    22/07/2026
    29/06/2026
    """

    texto = limpiar_texto(texto)

    match = re.search(
        r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b",
        texto
    )

    if not match:
        return None

    dia = int(match.group(1))
    mes = int(match.group(2))
    anio = int(match.group(3))

    return f"{anio:04d}-{mes:02d}-{dia:02d}"


def obtener_imagen(tarjeta):
    """
    Obtiene la imagen principal de una tarjeta FCF.

    Next.js puede utilizar:
    - src
    - srcset

    Preferimos src, que en el HTML proporcionado apunta
    a la versión de 1200 px.
    """

    imagen = tarjeta.find("img")

    if not imagen:
        return None

    src = imagen.get("src")

    if not src:
        return None

    # ---------------------------------------------------------
    # Las imágenes de Next.js tienen esta estructura:
    #
    # /_next/image?url=https%3A%2F%2Ffiles.fcf.cat%2F...
    #
    # Intentamos recuperar la URL original para no depender
    # del proxy de Next.js.
    # ---------------------------------------------------------

    match = re.search(
        r"[?&]url=([^&]+)",
        src
    )

    if match:
        from urllib.parse import unquote

        imagen_original = unquote(
            match.group(1)
        )

        if imagen_original.startswith("http"):
            return imagen_original

    return urljoin(
        BASE_URL,
        src
    )


def es_url_noticia(url):
    """
    Comprueba que la URL tenga la estructura:

    https://www.fcf.cat/ca/noticies-fcf/1036803
    """

    if not url:
        return False

    patron = (
        r"^https://www\.fcf\.cat/"
        r"ca/noticies-fcf/"
        r"\d+/?$"
    )

    return bool(
        re.match(
            patron,
            url
        )
    )


def encontrar_tarjeta(enlace):
    """
    En el HTML proporcionado, cada noticia está estructurada así:

    <a href="/ca/noticies-fcf/1036803">
        <div class="...">
            ...
            <span>22/07/2026</span>
            ...
            <h3>...</h3>
            <p>...</p>
        </div>
    </a>

    Por tanto, el propio <a> es el contenedor de la noticia.
    """

    if enlace.name == "a":
        return enlace

    return None


def obtener_titulo(tarjeta):
    """
    Extrae el título desde el <h3> de la tarjeta.
    """

    titulo = tarjeta.find("h3")

    if not titulo:
        return None

    texto = limpiar_texto(
        titulo.get_text(
            " ",
            strip=True
        )
    )

    return texto or None


def obtener_resumen(tarjeta):
    """
    Extrae la entradilla/resumen desde el <p> de la tarjeta.
    """

    titulo = tarjeta.find("h3")

    # El <p> que aparece en las tarjetas está después del h3.
    if titulo:

        siguiente_p = titulo.find_next("p")

        if siguiente_p:

            texto = limpiar_texto(
                siguiente_p.get_text(
                    " ",
                    strip=True
                )
            )

            if texto:
                return texto

    # Fallback: primer <p> de la tarjeta.
    for parrafo in tarjeta.find_all("p"):

        texto = limpiar_texto(
            parrafo.get_text(
                " ",
                strip=True
            )
        )

        if texto:
            return texto

    return None


def obtener_categoria(tarjeta):
    """
    Busca la etiqueta de categoría.

    En el HTML actual aparece como:

    <span ...>F. Platja</span>
    """

    texto_tarjeta = tarjeta.get_text(
        " ",
        strip=True
    )

    if CATEGORIA.lower() in texto_tarjeta.lower():
        return CATEGORIA

    return None


def obtener_fecha_tarjeta(tarjeta):
    """
    Busca la fecha dentro de la tarjeta.
    """

    texto = tarjeta.get_text(
        " ",
        strip=True
    )

    return extraer_fecha(texto)


def scrape():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36"
        ),
        "Accept-Language": "ca-ES,ca;q=0.9,es;q=0.8",
    }

    print(
        f"FCF: procesando {URL}"
    )

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
    # BUSCAR ENLACES DE NOTICIAS
    #
    # La estructura real de FCF utiliza:
    #
    # <a href="/ca/noticies-fcf/1036803">
    #
    # No buscamos clases concretas porque Tailwind/Next.js
    # genera clases que pueden cambiar.
    # ---------------------------------------------------------

    enlaces = soup.find_all(
        "a",
        href=True
    )

    for enlace in enlaces:

        href = enlace.get(
            "href",
            ""
        ).strip()

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

        tarjeta = encontrar_tarjeta(
            enlace
        )

        if not tarjeta:
            continue

        # -----------------------------------------------------
        # FILTRAR POR CATEGORÍA
        #
        # La tarjeta lleva explícitamente:
        #
        # F. Platja
        #
        # Esto evita coger noticias de fútbol, fútbol sala,
        # etc. que puedan aparecer en el mismo listado.
        # -----------------------------------------------------

        categoria = obtener_categoria(
            tarjeta
        )

        if categoria != CATEGORIA:
            continue

        titulo = obtener_titulo(
            tarjeta
        )

        if not titulo:
            continue

        fecha = obtener_fecha_tarjeta(
            tarjeta
        )

        if not fecha:
            continue

        resumen = obtener_resumen(
            tarjeta
        )

        imagen = obtener_imagen(
            tarjeta
        )

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha,
            "source": "FCF",
            "category": "Fútbol playa",
            "image": imagen,
            "summary": resumen,
        })

        urls_vistas.add(
            url
        )

    # ---------------------------------------------------------
    # ORDENAR DE MÁS RECIENTE A MÁS ANTIGUA
    # ---------------------------------------------------------

    noticias.sort(
        key=lambda noticia: (
            noticia.get("date") or ""
        ),
        reverse=True
    )

    print(
        f"FCF: {len(noticias)} noticias encontradas"
    )

    return noticias
