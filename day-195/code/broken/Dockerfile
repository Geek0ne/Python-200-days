FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY broken_app.py ./
EXPOSE 8080
HEALTHCHECK --interval=2s --timeout=1s --start-period=1s --retries=2 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=1).status == 200 else 1)"]
CMD ["python", "broken_app.py"]
