from flask import Flask, redirect, jsonify
from playwright.sync_api import sync_playwright
import requests
import time

app = Flask(__name__)

PLAYER_URL = "https://snrt.player.easybroadcast.io/events/73_almaghribia_83tz85q"

BASE_M3U8 = (
STREAM_URL = (
    "https://cdn.live.easybroadcast.io/"
    "abr_corp/73_almaghribia_83tz85q/playlist_dvr.m3u8"
    "abr_corp/73_almaghribia_83tz85q/"
    "corp/73_almaghribia_83tz85q_480p/"
    "chunks_dvr.m3u8"
)

TOKEN_URL = (
    "https://token.easybroadcast.io/all"
    "?url=https%3A%2F%2Fcdn.live.easybroadcast.io%2F"
    "abr_corp%2F73_almaghribia_83tz85q%2F"
    "corp%2F73_almaghribia_83tz85q_480p%2F"
    "chunks_dvr.m3u8"
)

cached_url = None
cached_time = 0


def get_m3u8():
def get_stream():
    global cached_url, cached_time

    # Cache 5 minutes
    if cached_url and time.time() - cached_time < 300:
    # Nouveau token toutes les 2 minutes
    if cached_url and time.time() - cached_time < 120:
        return cached_url

    token_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        page = browser.new_page()

        def capture(response):
            url = response.url

            if "token.easybroadcast.io" in url:
                print("Token URL:", url)
                token_urls.append(url)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://snrtlive.ma/"
    }

        page.on("response", capture)

        page.goto(
            PLAYER_URL,
            wait_until="domcontentloaded",
            timeout=30000
        )

        page.wait_for_timeout(6000)
        browser.close()

    if not token_urls:
        raise Exception("URL de token EasyBroadcast non trouvée")

    token_url = token_urls[-1]
    r = requests.get(
        TOKEN_URL,
        headers=headers,
        timeout=15
    )

    # EasyBroadcast renvoie :
    # token=XXX&token_path=XXX&expires=XXX
    response = requests.get(token_url, timeout=15)
    response.raise_for_status()
    r.raise_for_status()

    token_data = response.text.strip()
    token_data = r.text.strip()

    if "token=" not in token_data:
        raise Exception(
            "Réponse token invalide : " + token_data
            "Réponse EasyBroadcast invalide : " + token_data
        )

    final_url = BASE_M3U8 + "?" + token_data
    final_url = STREAM_URL + "?" + token_data

    cached_url = final_url
    cached_time = time.time()

    print("Final M3U8:", final_url)
    print("STREAM:", final_url)

    return final_url


@app.route("/")
def home():
    return """
    <h2>SNRT Proxy</h2>
    <p>Al Maghribia</p>
    <a href="/almaghribia.m3u8">Flux IPTV</a>
    <h2>SNRT Al Maghribia</h2>
    <p><a href="/almaghribia.m3u8">Ouvrir le flux</a></p>
    """


@app.route("/debug")
def debug():
    try:
        return jsonify({
            "m3u8": get_m3u8()
            "m3u8": get_stream()
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/almaghribia.m3u8")
def almaghribia():
def stream():
    try:
        return redirect(
            get_m3u8(),
            get_stream(),
            code=302
        )

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
