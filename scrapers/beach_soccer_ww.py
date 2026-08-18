import requests
from bs4 import BeautifulSoup


URL = "https://beachsoccer.com/news"


def scrape():
    response = requests.get(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    noticias = []

    # Buscar enlaces que apunten a noticias individuales
    for enlace in soup.find_all("a", href=True):
        titulo = enlace.get_text(" ", strip=True)
        url = enlace["href"]

        if not titulo:
            continue

        if not url.startswith("http"):
            url = "https://beachsoccer.com" + url

        # De momento solo aceptamos enlaces que parezcan noticias
        if url.startswith("https://beachsoccer.com/") and url != URL:
            noticias.append({
                "title": titulo,
                "url": url
            })

    # Eliminar duplicados
    unicas = []
    urls_vistas = set()

    for noticia in noticias:
        if noticia["url"] not in urls_vistas:
            urls_vistas.add(noticia["url"])
            unicas.append(noticia)

    return unicas
