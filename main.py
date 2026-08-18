import json

from scrapers.beach_soccer_ww import scrape as scrape_beach_soccer_ww
from scrapers.rfaf import scrape as scrape_rfaf
from scrapers.rfef import scrape as scrape_rfef
from scrapers.fcf import scrape as scrape_fcf
from scrapers.ffcv import scrape as scrape_ffcv
from scrapers.ffrm import scrape as scrape_ffrm
from scrapers.ffcm import scrape as scrape_ffcm


def cargar_noticias_existentes():
    try:
        with open(
            "data/noticias.json",
            "r",
            encoding="utf-8"
        ) as archivo:
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


# ---------------------------------------------------------
# Ejecutar scrapers
# ---------------------------------------------------------

noticias_beach_soccer_ww = scrape_beach_soccer_ww()
noticias_rfaf = scrape_rfaf()
noticias_rfef = scrape_rfef()
noticias_fcf = scrape_fcf()
noticias_ffcv = scrape_ffcv()
noticias_ffrm = scrape_ffrm()
noticias_ffcm = scrape_ffcm()

print(
    f"Beach Soccer Worldwide: "
    f"{len(noticias_beach_soccer_ww)}"
)

print(
    f"RFAF: "
    f"{len(noticias_rfaf)}"
)

print(
    f"RFEF: "
    f"{len(noticias_rfef)}"
)

print(
    f"FCF: "
    f"{len(noticias_fcf)}"
)

print(
    f"FFCV: "
    f"{len(noticias_ffcv)}"
)

print(
    f"FFRM: "
    f"{len(noticias_ffrm)}"
)

print(
    f"FFCM: "
    f"{len(noticias_ffcm)}"
)


# ---------------------------------------------------------
# Cargar noticias existentes
# ---------------------------------------------------------

noticias_existentes = cargar_noticias_existentes()


# ---------------------------------------------------------
# Combinar todo
# ---------------------------------------------------------

todas_las_noticias = (
    noticias_existentes
    + noticias_beach_soccer_ww
    + noticias_rfaf
    + noticias_rfef
    + noticias_fcf
    + noticias_ffcv
    + noticias_ffrm
    + noticias_ffcm
)


# ---------------------------------------------------------
# Eliminar duplicados por URL
# ---------------------------------------------------------

todas_las_noticias = combinar_noticias(
    todas_las_noticias
)


# ---------------------------------------------------------
# Ordenar por fecha, más recientes primero
# ---------------------------------------------------------

todas_las_noticias.sort(
    key=lambda noticia: noticia.get("date") or "",
    reverse=True
)


# ---------------------------------------------------------
# Guardar noticias
# ---------------------------------------------------------

with open(
    "data/noticias.json",
    "w",
    encoding="utf-8"
) as archivo:

    json.dump(
        todas_las_noticias,
        archivo,
        ensure_ascii=False,
        indent=2
    )


print(
    f"Total de noticias guardadas: "
    f"{len(todas_las_noticias)}"
)
