import logging
import os
import shutil
import subprocess
import tempfile
from urllib.parse import unquote

from flask import Flask, Response, jsonify, request

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

YTDLP_PATH = os.environ.get("YTDLP_PATH", "yt-dlp")

# Netscape-format cookies.txt exported from a signed-in browser. YouTube now
# asks many home IPs to "sign in to confirm you're not a bot", and cookies are
# the only reliable way past that check. Optional: skipped if the file is absent.
COOKIES_FILE = os.environ.get("COOKIES_FILE", "/cookies/cookies.txt")

YTDLP_ARGS = [
    "--quiet",
    "--no-warnings",
    "--no-playlist",
    "--no-part",
    "-f", "best",
]


def cookies_copy():
    """yt-dlp rewrites the cookies file it is given, so hand each process its
    own copy. That keeps concurrent streams from clobbering each other and lets
    the user's file be mounted read-only."""
    if not os.path.isfile(COOKIES_FILE):
        return None
    fd, path = tempfile.mkstemp(prefix="cookies-", suffix=".txt")
    os.close(fd)
    shutil.copyfile(COOKIES_FILE, path)
    return path


@app.route("/stream", methods=["GET"])
def stream():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL parameter is required"}), 400

    url = unquote(url)
    client_ip = request.remote_addr
    logging.info(f"[CLIENT CONNECT] {client_ip} → {url}")

    cookies = cookies_copy()
    command = [YTDLP_PATH] + YTDLP_ARGS
    if cookies:
        command += ["--cookies", cookies]
    command += ["-o", "-", url]

    # stderr goes to a temp file so a chatty yt-dlp/ffmpeg can never fill a
    # pipe nobody reads and stall the stream.
    errlog = tempfile.TemporaryFile()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=errlog,
        bufsize=8192
    )
    process.errlog = errlog

    # Wait for the first bytes so a failure (bot check, not live, bad URL)
    # comes back as an error with yt-dlp's reason instead of an empty stream.
    first_chunk = process.stdout.read(8192)
    if not first_chunk:
        process.wait()
        errlog.seek(0)
        error = errlog.read().decode("utf-8", errors="replace").strip()
        error = error or f"yt-dlp exited with code {process.returncode}"
        logging.warning(f"[YT-DLP ERROR] {error}")
        cleanup_process(process, client_ip, cookies)
        return jsonify({"error": "Failed to start stream", "detail": error}), 502

    def generate():
        try:
            logging.info(f"[STREAM START] {client_ip}")
            yield first_chunk
            while True:
                chunk = process.stdout.read(8192)
                if not chunk:
                    break
                yield chunk
        except GeneratorExit:
            logging.info(f"[CLIENT DISCONNECTED] {client_ip}")
        except Exception as e:
            logging.error(f"[STREAM ERROR] {e}")
        finally:
            cleanup_process(process, client_ip, cookies)

    response = Response(generate(), content_type="video/mp2t")

    @response.call_on_close
    def cleanup():
        cleanup_process(process, client_ip, cookies)

    return response


def cleanup_process(process, client_ip, cookies=None):
    if process.poll() is None:
        logging.info(f"[CLEANUP] Terminating process for {client_ip}")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    for f in (process.stdout, getattr(process, "errlog", None)):
        if f and not f.closed:
            f.close()

    if cookies and os.path.exists(cookies):
        os.remove(cookies)


if __name__ == "__main__":
    if os.path.isfile(COOKIES_FILE):
        logging.info(f"Using cookies from {COOKIES_FILE}")
    else:
        logging.info(f"No cookies file at {COOKIES_FILE}; YouTube may ask to confirm you're not a bot")
    app.run(host="0.0.0.0", port=6095, threaded=True)