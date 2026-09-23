#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02-determinism-redaction.py — 进阶用法与避坑（Day 165 · 进阶）

运行：
    python3 02-determinism-redaction.py

本文件回答三个"只有真跑过才会问"的问题：

Q1 报告为什么必须**字节级确定**？
A1 因为报告的价值一半在"能对比"。不能 diff 的报告只是截图。
   这里用两次"逻辑上完全相同、但输入顺序不同"的运行来证明 id 与排序稳定。

Q2 脱敏到底该放在哪一层？擦掉之后还怎么检测？
A2 这是最容易搞反的地方。顺序必须是：
       原始数据 → 提取"值指纹" → 擦除明文 → 用指纹/结构做检测 → 报告
   如果先擦再检测，检测规则会看到 `<REDACTED>` 而失效；
   如果先检测后擦，一旦中间对象被日志打到，秘密就泄漏了。
   本文件用一个"凭证复用检测"演示正确顺序。

Q3 报告里的"变化"怎么表达？
A3 用集合差：id 是内容哈希，所以 新增 = new_ids - old_ids、
   已修复 = old_ids - new_ids。这比"人肉看两份 markdown"可靠得多。
"""

from __future__ import annotations

import json
from pathlib import Path

from report_core import Finding, Report, redact_mapping, redact_text, stable_id

OUT_DIR = Path(__file__).resolve().parent / "out"


# ──────────────────────────────────────────────────────────────────────
# 实验 1：确定性 —— 输入顺序不影响输出
# ──────────────────────────────────────────────────────────────────────
def make_findings(order: list[int]) -> list[Finding]:
    pool = [
        Finding(rule_id="R-OPEN-PORT", title="开放端口", severity="medium",
                target="127.0.0.1:9000", reason="可连接", remediation="关闭"),
        Finding(rule_id="R-SQLI", title="SQL 注入", severity="critical",
                target="http://127.0.0.1:8080/i", reason="错误回显", remediation="参数化"),
        Finding(rule_id="R-CLEARTEXT", title="明文凭证", severity="high",
                target="http://127.0.0.1:8080/login", reason="明文传输", remediation="启用 TLS"),
    ]
    return [pool[i] for i in order]


def experiment_determinism() -> None:
    print("=" * 72)
    print("实验 1：确定性（输入顺序 ≠ 输出顺序）")
    print("=" * 72)

    a = Report(title="T", scope="s", generated_at="2026-09-24T06:00:00+08:00")
    a.extend(make_findings([0, 1, 2]))
    b = Report(title="T", scope="s", generated_at="2026-09-24T06:00:00+08:00")
    b.extend(make_findings([2, 1, 0]))          # 完全反序输入

    # 再塞一条重复项（同 id），验证去重也稳定
    a.add(make_findings([1])[0])
    b.add(make_findings([1])[0])

    ja, jb = a.render_json(), b.render_json()
    print(f"两次渲染是否字节一致：{ja == jb}")
    print(f"顺序 A：{[f['rule_id'] for f in a.model()['findings']]}")
    print(f"顺序 B：{[f['rule_id'] for f in b.model()['findings']]}")
    print("→ 结论：渲染器自己排序，调用方**不需要**先排好。")
    print()

    # 反例：如果没有稳定 id 和排序，会发生什么
    report = Report(title="T", scope="s", generated_at="fixed")
    report.extend(make_findings([0, 1, 2]))
    old_ids = {f["id"] for f in report.model()["findings"]}
    report.findings = [f for f in report.ordered_findings()
                       if f.rule_id != "R-SQLI"]          # 模拟"修好了 SQLi"
    new_ids = {f["id"] for f in report.model()["findings"]}
    print(f"已修复（old - new）：{sorted(old_ids - new_ids)}")
    print(f"新增　（new - old）：{sorted(new_ids - old_ids)}")
    print("→ 结论：靠 id 集合差就能生成「本次修复 / 本次新增」清单。")
    print()


# ──────────────────────────────────────────────────────────────────────
# 实验 2：脱敏顺序 —— 先指纹、再擦除、后检测
# ──────────────────────────────────────────────────────────────────────
def credential_fingerprint(value: str) -> str:
    """值指纹：只保留 sha256 前 8 位 + 长度。

    为什么不全留？因为"能对比两个请求用的是不是同一个口令"
    这件事，只需要指纹就够了——不需要知道口令本身。
    这就是"可验证性"与"保密性"的平衡点。
    """
    import hashlib
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()[:8]}/len={len(value)}"


def experiment_redaction_order() -> None:
    print("=" * 72)
    print("实验 2：脱敏顺序（先擦再检测 = 检测失效 + 误报）")
    print("=" * 72)

    # 被审计目标的"原始"观测记录：两条登录请求，用的是**两个不同**的口令。
    # 真实场景里这里可能是 HTTP 头、Cookie、表单体——我们都压缩成一个字符串，
    # 因为它正好能暴露"先擦后测"的问题。
    raw_events = [
        {"src": "127.0.0.1:51001", "user": "alice",
         "auth": "Authorization: Basic YWxpY2U6SHVudGVyMiFQYXNz"},
        {"src": "127.0.0.1:51022", "user": "bob",
         "auth": "Authorization: Basic Ym9iOldvcmtQbGFjZTk5"},
    ]

    # ── 正确顺序：先指纹 → 再擦除 → 用指纹做检测 ──
    enriched = []
    for ev in raw_events:
        enriched.append({
            "src": ev["src"],
            "user": ev["user"],
            # 指纹基于**明文**计算，明文本身不进结构
            "auth_fingerprint": credential_fingerprint(ev["auth"]),
            # 存下来的是已擦除的展示字段
            "auth_masked": redact_text(ev["auth"]),
        })

    def find_reuse(events: list[dict]) -> dict[str, set[str]]:
        """凭证复用检测：同一指纹出现在多个账号 → 高危。"""
        fp_to_users: dict[str, set[str]] = {}
        for ev in events:
            fp_to_users.setdefault(ev["auth_fingerprint"], set()).add(ev["user"])
        return {fp: u for fp, u in fp_to_users.items() if len(u) > 1}

    good_hits = find_reuse(enriched)
    print(f"[正确顺序] 凭证复用命中：{good_hits or '（无）'}")
    print(f"[正确顺序] 落盘字段：{json.dumps(redact_mapping(enriched[0]), ensure_ascii=False)}")
    print("→ 两个不同口令 → 两个不同指纹 → **不**误报。这是对的。")
    print()

    # ── 错误顺序：先擦除，再指纹 ──
    masked = [redact_mapping(ev) for ev in raw_events]
    wrong = []
    for ev in masked:
        wrong.append({
            "src": ev["src"],
            "user": ev["user"],
            "auth_fingerprint": credential_fingerprint(ev["auth"]),
        })
    bad_hits = find_reuse(wrong)
    print(f"[错误顺序] 被擦除后的字段：{' '.join(e['auth'] for e in masked)!r}")
    print(f"[错误顺序] 指纹：{sorted(e['auth_fingerprint'] for e in wrong)}")
    print(f"[错误顺序] 凭证复用命中：{bad_hits}")
    print("→ 两个**不同**的口令被擦成同一个字符串 → 指纹相同 → **误报「凭证复用」**。")
    print("→ 这是比「漏报」更坏的失败：它会精确地骗过只看告警数量的人。")
    print("→ 结论：擦除必须在提取指纹之后；检测靠指纹，不靠明文。")
    print()


# ──────────────────────────────────────────────────────────────────────
# 实验 3：脱敏的两个典型坑
# ──────────────────────────────────────────────────────────────────────
def experiment_redaction_pitfalls() -> None:
    print("=" * 72)
    print("实验 3：脱敏的典型坑")
    print("=" * 72)

    cases = [
        ("整段吃掉", "password=abc123; token=xyz987",
         "值里排除分隔符后才不会互相吞并"),
        ("只吃一个词", "Authorization: Bearer abcdefgh1234",
         "头字段类规则必须吃到行尾"),
        ("幂等性", "proxy-authorization: Basic dXNlcjpwYXNz",
         "二次脱敏结果必须与一次相同"),
    ]
    for name, text, why in cases:
        once = redact_text(text)
        twice = redact_text(once)
        print(f"[{name}] {text!r}")
        print(f"    -> {once!r}")
        print(f"    幂等：{once == twice}（{why}）")
    print()

    # 一个容易忽略的点：URL 里的凭证
    url = "http://alice:qwerty9876@example.com/api"
    print(f"URL 内嵌凭证：{url!r}")
    print(f"    -> {redact_text(url)!r}")
    print()


# ──────────────────────────────────────────────────────────────────────
# 实验 4：确定性报告的落地形态
# ──────────────────────────────────────────────────────────────────────
def experiment_write_stable_artifacts() -> None:
    print("=" * 72)
    print("实验 4：把确定性报告写盘（可进 git、可 diff）")
    print("=" * 72)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = Report(title="确定性演示", scope="127.0.0.1", generated_at="2026-09-24T06:00:00+08:00")
    report.extend(make_findings([2, 0, 1]))
    path = OUT_DIR / "day165-determinism.md"
    path.write_text(report.render_markdown(), encoding="utf-8")
    digest = stable_id(path.read_text(encoding="utf-8"), length=16)
    print(f"报告已写入 {path.name}，内容哈希 {digest}")
    print("→ 同一输入重复运行，这个哈希不会变；变了就说明目标变了或渲染器被改了。")
    print()


def main() -> int:
    experiment_determinism()
    experiment_redaction_order()
    experiment_redaction_pitfalls()
    experiment_write_stable_artifacts()
    print("✅ 全部实验完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
