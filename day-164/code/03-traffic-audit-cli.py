#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""03-traffic-audit-cli.py — 实战：完整的"捕获 → 分析 → 报告"流水线

这是 Day 164 的**收口件**：把前两个例子里的能力拼成一条可进 CI 的命令。

## 它和 01 / 02 的区别

| | 01 基础用法 | 02 进阶用法 | **03 实战 CLI** |
|---|---|---|---|
| 目标 | 跑通三方闭环 | 讲清规则与踩坑 | **产出可交付的报告** |
| 输出 | 终端汇总 | 终端明细 | **JSON + Markdown 文件** |
| 退出码 | 恒 0 | 打印 | **0/2/3/4 语义化，可直接进 CI** |
| 覆盖率 | 只有流量层 | 只有流量层 | **流量层 + 业务层（两层）** |

## 两层覆盖率：这是本课最容易做漏的一件事

大多数人只算第一层：

```text
第一层（流量层）：捕获到的 flow 里，有多少条"内容看得见"
                  → 100% 时很容易让人安心
```

但**真正的盲区常常在第二层**：

```text
第二层（业务层）：目标清单里的 URL，有多少条**从来没有出现在流量里**？
                  → 这些端点你根本没看过，而报告里它们连一个字都不会出现
```

**为什么第二层更重要？** 因为用户没点过的路径，流量里当然没有——
流量面是**被动**的。如果只用第一层，会得出"覆盖率 100%"的假象。
本 CLI 把两层都算出来，并让第二层也参与退出码判定。

## 用法

    # 全自动：起靶场 → 抓会话 → 分析 → 出报告
    python3 03-traffic-audit-cli.py

    # 只分析已有档案（不起任何服务，最适合 CI）
    python3 03-traffic-audit-cli.py --capture out/day164-basic-flows.jsonl

    # 指定报告目录与标签
    python3 03-traffic-audit-cli.py --out out --tag nightly-2026-09-23

    # 只看 JSON 路径（给脚本用）
    python3 03-traffic-audit-cli.py --quiet
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mitm_core import (  # noqa: E402
    AuditProxy,
    EXIT_FINDINGS,
    EXIT_GATE_REJECTED,
    EXIT_INCOMPLETE,
    EXIT_MEANING,
    EXIT_OK,
    FlowAnalyzer,
    FlowStore,
    LabOpaqueTCP,
    LabOrigin,
    LabSession,
    Scope,
    AuthorizationError,
    render_json,
    render_markdown,
)


# ─────────────────────────────────────────────────────────────────────────────
# 目标清单：读 + 业务层覆盖对账
# ─────────────────────────────────────────────────────────────────────────────


def load_targets(path: Path | None) -> list[str]:
    """读目标清单。`#` 注释、空行忽略。

    **为什么要支持"没有清单"的情况？** 因为真实场景里经常是这样：
    你先在网关/交换机上镜像了一段流量，手上**没有**清单。
    这时第二层覆盖率就没法算——CLI 应当**如实说"未提供清单"**，
    而不是假装算出一个 100%。
    """
    if path is None or not path.exists():
        return []
    targets: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        targets.append(line)
    return targets


def _norm(url: str) -> str:
    """归一化 URL：去掉查询串与末尾斜杠，用于"清单 ↔ 流量"的对账。

    **为什么去掉查询串？** 因为清单里写的是 `/api/user?id=1`，
    而流量里可能是 `/api/user?id=7` —— 它们是**同一个端点**。
    对账的目的是"这个端点有没有被访问过"，不是"参数值是否一致"。

    **为什么末尾斜杠也要归一？** 因为 `/search` 与 `/search/`
    在不少框架里是同一个路由，但字符串比较会认为它们不同，
    从而产生**假性的"未覆盖"**。这类假阳性会让人不再信任覆盖率数字。
    """
    parts = urlsplit(url)
    path = parts.path.rstrip("/") or "/"
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{parts.hostname}{port}{path}"


