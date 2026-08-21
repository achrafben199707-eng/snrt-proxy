from flask import Flask, redirect, jsonify
from playwright.sync_api import sync_playwright
import time

app = Flask(__name__)

PLAYER_URL = "https://snrt.player.easybroadcast.io/events/73_almaghribia_83tz85q"

cached_url = None
cached_time = 0


def get_m3u8():
    global cached_url, cached_time

    # Cache 5 minutes
    if cached_url and time.time() - cached_time < 300:
        return cached_url

    urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/131 Safari/537.36"
            )
        )

        def capture(response):
            url = response.url

            if ".m3u8" in url:
                print("M3U8:", url)
                urls.append(url)

        page.on("response", capture)

        page.goto(
            PLAYER_URL,
            wait_until="domcontentloaded",
            timeout=30000
        )

        page.wait_for_timeout(8000)

        browser.close()

    if not urls:
        raise Exception("Aucun flux M3U8 trouvé")

    # Priorité au flux 480p que tu utilisais
    preferred = [
        url for url in urls
        if "chunks_dvr.m3u8" in url
    ]

    final_url = preferred[-1] if preferred else urls[-1]

    cached_url = final_url
    cached_time = time.time()

    return final_url


@app.route("/")
def home():
    return """
    <h2>SNRT Proxy</h2>
    <p>Al Maghribia</p>
    <a href="/almaghribia.m3u8">Flux IPTV</a>
    """


@app.route("/almaghribia.m3u8")
def almaghribia():
    try:
        url = get_m3u8()
        return redirect(url, code=302)

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/debug")
def debug():
    try:
        return jsonify({
            "m3u8": get_m3u8()
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500