import json

from scrapers.beach_soccer_ww import scrape as scrape_beach_soccer_ww
from scrapers.rfef import scrape as scrape_rfef


def cargar_noticias_existentes():
    try:
        with open("data/noticias.json", "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def combinar_noticias(noticias):
    noticias_unicas = {}

    for noticia in noticias:
        url = noticia.get("url")

        if url:
            noticias_unicas[url] = noticia

    return list(noticias_unicas.values())


# Ejecutar scrapers
noticias_beach_soccer_ww = scrape_beach_soccer_ww()
noticias_rfef = scrape_rfef()

print(f"Beach Soccer Worldwide: {len(noticias_beach_soccer_ww)}")
print(f"RFEF: {len(noticias_rfef)}")


# Cargar noticias que ya estaban guardadas
noticias_existentes = cargar_noticias_existentes()

# Combinar todo
todas_las_noticias = (
    noticias_existentes
    + noticias_beach_soccer_ww
    + noticias_rfef
)

# Eliminar duplicados por URL
todas_las_noticias = combinar_noticias(todas_las_noticias)

# Ordenar por fecha, más recientes primero
todas_las_noticias.sort(
    key=lambda noticia: noticia.get("date", ""),
    reverse=True
)


with open("data/noticias.json", "w", encoding="utf-8") as archivo:
    json.dump(
        todas_las_noticias,
        archivo,
        ensure_ascii=False,
        indent=2
    )

print(f"Total de noticias guardadas: {len(todas_las_noticias)}")
