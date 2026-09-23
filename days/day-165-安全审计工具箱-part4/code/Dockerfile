# syntax=docker/dockerfile:1
#
# Dockerfile — 安全审计工具箱 · 报告生成器镜像（Day 165）
#
# 构建（在 code/ 目录下执行）：
#     docker build -t audit-toolbox:1.0 .
#
# 运行（只读根文件系统 + 无网络，最保守的默认）：
#     docker run --rm --network none --read-only \
#         --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges \
#         -v "$PWD/findings.example.json:/data/findings.json:ro" \
#         -v "$PWD/out:/out" \
#         audit-toolbox:1.0 --input /data/findings.json --format all --out-dir /out
#
# ─── 为什么这样写（每一条都是刻意的） ───────────────────────────────
#
# 1) 多阶段构建（multi-stage）
#    构建阶段装依赖、编译扩展；运行阶段只拷贝"装好的结果"。
#    结果是运行镜像里没有 pip 的构建垃圾、没有编译器、也没有缓存。
#    镜像越小 → 攻击面越小、拉取越快、扫描越干净。
#
# 2) 固定基础镜像的精确版本 + 摘要
#    `python:3.12-slim` 是会漂移的标签。今天构建和三个月后构建
#    可能拿到不同的解释器。审计工具的可复现性依赖"同一输入 → 同一输出"，
#    基础镜像漂移会直接破坏这个前提。
#    生产上应固定到 digest（形如 python:3.12-slim@sha256:...）。
#
# 3) 非 root 运行（uid 10001）
#    容器里默认是 root，而 root 在容器里逃逸到宿主的风险不是零。
#    用一个高位 uid 的普通用户，即使被攻破也只拿到一个空壳权限。
#
# 4) ENTRYPOINT 用 **exec 形式**（JSON 数组），不是 shell 形式
#    shell 形式会让进程以 `/bin/sh -c` 为 PID 1，
#    `docker stop` 发的 SIGTERM 会被 sh 吃掉，容器只能等超时被 SIGKILL。
#    同时 exec 形式能让脚本的**退出码直接冒泡**给 docker/CI。
#    ——这一点对本工具尤其关键：我们的门禁完全建立在退出码上。
#
# 5) 不打 pyc、不缓冲输出
#    PYTHONDONTWRITEBYTECODE=1：只读根文件系统下写 __pycache__ 会报错。
#    PYTHONUNBUFFERED=1：日志立刻可见，CI 里能实时看到进度。

# ─────────────── 阶段 1：构建 ───────────────
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# 依赖清单先拷贝：只要依赖没变，这一层就命中缓存。
# 这是 Docker 分层缓存最经典的一条优化——把"变得少的"放前面。
COPY requirements.txt ./
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

# ─────────────── 阶段 2：运行 ───────────────
FROM python:3.12-slim AS runtime

# 可复现构建的既有约定：固定时间戳，让产物（含报告）字节级稳定
ARG SOURCE_DATE_EPOCH=1758664800
ENV SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    AUDIT_OUT_DIR=/out

# 只读挂载点。声明 VOLUME 的目的是提醒使用者：
# "报告要写到容器外"，容器本身是**无状态、可随时销毁**的。
VOLUME ["/out"]

LABEL org.opencontainers.image.title="audit-toolbox" \
      org.opencontainers.image.description="安全审计报告生成器（Day 165 阶段项目）" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.licenses="MIT"

# 非 root 用户。--no-create-home 省一层数据，
# 这个容器不需要 home 目录（也不需要写权限）。
RUN groupadd --gid 10001 app \
 && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=10001:10001 report_core.py 03-toolbox-cli.py /app/

WORKDIR /app
USER 10001:10001

# 健康检查：容器"活着"不等于"能用"。
# 这里用 --help 做真实可执行性检查（比只看进程存在强得多）。
HEALTHCHECK --interval=60s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "03-toolbox-cli.py", "--help"]

# ⚠️ 注意：不要把 findings.json 烤进镜像。
# 审计数据属于客户/内部敏感数据，属于**运行时挂载**，不属于镜像层。
# 镜像会被推送、被缓存、被拉取——一旦数据进层，就再也删不干净了。

ENTRYPOINT ["python", "03-toolbox-cli.py"]
CMD ["--input", "/data/findings.json", "--format", "all", "--out-dir", "/out"]
