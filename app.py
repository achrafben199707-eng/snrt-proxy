from flask import Flask, redirect, jsonify
import requests
import time
from urllib.parse import quote

app = Flask(__name__)


# ============================================================
# CHAÎNES SNRT
# ============================================================

CHANNELS = {

    "almaghribia": {
        "id": "73_almaghribia_83tz85q",
        "quality": "480p"
    },

    "alaoula": {
        "id": "73_aloula_w1dqfwm",
        "quality": "480p"
    },

    "arryadia": {
        "id": "73_arryadia_k2tgcj0",
        "quality": "480p"
    },

    "tamazight": {
        "id": "73_tamazight_tccybxt",
        "quality": "480p"
    }
}


# ============================================================
# CACHE
# ============================================================

cache = {}

CACHE_SECONDS = 120


# ============================================================
# CONSTRUCTION URL STREAM
# ============================================================

def build_stream_url(channel):

    info = CHANNELS[channel]

    channel_id = info["id"]
    quality = info["quality"]

    return (
        "https://cdn.live.easybroadcast.io/"
        f"abr_corp/{channel_id}/"
        f"corp/{channel_id}_{quality}/"
        "chunks_dvr.m3u8"
    )


# ============================================================
# RÉCUPÉRATION TOKEN
# ============================================================

def get_stream(channel):

    if channel not in CHANNELS:
        raise Exception("Chaîne inconnue")

    now = time.time()

    # Cache pendant 2 minutes
    if channel in cache:

        if now - cache[channel]["time"] < CACHE_SECONDS:
            return cache[channel]["url"]

    stream_url = build_stream_url(channel)

    token_url = (
        "https://token.easybroadcast.io/all"
        "?url=" + quote(stream_url, safe="")
    )

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://snrtlive.ma/"
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
            "Réponse EasyBroadcast invalide : "
            + token_data
        )

    final_url = stream_url + "?" + token_data

    cache[channel] = {
        "url": final_url,
        "time": time.time()
    }

    print(channel, ":", final_url)

    return final_url


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.route("/")
def home():

    return """
    <h2>SNRT Live</h2>

    <p>
    <a href="/almaghribia.m3u8">
    Al Maghribia
    </a>
    </p>

    <p>
    <a href="/alaoula.m3u8">
    Al Aoula
    </a>
    </p>

    <p>
    <a href="/arryadia.m3u8">
    Arryadia
    </a>
    </p>

    <p>
    <a href="/tamazight.m3u8">
    Tamazight
    </a>
    </p>
    """


# ============================================================
# DEBUG
# ============================================================

@app.route("/debug/<channel>")
def debug(channel):

    try:

        return jsonify({
            "channel": channel,
            "m3u8": get_stream(channel)
        })

    except Exception as e:

        return jsonify({
            "channel": channel,
            "error": str(e)
        }), 500


# ============================================================
# STREAM
# ============================================================

@app.route("/<channel>.m3u8")
def stream(channel):

    try:

        return redirect(
            get_stream(channel),
            code=302
        )

    except Exception as e:

        return jsonify({
            "channel": channel,
            "error": str(e)
        }), 500


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )
