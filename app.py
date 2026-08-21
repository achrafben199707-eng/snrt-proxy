from flask import Flask, redirect, jsonify
import requests
import time

app = Flask(__name__)

STREAM_URL = (
    "https://cdn.live.easybroadcast.io/"
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


def get_stream():
    global cached_url, cached_time

    # Nouveau token toutes les 2 minutes
    if cached_url and time.time() - cached_time < 120:
        return cached_url

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://snrtlive.ma/"
    }

    r = requests.get(
        TOKEN_URL,
        headers=headers,
        timeout=15
    )

    r.raise_for_status()

    token_data = r.text.strip()

    if "token=" not in token_data:
        raise Exception(
            "Réponse EasyBroadcast invalide : " + token_data
        )

    final_url = STREAM_URL + "?" + token_data

    cached_url = final_url
    cached_time = time.time()

    print("STREAM:", final_url)

    return final_url


@app.route("/")
def home():
    return """
    <h2>SNRT Al Maghribia</h2>
    <p><a href="/almaghribia.m3u8">Ouvrir le flux</a></p>
    """


@app.route("/debug")
def debug():
    try:
        return jsonify({
            "m3u8": get_stream()
        })
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/almaghribia.m3u8")
def stream():
    try:
        return redirect(
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
