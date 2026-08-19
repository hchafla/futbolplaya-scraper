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
MAX_PAGINAS = 50


def es_futbol_playa(texto):
    texto = texto.lower().replace("-", " ")

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
            print(e)
            break

        soup = BeautifulSoup(r.text, "html.parser")

        cards = soup.select("div.noticiacard")

        if not cards:
            break

        encontradas = 0

        for card in cards:

            a = card.select_one("a[href*='/noticias/']")

            if not a:
                continue

            titulo = card.select_one("h4 p")

            if not titulo:
                continue

            titulo = titulo.get_text(" ", strip=True)

            resumen = ""

            ps = card.select("div.jss19 > p")

            if ps:
                resumen = ps[-1].get_text(" ", strip=True)

            texto = f"{titulo} {resumen}"

            if not es_futbol_playa(texto):
                continue

            href = a["href"]

            imagen = ""

            style = a.get("style", "")

            m = re.search(r'url\("([^"]+)"\)', style)

            if not m:
                m = re.search(r"url\((.*?)\)", style)

            if m:
                imagen = m.group(1).strip('"')

            fecha = ""

            cajas = card.select("div.MuiBox-root")

            for caja in cajas:

                txt = caja.get_text(" ", strip=True)

                if re.match(r"\d{2}/\d{2}/\d{4}", txt):
                    fecha = txt
                    break

            noticias.append({
                "title": titulo,
                "url": urljoin(BASE_URL, href),
                "date": fecha,
                "summary": resumen,
                "image": imagen,
                "source": "RFFM"
            })

            encontradas += 1

            print(f"  ✓ {titulo}")

        print(f"RFFM: {encontradas} noticias de fútbol playa")

    return noticias
