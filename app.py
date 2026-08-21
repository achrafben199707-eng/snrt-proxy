from flask import Flask, Response, request, jsonify
import requests
from urllib.parse import urljoin, quote
import time

app = Flask(__name__)

BASE = (
    "https://cdn.live.easybroadcast.io/"
    "abr_corp/73_almaghribia_83tz85q/"
)

MASTER = BASE + "playlist_dvr.m3u8"

TOKEN_API = (
    "https://token.easybroadcast.io/all"
    "?url="
    + quote(MASTER, safe="")
)

cached_token = None
cached_time = 0


def get_token():
    global cached_token, cached_time

    # Renouvelle toutes les 2 minutes
    if cached_token and time.time() - cached_time < 120:
        return cached_token

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://snrtlive.ma/"
    }

    r = requests.get(
        TOKEN_API,
        headers=headers,
        timeout=15
    )

    r.raise_for_status()

    data = r.text.strip()

    if "token=" not in data:
        raise Exception(
            "Token EasyBroadcast invalide : " + data
        )

    cached_token = data
    cached_time = time.time()

    return data


def signed_url(url):
    token = get_token()

    sep = "&" if "?" in url else "?"

    return url + sep + token


def rewrite_playlist(text, original_url):
    lines = []

    for line in text.splitlines():

        # Commentaires HLS
        if line.startswith("#"):
            lines.append(line)
            continue

        # Ligne vide
        if not line.strip():
            lines.append(line)
            continue

        absolute = urljoin(original_url, line.strip())

        proxy_url = (
            "/proxy?url="
            + quote(absolute, safe="")
        )

        lines.append(proxy_url)

    return "\n".join(lines)


@app.route("/")
def home():
    return """
    <h2>SNRT Al Maghribia Proxy</h2>
    <p>
        <a href="/almaghribia.m3u8">
            Al Maghribia
        </a>
    </p>
    """


@app.route("/almaghribia.m3u8")
def almaghribia():

    try:
        url = signed_url(MASTER)

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://snrtlive.ma/"
        }

        r = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        r.raise_for_status()

        playlist = rewrite_playlist(
            r.text,
            MASTER
        )

        return Response(
            playlist,
            content_type="application/vnd.apple.mpegurl"
        )

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/proxy")
def proxy():

    target = request.args.get("url")

    if not target:
        return "URL manquante", 400

    try:
        url = signed_url(target)

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://snrtlive.ma/"
        }

        r = requests.get(
            url,
            headers=headers,
            timeout=30,
            stream=True
        )

        r.raise_for_status()

        content_type = r.headers.get(
            "Content-Type",
            "application/octet-stream"
        )

        # Si c'est encore une playlist M3U8
        if ".m3u8" in target:
            playlist = rewrite_playlist(
                r.text,
                target
            )

            return Response(
                playlist,
                content_type="application/vnd.apple.mpegurl"
            )

        # Sinon segment vidéo/audio
        return Response(
            r.iter_content(chunk_size=64 * 1024),
            content_type=content_type
        )

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/debug")
def debug():
    try:
        return jsonify({
            "master": MASTER,
            "token": get_token()
        })
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
