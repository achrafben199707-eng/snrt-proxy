from flask import Flask, redirect, jsonify
from playwright.sync_api import sync_playwright
import time

app = Flask(__name__)

PLAYERS = {
    "alaoula":
        "https://snrt.player.easybroadcast.io/events/73_aloula_w1dqfwm",

    "arryadia":
        "https://snrt.player.easybroadcast.io/events/73_arryadia_k2tgcj0",

    "tamazight":
        "https://snrt.player.easybroadcast.io/events/73_tamazight_tccybxt",

    "almaghribia":
        "https://snrt.player.easybroadcast.io/events/73_almaghribia_83tz85q",
}

cache = {}
CACHE_SECONDS = 120


def choose_stream(urls):

    # Priorité au flux vidéo réellement chargé
    chunks = [
        u for u in urls
        if (
            "chunks_dvr.m3u8" in u
            and "cdn.live.easybroadcast.io" in u
            and "token=" in u
        )
    ]

    if chunks:
        return chunks[-1]

    # Sinon n'importe quel flux M3U8 signé du CDN
    cdn = [
        u for u in urls
        if (
            ".m3u8" in u
            and "cdn.live.easybroadcast.io" in u
            and "token=" in u
        )
    ]

    if cdn:
        return cdn[-1]

    raise Exception("Aucun flux vidéo trouvé")


def get_m3u8(channel):

    if channel not in PLAYERS:
        raise Exception("Chaîne inconnue")

    now = time.time()

    # Cache pendant 2 minutes
    if channel in cache:
        if now - cache[channel]["time"] < CACHE_SECONDS:
            return cache[channel]["url"]

    player_url = PLAYERS[channel]

    found = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--autoplay-policy=no-user-gesture-required"
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131 Safari/537.36"
            )
        )

        page = context.new_page()

        def capture_request(request):

            url = request.url

            if ".m3u8" in url:
                print(channel, "M3U8:", url)

                if url not in found:
                    found.append(url)

        page.on("request", capture_request)

        print("Opening:", player_url)

        page.goto(
            player_url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        # Essaie de lancer automatiquement la vidéo
        try:
            page.locator("video").evaluate(
                """
                v => {
                    v.muted = true;
                    v.play();
                }
                """
            )
        except Exception:
            pass

        # Attend que le player charge le flux
        page.wait_for_timeout(15000)

        browser.close()

    if not found:
        raise Exception(
            "Aucun M3U8 trouvé pour " + channel
        )

    final_url = choose_stream(found)

    cache[channel] = {
        "url": final_url,
        "time": time.time()
    }

    print(channel, "FINAL:", final_url)

    return final_url


@app.route("/")
def home():

    return """
    <h2>SNRT IPTV Proxy</h2>

    <p><a href="/alaoula.m3u8">
    Al Aoula
    </a></p>

    <p><a href="/arryadia.m3u8">
    Arryadia
    </a></p>

    <p><a href="/tamazight.m3u8">
    Tamazight
    </a></p>

    <p><a href="/almaghribia.m3u8">
    Al Maghribia
    </a></p>
    """


@app.route("/debug/<channel>")
def debug(channel):

    try:

        url = get_m3u8(channel)

        return jsonify({
            "channel": channel,
            "quality": "auto",
            "m3u8": url
        })

    except Exception as e:

        return jsonify({
            "channel": channel,
            "error": str(e)
        }), 500


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


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
