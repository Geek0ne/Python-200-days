#!/usr/bin/env python3
"""
Day 183 · 02 — Docker 镜像构建：单体 vs 多阶段

做三件事：
  1. 生成构建上下文（Dockerfile.single / Dockerfile.multi / .dockerignore / requirements.txt）
  2. 真构建两个镜像（--build single|multi|both），量出耗时与体积
  3. 离线自检（--self-test）：把「多阶段该长什么样」钉成断言，不依赖 Docker

关键认知（本课要验证的）：
  - 镜像体积 = 分层 tar 的和。多阶段的价值是**让构建期的东西不进最终镜像**。
  - 我们故意在单体镜像里装了 gcc（真实项目里极常见的失误），用来量化「省下多少」。
    这个 app 的依赖是纯 Python，其实不装 gcc 也能跑——所以多阶段省下的
    主要是「工具链 + 构建残留」，不是「依赖本身」。

用法：
    python3 02-multistage-image.py --self-test
    python3 02-multistage-image.py --out /tmp/day183/build --write-only
    python3 02-multistage-image.py --out /tmp/day183/build --build both
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_SRC = HERE / "01-ops-service.py"          # 被容器化的服务本体
REQUIREMENTS = "prometheus_client==0.26.0\n"  # 真依赖，锁定版本（可复现构建的前提）

DOCKERIGNORE = "\n".join([
    ".git",
    "**/__pycache__",
    "**/*.pyc",
    "tests/",
    "docs/",
    "*.md",
    ".env",
    ".deps/",
    "Dockerfile*",
    "",
])

# --- 单体镜像：一个 FROM，工具链和产物混在一起 --------------------------------
DOCKERFILE_SINGLE = """FROM python:3.12-slim

WORKDIR /app

# ⚠️ 典型的单体失误：把编译工具链装进最终镜像（这里为了量化体积差，故意的）
RUN apt-get update -qq \\
 && apt-get install -y -qq --no-install-recommends gcc \\
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY ops_service.py .

ENV APP_VERSION=dev \\
    PYTHONUNBUFFERED=1

EXPOSE 8080

# slim 镜像里没有 curl，探针要用 python3 自己打（这是很常见的一处想当然）
HEALTHCHECK --interval=5s --timeout=3s --start-period=3s --retries=3 \\
  CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz',timeout=2).status==200 else 1)"

CMD ["python3", "ops_service.py", "--port", "8080"]
"""

# --- 多阶段镜像：builder 装工具链，runtime 只拿 venv ---------------------------
DOCKERFILE_MULTI = """FROM python:3.12-slim AS builder

WORKDIR /build

# 构建期的工具链：只活在 builder 阶段，不会出现在最终镜像里
RUN apt-get update -qq \\
 && apt-get install -y -qq --no-install-recommends gcc \\
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# 依赖装进独立 venv，方便整目录跨阶段搬运
RUN python -m venv /opt/venv \\
 && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY ops_service.py .
# 构建期就验一遍：能编译、能导入、能自检。失败就停在这里，不产生「坏镜像」
RUN /opt/venv/bin/python -m compileall -q ops_service.py \\
 && /opt/venv/bin/python ops_service.py --once > /dev/null \\
 && echo "builder-stage verification OK"

FROM python:3.12-slim AS runtime

ENV APP_VERSION=dev \\
    PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PATH=/opt/venv/bin:$PATH

# 只搬 venv，不搬 gcc、不搬 apt 列表、不搬 pip 缓存
COPY --from=builder /opt/venv /opt/venv
COPY ops_service.py /app/ops_service.py

WORKDIR /app
EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --start-period=3s --retries=3 \\
  CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz',timeout=2).status==200 else 1)"

