#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""02-flow-analyze.py — 进阶用法：规则引擎 + 三个真实踩坑的现场复现

本文件做两件事：

**第一件**：把 `01-flow-capture.py` 抓下来的档案，用 `FlowAnalyzer` 变成
可读的 **Finding**（含证据 / 原因 / 修复建议 / 优先级），并算出覆盖率与退出码。

**第二件（本课重点）**：把 `mitm_core.py` 里修过的**三个真实 bug 现场复现一遍**。
每一个都写成"先让你看到错误结果 → 再说明根因 → 再给出修复"的三段式。

    ⚠️ 为什么要把 bug 也写进教学示例？

    因为"正确写法长什么样"是**记不住**的；而"我踩过这个坑、当时现象是 XX"
    是**忘不掉**的。这三个坑（框架默认行为 / 编码后字面量 / 同源数据漏脱敏）
    都不是"不小心"，而是"看起来完全正确"的代码。
    它们的共同结构是：**把假设当成了事实。**

运行：

    python3 02-flow-analyze.py                    # 自动抓一次新会话再分析
    python3 02-flow-analyze.py --capture out/x.jsonl   # 分析已有档案
    python3 02-flow-analyze.py --no-pitfalls      # 只看分析结果，跳过踩坑演示
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mitm_core import (  # noqa: E402
    AuditProxy,
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
    _body_has_sensitive_marker,
    _NoRedirect,
    _pii_labels,
    _redact_query_in_path,
    mask_pii,
    redact_body,
    redact_url,
)

SEVERITY_ICON = {
    "critical": "🟥",
    "high": "🟧",
    "medium": "🟨",
    "low": "🟦",
    "info": "⬜",
}


# ─────────────────────────────────────────────────────────────────────────────
# 第一部分：分析档案
# ─────────────────────────────────────────────────────────────────────────────


def print_findings(analyzer: FlowAnalyzer) -> None:
    findings = analyzer.findings_by_severity
    facts = analyzer.facts

    print("\n" + "=" * 78)
    print("🔎 规则引擎输出")
    print("=" * 78)
    print(f"分析 flow  : {facts['flows']} 条")
    print(f"覆盖率     : {facts['coverage_percent']}%"
          f"（已检查 {facts['inspected']} / 未检查 {facts['uninspected']}"
          f" / 传输错误 {facts['transport_errors']}）")
    print(f"命中规则   : {facts['rules_hit']}")
    print(f"严重度分布 : {facts['severity_counts']}")

    if not findings:
        print("\n（没有发现。记住：这不等于安全，先看覆盖率。）")
        return

    print(f"\n发现明细（按严重度 → 优先级排序，共 {len(findings)} 条）：")
    for idx, f in enumerate(findings, 1):
        icon = SEVERITY_ICON.get(f.severity, "·")
        print(f"\n{icon} {idx}. [{f.level} · {f.severity}] {f.rule}")
        print(f"    flow     : {f.flow_id}  {f.url}")
        print(f"    证据     : {f.evidence}")
        print(f"    为什么   : {f.why}")
        print(f"    修复建议 : {f.fix}")
        print(f"    优先级   : {f.priority}")


def print_exit_code(analyzer: FlowAnalyzer) -> int:
    code = analyzer.exit_code()
    print("\n" + "=" * 78)
    print(f"🚦 退出码 = {code} → {EXIT_MEANING.get(code, '未知')}")
    print("=" * 78)
    if code == EXIT_INCOMPLETE:
        print("注意：这个 4 不是『发现不够严重』，而是『这轮结论不完整』。")
        print("      让覆盖率掉下来的那条 flow 是 CONNECT 隧道（R10）。")
    elif code == EXIT_GATE_REJECTED:
        print("注意：这是流程/配置问题（越界），不是安全问题。")
    elif code == EXIT_OK:
        print("注意：0 的含义是『在已检查的流量里没有 P0/P1 发现』。")
    return code


# ─────────────────────────────────────────────────────────────────────────────
# 第二部分：三个真实踩坑的现场复现
# ─────────────────────────────────────────────────────────────────────────────


