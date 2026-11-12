#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03-tech-radar.py — 技术资产盘点：依赖雷达 + 长期维护审计

为什么要有这个脚本：
    学完 200 天，你手里不只有知识，还有一堆「以后要一直养着」的技术选择。
    每引入一个第三方包，就等于签了一份没有到期日的维护合同：
    它会有破坏性变更、会有安全公告、会有停止维护的那天。
    但选型时几乎没人算这笔账——因为账不在当下，在两年后。
    所以要把「我到底依赖了什么」变成可数的清单，再谈收敛。

它做什么：
    1. 用 ast 解析 days/ 下所有 .py 的 import（不执行代码，安全）
    2. 区分标准库 / 第三方 / 本地模块，统计每个包被多少课使用、跨度多大
    3. 按明确规则给每个第三方包打环：Adopt / Trial / Assess / Hold
    4. 审计 requirements.txt 的版本钉死情况（未钉版本 = 未来的破坏性变更）
    5. 输出人读报告 / Markdown / JSON，JSON 供 04-growth-roadmap.py 消费

用法：
    python 03-tech-radar.py                      # 人读报告
    python 03-tech-radar.py --ring Hold          # 只看某一环
    python 03-tech-radar.py --json radar.json
    python 03-tech-radar.py --markdown radar.md
    python 03-tech-radar.py --self-test          # 离线自证，不依赖本仓库

诚实边界（重要）：
    - 「使用课数」衡量的是本仓库的教学覆盖面，不是行业流行度，也不是质量。
    - STDLIB_ALT 里的替代是「部分覆盖 / 仅够演示」，不是等价替换。
      把 requests 换成 urllib 能发请求，但连接池、重试、会话全要自己写。
    - 环的阈值是产品判断，写在常量里，读者可以改；不要当成客观结论引用。

设计要点：
    - 只依赖标准库；Python 3.10+（用了 sys.stdlib_module_names）
    - ast.parse 而不是 import：仓库里有故意写坏的示例，执行会出事
    - 本地模块按「同课 code/ 下的文件名/包名」识别，避免把 pytools 当第三方
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass, asdict, field
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

DAY_DIR_RE = re.compile(r"^day-(\d{3})-")
REQ_NAME_RE = re.compile(r"^([A-Za-z0-9_.\-\[\]]+)\s*(.*)$")

# 环阈值：产品判断，不是统计结论
ADOPT_MIN_DAYS = 8
ADOPT_MIN_SPAN = 30
TRIAL_MIN_DAYS = 3
HOLD_MAX_DAYS = 2

# 标准库替代：键是 **import 名**，不是发行包名（PIL≠pillow、sklearn≠scikit-learn）。
# coverage 说明替代到什么程度，绝不假装等价。
STDLIB_ALT: dict[str, str] = {
    "requests": "urllib.request（仅发请求；连接池/重试/会话要自己写）",
    "httpx": "urllib.request（同上，且无异步）",
    "aiohttp": "asyncio + urllib（无现成客户端，需自行封装）",
    "flask": "http.server（仅够演示，无路由/模板/中间件）",
    "fastapi": "http.server（仅够演示，无校验/依赖注入/自动文档）",
    "pytest": "unittest（断言与参数化写法不同，生态插件缺失）",
    "yaml": "json（换格式，不是换库；人读性下降）",
    "dateutil": "datetime + zoneinfo（解析宽松格式要自己写）",
    "dotenv": "os.environ + 手写解析（仅够读简单 KEY=VALUE）",
    "PIL": "无（标准库没有图像处理）",
    "numpy": "array + math（仅够小规模；无向量化与广播）",
    "pandas": "csv + statistics（仅够小表；无分组聚合/时间序列）",
    "rich": "无（标准库无终端富文本）",
    "psutil": "无（跨平台系统指标必须靠它或读 /proc）",
    "jwt": "hmac + hashlib + base64（能验签，但无声明校验/过期处理）",
    "cv2": "无（标准库没有计算机视觉）",
    "bs4": "html.parser（能解析，无 CSS 选择器与容错修复）",
    "sklearn": "无（标准库没有机器学习）",
}

