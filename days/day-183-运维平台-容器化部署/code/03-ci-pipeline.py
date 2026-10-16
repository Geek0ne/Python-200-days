#!/usr/bin/env python3
"""
Day 183 · 03 — CI 流水线：构建 / 测试 / 推送

生成并校验一份 GitHub Actions workflow（4 个 job：lint → test(矩阵) → build → deploy），
再用 act 在本机把它真跑一遍（见 README 实验 3）。

三种用法，按「有多依赖外部世界」分层：
    --self-test    纯离线：生成 YAML → 解析 → 断言结构（DAG 无环、有 needs、有 secret 引用…）
    --dry-run      降级路径：不跑任何东西，打印每个 job 会执行的确切命令
    --run          真跑：调 act 在本机容器里执行 lint / test 两个 job

为什么 build / deploy 两个 job 是「未实测」的：
它们要 ghcr.io 的推送凭据和一台真机，本机没有。**没有的东西就不写假输出**，
README 里对这两步给的是「预期结果 + 验证方法」。

用法：
    python3 03-ci-pipeline.py --self-test
    python3 03-ci-pipeline.py --dry-run
    python3 03-ci-pipeline.py --out /tmp/day183/ci --write-only
    python3 03-ci-pipeline.py --out /tmp/day183/ci --run --jobs lint,test
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
    HAVE_YAML = True
except ImportError:  # pragma: no cover
    HAVE_YAML = False

BT = chr(96)
D = chr(36)
_FORCE_FALLBACK = False   # --force-fallback 时置真：验证「没装 PyYAML」的降级路径

# ⚠️ 本模板里凡是 GitHub 的表达式都要写成 `/$ 占位符再替换：
#    在生成它的脚本里，[[D]]{{ ... }} 会被 shell/模板解释掉，直接写会炸（翻车复盘第 2 条）。
WORKFLOW = """name: ops-platform-ci

# 触发：主干 push、所有 PR、以及手动按钮。
on:
  push:
    branches: [main]
    paths-ignore: ['docs/**', '**/*.md']
  pull_request:
  workflow_dispatch:

# 最小权限原则：默认只读，只有打镜像那一步需要写 packages。
permissions:
  contents: read
  packages: write

# 同一个 PR 连推两次，前一次自动作废——省 runner，也免得旧结果盖住新结果。
concurrency:
  group: ci-[[D]]{{ github.ref }}
  cancel-in-progress: true

env:
  IMAGE: ghcr.io/[[D]]{{ github.repository }}/ops-platform
  PYTHON_VERSION: '3.12'