def pitfall_1_redirect() -> None:
    """坑 ①：`build_opener()` 会替你装上重定向处理器。

    现象：`/redirect?to=/login` 在档案里记成 404，`redirect-chain` 规则永远沉默。
    """
    print("\n" + "─" * 78)
    print("坑 ① · 『我没装重定向处理器』≠『它不会跟随重定向』")
    print("─" * 78)

    with LabOrigin() as origin:
        url = f"{origin.base}/redirect?to=/login"

        # ❌ 错误写法：只传 HTTPHandler（**以为**不会跟随）
        naive = urllib.request.build_opener(urllib.request.HTTPHandler())
        try:
            with naive.open(url, timeout=5) as resp:
                wrong = f"{resp.status}（已被跟随到最终页）"
        except urllib.error.HTTPError as err:
            # 3xx 抛 HTTPError = 停在第一跳；其他码 = 它已经跟过去了
            if err.code in (301, 302, 303, 307, 308):
                wrong = f"{err.code}（停在第一跳）"
            else:
                wrong = f"{err.code}（❌ 已被跟随：/login 是 404）"

        # ✅ 正确写法：显式提供一个 redirect_request() 返回 None 的子类
        fixed = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPHandler())
        try:
            with fixed.open(url, timeout=5) as resp:
                right = f"{resp.status}（已被跟随）"
        except urllib.error.HTTPError as err:
            if err.code in (301, 302, 303, 307, 308):
                right = f"{err.code}（✅ 停在第一跳，可被 R9 记录）"
            else:
                right = f"{err.code}（❌ 被跟随）"

    print(f"  ❌ 默认 opener     : {wrong}")
    print(f"  ✅ 显式 _NoRedirect: {right}")
    print()
    print("  根因：`build_opener()` 的语义是『在**默认处理器**基础上加上你给的』。")
    print("        你不传 HTTPRedirectHandler，它就把默认实现补上。")
    print("  后果：302 被悄悄跟随，档案里只剩最终页的 404。")
    print("        → R9 redirect-chain 永不命中 → 重定向链完全从报告里消失。")
    print("  教训：『我没有做某件事』和『某件事不会发生』是两回事。")
    print("        遇到框架替你做默认选择的场景，要验证**默认值**，别推理你传了什么。")


def pitfall_2_form_encoding() -> None:
    """坑 ②：脱敏标记在 `urlencode` 之后变成了 `redacted%3a`。

    现象：`cleartext-credential` 规则对**所有 form 表单**都不命中。
    """
    print("\n" + "─" * 78)
    print("坑 ② · 序列化会改变字面量：`redacted:` → `redacted%3a`")
    print("─" * 78)

    raw = "username=ada&password=Sup3rSecret!"
    redacted, hits = redact_body(raw, "application/x-www-form-urlencoded")

    print(f"  原始请求体   : {raw}")
    print(f"  脱敏之后     : {redacted}")
    print(f"  命中字段     : {hits}")
    print()
    print("  现在做一次『朴素检测』——只认 ASCII 冒号的写法：")
    naive_ok = "redacted:" in redacted.lower()
    print(f"    朴素检测  if 'redacted:' in body   → {naive_ok}")
    print()
    print("  再做一次本课实际使用的检测（两种写法都认）：")
    real_ok = _body_has_sensitive_marker(redacted, "application/x-www-form-urlencoded")
    print(f"    正确检测  'redacted:' 或 'redacted%3a' → {real_ok}")
    print()
    print("  根因：`urlencode()` 会把 `:` `/` `<` `>` 全部百分号转义。")
    print("        检测代码在『我构造时的样子』上匹配，而不是在『真实落盘的样子』上匹配。")
    print("  教训：任何『写入 → 编码 → 再读出比对』的链路，")
    print("        都要在**编码之后的字面量**上做断言。")
    print("        （本课的自检就是这么做的：直接读档案文件全文做 in 判断。）")


def pitfall_3_partial_redaction() -> None:
    """坑 ③：只脱敏了 URL，忘了 `path` 里带着同一份查询串。

    现象：自检断言 `明文 token 泄漏进了档案！` 失败。
    """
    print("\n" + "─" * 78)
    print("坑 ③ · 脱敏必须穷尽『同源数据』：URL 与 path 是同一份秘密")
    print("─" * 78)

    token = "tk_live_164_fake"
    full_url = f"http://127.0.0.1:18081/search?q=python&token={token}"
    path = "/search?q=python&token=" + token   # ← 请求行里的 path 也带着它

    safe_url, keys = redact_url(full_url)
    safe_path = _redact_query_in_path(path)

    print(f"  原始 URL      : {full_url}")
    print(f"  脱敏后 URL    : {safe_url}")
    print(f"  敏感参数名    : {keys}")
    print()
    print(f"  请求行里的 path（❌ 若原样入库）: {path}")
    print(f"  请求行里的 path（✅ 脱敏后入库）: {safe_path}")
    print()
    leaked = token in path
    print(f"  如果只脱敏 URL、忘了 path，档案里还有明文吗？ → {leaked}")
    print()
    print("  根因：同一个秘密可能同时出现在 URL、path、Referer、")
    print("        日志字段、异常栈里。只处理你知道的那一处，等于没处理。")
    print("  教训：写完脱敏，**扫一遍产出物**去断言『那个明文不在了』。")
    print("        这是唯一可靠的兜底手段（本课自检的第 ② 组断言就是干这个的）。")