# 人工核对过的「不是发行包」的名字。静态 ast 扫描无法区分它们与真第三方，
# 所以单列出来并从第三方清单剔除。核对命令写在 reason 里，读者可自己复跑。
NON_DISTRIBUTION: dict[str, str] = {
    "myhelper": "day-014 在临时目录动态创建的模块（01-import-mechanism.py 里 write 出 myhelper.py）",
    "tools": "day-018 的 9 个文件 import 它，但仓库里不存在 → 实跑 ModuleNotFoundError",
}

RING_ORDER = ("Adopt", "Trial", "Assess", "Hold")
RING_MEANING = {
    "Adopt": "已反复验证，新项目可直接用",
    "Trial": "用过几次，值得继续但要盯变更",
    "Assess": "只碰过一两次，先评估再决定",
    "Hold": "面窄且有标准库替代，新项目优先别引入",
}


def pad(text: str, size: int, right: bool = False) -> str:
    """中文占两列，str.ljust 按码点数补齐会让表头歪掉。"""
    width = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)
    gap = " " * max(size - width, 0)
    return gap + text if right else text + gap


@dataclass
class Package:
    name: str
    days: list[int]
    imports: int
    first_day: int
    last_day: int
    span: int
    ring: str
    alt: str = ""


@dataclass
class ReqEntry:
    file: str
    name: str
    spec: str
    kind: str  # pinned / ranged / unpinned


@dataclass
class Radar:
    py_scanned: int
    py_failed: int
    failed_files: list[str]
    stdlib_imports: int
    thirdparty_imports: int
    local_imports: int
    stdlib_share: float
    packages: list[Package]
    ring_counts: dict[str, int]
    requirements: list[ReqEntry]
    req_counts: dict[str, int]
    narrow_packages: list[str] = field(default_factory=list)
    suspects: list[dict] = field(default_factory=list)