jobs:
  lint:
    name: lint（语法 + 生成器自检）
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: [[D]]{{ env.PYTHON_VERSION }}
      - name: 语法检查（编译所有脚本）
        run: python -m compileall -q code/
      - name: Dockerfile 生成器自检（纯离线）
        run: python code/02-multistage-image.py --self-test
      - name: workflow 自检（拿自己当输入）
        run: python code/03-ci-pipeline.py --self-test

  test:
    name: test（py[[D]]{{ matrix.python }}）
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: [[D]]{{ matrix.python }}
      # 顺序很重要：降级路径必须在「装依赖」**之前**跑。
      # 第一版我把它放在装依赖之后，于是 prometheus_client 已就位，
      # 断言 stdlib-fallback 必然失败——CI 一跑就红（翻车复盘第 5 条）。
      - name: 无依赖降级路径也要过（必须在装依赖之前）
        run: |
          python - <<'PY'
          import subprocess, sys
          out = subprocess.run([sys.executable, 'code/01-ops-service.py', '--once'],
                               capture_output=True, text=True)
          assert out.returncode == 0, out.stderr
          assert 'stdlib-fallback' in out.stdout, out.stdout
          print('stdlib 路径 OK')
          PY
      # ⚠️ 不能直接 python -m pip install：现代发行版 Python 是
      #    externally-managed（PEP 668），系统环境装包会被拒。
      #    本机 act 实测就是这么红的（见 README 实验 3 的「红→绿」）。
      #    正确做法和我们 Dockerfile builder 阶段一样：**先建 venv**。
      - name: 建虚拟环境并装依赖（PEP 668：系统 Python 不让直接装）
        run: |
          python -m venv [[VENV]]
          [[VENV]]/bin/pip install --no-cache-dir -r code/requirements.txt
      - name: 服务自检（venv 里的解释器，此时走 prometheus_client）
        run: [[VENV]]/bin/python code/01-ops-service.py --self-test
      - name: 确认依赖真的生效（前后两种后端都验过）
        run: |
          [[VENV]]/bin/python - <<'PY'
          import subprocess, sys
          out = subprocess.run([sys.executable, 'code/01-ops-service.py', '--once'],
                               capture_output=True, text=True)
          assert 'prometheus_client' in out.stdout, out.stdout
          print('prometheus_client 路径 OK')
          PY

  build:
    name: build & push（只在主干）
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - name: 登录镜像仓库（凭据来自 secrets，不落盘、不进日志）
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: [[D]]{{ github.actor }}
          password: [[D]]{{ secrets.GITHUB_TOKEN }}
      - name: 生成构建上下文
        run: python code/02-multistage-image.py --out build-ctx --write-only
      - name: 构建并推送（标签一律用 commit SHA，latest 只是方便人看）
        uses: docker/build-push-action@v6
        with:
          context: build-ctx
          file: build-ctx/Dockerfile.multi
          push: true
          tags: |
            [[D]]{{ env.IMAGE }}:[[D]]{{ github.sha }}
            [[D]]{{ env.IMAGE }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: 把镜像名写进 job 摘要（后面 deploy 要用）
        run: echo "image=[[D]]{{ env.IMAGE }}:[[D]]{{ github.sha }}" >> "[[D]]GITHUB_STEP_SUMMARY"

  deploy:
    name: deploy（一键部署 + 健康检查）
    needs: build
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: 一键部署（失败自动回滚，逻辑见 code/04-deploy-rollback.py）
        run: python code/04-deploy-rollback.py --image [[D]]{{ env.IMAGE }}:[[D]]{{ github.sha }} --version [[D]]{{ github.sha }}
"""


# --- act 演练专用变体 ---------------------------------------------------------
# 真实 workflow 里的 actions/checkout@v4 与 actions/setup-python@v5 需要从 github.com
# 克隆 action 仓库。本机到 github.com 的 git 协议不稳定（实测报 unexpected EOF），
# 所以另出一份「无外部 action」的等价 workflow 用于本机演练：
#   - 工作区由 act 直接挂载 → 不需要 checkout
#   - runner 镜像里自带 python3 → 不需要 setup-python
# 这两个替换是**为了本机可跑**而做的，不改变 lint/test 的验证内容。
WORKFLOW_ACT = WORKFLOW.replace(
    """      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: [[D]]{{ env.PYTHON_VERSION }}
      - name: 语法检查（编译所有脚本）""",
    """      # act 演练变体：省掉 actions/checkout@v4（工作区是挂载进来的）
      #              与 actions/setup-python@v5（runner 镜像自带 python3）
      - name: 打印 runner 自带的 Python（替代 setup-python 的现场证据）
        run: python3 --version
      - name: 语法检查（编译所有脚本）""",
).replace(
    """      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: [[D]]{{ matrix.python }}
      # 顺序很重要""",
    """      # act 演练变体：同上，不拉外部 action；矩阵两个值都落到容器自带的 python3
      - name: runner Python（替代 setup-python）
        run: python3 --version
      # 顺序很重要""",
)


def render(act_mode: bool = False, path_prefix: str = "") -> str:
    """--path-prefix 是给「在仓库根目录用 act --bind 跑」准备的：
    那时容器的工作区是**仓库根**，所以 steps 里的 code/... 要写成 <仓库内路径>/code/...。"""
    text = WORKFLOW_ACT if act_mode else WORKFLOW
    text = text.replace("[[BT]]", BT).replace("[[D]]", D)
    prefix = path_prefix.rstrip("/")
    # [[VENV]] 默认 .venv（真实 runner 上工作区是丢弃式的）；
    # 本机 --path-prefix 模式下必须落到 day 目录内部，绝不能写进仓库根。
    venv = f"{prefix}/.act-venv" if prefix else ".venv"
    text = text.replace("[[VENV]]", venv)
    if prefix:
        text = text.replace("code/", prefix + "/code/")
    return text


