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


def get_m3u8(channel):
    if channel not in CHANNELS:
        raise Exception("Chaîne inconnue")

    now = time.time()

    # Utiliser le cache pendant 2 minutes
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

            # On cherche un vrai flux EasyBroadcast signé
            if (
                "cdn.live.easybroadcast.io" in url
                and ".m3u8" in url
                and "token=" in url
            ):
                print(channel, "M3U8:", url)
                found.append(url)

        page.on("response", capture)

        page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        # Laisse le temps au player de démarrer
        page.wait_for_timeout(10000)

        browser.close()

    if not found:
        raise Exception(
            "Aucun flux M3U8 signé trouvé pour " + channel
        )

    # Priorité au flux chunks_dvr qui fonctionnait dans SS IPTV
    chunks = [
        url for url in found
        if "chunks_dvr.m3u8" in url
    ]

    if chunks:
        final_url = chunks[-1]
    else:
        final_url = found[-1]

    cache[channel] = {
        "url": final_url,
        "time": now
    }

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
        return jsonify({
            "channel": channel,
            "m3u8": get_m3u8(channel)
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
