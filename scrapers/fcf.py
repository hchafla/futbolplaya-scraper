from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import re


BASE_URL = "https://www.fcf.cat"
URL = "https://www.fcf.cat/ca/noticies-fcf"

CATEGORIA = "F. Platja"


def limpiar_texto(texto):
    if not texto:
        return ""

    return " ".join(texto.split()).strip()


def convertir_fecha(fecha):
    """
    Convierte:

    22/07/2026

    en:

    2026-07-22
    """

    match = re.match(
        r"^(\d{1,2})/(\d{1,2})/(\d{4})$",
        fecha.strip()
    )

    if not match:
        return None

    dia = int(match.group(1))
    mes = int(match.group(2))
    anio = int(match.group(3))

    return f"{anio:04d}-{mes:02d}-{dia:02d}"


def obtener_imagen(card):
    imagen = card.locator("img").first

    if imagen.count() == 0:
        return None

    # Next.js utiliza srcset y src.
    src = imagen.get_attribute("src")

    if not src:
        src = imagen.get_attribute("data-src")

    if not src:
        return None

    return urljoin(BASE_URL, src)


def extraer_noticias_de_pagina(page):
    noticias = []

    # Las tarjetas de noticias son enlaces.
    enlaces = page.locator(
        'a[href^="/ca/noticies-fcf/"]'
    )

    total = enlaces.count()

    for i in range(total):

        enlace = enlaces.nth(i)

        href = enlace.get_attribute("href")

        if not href:
            continue

        url = urljoin(BASE_URL, href)

        # -------------------------------------------------
        # Categoría
        # -------------------------------------------------

        texto_tarjeta = limpiar_texto(
            enlace.inner_text()
        )

        if CATEGORIA.lower() not in texto_tarjeta.lower():
            continue

        # -------------------------------------------------
        # Título
        # -------------------------------------------------

        titulo_locator = enlace.locator("h3").first

        if titulo_locator.count() == 0:
            continue

        titulo = limpiar_texto(
            titulo_locator.inner_text()
        )

        if not titulo:
            continue

        # -------------------------------------------------
        # Fecha
        # -------------------------------------------------

        # Las tarjetas contienen la fecha en un span.
        fecha = None

        spans = enlace.locator("span")

        for j in range(spans.count()):

            texto_span = limpiar_texto(
                spans.nth(j).inner_text()
            )

            if re.match(
                r"^\d{1,2}/\d{1,2}/\d{4}$",
                texto_span
            ):
                fecha = convertir_fecha(texto_span)
                break

        if not fecha:
            continue

        # -------------------------------------------------
        # Imagen
        # -------------------------------------------------

        imagen = obtener_imagen(enlace)

        # -------------------------------------------------
        # Guardar
        # -------------------------------------------------

        noticias.append({
            "title": titulo,
            "url": url,
            "date": fecha,
            "source": "FCF",
            "category": "Fútbol playa",
            "image": imagen,
        })

    return noticias


def scrape():

    noticias = []
    urls_vistas = set()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1200,
            },
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0 Safari/537.36"
            )
        )

        try:

            print(
                f"FCF: procesando {URL}"
            )

            page.goto(
                URL,
                wait_until="networkidle",
                timeout=60000
            )

            # -------------------------------------------------
            # Esperamos a que aparezcan las tarjetas.
            # -------------------------------------------------

            page.wait_for_selector(
                'a[href^="/ca/noticies-fcf/"]',
                timeout=30000
            )

            # -------------------------------------------------
            # La página carga noticias mediante JS.
            #
            # Dejamos que termine cualquier carga inicial.
            # -------------------------------------------------

            page.wait_for_timeout(2000)

            # -------------------------------------------------
            # Extraer las noticias visibles.
            # -------------------------------------------------

            noticias_pagina = extraer_noticias_de_pagina(
                page
            )

            for noticia in noticias_pagina:

                url = noticia.get("url")

                if not url:
                    continue

                if url in urls_vistas:
                    continue

                urls_vistas.add(url)
                noticias.append(noticia)

            print(
                f"FCF: {len(noticias_pagina)} noticias "
                f"de fútbol playa encontradas"
            )

            # -------------------------------------------------
            # Intentar cargar más noticias.
            #
            # La web puede utilizar un botón "Cargar más".
            # Si existe, lo pulsamos mientras siga apareciendo.
            # -------------------------------------------------

            for _ in range(50):

                botones = page.get_by_text(
                    "Cargar más",
                    exact=False
                )

                if botones.count() == 0:
                    break

                boton = botones.last

                if not boton.is_visible():
                    break

                cantidad_antes = page.locator(
                    'a[href^="/ca/noticies-fcf/"]'
                ).count()

                try:
                    boton.click(
                        timeout=5000
                    )
                except Exception:
                    break

                try:
                    page.wait_for_function(
                        """
                        (cantidadAntes) => {
                            return document.querySelectorAll(
                                'a[href^="/ca/noticies-fcf/"]'
                            ).length > cantidadAntes;
                        }
                        """,
                        arg=cantidad_antes,
                        timeout=10000
                    )
                except Exception:
                    break

                page.wait_for_timeout(1000)

                nuevas = extraer_noticias_de_pagina(
                    page
                )

                nuevas_count = 0

                for noticia in nuevas:

                    url = noticia.get("url")

                    if not url:
                        continue

                    if url in urls_vistas:
                        continue

                    urls_vistas.add(url)
                    noticias.append(noticia)
                    nuevas_count += 1

                print(
                    f"FCF: {nuevas_count} noticias nuevas "
                    f"cargadas"
                )

                if nuevas_count == 0:
                    break

        except Exception as error:

            print(
                f"FCF: error durante el scraping: {error}"
            )

        finally:

            browser.close()

    # ---------------------------------------------------------
    # Ordenar de más reciente a más antigua
    # ---------------------------------------------------------

    noticias.sort(
        key=lambda noticia: noticia.get("date") or "",
        reverse=True
    )

    print(
        f"FCF: {len(noticias)} noticias encontradas en total"
    )

    return noticias
