FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1

# ffmpeg: yt-dlp uses it to pipe live HLS out as MPEG-TS.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# deno: YouTube extraction in yt-dlp needs a JavaScript runtime.
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

# yt-dlp comes from pip so it is current; YouTube changes are usually fixed
# by a newer yt-dlp, which the weekly rebuild picks up. [default] pulls in
# yt-dlp-ejs, the scripts deno runs for YouTube.
RUN pip install --upgrade flask "yt-dlp[default]"

WORKDIR /app
COPY youtube-live.py ./

RUN useradd --system --uid 1000 app && chown -R app /app
USER app

EXPOSE 6095
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s \
  CMD python -c "import socket; socket.create_connection(('127.0.0.1', 6095), 3)"

CMD ["python3", "youtube-live.py"]
