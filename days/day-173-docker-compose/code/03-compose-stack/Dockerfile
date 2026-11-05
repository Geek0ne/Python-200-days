# Day 173 实验镜像：Compose 里的 app / worker 共用同一镜像、只靠 command 区分
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /srv

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py worker.py ./

# 非 root 运行：compose 里可用 user: 覆盖，但先给个安全的默认值
RUN useradd -u 10001 -m appuser && chown -R appuser /srv
USER appuser

EXPOSE 8000
CMD ["python", "app.py", "--port", "8000"]