CMD ["python3", "ops_service.py", "--port", "8080"]
"""


def generate(out: Path) -> dict[str, Path]:
    """把构建上下文写进 out/，返回各文件路径。"""
    out.mkdir(parents=True, exist_ok=True)
    if not APP_SRC.exists():
        raise FileNotFoundError(f"找不到服务源码：{APP_SRC}")
    written = {
        "single": out / "Dockerfile.single",
        "multi": out / "Dockerfile.multi",
        "dockerignore": out / ".dockerignore",
        "requirements": out / "requirements.txt",
        "app": out / "ops_service.py",
    }
    written["single"].write_text(DOCKERFILE_SINGLE, encoding="utf-8")
    written["multi"].write_text(DOCKERFILE_MULTI, encoding="utf-8")
    written["dockerignore"].write_text(DOCKERIGNORE, encoding="utf-8")
    written["requirements"].write_text(REQUIREMENTS, encoding="utf-8")
    shutil.copy2(APP_SRC, written["app"])
    return written


# --- 离线自检 ------------------------------------------------------------------
def analyse(text: str) -> dict:
    """粗解析 Dockerfile：数 FROM / 找阶段名 / 看 COPY --from / 看有没有 apt-get。

    注意：判断「有没有用到某个命令」时**必须先去掉注释**——
    我们的 Dockerfile 注释里就写着「slim 镜像里没有 curl」，
    不剥注释的话这条断言会假失败（本日翻车复盘第 1 条就是这个）。
    """
    code_lines = [l for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    code_text = "\n".join(code_lines)
    stages: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith("FROM "):
            parts = s.split()
            name = parts[-1] if "as" in s.lower() else parts[1]
            stages.append(name if "as" in s.lower() else "<anon>")
    return {
        "from_count": text.upper().count("FROM "),
        "stages": stages,
        "has_builder": "AS builder" in text,
        "has_runtime": "AS runtime" in text,
        "copy_from": "--from=builder" in text,
        "apt_get": "apt-get install" in text,
        "healthcheck_python": "HEALTHCHECK" in text and "python3 -c" in text,
        "no_curl": "curl" not in code_text,   # 只看非注释行
        "cmd": 'CMD ["python3", "ops_service.py", "--port", "8080"]' in text,
    }


def self_test() -> int:
    import tempfile

    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as td:
        written = generate(Path(td))
        single = analyse(written["single"].read_text(encoding="utf-8"))
        multi = analyse(written["multi"].read_text(encoding="utf-8"))

        checks.append(("生成 5 个上下文文件", all(p.exists() for p in written.values())))
        checks.append(("单体：只有 1 个 FROM", single["from_count"] == 1))
        checks.append(("单体：含 apt-get 装 gcc（就要这个反例）", single["apt_get"]))
        checks.append(("多阶段：2 个 FROM，且命名 builder/runtime", multi["from_count"] == 2 and multi["has_builder"] and multi["has_runtime"]))
        checks.append(("多阶段：runtime 来自 COPY --from=builder", multi["copy_from"]))
        checks.append(("多阶段：runtime 阶段没有 apt-get",
                       "apt-get" not in written["multi"].read_text(encoding="utf-8").split("AS runtime")[1]))
        checks.append(("两者都有 HEALTHCHECK 用 python3 而非 curl", single["healthcheck_python"] and multi["healthcheck_python"]))
        checks.append(("两者都不依赖 curl（slim 里没有）", single["no_curl"] and multi["no_curl"]))
        checks.append(("两者 CMD 一致（同一个服务）", single["cmd"] and multi["cmd"]))
        checks.append(("requirements 锁定版本（==）", "==" in written["requirements"].read_text(encoding="utf-8")))
        di = written["dockerignore"].read_text(encoding="utf-8")
        checks.append((".dockerignore 排除 .git / __pycache__ / tests", all(k in di for k in (".git", "__pycache__", "tests/"))))
        checks.append(("多阶段在构建期做过 compileall 校验",
                       "compileall" in written["multi"].read_text(encoding="utf-8")))

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'✅' if ok else '❌'} {n}")
    if failed:
        print(f"❌ self-test 失败：{len(failed)}/{len(checks)} -> {failed}")
        return 1
    print(f"✅ self-test 通过：{len(checks)} 项断言全过（离线，不需要 Docker）")
    return 0


# --- 真构建 --------------------------------------------------------------------
def build_one(out: Path, which: str, tag: str, no_cache: bool) -> dict:
    dockerfile = out / f"Dockerfile.{which}"
    cmd = ["docker", "build", "-f", str(dockerfile), "-t", tag]
    if no_cache:
        cmd.append("--no-cache")
    cmd.append(str(out))
    print(f"▶ docker build -f Dockerfile.{which} -t {tag} {out}")
    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dur = time.monotonic() - t0
    tail = "\n".join([l for l in proc.stdout.splitlines() if l.strip()][-3:])
    if proc.returncode != 0:
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:], file=sys.stderr)
        raise SystemExit(f"❌ 构建 {which} 失败（exit={proc.returncode}）")

    size = int(subprocess.run(["docker", "image", "inspect", tag, "--format", "{{.Size}}"],
                              capture_output=True, text=True).stdout.strip())
    layers = subprocess.run(["docker", "history", "--no-trunc", "--format", "{{.Size}}\t{{.CreatedBy}}", tag],
                            capture_output=True, text=True).stdout.strip().splitlines()
    return {
        "variant": which,
        "tag": tag,
        "seconds": round(dur, 2),
        "size_bytes": size,
        "size_mb": round(size / 1024 / 1024, 1),
        "layers": len(layers),
        "tail": tail,
    }


def cmd_build(out: Path, which: str, tag_prefix: str, no_cache: bool) -> int:
    results = []
    if which in ("single", "both"):
        results.append(build_one(out, "single", f"{tag_prefix}:single", no_cache))
    if which in ("multi", "both"):
        results.append(build_one(out, "multi", f"{tag_prefix}:multi", no_cache))

    print("\n镜像实测：")
    print(f"  {'变体':<8}{'标签':<34}{'体积':>9}{'层数':>6}{'构建耗时':>10}")
    for r in results:
        print(f"  {r['variant']:<8}{r['tag']:<34}{str(r['size_mb']) + ' MB':>9}{r['layers']:>6}{str(r['seconds']) + 's':>10}")

    if len(results) == 2:
        s, m = results[0]["size_bytes"], results[1]["size_bytes"]
        saved = s - m
        print(f"\n  多阶段省下：{saved / 1024 / 1024:.1f} MB（单体 {s/1024/1024:.1f} MB 的 {saved/s*100:.1f}%）")
    (out / "build-report.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  报告写入：{out / 'build-report.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Day 183 · 镜像构建（单体 / 多阶段）")
    p.add_argument("--out", default="/tmp/day183/build", help="构建上下文目录")
    p.add_argument("--write-only", action="store_true", help="只生成构建上下文，不构建")
    p.add_argument("--build", choices=["none", "single", "multi", "both"], default="none")
    p.add_argument("--tag-prefix", default="day183-ops", help="镜像名前缀")
    p.add_argument("--no-cache", action="store_true", help="禁用构建缓存（更慢但更接近 CI 首跑）")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)

    if args.self_test:
        return self_test()

    out = Path(args.out)
    written = generate(out)
    print(f"✅ 构建上下文已生成 → {out}")
    for k, v in written.items():
        print(f"   {k:<14} {v.name:<20} {v.stat().st_size} 字节")

    if args.write_only or args.build == "none":
        return 0
    return cmd_build(out, args.build, args.tag_prefix, args.no_cache)


if __name__ == "__main__":
    sys.exit(main())
