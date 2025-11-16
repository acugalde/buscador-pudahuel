import concurrent.futures
import logging
from urllib.parse import urljoin, urlparse

from flask import Flask, jsonify, render_template, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Lista de sitios a consultar
SITES = [
    "https://www.latercera.com/",
    "https://www.elmostrador.cl/",
    "https://digital.elmercurio.com/2025/11/16/A",
    "https://www.lacuarta.com/",
    "https://www.lanacion.cl/",
    "https://www.lun.com/",
    "https://www.theclinic.cl/",
    "https://www.emol.com/",
    "https://www.hoyxhoy.cl/2025/11/14/papel/",
    "https://www.lanacion.cl/",
    "https://www.publimetro.cl/noticias/",
    "https://www.soychile.cl/",
    "https://www.df.cl/",
    "https://www.diarioestrategia.cl/",
    "https://www.latercera.com/canal/pulso/",
    "https://radio.uchile.cl/",
    "https://radioportales.cl/sitio/",
    "https://www.radioimagina.cl/",
    "https://www.concierto.cl/",
    "https://www.futuro.cl/",
    "https://duna.cl/",
    "https://www.pudahuel.cl/",
    "https://elconquistadorfm.net/",
    "https://www.adnradio.cl/",
    "https://www.radioagricultura.cl/",
    "https://www.radioactiva.cl/",
    "https://www.radiolaclave.cl/",
    "https://www.cooperativa.cl/",
    "https://universo.cl/",
    "https://www.rockandpop.cl/",
    "https://www.diariousach.cl/",
    "https://cl.radiodisney.com/",
    "https://lametrofm.cl/",
    "https://www.radiocorporacion.cl/",
    "https://www.beethovenfm.cl/",
    "https://www.fmdos.cl/",
    "https://www.carolina.cl/",
    "https://www.biobiochile.cl/",
    "https://www.infinita.cl/",
    "https://www.pauta.cl/",
    "https://playfm.cl/",
    "https://www.corazon.cl/",
    "https://radio13c.cl/",
    "https://radio.uchile.cl/",
    "https://tele13radio.cl/",
    "https://www.romantica.cl/",
    "https://sonarfm.cl/",
    "https://www.tvn.cl/",
    "https://www.cnnchile.com/",
    "https://www.dw.com/es/live-tv/channel-spanish",
    "https://www.lared.cl/",
    "https://www.mega.cl/",
    "https://www.tvr.cl/",
    "https://tvmas.tv/",
    "https://www.13.cl/",
    "https://www.chilevision.cl/",
]

KEYWORD = "Pudahuel"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PudahuelNewsBot/1.0; +https://example.com)"
}

logging.basicConfig(level=logging.INFO)


def get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")


def search_site(url: str, keyword: str):
    """
    Busca links en una página cuyo texto o href contenga la palabra `keyword`.
    Retorna una lista de dicts con título, link y fuente.
    """
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logging.warning(f"Error al obtener {url}: {e}")
        return results

    soup = BeautifulSoup(resp.text, "html.parser")

    seen_links = set()
    keyword_lower = keyword.lower()

    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True) or ""
        href = a["href"]

        text_lower = text.lower()
        href_lower = href.lower()

        if keyword_lower in text_lower or keyword_lower in href_lower:
            full_url = urljoin(url, href)
            if full_url in seen_links:
                continue
            seen_links.add(full_url)

            title = text if text.strip() else "(Sin título)"
            results.append(
                {
                    "titulo": title,
                    "link": full_url,
                    "fuente": get_domain(url),
                }
            )

    return results


def search_all_sites(keyword: str):
    """
    Consulta todos los sitios en paralelo para acelerar la búsqueda.
    (Ojo: el filtro de fecha es aún básico; se podría mejorar
    implementando reglas específicas por sitio).
    """
    all_results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_site = {
            executor.submit(search_site, site, keyword): site for site in SITES
        }

        for future in concurrent.futures.as_completed(future_to_site):
            site = future_to_site[future]
            try:
                site_results = future.result()
                all_results.extend(site_results)
            except Exception as e:
                logging.warning(f"Error procesando {site}: {e}")

    # Orden simple: por fuente y título
    all_results.sort(key=lambda x: (x["fuente"], x["titulo"]))
    return all_results


@app.route("/")
def index():
    # Renderiza el sitio HTML principal
    return render_template("index.html")


@app.route("/api/buscar", methods=["POST"])
def api_buscar():
    data = request.get_json(silent=True) or {}
    fecha_inicio = data.get("fechaInicio")
    fecha_fin = data.get("fechaFin")

    # En esta versión, las fechas se reciben pero el filtrado aún es básico.
    # Podrías implementar, más adelante, parsing de fechas específicas por medio.
    logging.info(f"Buscando noticias entre {fecha_inicio} y {fecha_fin}")

    resultados = search_all_sites(KEYWORD)

    return jsonify(
        {
            "success": True,
            "data": {
                "total": len(resultados),
                "resultados": resultados,
            },
        }
    )


if __name__ == "__main__":
    # Para desarrollo local
    app.run(host="0.0.0.0", port=5001, debug=True)
