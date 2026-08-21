from flask import Flask, redirect, jsonify
from playwright.sync_api import sync_playwright
import requests
import time

app = Flask(__name__)

PLAYER_URL = (
    "https://snrt.player.easybroadcast.io/"
    "events/73_almaghribia_83tz85q"
)

BASE_M3U8 = (
    "https://cdn.live.easybroadcast.io/"
    "abr_corp/73_almaghribia_83tz85q/"
    "playlist_dvr.m3u8"
)

cached_url = None
cached_time = 0


def get_m3u8():
    global cached_url, cached_time

    # Renouvellement toutes les 2 minutes
    if cached_url and time.time() - cached_time < 120:
        return cached_url

    token_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        page = browser.new_page()

        def capture(response):
            url = response.url

            if "token.easybroadcast.io" in url:
                print("TOKEN URL:", url)
                token_urls.append(url)

        page.on("response", capture)

        page.goto(
            PLAYER_URL,
            wait_until="domcontentloaded",
            timeout=30000
        )

        page.wait_for_timeout(7000)

        browser.close()

    if not token_urls:
        raise Exception(
            "Impossible de récupérer le token EasyBroadcast"
        )

    # Prend l'appel de token correspondant au master
    master_tokens = [
        u for u in token_urls
        if "playlist_dvr.m3u8" in u
    ]

    if master_tokens:
        token_url = master_tokens[-1]
    else:
        token_url = token_urls[-1]

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": PLAYER_URL
    }

    r = requests.get(
        token_url,
        headers=headers,
        timeout=15
    )

    r.raise_for_status()

    token_data = r.text.strip()

    if "token=" not in token_data:
        raise Exception(
            "Token EasyBroadcast invalide : " + token_data
        )

    final_url = BASE_M3U8 + "?" + token_data

    cached_url = final_url
    cached_time = time.time()

    print("FINAL:", final_url)

    return final_url


@app.route("/")
def home():
    return """
    <h2>Al Maghribia</h2>
    <p>
        <a href="/almaghribia.m3u8">
            Ouvrir Al Maghribia
        </a>
    </p>
    """


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


@app.route("/almaghribia.m3u8")
def stream():
    try:
        return redirect(
            get_m3u8(),
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