def pitfall_4_pii_erasure() -> None:
    """坑 ④（附加）：PII 擦除之后，再扫正文就什么也扫不到了。

    现象：`pii-in-request` 规则永远沉默——因为值已经被替换成 `<pii:类别>`。
    """
    print("\n" + "─" * 78)
    print("坑 ④ · 『擦除』与『检测』必须分开：擦掉就再也扫不到")
    print("─" * 78)

    body = "username=13800138000&note=联系我 ada@example.com"
    erased, labels = mask_pii(body)

    print(f"  原始正文           : {body}")
    print(f"  擦除后正文         : {erased}")
    print(f"  擦除时记下的类别   : {labels}")
    print()
    print("  现在用『事后重扫正文』的办法做检测：")
    rescan = _pii_labels(erased)
    print(f"    重扫擦除后的正文 → {rescan}   ← 空！PII 已经不在了")
    print()
    print("  正确做法：擦除时**当场**把类别记进 flow.pii_labels 字段。")
    print("    规则 R13 读的是 pii_labels，不是重扫正文。")
    print()
    print("  根因：『破坏性操作』与『基于原文的检测』有先后依赖，")
    print("        顺序错了就永久丢失信息。")
    print("  教训：先问清楚『信息在哪一步还在』，再决定在哪一步采集它。")


# ─────────────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────────────


def capture_fresh(capture_path: Path) -> None:
    """没有现成档案时，自己抓一份。"""
    if capture_path.exists():
        capture_path.unlink()
    scope = Scope(ticket="LAB-164-ADV")
    print(f"📥 抓取新会话 → {capture_path}")
    with LabOrigin() as origin, LabOpaqueTCP() as opaque, AuditProxy(
        capture_path, scope=scope, verbose=False
    ) as proxy:
        LabSession(proxy.url, scope=scope, rate=20).run_demo(
            origin.base, opaque_port=opaque.port
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Day 164 · 进阶用法：规则引擎与踩坑复现")
    parser.add_argument("--capture", default="out/day164-basic-flows.jsonl", help="已有档案路径")
    parser.add_argument("--no-pitfalls", action="store_true", help="跳过踩坑演示")
    args = parser.parse_args()

    capture_path = Path(args.capture)
    if not capture_path.exists():
        capture_fresh(capture_path)

    rows = FlowStore(capture_path).load()
    print(f"📂 档案：{capture_path}（{len(rows)} 条 flow）")

    scope = Scope(ticket="LAB-164-ADV")
    analyzer = FlowAnalyzer(scope=scope)
    analyzer.analyze(rows)

    print_findings(analyzer)
    code = print_exit_code(analyzer)

    if not args.no_pitfalls:
        print("\n" + "=" * 78)
        print("🧪 四个真实踩坑的现场复现（这些 bug 都真的写过）")
        print("=" * 78)
        pitfall_1_redirect()
        pitfall_2_form_encoding()
        pitfall_3_partial_redaction()
        pitfall_4_pii_erasure()

        print("\n" + "=" * 78)
        print("🧠 四个坑的共同结构")
        print("=" * 78)
        print("  ① 假设了框架的默认行为（其实是别的）")
        print("  ② 假设了字面量在编码后不变（其实会变）")
        print("  ③ 假设了『处理一处 = 处理全部』（其实不是）")
        print("  ④ 假设了『检测能在擦除之后再做』（其实不能）")
        print("  ─────────────────────────────────────────────")
        print("  共同点：都是关于『我以为』的假设，而不是关于『实际数据』的观测。")
        print("  对策  ：把假设变成断言，让它在每次运行时替你记住。")

    print("\n下一步：python3 03-traffic-audit-cli.py   # 完整 CLI 流水线 + 报告")
    return 0


if __name__ == "__main__":
    sys.exit(main())
