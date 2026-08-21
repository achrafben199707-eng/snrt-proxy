from flask import Flask, redirect, jsonify
from playwright.sync_api import sync_playwright
import time

app = Flask(__name__)

CHANNELS = {
    "alaoula": "https://snrtlive.ma/fr/al-aoula",
    "arryadia": "https://snrtlive.ma/fr/arryadia",
    "assadissa": "https://snrtlive.ma/fr/assadissa",
    "tamazight": "https://snrtlive.ma/fr/tamazight",
    "almaghribia": "https://snrtlive.ma/fr/almaghribia",
}

cache = {}
CACHE_SECONDS = 120


def select_best_stream(urls):

    chunks = [
        u for u in urls
        if "chunks_dvr.m3u8" in u
    ]

    # 1. Priorité 720p
    quality_720 = [
        u for u in chunks
        if "720p" in u.lower() or "_720_" in u.lower()
    ]

    if quality_720:
        print("720p sélectionné")
        return quality_720[-1]

    # 2. Sinon 480p
    quality_480 = [
        u for u in chunks
        if "480p" in u.lower() or "_480_" in u.lower()
    ]

    if quality_480:
        print("720p indisponible -> 480p sélectionné")
        return quality_480[-1]

    # 3. Sinon un autre chunks_dvr
    if chunks:
        print("Qualité automatique sélectionnée")
        return chunks[-1]

    # 4. Dernier recours
    if urls:
        return urls[-1]

    raise Exception("Aucun flux disponible")


def get_m3u8(channel):

    if channel not in CHANNELS:
        raise Exception("Chaîne inconnue")

    now = time.time()

    if channel in cache:
        if now - cache[channel]["time"] < CACHE_SECONDS:
            return cache[channel]["url"]

    page_url = CHANNELS[channel]

    found = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131 Safari/537.36"
            )
        )

        def capture(response):

            url = response.url

            if (
                "cdn.live.easybroadcast.io" in url
                and ".m3u8" in url
                and "token=" in url
            ):
                print(channel, ":", url)

                if url not in found:
                    found.append(url)

        page.on("response", capture)

        page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        # Attend les différentes qualités du player
        page.wait_for_timeout(10000)

        browser.close()

    if not found:
        raise Exception(
            "Aucun M3U8 trouvé pour " + channel
        )

    final_url = select_best_stream(found)

    cache[channel] = {
        "url": final_url,
        "time": now
    }

    print("Flux final :", final_url)

    return final_url


@app.route("/")
def home():

    return """
    <h2>SNRT IPTV Proxy</h2>

    <p><a href="/alaoula.m3u8">Al Aoula</a></p>
    <p><a href="/arryadia.m3u8">Arryadia</a></p>
    <p><a href="/assadissa.m3u8">Assadissa</a></p>
    <p><a href="/tamazight.m3u8">Tamazight</a></p>
    <p><a href="/almaghribia.m3u8">Al Maghribia</a></p>
    """


@app.route("/<channel>.m3u8")
def stream(channel):

    try:

        return redirect(
            get_m3u8(channel),
            code=302
        )

    except Exception as e:

        return jsonify({
            "channel": channel,
            "error": str(e)
        }), 500


@app.route("/debug/<channel>")
def debug(channel):

    try:

        url = get_m3u8(channel)

        quality = "unknown"

        if "720p" in url.lower():
            quality = "720p"
        elif "480p" in url.lower():
            quality = "480p"

        return jsonify({
            "channel": channel,
            "quality": quality,
            "m3u8": url
        })

    except Exception as e:

        return jsonify({
            "channel": channel,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