def reconcile_targets(targets: list[str], rows: list[dict]) -> dict:
    """业务层覆盖对账：清单里哪些端点**没有**在流量里出现过。"""
    seen = {_norm(r.get("url") or "") for r in rows if r.get("url")}
    unseen: list[str] = []
    seen_targets: list[str] = []
    for target in targets:
        if _norm(target) in seen:
            seen_targets.append(target)
        else:
            unseen.append(target)
    total = len(targets)
    return {
        "provided": bool(targets),
        "targets_total": total,
        "targets_seen": len(seen_targets),
        "targets_unseen": unseen,
        "target_coverage_percent": round(100.0 * len(seen_targets) / total, 1) if total else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────────────


def _bind_or_fallback(factory, preferred: int, label: str):
    """优先绑固定端口；被占用则退回内核分配并**明确告警**。

    **为什么非要固定端口不可？** 因为本 CLI 做的是**两层覆盖对账**：
    目标清单里写的是 `http://127.0.0.1:18081/api/user?id=1`，
    如果这次靶场恰好被分到 `:40697`，对账就会算出"业务覆盖率 0%"
    —— 一个**因为端口漂移而产生的假盲区**。

    这类假阳性比"漏报"更伤信任：读者看到 0% 会去追一个不存在的问题，
    追一次之后就不再相信这个数字了。

    但端口确实可能被占用（上次的进程没退干净），所以**不能硬失败**：
    退回随机端口 + 打印一句明确告警，让读者知道"这次的业务层覆盖率不可信"，
    比让脚本崩掉更有用。
    """
    try:
        return factory(port=preferred), preferred
    except OSError as exc:
        print(f"⚠️ {label} 端口 {preferred} 不可用（{exc}），退回内核分配。")
        if label == "靶站":
            print("   → 注意：目标清单用的是固定端口，本次【业务层覆盖率】会失真，不可采信。")
        return factory(port=0), 0


def do_capture(
    capture_path: Path,
    tag: str,
    origin_port: int = 18081,
    proxy_port: int = 18080,
) -> None:
    """起靶场 + 起代理 + 跑一遍示范会话。

    **注意这一段的顺序**：先起服务（with 块），跑完会话后**退出 with**，
    再读档案。这个顺序保证了 socket 已经关闭、文件已经 flush——
    否则你会遇到"档案里少了最后几条 flow"这种随机失败。
    """
    if capture_path.exists():
        capture_path.unlink()
    scope = Scope(ticket=f"LAB-164-CLI/{tag}")

    origin, actual_origin_port = _bind_or_fallback(LabOrigin, origin_port, "靶站")
    proxy, _ = _bind_or_fallback(
        lambda port: AuditProxy(capture_path, port=port, scope=scope, verbose=False),
        proxy_port,
        "代理",
    )
    with origin, LabOpaqueTCP() as opaque, proxy:
        print(f"   靶站 {origin.base} · 代理 {proxy.url}")
        LabSession(proxy.url, scope=scope, rate=20).run_demo(
            origin.base, opaque_port=opaque.port
        )


def analyze_scope_aware(rows: list[dict], targets: list[str]) -> tuple[FlowAnalyzer, int]:
    """分析 + 计算最终退出码。"""
    scope = Scope(ticket="LAB-164-CLI")

    # 门禁二次校验：档案里如果出现越界主机，说明采集环节的配置出了问题。
    # **为什么要在分析阶段再查一次？** 因为档案可能来自"别人的采集器"
    # 或上一轮任务——分析器不能假设"采集侧一定守规矩"。
    for row in rows:
        host = (row.get("host") or "").lower()
        if host and not scope.check_host(host):
            print(f"❌ 档案中出现越界主机：{host}（拒绝出结论）")
            analyzer = FlowAnalyzer(scope=scope)
            analyzer.analyze(rows)
            analyzer.facts["targets"] = reconcile_targets(targets, rows)
            return analyzer, EXIT_GATE_REJECTED

    analyzer = FlowAnalyzer(scope=scope)
    analyzer.analyze(rows)

    code = analyzer.exit_code()

    # 业务层缺口也要参与退出码：有"从没出现过的端点" → 同样是不完整。
    recon = reconcile_targets(targets, rows)
    analyzer.facts["targets"] = recon
    if recon["provided"] and recon["targets_unseen"] and code == EXIT_OK:
        code = EXIT_INCOMPLETE
    return analyzer, code


def print_report(analyzer: FlowAnalyzer, code: int, json_path: Path, md_path: Path) -> None:
    facts = analyzer.facts
    recon = facts.get("targets", {})

    print("\n" + "=" * 78)
    print("📋 流量审计报告摘要")
    print("=" * 78)
    print(f"总 flow          : {facts['flows']}")
    print(f"覆盖率（流量层）  : {facts['coverage_percent']}%"
          f"（已检查 {facts['inspected']} / 未检查 {facts['uninspected']}"
          f" / 传输错误 {facts['transport_errors']}）")

    if recon.get("provided"):
        print(f"覆盖率（业务层）  : {recon['target_coverage_percent']}%"
              f"（清单 {recon['targets_total']} 个端点，"
              f"命中 {recon['targets_seen']}，未见 {len(recon['targets_unseen'])}）")
        if recon["targets_unseen"]:
            print("  ⚠️ 从未出现在流量里的端点（业务盲区）：")
            for target in recon["targets_unseen"]:
                print(f"     · {target}")
    else:
        print("覆盖率（业务层）  : 未提供目标清单 → 无法计算（不是 100%）")

    print(f"\n命中规则         : {facts['rules_hit']}")
    print(f"严重度分布       : {facts['severity_counts']}")

    p0p1 = [f for f in analyzer.findings if f.level in ("P0", "P1")]
    if p0p1:
        print(f"\n🔴 P0/P1 共 {len(p0p1)} 条：")
        for f in sorted(p0p1, key=lambda x: -x.priority):
            print(f"   [{f.level}·{f.severity}] {f.rule:<28} {f.flow_id}  {f.evidence[:52]}")

    print(f"\n报告文件         : {json_path}")
    print(f"                 : {md_path}")
    print(f"\n🚦 退出码 = {code} → {EXIT_MEANING.get(code, '未知')}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Day 164 · 流量审计 CLI（捕获 → 分析 → 报告）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--capture", default=None,
                        help="已有档案（.jsonl）。不传则自动起靶场抓一份")
    parser.add_argument("--targets", default="targets.example.txt",
                        help="目标清单（URL 一行一个；不传则跳过业务层覆盖对账）")
    parser.add_argument("--out", default="out", help="报告输出目录")
    parser.add_argument("--tag", default=None, help="报告标签（默认用日期）")
    parser.add_argument("--quiet", action="store_true", help="只打印两个报告路径")
    parser.add_argument("--origin-port", type=int, default=18081,
                        help="靶站端口（默认 18081，需与目标清单一致）")
    parser.add_argument("--proxy-port", type=int, default=18080,
                        help="代理端口（默认 18080）")
    args = parser.parse_args()

    tag = args.tag or datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"day164-audit-{tag}.json"
    md_path = out_dir / f"day164-audit-{tag}.md"

    targets = load_targets(Path(args.targets) if args.targets else None)
    if not args.quiet:
        print(f"🎫 目标清单：{args.targets}（{len(targets)} 条）")

    # —— 阶段 1：采集 ——
    if args.capture:
        capture_path = Path(args.capture)
        if not capture_path.exists():
            print(f"❌ 档案不存在：{capture_path}")
            return 2
        if not args.quiet:
            print(f"📂 使用已有档案：{capture_path}")
    else:
        capture_path = out_dir / f"day164-capture-{tag}.jsonl"
        if not args.quiet:
            print(f"📥 未指定 --capture，自动抓取会话 → {capture_path}")
        started = time.monotonic()
        do_capture(capture_path, tag, origin_port=args.origin_port, proxy_port=args.proxy_port)
        if not args.quiet:
            print(f"   采集耗时 {time.monotonic() - started:.2f}s")

    # —— 阶段 2：分析 ——
    try:
        rows = FlowStore(capture_path).load()
        analyzer, code = analyze_scope_aware(rows, targets)
    except AuthorizationError as exc:
        print(f"❌ 门禁拒绝：{exc}")
        return EXIT_GATE_REJECTED

    # —— 阶段 3：报告 ——
    meta = {
        "标签": tag,
        "档案": str(capture_path),
        "目标清单": str(args.targets) if targets else "（未提供）",
        "覆盖口径": "流量层 = 内容可见；业务层 = 清单端点是否出现在流量里",
    }
    json_path.write_text(
        render_json(analyzer.findings, analyzer.facts, code, meta=meta), encoding="utf-8"
    )
    md_path.write_text(
        render_markdown(analyzer.findings, analyzer.facts, code, meta=meta), encoding="utf-8"
    )

    if args.quiet:
        print(str(json_path))
        print(str(md_path))
    else:
        print_report(analyzer, code, json_path, md_path)
        print("\nCI 用法示例：")
        print(f"  python3 03-traffic-audit-cli.py --capture {capture_path} --quiet \\")
        print("      && echo '✅ 无 P0/P1 发现' || echo \"❌ 退出码 $?（见报告）\"")

    return code


if __name__ == "__main__":
    sys.exit(main())
