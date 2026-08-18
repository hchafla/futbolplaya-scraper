import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

URL = "https://rfef.es/es/noticias/futbol-playa"

MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
}

# Lista de slugs que no son noticias, sino categorías, secciones o páginas estáticas.
SLUGS_BLOQUEADOS = {
    "futbol-playa", "selecciones-de-futbol-playa", "futbol-sala", 
    "institucional", "competiciones-masculinas", "competiciones-femeninas", 
    "arbitros", "entrenadores", "formacion", "seleccion-absoluta", 
    "selecciones-masculinas", "selecciones-femeninas", "e-sports", 
    "leyendas", "grassroots", "area-medica", "proteccion-de-la-infancia"
}

def limpiar_texto(texto):
    return " ".join(texto.split()).strip()

def extraer_fecha(texto):
    texto = limpiar_texto(texto).lower()
    patron = (
        r"\b(\d{1,2})\s+"
        r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
        r"septiembre|octubre|noviembre|diciembre)\s+"
        r"(\d{4})\b"
    )
    match = re.search(patron, texto)
    if not match:
        return None

    dia = int(match.group(1))
    mes = MESES[match.group(2)]
    anio = match.group(3)
    return f"{anio}-{mes}-{dia:02d}"

def obtener_imagen(contenedor):
    imagen = contenedor.find("img")
    if not imagen:
        return None

    src = imagen.get("src") or imagen.get("data-src") or imagen.get("data-lazy-src")
    if not src:
        return None
    return urljoin(URL, src)

def es_url_noticia(url):
    parsed = urlparse(url)
    if parsed.netloc != "rfef.es":
        return False

    partes = [parte for parte in parsed.path.strip("/").split("/") if parte]

    if len(partes) != 3:
        return False
    if partes[0] != "es" or partes[1] != "noticias":
        return False
        
    # Descartamos si el tercer segmento (slug) es una categoría
    if partes[2] in SLUGS_BLOQUEADOS:
        return False

    return True

def encontrar_tarjeta(enlace):
    actual = enlace
    
    # Reducimos los niveles a 4 para no saltar accidentalmente a contenedores masivos (main, body, wrappers)
    for _ in range(4):
        if not actual.parent:
            break
            
        actual = actual.parent
        
        # Rompemos si chocamos con etiquetas maestras de estructura
        if actual.name in ["main", "body", "header", "nav", "footer", "section"]:
            break

        texto = limpiar_texto(actual.get_text(" ", strip=True))
        fecha = extraer_fecha(texto)

        if fecha:
            return actual, fecha

    return None, None

def obtener_titulo(tarjeta, url):
    for etiqueta in tarjeta.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        texto = limpiar_texto(etiqueta.get_text(" ", strip=True))
        if texto:
            return texto

    for enlace in tarjeta.find_all("a", href=True):
        enlace_url = urljoin(URL, enlace.get("href", ""))
        if enlace_url == url:
            texto = limpiar_texto(enlace.get_text(" ", strip=True))
            if texto:
                return texto
    return None

def scrape():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36"
        )
    }

    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    noticias = []
    urls_vistas = set()

    # Acotamos la búsqueda estrictamente al bloque de contenido central, omitiendo header y nav.
    # Usamos <main> de forma preferente. Si no existe, usamos un fallback a todo el soup pero sin procesar tags de <header>
    contenedor_principal = soup.find("main") or soup.find("div", role="main")
    if not contenedor_principal:
        # Destruir header y nav si no hay etiqueta main para evitar barrer los menús
        for etiqueta in soup.find_all(["header", "nav", "footer"]):
            etiqueta.decompose()
        contenedor_principal = soup

    for enlace in contenedor_principal.find_all("a", href=True):
        href = enlace.get("href", "").strip()
        if not href:
            continue

        url = urljoin(URL, href)

        if not es_url_noticia(url):
            continue

        if url in urls_vistas:
            continue

        tarjeta, fecha = encontrar_tarjeta(enlace)
        if not tarjeta or not fecha:
            continue

        titulo = obtener_titulo(tarjeta, url)
        if not titulo:
            continue

        imagen = obtener_imagen(tarjeta)

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha,
            "source": "RFEF",
            "category": "Fútbol playa",
            "image": imagen,
        })
        urls_vistas.add(url)

    noticias.sort(key=lambda noticia: noticia.get("date") or "", reverse=True)
    print(f"RFEF: {len(noticias)} noticias encontradas")
    return noticias
