#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01-basic-report.py — 报告核心库基础用法（Day 165 · 基础）

运行：
    python3 01-basic-report.py

这个文件只演示"最小可用路径"：
    收集 Finding → 组装 Report → 渲染 Markdown

请重点看三件事：
  1. `generated_at` 是**手写死的字符串**，不是 `datetime.now()`。
     这是为了确定性（见 README 第 3 节）。
  2. 输出目录默认 `out/`，写文件而不是打印一坨到终端。
  3. `coverage_gaps` 一定要填——报告里有"没查到什么"比"查到什么"更容易被忽略。
"""

from __future__ import annotations

import os
from pathlib import Path

from report_core import Finding, Report, summarize

OUT_DIR = Path(__file__).resolve().parent / "out"


def build_report() -> Report:
    """构造一份演示报告。

    这里刻意混入一条"无证据的建议项"（info 级），用来验证渲染逻辑
    不会给没有证据的条目编造证据。
    """
    report = Report(
        title="安全审计报告 — 本机自建靶场",
        scope="127.0.0.1 (自建靶场，非真实目标)",
        # 固定时间戳：保证同一输入每次渲染结果字节一致
        generated_at="2026-09-24T06:00:00+08:00",
        tool_version="audit-toolbox/1.0",
    )

    # ── 来自 Day 162 资产面的发现 ──
    report.add(Finding(
        rule_id="ASSET-OPEN-PORT",
        title="发现对外开放的调试端口",
        severity="medium",
        target="127.0.0.1:9000",
        phase="Day 162 资产面",
        reason="端口 9000 可建立 TCP 连接，且 banner 显示为调试服务。",
        remediation="确认该服务是否必须监听；若非必要，绑定到 127.0.0.1 或直接关闭。",
        confidence="high",
        evidence=(
            "TCP connect 127.0.0.1:9000 -> open",
            "banner: 'debug-http/0.3'",
        ),
        tags=("asset", "port"),
    ))

    # ── 来自 Day 163 漏洞面的发现（含会被脱敏的证据） ──
    report.add(Finding(
        rule_id="WEB-SQLI-ERROR",
        title="SQL 注入：错误回显型",
        severity="critical",
        target="http://127.0.0.1:8080/item?id=1",
        phase="Day 163 漏洞面",
        reason="注入单引号后服务端返回数据库错误信息，说明参数未参数化。",
        remediation="使用参数化查询（预编译语句），禁止字符串拼接 SQL。",
        confidence="high",
        evidence=(
            "request: GET /item?id=1%27",
            "response: 500 'You have an error in your SQL syntax'",
            # 下面这行演示"证据里带秘密时会被自动擦除"
            "captured header: Authorization: Bearer SUPERSECRETTOKEN123",
        ),
        tags=("web", "sqli"),
    ))

    # ── 来自 Day 164 流量面的发现 ──
    report.add(Finding(
        rule_id="TRAFFIC-CLEARTEXT-CRED",
        title="凭证以明文形式在 HTTP 上传输",
        severity="high",
        target="http://127.0.0.1:8080/login",
        phase="Day 164 流量面",
        reason="请求体中出现口令字段的明文（值指纹已记录，值本身不落盘）。",
        remediation="全站启用 HTTPS 并强制 HSTS；口令只在 TLS 通道内传输。",
        confidence="high",
        evidence=(
            "POST /login body: username=alice&password=<REDACTED>",
        ),
        tags=("traffic", "cleartext"),
    ))

    # ── 一条低置信度发现：要证明"乘置信度"是必要的 ──
    report.add(Finding(
        rule_id="TRAFFIC-SUSPICIOUS-UA",
        title="可疑扫描器 User-Agent",
        severity="high",
        target="127.0.0.1:9000",
        phase="Day 164 流量面",
        reason="UA 命中扫描器特征串，但目标可能只是本机压测脚本，存在误报可能。",
        remediation="结合源 IP 与频率再判断；如为压测脚本请加入白名单。",
        confidence="low",          # ← low 置信度会把风险分从 25 压到 7
        evidence=("ua: 'masscan/1.3'",),
        tags=("traffic", "scanner"),
    ))

    # ── 一条无证据的建议项 ──
    report.add(Finding(
        rule_id="PROCESS-NO-RETENTION",
        title="尚未定义报告留存策略",
        severity="info",
        target="audit-process",
        phase="Day 165 报告层",
        reason="当前报告未规定保存周期与访问权限，审计证据可能失效或被越权读取。",
        remediation="约定留存周期（例如 180 天）、存放位置与最小可读角色。",
        confidence="high",
        evidence=(),               # ← 空证据，渲染时必须显示"（无证据，属建议项）"
        tags=("process",),
    ))

    # ── 覆盖缺口：**必须**写清楚哪里没测 ──
    report.coverage_gaps.extend([
        "CONNECT 隧道内容不可见（TLS 内层未解密），流量面结论仅覆盖明文 HTTP。",
        "未做认证后的越权测试（无有效账号，属授权范围外）。",
        "未覆盖 IPv6 目标。",
    ])
    report.notes.append("本报告仅针对自建靶场，不代表任何真实资产的结论。")
    return report


def main() -> int:
    report = build_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    md_path = OUT_DIR / "day165-basic-report.md"
    json_path = OUT_DIR / "day165-basic-report.json"

    md_path.write_text(report.render_markdown(), encoding="utf-8")
    json_path.write_text(report.render_json(), encoding="utf-8")

    print(f"✅ Markdown 报告：{os.path.relpath(md_path)}")
    print(f"✅ JSON 报告　　：{os.path.relpath(json_path)}")
    print(f"📊 摘要：{summarize(report)}")
    print()
    # 把 Markdown 前 55 行打出来，方便直接在终端确认渲染结果
    preview = report.render_markdown().splitlines()
    print("\n".join(preview[:55]))
    print(f"... （共 {len(preview)} 行，完整内容见 {md_path.name}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
