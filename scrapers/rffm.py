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
    )
}

NOTICIAS_POR_PAGINA = 12
MAX_PAGINAS = 10


def es_futbol_playa(texto):
    if not texto:
        return False

    texto = texto.lower()
    texto = texto.replace("-", " ")

    patrones = [
        r"\bfútbol\s+playa\b",
        r"\bfutbol\s+playa\b",
        r"\bbeach\s+soccer\b",
    ]

    return any(
        re.search(p, texto, re.IGNORECASE)
        for p in patrones
    )


def scrape():

    noticias = []

    for pagina in range(MAX_PAGINAS):

        start = pagina * NOTICIAS_POR_PAGINA

        url = (
            f"{BASE_URL}/actualidad/federacion?_start={start}"
        )

        print(f"RFFM: {url}")

        try:
            r = requests.get(
                url,
                headers=HEADERS,
                timeout=30
            )

            r.raise_for_status()

        except Exception as e:
            print(f"Error: {e}")
            break

        soup = BeautifulSoup(r.text, "html.parser")

        cards = soup.select("div.noticiacard")

        if not cards:
            print("No se encontraron noticias. Fin.")
            break

        encontradas = 0

        for card in cards:

            # URL
            a = card.select_one("a[href*='/noticias/']")

            if not a:
                continue

            href = a.get("href")

            if not href:
                continue

            noticia_url = urljoin(BASE_URL, href)

            # Título
            titulo_element = card.select_one("h4")

            if not titulo_element:
                continue

            titulo = titulo_element.get_text(
                " ",
                strip=True
            )

            # Resumen
            resumen = ""

            resumen_element = card.select_one(
                "div.jss19 > p"
            )

            if resumen_element:
                resumen = resumen_element.get_text(
                    " ",
                    strip=True
                )

            # Buscar fútbol playa en título + resumen
            texto = f"{titulo} {resumen}"

            if not es_futbol_playa(texto):
                continue

            # Imagen
            imagen = ""

            style = a.get("style", "")

            m = re.search(
                r'url\(["\']?(.*?)["\']?\)',
                style
            )

            if m:
                imagen = m.group(1).strip()

            # Fecha
            fecha = ""

            fecha_element = card.select_one(
                "div.MuiBox-root"
            )

            if fecha_element:

                texto_fecha = fecha_element.get_text(
                    " ",
                    strip=True
                )

                m = re.search(
                    r"\d{2}/\d{2}/\d{4}",
                    texto_fecha
                )

                if m:
                    fecha = m.group(0)

            noticias.append({
                "title": titulo,
                "url": noticia_url,
                "date": fecha,
                "summary": resumen,
                "image": imagen,
                "source": "RFFM"
            })

            encontradas += 1

            print(f"  ✓ {titulo}")

        print(
            f"RFFM: {encontradas} noticias de fútbol playa"
        )

    return noticias