def find_repo(start: Path | None = None) -> Path:
    env = os.environ.get("LEARN_PYTHON_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "days").is_dir():
            return candidate
    raise SystemExit("找不到仓库根；用 --root 或 LEARN_PYTHON_ROOT 指定")


def local_names(code_dir: Path) -> set[str]:
    """同课 code/ 下的模块名与包名。少了这一步，pytools 会被误判成第三方包。"""
    if not code_dir.is_dir():
        return set()
    names = {p.stem for p in code_dir.rglob("*.py") if "__pycache__" not in p.parts}
    names |= {d.name for d in code_dir.iterdir() if d.is_dir() and (d / "__init__.py").exists()}
    return names


def top_levels(node: ast.AST) -> list[str]:
    """一个 `import os, sys` 是两个依赖，不是一个。只取 names[0] 会整包漏统计。"""
    if isinstance(node, ast.Import):
        return [alias.name.split(".")[0] for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.level or not node.module:  # 相对导入由调用方计入本地
            return []
        return [node.module.split(".")[0]]
    return []


def has_alt(name: str) -> bool:
    """替代说明以「无」开头的，等于没有替代。bool(alt) 会把「无」当成有。"""
    alt = STDLIB_ALT.get(name, "")
    return bool(alt) and not alt.startswith("无")


def ring_of(day_count: int, span: int, has_alternative: bool) -> str:
    """判定顺序即优先级：先 Hold（可收敛），再按覆盖面分级。"""
    if has_alternative and day_count <= HOLD_MAX_DAYS:
        return "Hold"
    if day_count >= ADOPT_MIN_DAYS and span >= ADOPT_MIN_SPAN:
        return "Adopt"
    if day_count >= TRIAL_MIN_DAYS:
        return "Trial"
    return "Assess"


def scan(repo: Path) -> Radar:
    days_dir = repo / "days"
    if not days_dir.is_dir():
        raise SystemExit(f"找不到 days/ 目录: {days_dir}")

    stdlib = sys.stdlib_module_names
    usage: dict[str, set[int]] = {}
    suspect: dict[str, set[int]] = {}
    counts: Counter[str] = Counter()
    stdlib_n = third_n = local_n = 0
    scanned = failed = 0
    failed_files: list[str] = []

    for child in sorted(days_dir.iterdir()):
        match = DAY_DIR_RE.match(child.name)
        if not child.is_dir() or not match:
            continue
        day = int(match.group(1))
        code_dir = child / "code"
        if not code_dir.is_dir():
            continue
        locals_ = local_names(code_dir)
        for py in sorted(code_dir.rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            scanned += 1
            try:
                tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"), filename=str(py))
            except (SyntaxError, ValueError, OSError):
                failed += 1
                failed_files.append(str(py.relative_to(repo)))
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                if isinstance(node, ast.ImportFrom) and node.level:
                    local_n += 1
                    continue
                for name in top_levels(node):
                    if not name:
                        continue
                    if name in locals_:
                        local_n += 1
                    elif name in stdlib:
                        stdlib_n += 1
                    elif name in NON_DISTRIBUTION:
                        suspect.setdefault(name, set()).add(day)
                    else:
                        third_n += 1
                        usage.setdefault(name, set()).add(day)
                        counts[name] += 1

    packages: list[Package] = []
    for name, day_set in usage.items():
        days = sorted(day_set)
        span = days[-1] - days[0]
        alt = STDLIB_ALT.get(name, "")
        packages.append(Package(
            name=name, days=days, imports=counts[name], first_day=days[0], last_day=days[-1],
            span=span, ring=ring_of(len(days), span, has_alt(name)), alt=alt,
        ))
    packages.sort(key=lambda p: (-len(p.days), p.name))

    requirements: list[ReqEntry] = []
    for req in sorted(days_dir.rglob("requirements*.txt")):
        if "__pycache__" in req.parts:
            continue
        for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "-r", "-e", "--")):
                continue
            match = REQ_NAME_RE.match(line)
            if not match:
                continue
            name, spec = match.group(1), match.group(2).strip()
            kind = "pinned" if spec.startswith("==") else ("ranged" if spec else "unpinned")
            requirements.append(ReqEntry(file=str(req.relative_to(repo)), name=name, spec=spec, kind=kind))

    total_imports = stdlib_n + third_n + local_n
    return Radar(
        py_scanned=scanned, py_failed=failed, failed_files=failed_files[:10],
        stdlib_imports=stdlib_n, thirdparty_imports=third_n, local_imports=local_n,
        stdlib_share=round(stdlib_n / total_imports, 4) if total_imports else 0.0,
        packages=packages,
        ring_counts={r: sum(1 for p in packages if p.ring == r) for r in RING_ORDER},
        requirements=requirements,
        req_counts={k: sum(1 for r in requirements if r.kind == k) for k in ("pinned", "ranged", "unpinned")},
        narrow_packages=[p.name for p in packages if len(p.days) <= HOLD_MAX_DAYS],
        suspects=[{"name": n, "days": sorted(ds), "reason": NON_DISTRIBUTION[n]}
                  for n, ds in sorted(suspect.items())],
    )


def render(radar: Radar, ring_filter: str | None) -> str:
    out = [
        f"解析 {radar.py_scanned} 个 .py（失败 {radar.py_failed} 个）",
        f"import 归类：标准库 {radar.stdlib_imports} · 第三方 {radar.thirdparty_imports} · 本地 {radar.local_imports}",
        f"标准库占比：{radar.stdlib_share * 100:.1f}%（教学以标准库为主，这是刻意的）",
        f"第三方包总数：{len(radar.packages)} · 其中窄面（<= {HOLD_MAX_DAYS} 课）{len(radar.narrow_packages)} 个",
        "",
        "技术雷达（环阈值是产品判断，见文件头常量）：",
    ]
    for ring in RING_ORDER:
        out.append(f"  {ring:<8}{radar.ring_counts[ring]:>4} 个   {RING_MEANING[ring]}")
    out.append("")
    shown = [p for p in radar.packages if ring_filter is None or p.ring == ring_filter]
    out.append(pad("包名", 20) + pad("课数", 5, True) + pad("import", 8, True)
               + pad("首次", 6, True) + pad("最近", 6, True) + pad("跨度", 6, True) + "  环")
    out.append("-" * 72)
    for p in shown:
        out.append(f"{p.name:<20}{len(p.days):>5}{p.imports:>8}{p.first_day:>6}{p.last_day:>6}{p.span:>6}  {p.ring}")
    if not shown:
        out.append("  （该环没有包）")
    out.append("")
    holds = [p for p in radar.packages if p.ring == "Hold"]
    if holds:
        out.append("Hold 环的标准库替代（注意：不是等价替换）：")
        for p in holds:
            out.append(f"  {p.name} → {p.alt}")
        out.append("")
    out.append(f"requirements 审计：{len(radar.requirements)} 条依赖声明")
    for kind, label in (("pinned", "钉死 =="), ("ranged", "范围 >=/~= "), ("unpinned", "未约束")):
        out.append(f"  {pad(label, 14)}{radar.req_counts[kind]:>4} 条")
    risky = [r for r in radar.requirements if r.kind != "pinned"]
    if risky:
        out.append("")
        out.append("未钉死的条目（未来破坏性变更的入口）：")
        for r in risky[:12]:
            out.append(f"  {r.name}{r.spec or '(无约束)'}   ← {r.file}")
        if len(risky) > 12:
            out.append(f"  …… 另有 {len(risky) - 12} 条")
    if radar.suspects:
        out.append("")
        out.append("疑似本地/运行时模块（已从第三方清单剔除，需人工核对）：")
        for s in radar.suspects:
            out.append(f"  {s['name']}  Day {s['days']}  ← {s['reason']}")
    if radar.failed_files:
        out.append("")
        out.append(f"解析失败的文件（故意写坏的示例也算，前 {len(radar.failed_files)} 个）：")
        out += [f"  {f}" for f in radar.failed_files]
    return "\n".join(out)


def render_markdown(radar: Radar) -> str:
    out = [
        "# 技术资产雷达",
        "",
        f"- 解析 .py：{radar.py_scanned} 个，失败 {radar.py_failed} 个",
        f"- 标准库占比：{radar.stdlib_share * 100:.1f}%",
        f"- 第三方包：{len(radar.packages)} 个，窄面 {len(radar.narrow_packages)} 个",
        "",
        "| 包 | 使用课数 | 首次 | 最近 | 跨度 | 环 | 标准库替代 |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for p in radar.packages:
        out.append(f"| {p.name} | {len(p.days)} | {p.first_day} | {p.last_day} | {p.span} | {p.ring} | {p.alt or '—'} |")
    out += ["", "## requirements 版本约束", "",
            f"- 钉死 ==：{radar.req_counts['pinned']} 条",
            f"- 范围约束：{radar.req_counts['ranged']} 条",
            f"- 未约束：{radar.req_counts['unpinned']} 条", ""]
    if radar.suspects:
        out += ["## 疑似本地/运行时模块", ""]
        out += [f"- `{s['name']}`（Day {s['days']}）：{s['reason']}" for s in radar.suspects]
        out.append("")
    out += ["> 使用课数 = 本仓库教学覆盖面，不是行业流行度；替代项均为部分覆盖。", ""]
    return "\n".join(out)


def self_test() -> int:
    checks = 0

    def check(cond: bool, label: str) -> None:
        nonlocal checks
        print(("  ✅ " if cond else "  ❌ ") + label)
        assert cond, label
        checks += 1

    check(ring_of(10, 60, False) == "Adopt", "广覆盖 + 长跨度 → Adopt")
    check(ring_of(10, 5, False) == "Trial", "课数够但跨度短 → 不是 Adopt")
    check(ring_of(4, 10, False) == "Trial", "3 课以上 → Trial")
    check(ring_of(2, 1, True) == "Hold", "窄面 + 有替代 → Hold")
    check(ring_of(2, 1, False) == "Assess", "窄面无替代 → Assess")
    check(ring_of(9, 60, True) == "Adopt", "有替代但覆盖广 → 仍是 Adopt（Hold 优先只管窄面）")
    check(has_alt("httpx") and not has_alt("cv2"), "替代说明写「无」的包不算有替代")
    check(ring_of(1, 0, has_alt("cv2")) == "Assess", "cv2 无替代 → 不该进 Hold")

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        code = repo / "days" / "day-001-x" / "code"
        code.mkdir(parents=True)
        (code / "01-a.py").write_text(
            "import os, sys\nimport requests\nfrom pytools import text\nfrom . import sibling\n",
            encoding="utf-8")
        (code / "pytools.py").write_text("text = 1\n", encoding="utf-8")
        (code / "02-broken.py").write_text("def f(:\n", encoding="utf-8")
        (code / "requirements.txt").write_text(
            "# 注释\nrequests==2.31.0\nflask>=3.0\nrich\n-r other.txt\n", encoding="utf-8")
        code2 = repo / "days" / "day-060-y" / "code"
        code2.mkdir(parents=True)
        (code2 / "01-c.py").write_text("import requests, numpy\nfrom tools import console\n", encoding="utf-8")

        radar = scan(repo)
        check(radar.py_scanned == 4 and radar.py_failed == 1, "解析计数含失败文件（pytools.py 也算一个）")
        check(radar.stdlib_imports == 2, "os/sys 归标准库")
        check(radar.local_imports == 2, "pytools 与相对导入归本地，不算第三方")
        names = {p.name: p for p in radar.packages}
        check(set(names) == {"requests", "numpy"}, f"逗号分隔的 import 两个包都要认出：{set(names)}")
        check(names["numpy"].imports == 1, "import requests, numpy 里的 numpy 没被漏掉")
        check(names["requests"].days == [1, 60], "requests 跨两课")
        check(names["requests"].span == 59, "跨度 = 最近 − 首次")
        check(names["requests"].ring == "Hold", "requests 窄面且有替代 → Hold")
        check(names["numpy"].ring == "Hold", "numpy 窄面且有替代 → Hold")
        check(radar.req_counts == {"pinned": 1, "ranged": 1, "unpinned": 1}, f"版本约束分类 {radar.req_counts}")
        check([s["name"] for s in radar.suspects] == ["tools"], "缺失的本地模块单列，不混进第三方")
        check("ModuleNotFoundError" in render(radar, None), "报告点明缺失模块的真实后果")
        check(all(not r.name.startswith("-") for r in radar.requirements), "-r 指令被跳过")
        check("不是等价替换" in render(radar, None), "报告声明替代不等价")
        check("| requests |" in render_markdown(radar), "Markdown 表格可生成")
        check(render(radar, "Adopt").count("（该环没有包）") == 1, "空环有明确提示")

    print(f"SELF-TEST PASS（{checks} 条）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="技术资产雷达与依赖维护审计")
    parser.add_argument("--root", help="仓库根目录")
    parser.add_argument("--ring", choices=RING_ORDER, help="只显示某一环")
    parser.add_argument("--json", metavar="PATH", help="导出结构化结果（供 04 消费）")
    parser.add_argument("--markdown", metavar="PATH", help="导出 Markdown 报告")
    parser.add_argument("--self-test", action="store_true", help="离线自证")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    repo = Path(args.root).expanduser().resolve() if args.root else find_repo()
    started = time.perf_counter()
    radar = scan(repo)
    elapsed = time.perf_counter() - started

    if args.json:
        Path(args.json).write_text(
            json.dumps({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "scan_seconds": round(elapsed, 3), **asdict(radar)},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入 {args.json}")
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(radar), encoding="utf-8")
        print(f"已写入 {args.markdown}")
    print(render(radar, args.ring))
    print(f"\n（ast 扫描耗时 {elapsed * 1000:.1f} ms）")
    return 0


if __name__ == "__main__":
    sys.exit(main())