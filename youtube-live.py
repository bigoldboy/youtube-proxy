import subprocess
import json
import logging
import os
import time
from flask import Flask, request, Response, jsonify
from urllib.parse import unquote

# Ensure UTF-8 encoding
os.environ["PYTHONIOENCODING"] = "utf-8"

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

STREAMLINK_PATH = "streamlink"  # Full path if needed

COMMON_HEADERS = [
    "--http-header",
    "User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "--http-header",
    "Accept-Language=en-US,en;q=0.9"
]


# -----------------------------
# Streamlink JSON Info (with retry)
# -----------------------------
def get_stream_info(url, retries=3):
    last_error = None
    for attempt in range(retries):
        logging.info(f"Fetching stream info (attempt {attempt+1})")

        cmd = [STREAMLINK_PATH, "--json"] + COMMON_HEADERS + [url]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = process.communicate()

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        if process.returncode == 0:
            return json.loads(out), None

        # With --json, streamlink reports failures as {"error": "..."} on stdout
        try:
            reason = json.loads(out).get("error") or out
        except ValueError:
            reason = out
        reason = reason or err or f"streamlink exited with code {process.returncode}"

        logging.warning(f"[STREAMLINK ERROR] {reason}")
        if err:
            logging.warning(f"[STREAMLINK STDERR] {err}")
        last_error = reason
        time.sleep(1)

    return None, last_error


# -----------------------------
# Main Stream Endpoint
# -----------------------------
@app.route("/stream", methods=["GET"])
def stream():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL parameter is required"}), 400

    url = unquote(url)
    client_ip = request.remote_addr

    logging.info(f"[CLIENT CONNECT] {client_ip} → {url}")

    stream_info, error = get_stream_info(url)

    if not stream_info or "streams" not in stream_info:
        return jsonify({
            "error": "Failed to retrieve stream info",
            "detail": error,
        }), 500

    if "best" not in stream_info["streams"]:
        return jsonify({"error": "No valid streams found"}), 404

    # -----------------------------
    # Streamlink execution command
    # -----------------------------
    command = [
        STREAMLINK_PATH,
        "--hls-live-restart",
    ] + COMMON_HEADERS + [
        url,
        "best",
        "--stdout"
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=8192
    )

    def generate():
        try:
            logging.info(f"[STREAM START] {client_ip}")
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
            cleanup_process(process, client_ip)

    response = Response(generate(), content_type="video/mp2t")

    @response.call_on_close
    def cleanup():
        cleanup_process(process, client_ip)

    return response


# -----------------------------
# Cleanup Helper
# -----------------------------
def cleanup_process(process, client_ip):
    if process.poll() is None:
        logging.info(f"[CLEANUP] Terminating process for {client_ip}")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    if process.stdout:
        process.stdout.close()
    if process.stderr:
        process.stderr.close()


# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6095, threaded=True)