def parse_pipeline(text: str) -> dict:
    """解析 workflow。有 PyYAML 就用它；没有就退回正则。

    ⚠️ 第一版的正则回退只把 job 名捞出来、完全没解析 needs，
    于是自检里「test 依赖 lint」这类断言在没有 PyYAML 的机器上必然失败——
    「有降级路径」和「降级路径真的能用」是两件事（翻车复盘第 6 条）。
    本版按缩进做两趟扫描，job 名（缩进 2）与 needs（缩进 4）都能解出来。
    """
    global _FORCE_FALLBACK
    if HAVE_YAML and not _FORCE_FALLBACK:
        return yaml.safe_load(text)

    doc: dict = {"jobs": {}, "_backend": "regex-fallback"}
    if re.search(r"^on:", text, re.M):
        doc[True] = True   # 模拟 YAML 1.1 把 on 读成布尔的老坑，让上层两种写法都能过
    current = None
    in_jobs = False
    for line in text.splitlines():
        if re.match(r"^[A-Za-z]", line):          # 顶层键
            top = line.split(":")[0]
            doc.setdefault(top, {})
            # ⚠️ 第一版没有这个 in_jobs 作用域，于是 on: 下面的
            #    pull_request: / workflow_dispatch: 也被当成了 job（翻车复盘第 6 条后半）
            in_jobs = (top == "jobs")
            current = None
            continue
        m_job = re.match(r"^  ([A-Za-z_][\w-]*):\s*$", line)
        if m_job and in_jobs:
            current = m_job.group(1)
            doc["jobs"][current] = {}
            continue
        m_needs = re.match(r"^    needs:\s*\[?([\w,\s-]+?)\]?\s*$", line)
        if m_needs and current:
            doc["jobs"][current]["needs"] = [n.strip() for n in m_needs.group(1).split(",") if n.strip()]
        m_run = re.match(r"^    runs-on:\s*(\S+)\s*$", line)
        if m_run and current:
            doc["jobs"][current]["runs-on"] = m_run.group(1)
        m_if = re.match(r"^    if:\s*(.+)$", line)
        if m_if and current:
            doc["jobs"][current]["if"] = m_if.group(1).strip()
    # 正则后端只能到这层：steps / strategy 这类深层结构它解不出来，
    # 所以上层自检会把依赖它们的断言标成「跳过」而不是「失败」。
    return doc


def is_full_backend(doc: dict) -> bool:
    return doc.get("_backend") != "regex-fallback"


def collect_needs(doc: dict) -> dict[str, list[str]]:
    """job -> 它依赖的 job 列表。"""
    out: dict[str, list[str]] = {}
    for name, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            out[name] = []
            continue
        needs = job.get("needs") or []
        if isinstance(needs, str):
            needs = [needs]
        out[name] = list(needs)
    return out


