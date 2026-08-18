from datetime import datetime

print("Hola desde GitHub Actions")

with open("data/noticias.json", "w", encoding="utf-8") as f:
    f.write(
        '{"actualizado":"' + datetime.now().isoformat() + '"}'
    )
