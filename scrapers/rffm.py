import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.rffm.es"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


NOTICIAS_POR_PAGINA = 12
MAX_PAGINAS = 20


def es_futbol_playa(texto):
    """
    Comprueba si un texto contiene referencias explícitas
    a fútbol playa.
    """

    if not texto:
        return False

    texto = texto.lower()

    # Normalizar diferentes tipos de guion
    texto = re.sub(r"[-–—]", " ", texto)

    patrones = [
        r"\bfútbol\s+playa\b",
        r"\bfutbol\s+playa\b",
        r"\bbeach\s+soccer\b",
    ]

    return any(
        re.search(patron, texto, re.IGNORECASE)
        for patron in patrones
    )


def extraer_imagen(enlace):
    """
    Extrae la imagen del background del enlace de la noticia.
    """

    style = enlace.get("style", "")

    patrones = [
        r'url\(["\']([^"\']+)["\']\)',
        r"url\(([^)]+)\)",
    ]

    for patron in patrones:

        match = re.search(
            patron,
            style,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip(
                "\"'"
            )

    return ""


def extraer_fecha(card):
    """
    Busca una fecha DD/MM/YYYY dentro de la tarjeta.
    """

    texto = card.get_text(
        " ",
        strip=True
    )

    match = re.search(
        r"\b\d{2}/\d{2}/\d{4}\b",
        texto
    )

    if match:
        return match.group(0)

    return ""


def scrape():

    noticias = []

    for pagina in range(MAX_PAGINAS):

        start = pagina * NOTICIAS_POR_PAGINA

        url = (
            f"{BASE_URL}/actualidad/federacion"
            f"?_start={start}"
        )

        print(f"RFFM: {url}")

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=30
            )

            response.raise_for_status()

        except requests.RequestException as e:

            print(
                f"RFFM: error descargando página: {e}"
            )

            break

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # --------------------------------------------------
        # Localizar las noticias
        #
        # No dependemos de las clases jssXX/noticiacard.
        # Buscamos enlaces a /noticias/ que contienen un h4.
        # --------------------------------------------------

        enlaces_noticias = soup.select(
            "a[href*='/noticias/']"
        )

        cards = []

        vistos = set()

        for enlace in enlaces_noticias:

            titulo_element = enlace.select_one("h4")

            if not titulo_element:
                continue

            href = enlace.get("href")

            if not href:
                continue

            href = urljoin(
                BASE_URL,
                href
            )

            if href in vistos:
                continue

            vistos.add(href)

            # La tarjeta es el ancestro que contiene el h4,
            # el resumen y la fecha.
            card = enlace

            for _ in range(5):

                if card.parent is None:
                    break

                card = card.parent

                texto_card = card.get_text(
                    " ",
                    strip=True
                )

                if re.search(
                    r"\d{2}/\d{2}/\d{4}",
                    texto_card
                ):
                    break

            cards.append(
                (card, enlace)
            )

        if not cards:

            print(
                "RFFM: no se encontraron noticias. Fin."
            )

            break

        encontradas = 0

        for card, enlace in cards:

            # --------------------------------------------------
            # TÍTULO
            # --------------------------------------------------

            titulo_element = enlace.select_one("h4")

            if not titulo_element:
                continue

            titulo = titulo_element.get_text(
                " ",
                strip=True
            )

            if not titulo:
                continue

            # --------------------------------------------------
            # RESUMEN
            # --------------------------------------------------

            resumen = ""

            # El resumen en el HTML real está dentro de .jss19
            # y es un <p> posterior al bloque del título.
            contenedor = enlace.parent

            for _ in range(4):

                if contenedor is None:
                    break

                resumen_element = contenedor.select_one(
                    "div.jss19 > p"
                )

                if resumen_element:

                    resumen = resumen_element.get_text(
                        " ",
                        strip=True
                    )

                    break

                contenedor = contenedor.parent

            # --------------------------------------------------
            # FILTRO FÚTBOL PLAYA
            # --------------------------------------------------

            texto = f"{titulo} {resumen}"

            if not es_futbol_playa(texto):
                continue

            # --------------------------------------------------
            # URL
            # --------------------------------------------------

            noticia_url = urljoin(
                BASE_URL,
                enlace.get("href")
            )

            # --------------------------------------------------
            # IMAGEN
            # --------------------------------------------------

            imagen = extraer_imagen(
                enlace
            )

            # --------------------------------------------------
            # FECHA
            # --------------------------------------------------

            fecha = extraer_fecha(
                card
            )

            # --------------------------------------------------
            # GUARDAR
            # --------------------------------------------------

            noticias.append({
                "title": titulo,
                "url": noticia_url,
                "date": fecha,
                "summary": resumen,
                "image": imagen,
                "source": "RFFM"
            })

            encontradas += 1

            print(
                f"  ✓ {titulo}"
            )

        print(
            f"RFFM: {encontradas} noticias "
            f"de fútbol playa"
        )

    return noticias