def topo_order(needs: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    """Kahn 拓扑排序。返回 (顺序, 环里的节点)。"""
    indeg = {n: len(set(d)) for n, d in needs.items()}
    order: list[str] = []
    ready = sorted([n for n, d in indeg.items() if d == 0])
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m, deps in needs.items():
            if n in deps:
                indeg[m] -= 1
                if indeg[m] == 0:
                    ready.append(m)
        ready.sort()
    cyclic = [n for n in needs if n not in order]
    return order, cyclic


def human(s: str) -> str:
    """把 [[D]] / [[BT]] 占位符还原成人看的字符（只用于打印）。"""
    return s.replace("[[D]]", D).replace("[[BT]]", BT)


def dry_run(text: str, doc: dict) -> int:
    """降级路径：不执行，只把「每个 job 会跑什么」摊开。"""
    needs = collect_needs(doc)
    order, cyclic = topo_order(needs)
    print("▶ CI 流水线（--dry-run，不执行任何命令）")
    print(f"  解析后端：{'PyYAML' if HAVE_YAML else 'regex-fallback'}")
    if cyclic:
        print(f"  ❌ needs 存在环：{cyclic}")
        return 1
    layers = _layers(needs)
    print(f"  拓扑序：{' → '.join(order)}")
    print(f"  并行分层：{layers}")
    print()
    for name in order:
        job = doc["jobs"].get(name, {}) or {}
        cond = job.get("if", "（默认：success()）")
        print(f"  [{name}] runs-on={job.get('runs-on', '?')}  needs={needs[name]}  if={cond}")
        for step in job.get("steps", []) or []:
            if "uses" in step:
                print(f"      uses: {step['uses']}")
            elif "run" in step:
                cmd = step["run"].strip().splitlines()[0]
                print(f"      run : {cmd}")
        print()
    print("  说明：build/deploy 加了 if（只在 main 的 push 上跑），")
    print("        所以本机 act 演练只跑 lint/test —— 这是刻意的，不是漏了。")
    return 0


def _layers(needs: dict[str, list[str]]) -> list[list[str]]:
    remaining = dict(needs)
    done: set[str] = set()
    layers: list[list[str]] = []
    while remaining:
        layer = sorted(n for n, d in remaining.items() if set(d) <= done)
        if not layer:
            break
        layers.append(layer)
        done |= set(layer)
        for n in layer:
            remaining.pop(n)
    return layers


def self_test() -> int:
    checks: list[tuple[str, bool]] = []
    text = render()
    doc = parse_pipeline(text)
    needs = collect_needs(doc)

    checks.append(("解析出 4 个 job", set(needs) == {"lint", "test", "build", "deploy"}))
    checks.append(("test 依赖 lint", needs.get("test") == ["lint"]))
    checks.append(("build 依赖 test", needs.get("build") == ["test"]))
    checks.append(("deploy 依赖 build", needs.get("deploy") == ["build"]))
    order, cyclic = topo_order(needs)
    checks.append(("needs 无环且拓扑序正确", not cyclic and order == ["lint", "test", "build", "deploy"]))
    layers = _layers(needs)
    checks.append(("串行链 = 4 层（没有并行兄弟）", len(layers) == 4))
    # ⚠️ PyYAML 按 YAML 1.1 解析，未加引号的 on: 会被读成布尔 True 而不是字符串 "on"。
    #    所以这里两种都要认——这条断言本身就是在演示那个坑（翻车复盘第 3 条）。
    has_on = ("on" in doc) or (True in doc)
    checks.append(("workflow 有 on / permissions / concurrency（on 可能是 True，PyYAML 老坑）",
                   has_on and all(k in doc for k in ("permissions", "concurrency"))))
    # 下面这几条要读深层结构，正则后端解不出来 → 标 None（跳过），不算失败。
    full = is_full_backend(doc)
    checks.append(("permissions 里 packages: write（推镜像需要）",
                   (doc.get("permissions") or {}).get("packages") == "write" if full else None))
    checks.append(("build/deploy 带 if 门禁（只在 main push 跑）",
                   "refs/heads/main" in str((doc["jobs"]["build"] or {}).get("if", ""))
                   and "refs/heads/main" in str((doc["jobs"]["deploy"] or {}).get("if", ""))))
    checks.append(("test 用了矩阵且 fail-fast: false",
                   ((doc["jobs"]["test"].get("strategy") or {}).get("fail-fast") is False) if full else None))
    checks.append(("镜像标签用 commit SHA，不用 latest 当唯一标签", "github.sha" in text and "cache-from: type=gha" in text))
    # 两版都踩过坑，记下来（翻车复盘第 4 条）：
    #  v1: (?![[D]]{{)   —— render() 早把 [[D]] 换成了 $，负向断言永远为真 → 假通过；
    #  v2: \s*(?!\$\{\{) —— \s* 会倒退：先吃空格断言失败，再退成零宽断言成功，照样假通过；
    #  v3（本版）：把 \s* 挪进断言内部。断言是原子的，不存在「退回去让它成立」这条路。
    hardcoded_pw = re.search(r"password:(?!\s*\$\{\{)", text)
    checks.append(("凭据只以 [[D]]{{ secrets.* }} 出现，没有硬编码口令",
                   "secrets.GITHUB_TOKEN" in text and hardcoded_pw is None))
    checks = [(human(n), ok) for n, ok in checks]
    checks.append(("推送标签可复现（有 SHA 标签）", re.search(r"IMAGE \}\}:\[\[D\]\]\{\{ github\.sha", text) is not None or "github.sha" in text))
    checks.append(("每个 job 都有 steps 且非空",
                   all(len((doc["jobs"][n] or {}).get("steps", [])) > 0 for n in ("lint", "test", "build", "deploy")) if full else None))

    failed = [n for n, ok in checks if ok is False]
    skipped = [n for n, ok in checks if ok is None]
    for n, ok in checks:
        mark = "✅" if ok else ("❌" if ok is False else "⏭")
        print(f"  {mark} {n}")
    if failed:
        print(f"❌ self-test 失败：{len(failed)}/{len(checks)} -> {failed}")
        return 1
    backend = "regex-fallback（--force-fallback）" if not full else "PyYAML"
    print(f"✅ self-test 通过：{len(checks) - len(skipped)}/{len(checks)} 项通过"
          f"，{len(skipped)} 项因后端能力跳过 | 后端={backend}")
    return 0


def run_act(out: Path, jobs: list[str], event: str, bind: bool = True) -> int:
    """在本机用 act 跑 workflow。只跑不需要 registry / 真机的 job。

    ⚠️ --bind 不是可选项：实测（见 README 实验 3）不加 --bind 时 act 给容器的
    工作区是**空目录**（ls -la 只有 . 和 ..），所有基于文件的 step 都会 FileNotFound。
    """
    cmd = ["act", event, "-W", str(out / ".github/workflows/ci.yml"),
           "-P", "ubuntu-latest=catthehacker/ubuntu:act-latest", "--pull=false"]
    if bind:
        cmd.append("--bind")
    for j in jobs:
        cmd += ["-j", j]
    print("▶ " + " ".join(cmd))
    return subprocess.call(cmd)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Day 183 · CI 流水线生成 / 校验 / 演练")
    p.add_argument("--out", default="/tmp/day183/ci", help="生成目录（会写 .github/workflows/ci.yml）")
    p.add_argument("--write-only", action="store_true")
    p.add_argument("--print", dest="do_print", action="store_true", help="打印生成的 YAML")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="打印每个 job 会跑什么，不执行")
    p.add_argument("--run", action="store_true", help="用 act 在本机真跑")
    p.add_argument("--jobs", default="lint,test", help="--run 时跑哪几个 job")
    p.add_argument("--no-bind", dest="bind", action="store_false", default=True,
                   help="--run 时不要 --bind（默认要，见 run_act 的说明）")
    p.add_argument("--event", default="push", help="--run 时的触发事件名")
    p.add_argument("--path-prefix", default="",
                   help="给 steps 里的 code/ 加前缀（在仓库根用 act --bind 时必填）")
    p.add_argument("--act-mode", action="store_true",
                   help="生成 act 本机演练用的等价 workflow（去掉需要联网拉取的 actions）")
    p.add_argument("--force-fallback", action="store_true",
                   help="强制走正则后端（没有 PyYAML 时的降级路径，用来验证它真的能用）")
    args = p.parse_args(argv)

    global _FORCE_FALLBACK
    if args.force_fallback:
        _FORCE_FALLBACK = True

    if args.self_test:
        return self_test()

    text = render(args.act_mode, args.path_prefix)
    doc = parse_pipeline(text)

    if args.act_mode:
        print("ℹ️ --act-mode：已换成「无外部 action」的等价 workflow（本机 act 可跑）")
    if args.do_print:
        print(text)

    out = Path(args.out)
    target = out / ".github" / "workflows" / "ci.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"✅ workflow 已生成 → {target}（{target.stat().st_size} 字节）")

    if args.dry_run:
        print()
        return dry_run(text, doc)
    if args.run:
        return run_act(out, [j for j in args.jobs.split(",") if j], args.event, bind=args.bind)
    return 0


if __name__ == "__main__":
    sys.exit(main())
