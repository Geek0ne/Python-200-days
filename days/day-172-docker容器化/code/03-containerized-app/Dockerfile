# =============================================================================
# Day 172 实战 —— 生产风格 Dockerfile
# 每条指令的作用都在 Day 172 README 里讲过，这里刻意做成可对照的样板。
# =============================================================================

# ---------- Stage 1: builder（装依赖，可用编译工具链）----------
FROM python:3.12-slim AS builder
WORKDIR /build

# 依赖清单单独 COPY：只有它变了这一层才失效
COPY requirements.txt .

# --no-cache-dir：避免把 pip 缓存写进镜像层（--no-cache 则是构建期参数，不进镜像）
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------- Stage 2: final（干净运行时）----------
FROM python:3.12-slim

# 1) 创建非 root 用户（uid 固定，方便 k8s runAsNonRoot 校验）
RUN useradd -u 10001 -m appuser

WORKDIR /app

# 2) 只从 builder 拷「装好的包」，不拷任何构建中间产物
COPY --from=builder /install/lib/python3.12/site-packages/ \
     /usr/local/lib/python3.12/site-packages/

# 3) 代码归 appuser 所有
COPY --chown=appuser:appuser app.py .

# 4) 切非 root
USER appuser

# 5) 环境配置：日志不缓冲（否则 docker logs 会看到"空"的容器）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_NAME=day172-app \
    PORT=8000

# 6) 声明端口（仅文档，不发布端口）
EXPOSE 8000

# 7) 健康检查：start-period 给应用留启动时间，避免启动慢被误判
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"

# 8) exec form：SIGTERM 能直达 python 进程
CMD ["python", "app.py"]
