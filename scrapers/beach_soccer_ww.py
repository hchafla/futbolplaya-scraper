import requests
from bs4 import BeautifulSoup


URL = "https://beachsoccer.com/news"
BASE_URL = "https://beachsoccer.com"


def scrape():
    response = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    noticias = []
    urls_vistas = set()

    for enlace in soup.find_all("a", href=True):

        url = enlace["href"]

        # Convertir URLs relativas en absolutas
        if url.startswith("/"):
            url = BASE_URL + url

        # Solo queremos noticias de Beach Soccer Worldwide
        if not url.startswith(BASE_URL + "/"):
            continue

        # Excluir páginas que no son noticias
        rutas_excluidas = (
            "/event/",
            "/calendar",
            "/rankings",
            "/players",
            "/teams",
            "/referees",
            "/coaches",
            "/partners",
            "/history",
            "/laws-of-the-game",
            "/who-we-are",
            "/ambassadors",
            "/foundation",
            "/contact",
            "/mybeachsoccer",
            "/news"
        )

        if any(ruta in url for ruta in rutas_excluidas):
            continue

        # Evitar duplicados
        if url in urls_vistas:
            continue

        titulo = enlace.get_text(" ", strip=True)

        if not titulo:
            continue

        # Las noticias de BSWW suelen contener una fecha
        # en el texto del enlace.
        if not any(str(año) in titulo for año in range(2024, 2030)):
            continue

        urls_vistas.add(url)

        noticias.append({
            "title": titulo,
            "url": url,
            "source": "Beach Soccer Worldwide"
        })

    return noticias
