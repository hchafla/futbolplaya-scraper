import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin


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
    }

    response = requests.get(
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

    # ---------------------------------------------------------
    # BUSCAR ENLACES QUE APUNTEN A NOTICIAS REALES
    # ---------------------------------------------------------

    for enlace in soup.find_all("a", href=True):

        href = enlace["href"]

        url = urljoin(BASE_URL, href)

        # Solo URLs de noticias
        if not url.startswith(BASE_URL + "/es/noticias/"):
            continue

        # Excluir categorías y secciones conocidas
        partes_url = url.rstrip("/").split("/")

        if len(partes_url) < 6:
            continue

        # La URL de una noticia real termina directamente
        # en el slug. Las categorías tienen estructuras como:
        #
        # /es/noticias/futbol-playa/campeonatos-clubes-base-playa
        # /es/noticias/selecciones-de-futbol-playa/absoluta-masculina-playa
        #
        # Excluimos esas rutas de categoría.

        categorias_excluidas = {
            "futbol-playa",
            "selecciones-de-futbol-playa",
            "campeonatos-clubes-base-playa",
        }

        if any(
            categoria in partes_url
            for categoria in categorias_excluidas
        ):
            continue

        if url in urls_vistas:
            continue

        texto = enlace.get_text(" ", strip=True)

        if not texto:
            continue

        # -----------------------------------------------------
        # BUSCAR FECHA
        # -----------------------------------------------------

        palabras = texto.split()

        fecha = None
        indice_fecha = None

        for i in range(len(palabras) - 2):

            dia = palabras[i]
            mes = palabras[i + 1].lower()
            año = palabras[i + 2]

            if (
                dia.isdigit()
                and mes in meses
                and año.isdigit()
            ):
                try:
                    fecha = datetime(
                        int(año),
                        meses[mes],
                        int(dia)
                    ).strftime("%Y-%m-%d")

                    indice_fecha = i

                except ValueError:
                    pass

                break

        if not fecha:
            continue

        # -----------------------------------------------------
        # BUSCAR EL TÍTULO REAL
        # -----------------------------------------------------

        # El enlace contiene:
        #
        # TITULO
        # ENTRADILLA
        # FECHA
        #
        # En vez de intentar adivinar dónde acaba el título
        # dentro del enlace, buscamos los elementos de título
        # del propio bloque de noticia.

        contenedor = enlace

        for _ in range(6):
            if contenedor.parent:
                contenedor = contenedor.parent

        titulo = None

        # Buscar headings dentro de la tarjeta
        for tag in contenedor.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6"]
        ):
            texto_titulo = tag.get_text(" ", strip=True)

            if texto_titulo:
                titulo = texto_titulo
                break

        # Si no encontramos heading, usar el texto anterior
        # a la fecha como fallback.
        if not titulo:
            titulo = " ".join(
                palabras[:indice_fecha]
            ).strip()

        if not titulo:
            continue

        # -----------------------------------------------------
        # IMAGEN
        # -----------------------------------------------------

        imagen = None

        img = contenedor.find("img")

        if img:
            imagen = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
            )

            if imagen:
                imagen = urljoin(BASE_URL, imagen)

        # -----------------------------------------------------
        # GUARDAR
        # -----------------------------------------------------

        urls_vistas.add(url)

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha,
            "source": "RFEF",
            "category": "Fútbol playa",
            "image": imagen
        })

    return noticias
