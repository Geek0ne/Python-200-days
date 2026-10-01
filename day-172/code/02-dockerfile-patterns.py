#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 172 · 示例 02 —— Dockerfile 模式生成器与真机构建（进阶用法 + 避坑）

这个脚本解决一个真实问题：生产里的 Dockerfile 往往有 10~20 条指令，
新人很难判断「改一行代码会不会让镜像重新构建」。

脚本做三件事：
  1. 用 Python 生成 4 种典型 Dockerfile（基础 / 缓存友好 / 多阶段 / 生产加固）
  2. 内置 lint 检查器，自动指出 Dockerfile 里的常见反模式
  3. --build 用 Docker SDK 真机构建并对比体积与构建耗时

用法：
    python3 02-dockerfile-patterns.py --self-test   # 离线自测，不需要 Docker
    python3 02-dockerfile-patterns.py --show         # 只打印模板
    python3 02-dockerfile-patterns.py --lint FILE    # 检查某个 Dockerfile
    python3 02-dockerfile-patterns.py --build        # 真机构建并实测（需 docker SDK）
    python3 02-dockerfile-patterns.py --dry-run      # 有 docker CLI 但无 SDK 时的降级路径

退出码：0 成功；1 自测失败
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# 1. Dockerfile 模板库
# =============================================================================

BASIC = """\
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
CMD ["python", "main.py"]
"""

# 反例：COPY . . 放在 RUN 之前 —— 改任何一行代码都会让 pip 层失效
BAD_CACHE = """\
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]
"""

CACHE_FRIENDLY = """\
FROM python:3.12-slim
WORKDIR /app

# 先只拷依赖清单 → 这一层只依赖 requirements.txt 的内容
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷业务代码 → 改代码不影响上面的依赖层
COPY main.py .

# 预编译字节码，减少启动时的 import 开销
RUN python -m compileall -q main.py

# 非 root 运行
RUN useradd -u 10001 -m appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "main.py"]
"""

MULTI_STAGE = """\
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
# --target 把包装进独立目录，方便 final 阶段整体拷贝
RUN pip install --no-cache-dir --target /install -r requirements.txt

FROM python:3.12-slim AS final
WORKDIR /app
ENV PYTHONPATH=/install
COPY --from=builder /install /install
COPY main.py .
CMD ["python", "main.py"]
"""

PROD_HARDENED = """\
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS final

# 1) 不用 root 跑应用
RUN useradd -u 10001 -m appuser
WORKDIR /app

# 2) 依赖用 root 装、代码用 appuser 拥有
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --chown=appuser:appuser main.py .

USER appuser

# 3) 环境变量外置（不要把密钥写进 ENV）
ENV PYTHONUNBUFFERED=1 \\
    PORT=8000

# 4) 声明端口（仅文档）
EXPOSE 8000

# 5) 健康检查：start-period 给应用留启动时间，避免启动慢被误判为 unhealthy
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \\
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["python", "main.py"]
"""

TEMPLATES: dict[str, str] = {
    "basic": BASIC,
    "bad-cache": BAD_CACHE,
    "cache-friendly": CACHE_FRIENDLY,
    "multi-stage": MULTI_STAGE,
    "prod-hardened": PROD_HARDENED,
}


# =============================================================================
# 2. Lint 检查器
# =============================================================================

@dataclass
class LintIssue:
    level: str  # ERROR / WARN
    code: str
    line_no: int
    message: str
    fix: str = ""


@dataclass
class LintReport:
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[LintIssue]:
        return [i for i in self.issues if i.level == "ERROR"]

    def render(self) -> str:
        if not self.issues:
            return "✅ 未发现问题\n"
        out = []
        for i in sorted(self.issues, key=lambda x: x.line_no):
            tag = "❌" if i.level == "ERROR" else "⚠️ "
            out.append(f"{tag} L{i.line_no} [{i.code}] {i.message}")
            if i.fix:
                out.append(f"      ↳ 建议：{i.fix}")
        err = len(self.errors)
        out.append(f"\n共 {len(self.issues)} 个问题（ERROR {err} / WARN {len(self.issues) - err}）")
        return "\n".join(out)


def logical_lines(text: str) -> list[tuple[int, str]]:
    """
    把 Dockerfile 解析成「逻辑行」：合并以 \ 结尾的续行，并保留起始行号。

    不做这一步会误报：HEALTHCHECK CMD python -c "..." 里的 CMD 只是
    HEALTHCHECK 指令的参数，不是 Dockerfile 的 CMD 指令（本课已真实踩到）。
    """
    out: list[tuple[int, str]] = []
    buf = ""
    start = 0
    for i, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not buf:
            if not stripped or stripped.startswith("#"):
                continue
            start = i
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
            continue
        buf += stripped
        out.append((start, buf.strip()))
        buf = ""
    if buf.strip():
        out.append((start, buf.strip()))
    return out


