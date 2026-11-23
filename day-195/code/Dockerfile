# syntax=docker/dockerfile:1.7
# ── 构建阶段：只在这里装依赖，运行镜像里没有 pip 缓存和编译工具 ──
FROM python:3.12-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ── 运行阶段 ──
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    PORT=8080

# 非 root 运行：容器逃逸后的第一道止损线
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app \
      --shell /usr/sbin/nologin app

COPY --from=builder /install /usr/local
WORKDIR /app
COPY ops_lib.py crypto_lib.py app.py ./
RUN mkdir -p /data && chown -R app:app /app /data

USER app
EXPOSE 8080

# ⚠️ 不要用 curl：python:3.12-slim 里没有 curl。
# 第一次写这一行时镜像一直 unhealthy，日志里是 "curl: not found"。
HEALTHCHECK --interval=5s --timeout=3s --start-period=8s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2).status == 200 else 1)"]

CMD ["python", "app.py"]
