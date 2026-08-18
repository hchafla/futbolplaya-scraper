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

        # Convertir URLs relativas en absolutas
        if url.startswith("/"):
            url = BASE_URL + url

        # Solo queremos enlaces de Beach Soccer Worldwide
        if not url.startswith(BASE_URL + "/"):
            continue

        # Excluir páginas que no son noticias
        if any(ruta in url for ruta in rutas_excluidas):
            continue

        # Evitar duplicados
        if url in urls_vistas:
            continue

        texto = enlace.get_text(" ", strip=True)

        if not texto:
            continue

        # Buscar una fecha del tipo:
        # 6 August 2026
        partes = texto.split()

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
                    fecha_encontrada = datetime(
                        año, mes, dia
                    ).strftime("%Y-%m-%d")

                    indice_fecha = i

                except ValueError:
                    pass

                break

        # Si no encontramos una fecha, no es una noticia
        if not fecha_encontrada:
            continue

        # Texto anterior a la fecha = categoría
        categoria = " ".join(
            partes[:indice_fecha]
        ).strip()

        # Texto posterior a la fecha = título
        titulo = " ".join(
            partes[indice_fecha + 3:]
        ).strip()

        if not titulo:
            continue

        # Buscar imagen asociada a la noticia
        imagen = None

        img = enlace.find("img")

        if img:

            # Primero intentamos src
            imagen = img.get("src")

            # Algunas webs utilizan data-src para lazy loading
            if not imagen:
                imagen = img.get("data-src")

            # Convertir URL relativa en absoluta
            if imagen and imagen.startswith("/"):
                imagen = BASE_URL + imagen

        urls_vistas.add(url)

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha_encontrada,
            "source": "Beach Soccer Worldwide",
            "category": categoria,
            "image": imagen
        })

    return noticias
