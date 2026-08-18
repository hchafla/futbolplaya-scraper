import requests
from bs4 import BeautifulSoup
from datetime import datetime


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

    meses = {
        "January": 1,
        "February": 2,
        "March": 3,
        "April": 4,
        "May": 5,
        "June": 6,
        "July": 7,
        "August": 8,
        "September": 9,
        "October": 10,
        "November": 11,
        "December": 12
    }

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

    for enlace in soup.find_all("a", href=True):

        url = enlace["href"]

        if url.startswith("/"):
            url = BASE_URL + url

        if not url.startswith(BASE_URL + "/"):
            continue

        if any(ruta in url for ruta in rutas_excluidas):
            continue

        if url in urls_vistas:
            continue

        texto = enlace.get_text(" ", strip=True)

        if not texto:
            continue

        # Separar el texto en partes
        partes = texto.split()

        # Buscar una fecha del tipo:
        # 6 August 2026
        fecha_encontrada = None
        indice_fecha = None

        for i in range(len(partes) - 2):
            if (
                partes[i].isdigit()
                and partes[i + 1] in meses
                and partes[i + 2].isdigit()
            ):
                dia = int(partes[i])
                mes = meses[partes[i + 1]]
                año = int(partes[i + 2])

                try:
                    fecha_encontrada = datetime(año, mes, dia).strftime("%Y-%m-%d")
                    indice_fecha = i
                except ValueError:
                    pass

                break

        if not fecha_encontrada:
            continue

        # Lo que aparece antes de la fecha es la categoría
        categoria = " ".join(partes[:indice_fecha]).strip()

        # Lo que aparece después de la fecha es el título
        titulo = " ".join(partes[indice_fecha + 3:]).strip()

        if not titulo:
            continue

        urls_vistas.add(url)

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha_encontrada,
            "source": "Beach Soccer Worldwide",
            "category": categoria
        })

    return noticias