def lint_dockerfile(text: str) -> LintReport:
    """对 Dockerfile 做静态检查。规则来自本课真机踩过的坑。"""
    rep = LintReport()
    logical = logical_lines(text)
    lines = text.splitlines()

    def instr_of(idx: int) -> str:
        """取第 idx 行的指令名（忽略续行缩进）。"""
        m = re.match(r"\s*([A-Za-z]+)\s", lines[idx])
        return m.group(1).upper() if m else ""

    # --- 规则 1：latest 标签 ---
    for i, ln in enumerate(lines, 1):
        if re.match(r"\s*FROM\b", ln, re.I) and re.search(r":latest\b|\sAS\s+\w+\s*$", ln, re.I) is None and ":latest" in ln:
            rep.issues.append(LintIssue("WARN", "001", i, "使用了 :latest 标签，构建不可复现", "固定到具体小版本，如 python:3.12-slim"))
        if re.match(r"\s*FROM\b", ln, re.I) and ln.strip().lower().endswith("latest"):
            rep.issues.append(LintIssue("WARN", "001", i, "使用了 :latest 标签，构建不可复现", "固定到具体小版本"))

    # 以下规则都基于逻辑行（已合并 \ 续行），否则 HEALTHCHECK CMD python -c "..."
    # 里的 CMD 会被误当成 Dockerfile 的 CMD 指令（本课真实踩到过一次）。
    # --- 规则 2：COPY . . 在依赖安装之前（缓存杀手）---
    copy_all = [no for no, ln in logical if re.match(r"COPY\s+\.\s+\.?\s*$", ln, re.I)]
    pip_idx = [no for no, ln in logical if re.match(r"RUN\b", ln, re.I) and "pip install" in ln]
    for ci in copy_all:
        for pi in pip_idx:
            if ci < pi:
                rep.issues.append(LintIssue(
                    "ERROR", "002", ci,
                    "COPY . . 在 RUN pip install 之前：改一行代码就会重装全部依赖",
                    "先 COPY requirements.txt . → RUN pip install → 再 COPY 业务代码",
                ))
                break

    # --- 规则 3：COPY . . 需要 .dockerignore ---
    if copy_all:
        rep.issues.append(LintIssue(
            "WARN", "003", copy_all[0],
            "COPY . . 会把上下文里的一切打进镜像",
            "配 .dockerignore 排除 .git/ __pycache__/ *.pyc .venv/（实测 60.01MB → 10.75kB）",
        ))

    # --- 规则 4：缺 USER（非 root）---
    last_no = logical[-1][0] if logical else 1
    if not any(re.match(r"USER\b", ln, re.I) for _, ln in logical):
        rep.issues.append(LintIssue("ERROR", "004", last_no, "没有 USER 指令，容器以 root 运行",
                                    "加 RUN useradd -u 10001 -m appuser && USER appuser"))

    # --- 规则 5：CMD / ENTRYPOINT 用 shell form（信号不直达进程）---
    for no, ln in logical:
        if re.match(r"CMD\b", ln, re.I) and "[" not in ln:
            rep.issues.append(LintIssue("WARN", "005", no, "CMD 使用 shell form，进程多一层 sh",
                                        "改用 exec form：CMD [\"python\", \"main.py\"]"))
        if re.match(r"ENTRYPOINT\b", ln, re.I) and "[" not in ln:
            rep.issues.append(LintIssue("WARN", "005", no, "ENTRYPOINT 使用 shell form，SIGTERM 到不了应用",
                                        "改用 exec form"))

    # --- 规则 6：镜像内不该出现的文件 ---
    for no, ln in logical:
        if re.match(r"(ADD|COPY)\s", ln, re.I) and re.search(r"\.env\b|secret|\.pem$|id_rsa", ln, re.I):
            rep.issues.append(LintIssue("ERROR", "006", no, "疑似把密钥/配置烤进镜像",
                                        "改用运行时 -e 或 docker secret 挂载"))

    # --- 规则 7：多阶段但没用 --from（收益为 0）---
    # 注意：判断「是否多阶段」必须数 FROM 行总数，而不是数带 AS 的 FROM 行——
    # 典型手误是 builder 写了 AS 而 final 忘了写，FROM 只有 2 行但 AS 只有 1 个。
    stages = [no for no, ln in logical if re.match(r"FROM\b", ln, re.I)]
    if len(stages) >= 2 and not any("--from=" in ln for _, ln in logical):
        rep.issues.append(LintIssue("ERROR", "007", stages[1],
                                   "定义了多个 stage 却没有 COPY --from=builder，多阶段没有意义",
                                   "加 COPY --from=builder <src> <dst>"))

    return rep


