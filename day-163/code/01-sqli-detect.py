#!/usr/bin/env python3
"""Day 163 · 基础用法：SQL 注入检测（错误回显 + 布尔差分）。

运行（默认在本机回环靶标上做实验，不碰任何外部目标）：

    python3 01-sqli-detect.py

这个脚本回答三个问题：

1. **探针长什么样**：四个探针各是什么、为什么是这四个；
2. **检测器看到了什么**：每个探针的状态码 / 响应长度；
3. **结论怎么来**：错误回显（error-based）与布尔差分（boolean-based）
   各自的判定条件，以及为什么必须**锚定 baseline**。

⚠️ 边界：本脚本只做**检测**。不 UNION 取数、不拖库、不时间盲注、
   不做任何"绕过"；每个参数最多 4 个探针，默认限速 2 请求/秒。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vuln_core import (  # noqa: E402
    DEFAULT_RATE,
    AuthorizationError,
    LabVulnHTTP,
    detect_sqli,
    default_lab_scope,
)

PORT = 18086


def show(title: str, url: str, scope) -> None:
    """跑一次 SQLi 检测并打印"探针表 + 结论"。"""
    print(f"\n{'=' * 66}\n{title}\n  URL: {url}\n{'=' * 66}")
    result = detect_sqli(url, scope, rate=20)

    print(f"  参数: {result.param}   基准值: {result.base_value!r}")
    print(f"  {'探针':<10}{'注入值':<22}{'状态':>5}{'长度':>7}")
    print(f"  {'-' * 46}")
    for p in result.probes:
        print(f"  {p.label:<10}{p.value:<22}{p.status:>5}{p.length:>7}")

    print(f"\n  判定技术: {result.technique or 'none'}")
    print(f"  证据    : {result.evidence}")
    return result


def main() -> int:
    # 靶标只绑定回环地址；scope 也把目标锁死在 127.0.0.1:PORT
    with LabVulnHTTP(port=PORT) as lab:
        scope = default_lab_scope(lab.port)
        base = f"http://127.0.0.1:{lab.port}"
        print(f"[lab] 实验靶标已启动: {base}（限速 {DEFAULT_RATE:.0f} 请求/秒）")

        # ① 有缺陷的端点：字符串拼接 → 单引号就能把 SQL 语法搞坏
        r1 = show("① 有缺陷的端点 /product（字符串拼接）", f"{base}/product?id=1", scope)
        assert r1.technique == "error_based", "该端点应当被判定为错误回显型注入"

        # ② 安全对照：同一个业务、参数化写法 → 检测器必须沉默
        r2 = show("② 安全对照 /safe-product（参数化）", f"{base}/safe-product?id=1", scope)
        assert r2.technique == "none", "安全对照不应被判定为注入"

        # ③ 假阳性陷阱：页面原样回显输入（但已转义）→ 长度必然变化
        r3 = show("③ 假阳性陷阱 /echo（原样回显，已转义）", f"{base}/echo?id=1", scope)
        assert r3.technique == "none", "只比长度会误报；锚定 baseline 后应当沉默"

        # ④ 越界：URL 层门禁在构造请求之前就拒绝
        print(f"\n{'=' * 66}\n④ 越界目标必须被门禁拦下（不发任何请求）\n{'=' * 66}")
        try:
            detect_sqli("http://192.0.2.1:8086/product?id=1", scope, rate=20)
        except AuthorizationError as exc:
            print(f"  ⛔ AuthorizationError: {exc}")
            print("  （策略拒绝：不重试、不降级、整轮终止；退出码 2）")

    print("\n[结论] 三类结果很清楚：")
    print("  · 有缺陷端点  → error_based（单引号触发数据库报错特征）")
    print("  · 参数化对照  → none（同一个业务，写法决定安全性）")
    print("  · 回显型页面  → none（长度变了 ≠ 注入，必须锚定 baseline）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
