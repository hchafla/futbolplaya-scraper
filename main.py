import json

from scrapers.beach_soccer_ww import scrape


noticias = scrape()

print(f"Noticias encontradas: {len(noticias)}")

with open("data/noticias.json", "w", encoding="utf-8") as archivo:
    json.dump(noticias, archivo, ensure_ascii=False, indent=2)