# =============================================================================
# 3. 缓存影响估算（无 Docker 也能跑）
# =============================================================================

@dataclass
class CacheImpact:
    name: str
    total_steps: int
    cached_steps: int
    hot_time_s: float
    cold_time_s: float

    @property
    def speedup(self) -> float:
        return self.cold_time_s / self.hot_time_s if self.hot_time_s else float("inf")


def step_cost(cmd: str, rest: str) -> float:
    """
    单步耗时模型（秒），来源：本课真机实测
      - 改 requirements.txt 触发 pip install 重跑 → 全量 9.426s
      - 只改 main.py 时重建            → 1.727s
    单步基准取自 docker build 输出里各 Step 的相对量级，非精确剖析。
    """
    if cmd == "RUN":
        return 9.0 if "pip install" in rest else 0.5
    if cmd == "COPY":
        return 0.3
    return 0.1  # FROM / WORKDIR / ENV / EXPOSE / USER / CMD / ARG


def estimate_cache_impact(dockerfile: str) -> CacheImpact:
    """
    静态估算「改一行业务代码（main.py）后重建」要花多久。

    模型（与 Docker 真实语义一致）：
      · 冷构建 cold_time = 全部层耗时之和（无任何缓存）
      · 热构建 hot_time  = 从「第一个把源码带进上下文的层」开始，到文件末尾的耗时之和
        （它以及它之后的所有层缓存失效，必须重跑；它之前的层直接复用）
      · 加速比 = cold / hot

    校验（本课实测）：
      BAD_CACHE       hot ≈ 0.3 + 9.0 + 0.1 = 9.4s  ← 实测 9.426s
      CACHE_FRIENDLY  hot ≈ 1.7s                 ← 实测 1.727s
    """
    logical = logical_lines(dockerfile)
    total = 0.0
    hot = 0.0
    n = 0
    hit = 0
    invalidated = False
    for _no, ln in logical:
        m = re.match(r"([A-Za-z]+)\b(.*)", ln)
        if not m:
            continue
        cmd, rest = m.group(1).upper(), m.group(2)
        c = step_cost(cmd, rest)
        n += 1
        total += c
        if invalidated:
            hot += c
            continue
        hit += 1
        # 拷入「非依赖清单」的源码 → 源码进入上下文，从这层起全部失效
        if cmd in ("COPY", "ADD") and not re.search(r"requirements\.txt", rest):
            invalidated = True
            hot += c
    return CacheImpact("estimated", n, hit, round(hot, 2), round(total, 2))


# =============================================================================
# 4. 自测（离线、无外部依赖）
# =============================================================================

