import json

# -----------------------------------------------------------
# main2.py — flujo de PRUEBAS
#
# Aquí solo van los scrapers que estás probando/afinando en
# cada momento. No lee ni escribe data/noticias.json, no se
# mezcla con el flujo de producción (main.py). Sirve para
# iterar rápido sin esperar a que corran los scrapers ya
# validados.
#
# Cuando un scraper quede validado aquí, se mueve el import a
# main.py y se borra de esta lista.
# -----------------------------------------------------------

from scrapers.rffpa import scrape as scrape_rffpa
from scrapers.rfgf import scrape as scrape_rfgf
from scrapers.rfmf import scrape as scrape_rfmf
from scrapers.ffib import scrape as scrape_ffib


SCRAPERS_EN_PRUEBA = {
    "RFFPA": scrape_rffpa,
    "RFGF": scrape_rfgf,
    "RFMF": scrape_rfmf,
    "FFIB": scrape_ffib,
}


def main():

    resultados = {}

    for nombre, funcion_scrape in SCRAPERS_EN_PRUEBA.items():

        print(f"\n=== {nombre} ===")

        try:
            noticias = funcion_scrape()

        except Exception as e:
            print(f"{nombre}: ERROR -> {e}")
            continue

        resultados[nombre] = noticias

        print(f"{nombre}: {len(noticias)} noticias de fútbol playa")

        for noticia in noticias:
            print(
                f"  {noticia.get('date')} | "
                f"{noticia.get('title')} | "
                f"{noticia.get('url')}"
            )

    print("\n=== RESUMEN ===")

    for nombre, noticias in resultados.items():
        print(f"{nombre}: {len(noticias)}")

    # Volcado a un JSON de prueba aparte, solo para inspección
    # manual si hace falta (no se sube a futbolplaya.es).
    with open(
        "data/noticias_test.json",
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            resultados,
            archivo,
            ensure_ascii=False,
            indent=2
        )

    print("\nResultados volcados en data/noticias_test.json")


if __name__ == "__main__":
    main()
