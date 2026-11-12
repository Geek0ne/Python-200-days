#!/usr/bin/env python3
"""Day 163 · 实战案例：SQLi + XSS 检测流水线 CLI（安全审计工具箱 · 漏洞面）。

这是 Day 162（资产面）之后的第二个模块：拿到"目标 + 参数"清单后，
自动跑完 SQLi 与 XSS 检测，产出统一的 JSON + Markdown 报告，
并用**语义化退出码**把结论交给上层的 CI / 调度器。

## 用法

```bash
# ① 最省事：起内置回环靶标，扫它（推荐先跑这个）
python3 03-vuln-scan-cli.py --lab

# ② 演示"覆盖不完整"：靶标在第 6 个请求后开始返回 429
python3 03-vuln-scan-cli.py --lab --throttle-after 6

# ③ 扫自己的授权目标：用 targets 文件（每行 "URL [参数名]"，# 开头是注释）
python3 03-vuln-scan-cli.py --targets targets.example.txt --base https://your-host

# ④ 只出 JSON（给机器读）
python3 03-vuln-scan-cli.py --lab --json-only
```

## 退出码（为什么必须是"语义化"的）

| 退出码 | 含义 | 上层应该怎么做 |
|---|---|---|
| `0` | 跑完且无 P0/P1 发现 | 归档，继续 |
| `2` | **越界 / 用法错误** | 立即停下并人工确认授权（**绝不重试**） |
| `3` | 有 P0/P1 级发现 | 阻断发布 / 拉起人工复核 |
| `4` | **覆盖不完整**（429 / 网络异常） | 降速重跑；**不能**当成"通过" |

`4` 单独占一个码是关键设计：**"没测完"和"测完了没问题"必须能被区分开**。
很多自动化扫描器的最大问题就是把限速后的空结果当成"干净"。

⚠️ 安全边界（与 `vuln_core.py` 一致）：
只发 `GET`、只做检测、不取数、不绕过；每个参数最多 4 个探针；
默认限速 2 请求/秒。**请只对你自己拥有或已获书面授权的目标运行。**
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vuln_core import (  # noqa: E402
    DEFAULT_RATE,
    AuthorizationError,
    LabVulnHTTP,
    Scope,
    ScopeError,
    build_report,
    detect_sqli,
    detect_xss,
    exit_code,
    findings_from_sqli,
    findings_from_xss,
    render_markdown,
    write_report,
)

# 默认扫描计划：URL 与要测的参数名。
# 顺序固定 → 报告可复现（同样的目标得到同样的探针序列）。
DEFAULT_PLAN: list[tuple[str, str, str]] = [
    # (path, param, 检测器)
    ("/product?id=1", "id", "sqli"),
    ("/safe-product?id=1", "id", "sqli"),
    ("/echo?id=1", "id", "sqli"),
    ("/search?q=hello", "q", "xss"),
    ("/safe-search?q=hello", "q", "xss"),
    ("/profile?name=ops", "name", "xss"),
    ("/greeting?name=ops", "name", "xss"),
    ("/comment?note=hi", "note", "xss"),
    ("/echo?id=hi", "id", "xss"),
]


def scope_from_base(base: str) -> Scope:
    """从 `--base` 推导授权范围：主机锁死该 IP、端口锁死该端口。"""
    import urllib.parse
    parts = urllib.parse.urlsplit(base)
    host = parts.hostname or ""
    port = parts.port or (443 if parts.scheme == "https" else 80)
    return Scope(networks=(host + "/32",), ports=(port,),
                 http_bases=(base.rstrip("/"),), ticket="CLI-163")


def load_targets(path: str) -> list[tuple[str, str, str]]:
    """读 targets 文件：每行 `URL [参数名] [sqli|xss]`，`#` 开头是注释。

    参数名与检测器可省略：省略参数名时由检测器自己取第一个查询参数。
    """
    plan: list[tuple[str, str, str]] = []
    for lineno, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if "#" in line:                      # 支持行尾注释：便于在清单里直接写「为什么测这个」
            line = line.split("#", 1)[0].strip()
        if not line:
            continue
        chunks = line.split()
        if len(chunks) > 3:
            raise ScopeError(f"{path}:{lineno} 字段过多: {line!r}")
        url = chunks[0]
        param = chunks[1] if len(chunks) > 1 else ""
        if param.lower() in ("sqli", "xss") and len(chunks) == 2:
            param, kind = "", param.lower()
        else:
            kind = chunks[2].lower() if len(chunks) > 2 else ("sqli" if "id=" in url else "xss")
        if kind not in ("sqli", "xss"):
            raise ScopeError(f"{path}:{lineno} 未知检测器: {kind!r}")
        plan.append((url, param, kind))
    if not plan:
        raise ScopeError(f"{path} 里没有任何有效目标")
    return plan


def run_plan(plan, scope: Scope, rate: float) -> tuple[list, list, dict]:
    """顺序执行检测计划，返回 (sqli 结果, xss 结果, 覆盖统计)。

    为什么顺序执行而不是并发？因为**限速是全局的**：并发只会让
    令牌桶排队，还会让"探针顺序 ↔ 报告顺序"的对应关系变难读。
    资产面（端口扫描）适合并发，漏洞面适合慢而有序。
    """
    sqli_all, xss_all = [], []
    probes = throttled = errors = 0

    for idx, (url, param, kind) in enumerate(plan, 1):
        # 允许两种写法：以 / 开头的路径（拼授权基址）、或完整 URL（由门禁校验）
        target = url if url.startswith(("http://", "https://")) else f"{scope.http_bases[0]}{url}"
        print(f"[{idx:>2}/{len(plan)}] {kind:<4} {target}"
              + (f"  参数={param}" if param else ""), flush=True)
        kw = {"param": param or None, "rate": rate}
        if kind == "sqli":
            res = detect_sqli(target, scope, **kw)
            sqli_all.append(res)
            probes += len(res.probes)
            throttled += sum(1 for p in res.probes if p.status == 429)
            if res.throttled:
                print("        ⚠️ 命中限速：该目标**没有有效结论**（覆盖缺口）")
        else:
            res = detect_xss(target, scope, **kw)
            xss_all.append(res)
            probes += 1
            throttled += 1 if res.throttle_or_error else 0
            if res.throttle_or_error:
                print("        ⚠️ 限速/异常：该目标**没有有效结论**（覆盖缺口）")
        errors += 1 if any(getattr(r, "error", "") for r in
                           ([res] if kind == "xss" else res.probes)) else 0

    incomplete = throttled > 0 or errors > 0
    coverage = {
        "targets": len(plan),
        "probes": probes,
        "throttled": throttled,
        "errors": errors,
        "incomplete": incomplete,
        "note": ("覆盖不完整：存在 429/网络异常，未取得结论的目标需降速重跑"
                 if incomplete else "全部目标均取得有效结论"),
    }
    return sqli_all, xss_all, coverage


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="SQLi + XSS 检测流水线（检测-only，只对授权目标运行）")
    ap.add_argument("--lab", action="store_true", help="启动内置回环靶标并扫描它")
    ap.add_argument("--lab-port", type=int, default=18088, help="内置靶标端口")
    ap.add_argument("--throttle-after", type=int, default=None,
                    help="靶标在第 N 个请求后返回 429（用于演示覆盖缺口）")
    ap.add_argument("--base", default=None, help="授权基址，如 http://127.0.0.1:8080")
    ap.add_argument("--targets", default=None, help="目标文件（每行 URL [参数] [sqli|xss]）")
    ap.add_argument("--rate", type=float, default=DEFAULT_RATE, help="请求/秒，默认 2")
    ap.add_argument("--out", default="out", help="报告输出目录")
    ap.add_argument("--tag", default="day163-pipeline", help="报告标签（文件名前缀）")
    ap.add_argument("--json-only", action="store_true", help="只输出 JSON")
    args = ap.parse_args(argv)

    lab: LabVulnHTTP | None = None
    try:
        if args.lab:
            lab = LabVulnHTTP(port=args.lab_port, throttle_after=args.throttle_after)
            lab.start()
            base = f"http://127.0.0.1:{lab.port}"
            # --lab 也可以配合 --targets：验证「自写清单能否正确落到靶标上」
            plan = load_targets(args.targets) if args.targets else list(DEFAULT_PLAN)
        else:
            if not args.base:
                ap.error("必须给出 --lab 或 --base")
            base = args.base.rstrip("/")
            plan = load_targets(args.targets) if args.targets else list(DEFAULT_PLAN)

        scope = scope_from_base(base)
        if not args.json_only:
            print(f"[scope] 授权基址 {base}")
            print(f"[scope] 网段 {list(scope.networks)}  端口 {list(scope.ports)}")
            print(f"[scope] 限速 {args.rate} 请求/秒 · 计划 {len(plan)} 个目标")
            print("-" * 68)

        sqli_all, xss_all, coverage = run_plan(plan, scope, args.rate)
        findings = findings_from_sqli(sqli_all) + findings_from_xss(xss_all)
        report = build_report(scope, sqli_all, xss_all, findings, coverage, tag=args.tag)
        code = exit_code(findings, incomplete=coverage["incomplete"])

        # 报告同时落盘 JSON（机器读）与 Markdown（人读）
        jp, mp = write_report(report, args.out)
        if args.json_only:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print("-" * 68)
            print(f"[report] {jp}")
            print(f"[report] {mp}")
            print(f"[summary] 发现 {report['summary']['total']} 条 · "
                  f"优先级分布 {report['summary']['by_priority']}")
            print(f"[coverage] {coverage['note']}")
            print(f"[exit] {code}")
        return code
    finally:
        if lab:
            lab.stop()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuthorizationError as exc:
        # 越界：策略拒绝 → 退出码 2，**不重试**
        print(f"⛔ AuthorizationError: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except ScopeError as exc:
        print(f"⛔ ScopeError: {exc}", file=sys.stderr)
        raise SystemExit(2)