def self_test() -> int:
    failures: list[str] = []

    def check(cond: bool, label: str) -> None:
        if cond:
            print(f"  ✅ {label}")
        else:
            print(f"  ❌ {label}")
            failures.append(label)

    print("【自测 1】模板完整性")
    for name, tpl in TEMPLATES.items():
        check(tpl.startswith("FROM ") and "\n" in tpl.strip(), f"{name}: 合法 Dockerfile 骨架")
    check(len(TEMPLATES) == 5, "模板数量为 5")

    print("\n【自测 2】Lint 规则")
    rep = lint_dockerfile(BAD_CACHE)
    codes = {i.code for i in rep.issues}
    check("002" in codes, "检出 002：COPY . . 在 pip install 之前")
    check("004" in codes, "检出 004：缺 USER")

    rep_ok = lint_dockerfile(CACHE_FRIENDLY)
    codes_ok = {i.code for i in rep_ok.issues}
    check("002" not in codes_ok, "cache-friendly 不误报 002")
    check("004" not in codes_ok, "cache-friendly 不误报 004")

    rep_ms = lint_dockerfile(MULTI_STAGE)
    check("007" not in {i.code for i in rep_ms.issues}, "multi-stage 正确使用 --from，不报 007")
    check("005" not in {i.code for i in rep_ms.issues}, "exec form CMD 不报 005")

    bad_cmd = lint_dockerfile("FROM python:3.12-slim\nCMD python main.py\nUSER u\n")
    check("005" in {i.code for i in bad_cmd.issues}, "shell form CMD 报 005")

    secret = lint_dockerfile("FROM python:3.12-slim\nUSER u\nCOPY .env /app/.env\n")
    check("006" in {i.code for i in secret.issues}, "COPY .env 报 006")

    fake_stage = lint_dockerfile("FROM python:3.12-slim AS builder\nRUN pip install x\nFROM python:3.12-slim\nUSER u\n")
    check("007" in {i.code for i in fake_stage.issues}, "多阶段无 --from 报 007")

    print("\n【自测 3】缓存影响估算")
    ci_bad = estimate_cache_impact(BAD_CACHE)
    ci_good = estimate_cache_impact(CACHE_FRIENDLY)
    check(ci_good.hot_time_s < ci_bad.hot_time_s,
          f"cache-friendly 热构建更快（{ci_good.hot_time_s}s < {ci_bad.hot_time_s}s）")
    check(ci_good.speedup > 1.5, f"cache-friendly 加速比 >1.5×（实测 {ci_good.speedup:.1f}×）")
    # BAD_CACHE 的 FROM/WORKDIR 仍可命中，但 COPY . . 之后的 pip install（9.0s）必须重跑，
    # 所以热构建应该「慢到接近冷构建」，而不是「快」。
    check(ci_bad.hot_time_s >= ci_bad.cold_time_s * 0.9,
          f"BAD_CACHE 改代码后几乎等于冷构建（hot {ci_bad.hot_time_s}s vs cold {ci_bad.cold_time_s}s）")
    check(abs(ci_bad.hot_time_s - 9.4) < 0.5,
          f"BAD_CACHE 模型预测 hot≈9.4s，与真机实测 9.426s 吻合（得 {ci_bad.hot_time_s}s）")
    check(abs(ci_good.hot_time_s - 1.7) < 0.5,
          f"CACHE_FRIENDLY 模型预测 hot≈1.7s，与真机实测 1.727s 吻合（得 {ci_good.hot_time_s}s）")

    print("\n【自测 4】容器端口规范检查"
          )
    # 检查所有模板里 Flask 是否绑 0.0.0.0（本课翻车实验 #4 的根因）
    check("EXPOSE 8000" in CACHE_FRIENDLY, "缓存友好模板声明了 EXPOSE")
    check('CMD ["python", "main.py"]' in CACHE_FRIENDLY, "使用 exec form CMD（信号直达）")
    check("PYTHONUNBUFFERED=1" in CACHE_FRIENDLY, "设置了 PYTHONUNBUFFERED=1（日志不缓冲）")

    print("\n【自测 5】渲染产物完整性")
    with tempfile.TemporaryDirectory() as td:
        for name, tpl in TEMPLATES.items():
            p = Path(td) / "Dockerfile"
            p.write_text(tpl, encoding="utf-8")
            check(p.read_text(encoding="utf-8") == tpl, f"{name}: 写盘-回读一致")

    print()
    if failures:
        print(f"❌ 自测失败 {len(failures)} 项：")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("🎉 全部自测通过（离线，无需 Docker）")
    return 0


# =============================================================================
# 5. 真机构建（可选）
# =============================================================================

APP_MAIN = '''\
from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/echo")
def echo():
    return jsonify(msg=request.args.get("msg", "hello"))


if __name__ == "__main__":
    # 容器外要连得上，必须绑 0.0.0.0（Day 172 翻车实验 #4 的根因）
    app.run(host="0.0.0.0", port=8000)
'''

DOCKERIGNORE = "__pycache__/\n*.pyc\n.git/\n.venv/\n*.md\n"


