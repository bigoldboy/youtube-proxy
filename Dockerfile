FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1

# Streamlink comes from pip so it is current; YouTube changes are usually fixed
# by a newer streamlink, which a rebuild picks up.
RUN pip install --upgrade flask streamlink

WORKDIR /app
COPY youtube-live.py ./

RUN useradd --system --uid 1000 app && chown -R app /app
USER app

EXPOSE 6095
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s \
  CMD python -c "import socket; socket.create_connection(('127.0.0.1', 6095), 3)"

CMD ["python3", "youtube-live.py"]
