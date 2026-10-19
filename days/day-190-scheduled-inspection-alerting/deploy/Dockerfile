FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /data/worker && chown -R app:app /data
COPY app/ /app/

USER app

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status==200 else 1)"

CMD ["python", "sink.py"]