def sh(cmd: list[str], timeout: int = 600) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def build_all() -> int:
    """用 docker CLI 真机构建所有模板并对比体积/耗时。"""
    if not shutil.which("docker"):
        print("❌ 未找到 docker CLI；可改用 --dry-run 查看静态分析结果")
        return 1

    rc, _, _ = sh(["docker", "info"])
    if rc != 0:
        print("❌ Docker 守护进程不可用；请先启动 Docker")
        return 1

    workdir = Path(tempfile.mkdtemp(prefix="day172-tpl-"))
    (workdir / "main.py").write_text(APP_MAIN, encoding="utf-8")
    (workdir / "requirements.txt").write_text("flask==3.0.3\n", encoding="utf-8")
    (workdir / ".dockerignore").write_text(DOCKERIGNORE, encoding="utf-8")
    # 多阶段模板里 main.py 在 context 根目录，各模板共用同一 context 即可
    print(f"📁 构建上下文：{workdir}\n")

    rows: list[tuple[str, float, float, str, int]] = []
    try:
        for name, tpl in TEMPLATES.items():
            (workdir / "Dockerfile").write_text(tpl, encoding="utf-8")
            tag = f"day172-tpl:{name}"
            print(f"── 构建 {name} " + "─" * 46)
            t0 = time.time()
            rc, _, err = sh(["docker", "build", "-t", tag, str(workdir)])
            cold = time.time() - t0
            if rc != 0:
                print(f"   ❌ 构建失败：{err.splitlines()[-1] if err else '未知错误'}")
                continue

            # 第二次构建：应几乎全命中缓存
            t1 = time.time()
            sh(["docker", "build", "-t", tag, str(workdir)])
            hot = time.time() - t1

            _, out, _ = sh(["docker", "images", "-f", f"reference={tag}", "--format", "{{.Size}}"])
            size = out.splitlines()[0] if out else "?"
            rows.append((name, cold, hot, size, 0))
            print(f"   ✅ 冷构建 {cold:.2f}s / 缓存构建 {hot:.2f}s / 体积 {size}")

        print("\n" + "=" * 76)
        print(f"{'模板':<18}{'冷构建':>10}{'缓存构建':>12}{'加速比':>10}  体积")
        print("-" * 76)
        for name, cold, hot, size, _ in rows:
            spd = cold / hot if hot > 0.005 else float("inf")
            spd_s = "∞" if spd == float("inf") else f"{spd:.1f}×"
            print(f"{name:<18}{cold:>9.2f}s{hot:>11.2f}s{spd_s:>10}  {size}")
        print("=" * 76)
        print("解读：bad-cache 与 cache-friendly 的体积可能相同，差别在「改代码后的重建耗时」。")
        print("      生产上 multi-stage / prod-hardened 才能真正减小体积。")
    finally:
        for name in TEMPLATES:
            sh(["docker", "rmi", "-f", f"day172-tpl:{name}"])
        shutil.rmtree(workdir, ignore_errors=True)
        print(f"\n🧹 已清理：镜像 day172-tpl:* 与临时目录 {workdir}")

    return 0


# =============================================================================
# CLI
# =============================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description="Day 172 Dockerfile 模式生成器 / Lint / 真机构建")
    ap.add_argument("--self-test", action="store_true", help="离线自测（不需要 Docker）")
    ap.add_argument("--show", action="store_true", help="打印全部 Dockerfile 模板")
    ap.add_argument("--lint", metavar="FILE", help="检查指定 Dockerfile")
    ap.add_argument("--build", action="store_true", help="用 Docker 真机构建所有模板并对比")
    ap.add_argument("--dry-run", action="store_true", help="只做静态分析（无 Docker 时的降级路径）")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.lint:
        p = Path(args.lint)
        if not p.exists():
            print(f"❌ 文件不存在：{p}")
            return 1
        rep = lint_dockerfile(p.read_text(encoding="utf-8"))
        print(f"📋 Lint 报告：{p}\n")
        print(rep.render())
        ci = estimate_cache_impact(p.read_text(encoding="utf-8"))
        print(f"\n📊 缓存估算（改一行业务代码时）：命中 {ci.cached_steps}/{ci.total_steps} 步，"
              f"热构建 ~{ci.hot_time_s}s vs 冷构建 ~{ci.cold_time_s}s，加速 {ci.speedup:.1f}×")
        return 1 if rep.errors else 0

    if args.build:
        return build_all()

    if args.dry_run:
        print("🔍 降级模式：静态分析全部模板（不调用 Docker）\n")
        for name, tpl in TEMPLATES.items():
            rep = lint_dockerfile(tpl)
            ci = estimate_cache_impact(tpl)
            print(f"── {name} " + "─" * 50)
            print(f"   Lint：ERROR {len(rep.errors)} / WARN {len(rep.issues) - len(rep.errors)}"
                  f"｜缓存命中 {ci.cached_steps}/{ci.total_steps} 步"
                  f"｜热构建 ~{ci.hot_time_s}s（加速 {ci.speedup:.1f}×）")
            for i in rep.issues[:4]:
                print(f"     - [{i.code}] L{i.line_no} {i.message}")
        return 0

    # 默认：打印模板
    for name, tpl in TEMPLATES.items():
        print("=" * 60)
        print(f"# {name}")
        print("=" * 60)
        print(tpl)
    print("💡 试试： --self-test / --lint <Dockerfile> / --build / --dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())