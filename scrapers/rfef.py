import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


URL = "https://rfef.es/es/noticias/futbol-playa"
BASE_URL = "https://rfef.es"


# URLs que pertenecen a categorías/secciones y NO son noticias
EXCLUDED_URLS = {
    "/es/noticias/futbol-playa",
}

# Prefijos que corresponden a páginas de categorías/secciones
EXCLUDED_PREFIXES = (
    "/es/noticias/futbol-playa/",
    "/es/noticias/selecciones-de-futbol-playa/",
)


def is_excluded_url(url):
    """
    Comprueba si una URL pertenece a una categoría o sección
    en lugar de ser una noticia individual.
    """
    path = url.replace(BASE_URL, "").split("?")[0].split("#")[0]

    if path in EXCLUDED_URLS:
        return True

    if path.startswith(EXCLUDED_PREFIXES):
        return True

    return False


def scrape():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    noticias = []
    urls_vistas = set()

    # Buscar enlaces de noticias
    for link in soup.find_all("a", href=True):

        href = link.get("href", "").strip()

        if not href:
            continue

        # Convertir URL relativa en absoluta
        article_url = urljoin(BASE_URL, href)

        # Solo aceptar URLs de rfef.es
        if not article_url.startswith(BASE_URL):
            continue

        # Limpiar posibles parámetros/anclas
        article_url = article_url.split("?")[0].split("#")[0]

        # Ignorar categorías y secciones
        if is_excluded_url(article_url):
            continue

        # Evitar duplicados
        if article_url in urls_vistas:
            continue

        # Las noticias de esta sección están bajo /es/noticias/
        if not article_url.startswith(BASE_URL + "/es/noticias/"):
            continue

        # Texto del enlace
        title = link.get_text(" ", strip=True)

        if not title:
            continue

        # Buscar el contenedor de la noticia para obtener fecha e imagen
        container = (
            link.find_parent("article")
            or link.find_parent("div", class_=lambda x: x and "views-row" in x)
            or link.parent
        )

        if not container:
            container = link

        # -------------------------
        # FECHA
        # -------------------------

        date = None

        # Buscar elementos típicos de fecha
        date_element = container.find(
            ["time", "span", "div"],
            class_=lambda x: x and any(
                word in " ".join(x).lower()
                for word in ["date", "fecha", "published", "created"]
            )
        )

        if date_element:
            date_text = date_element.get("datetime") or date_element.get_text(
                " ", strip=True
            )

            # Buscar una fecha YYYY-MM-DD
            import re

            match = re.search(r"\d{4}-\d{2}-\d{2}", date_text)

            if match:
                date = match.group(0)

            else:
                # Fechas tipo "11 Agosto 2026"
                meses = {
                    "enero": "01",
                    "febrero": "02",
                    "marzo": "03",
                    "abril": "04",
                    "mayo": "05",
                    "junio": "06",
                    "julio": "07",
                    "agosto": "08",
                    "septiembre": "09",
                    "octubre": "10",
                    "noviembre": "11",
                    "diciembre": "12",
                }

                match = re.search(
                    r"(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})",
                    date_text.lower(),
                )

                if match:
                    day = match.group(1).zfill(2)
                    month = meses.get(match.group(2))
                    year = match.group(3)

                    if month:
                        date = f"{year}-{month}-{day}"

        # -------------------------
        # IMAGEN
        # -------------------------

        image = None

        img = container.find("img")

        if img:
            image = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
            )

            if image:
                image = urljoin(BASE_URL, image)

        # -------------------------
        # CATEGORÍA
        # -------------------------

        category = "Fútbol playa"

        noticia = {
            "title": title,
            "url": article_url,
            "date": date,
            "source": "RFEF",
            "category": category,
        }

        if image:
            noticia["image"] = image

        noticias.append(noticia)
        urls_vistas.add(article_url)

    return noticias
