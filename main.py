import json

from scrapers.beach_soccer_ww import scrape as scrape_beach_soccer_ww
from scrapers.rfaf import scrape as scrape_rfaf
from scrapers.rfef import scrape as scrape_rfef
from scrapers.fcf import scrape as scrape_fcf
from scrapers.ffcv import scrape as scrape_ffcv
from scrapers.ffrm import scrape as scrape_ffrm
from scrapers.ffcm import scrape as scrape_ffcm
from scrapers.fexfutbol import scrape as scrape_fexfutbol
from scrapers.rffm import scrape as scrape_rffm
from scrapers.fnf import scrape as scrape_fnf
from scrapers.rffpa import scrape as scrape_rffpa
from scrapers.rfgf import scrape as scrape_rfgf
from scrapers.rfmf import scrape as scrape_rfmf
from scrapers.ffib import scrape as scrape_ffib
from scrapers.fiflp import scrape as scrape_fiflp
from scrapers.ftf import scrape as scrape_ftf


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
noticias_fexfutbol = scrape_fexfutbol()
noticias_rffm = scrape_rffm()
noticias_fnf = scrape_fnf()
noticias_rffpa = scrape_rffpa()
noticias_rfgf = scrape_rfgf()
noticias_rfmf = scrape_rfmf()
noticias_ffib = scrape_ffib()
noticias_fiflp = scrape_fiflp()
noticias_ftf = scrape_ftf()

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

print(
    f"FEXFútbol: "
    f"{len(noticias_fexfutbol)}"
)

print(
    f"RFFM: "
    f"{len(noticias_rffm)}"
)

print(
    f"FNF: "
    f"{len(noticias_fnf)}"
)

print(
    f"RFFPA: "
    f"{len(noticias_rffpa)}"
)

print(
    f"RFGF: "
    f"{len(noticias_rfgf)}"
)

print(
    f"RFMF: "
    f"{len(noticias_rfmf)}"
)

print(
    f"FFIB: "
    f"{len(noticias_ffib)}"
)

print(
    f"FIFLP: "
    f"{len(noticias_fiflp)}"
)

print(
    f"FTF: "
    f"{len(noticias_ftf)}"
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
    + noticias_fexfutbol
    + noticias_rffm
    + noticias_fnf
    + noticias_rffpa
    + noticias_rfgf
    + noticias_rfmf
    + noticias_ffib
    + noticias_fiflp
    + noticias_ftf
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
