import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import re

BASE_URL = "https://ffcv.es"
URL = "https://ffcv.es/wp/futbol-playa/"


def limpiar_texto(texto):
    return " ".join(texto.split()).strip()


def extraer_fecha(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # datetime="2026-08-15T..."
    time = soup.find("time")
    if time and time.has_attr("datetime"):
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", time["datetime"])
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # Buscar DD/MM/YYYY
    texto = soup.get_text(" ", strip=True)

    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
    if m:
        d, mes, a = m.groups()
        try:
            return datetime.strptime(
                f"{d}/{mes}/{a}",
                "%d/%m/%Y"
            ).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Fallback usando la URL
    m = re.search(r"/blog/(\d{4})/(\d{2})/", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-01"

    return None


def scrape():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151 Safari/537.36"
        )
    }

    print(f"FFCV: procesando {URL}")

    try:
        r = requests.get(URL, headers=headers, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"FFCV: error: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    noticias = []
    urls = set()

    for li in soup.select("li.latest_posts2-post"):

        a = li.select_one("h4.latest_posts2-title a[href]")

        if not a:
            continue

        url = urljoin(BASE_URL, a["href"])

        if url in urls:
            continue

        titulo = limpiar_texto(a.get_text(" ", strip=True))

        if not titulo:
            continue

        img = li.find("img")

        imagen = None

        if img:
            imagen = (
                img.get("src")
                or img.get("data-src")
            )

            if imagen:
                imagen = urljoin(BASE_URL, imagen)

        print(f"FFCV: obteniendo fecha: {titulo}")

        fecha = extraer_fecha(url, headers)

        if not fecha:
            print("FFCV: fecha no encontrada")
            continue

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha,
            "source": "FFCV",
            "category": "Fútbol playa",
            "image": imagen,
        })

        urls.add(url)

    noticias.sort(
        key=lambda x: x["date"],
        reverse=True
    )

    print(f"FFCV: {len(noticias)} noticias encontradas")

    return noticias
