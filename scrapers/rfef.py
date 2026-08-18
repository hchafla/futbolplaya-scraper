import requests
from bs4 import BeautifulSoup
from datetime import datetime


URL = "https://rfef.es/es/noticias/futbol-playa"
BASE_URL = "https://rfef.es"


def scrape():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://rfef.es/",
        "Connection": "keep-alive"
    }

    session = requests.Session()

    response = session.get(
        URL,
        headers=headers,
        timeout=30
    )

    print(f"RFEF HTTP status: {response.status_code}")

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    noticias = []
    urls_vistas = set()

    meses = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12
    }

    for enlace in soup.find_all("a", href=True):

        url = enlace["href"]

        # Convertir URL relativa en absoluta
        if url.startswith("/"):
            url = BASE_URL + url

        # Solo enlaces de noticias
        if not url.startswith(BASE_URL + "/es/noticias/"):
            continue

        # Evitar duplicados
        if url in urls_vistas:
            continue

        texto = enlace.get_text(" ", strip=True)

        if not texto:
            continue

        partes = texto.split()

        fecha_encontrada = None
        indice_fecha = None

        # Buscar una fecha del tipo:
        # 11 Agosto 2026
        for i in range(len(partes) - 2):

            if (
                partes[i].isdigit()
                and partes[i + 1].lower() in meses
                and partes[i + 2].isdigit()
            ):
                dia = int(partes[i])
                mes = meses[partes[i + 1].lower()]
                año = int(partes[i + 2])

                try:
                    fecha_encontrada = datetime(
                        año,
                        mes,
                        dia
                    ).strftime("%Y-%m-%d")

                    indice_fecha = i

                except ValueError:
                    pass

                break

        # Si el propio enlace no contiene fecha,
        # no es una noticia.
        if not fecha_encontrada:
            continue

        # El título está antes de la fecha.
        texto_antes_fecha = " ".join(
            partes[:indice_fecha]
        ).strip()

        if not texto_antes_fecha:
            continue

        titulo = texto_antes_fecha

        # Buscar el contenedor de la tarjeta para localizar imagen
        contenedor = enlace

        for _ in range(5):
            if contenedor.parent:
                contenedor = contenedor.parent

        # Buscar imagen
        imagen = None

        img = contenedor.find("img")

        if img:
            imagen = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
            )

            if imagen and imagen.startswith("/"):
                imagen = BASE_URL + imagen

        urls_vistas.add(url)

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha_encontrada,
            "source": "RFEF",
            "category": "Fútbol playa",
            "image": imagen
        })

    return noticias
