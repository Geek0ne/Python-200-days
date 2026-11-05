#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""01-flow-capture.py — 基础用法：起靶场 + 起代理 + 抓一次完整会话

本文件是 Day 164 的**最小可运行闭环**。跑完它，你会得到两样东西：

1. 终端里的实时流日志（每处理完一次往返就打一行）；
2. `out/day164-basic-flows.jsonl` —— 脱敏后的**流量档案**。

## 为什么第一个例子就要"完整闭环"？

因为中间人代理最反直觉的地方是：**它是三方系统**。

    客户端 ──▶ 代理 ──▶ 源站

少任何一方，你都无法验证"代理到底有没有正确转发"。
很多同学第一次写代理时的迷惑是：**"我不知道是我写错了，
还是源站本来就这么回。"** 所以本课一开始就把**靶站**和**客户端**都给你，
三方的行为都在你眼皮底下，出了偏差立刻能定位到是哪一段。

## 怎么读这个文件

    pip 不需要装任何东西（纯标准库）；直接跑：
        python3 01-flow-capture.py

    想改端口 / 换输出文件：
        python3 01-flow-capture.py --port 18080 --out /tmp/flows.jsonl

    只想起靶站和代理、手工用 curl 玩：
        python3 01-flow-capture.py --hold
        # 另开一个终端（注意：--hold 模式下端口是打印出来的）：
        curl -x http://127.0.0.1:PORT http://127.0.0.1:ORIGIN_PORT/api/user?id=1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 同目录导入共享引擎（教学代码不装包，靠 sys.path 解决）
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mitm_core import (  # noqa: E402
    AuditProxy,
    LabOpaqueTCP,
    LabOrigin,
    LabSession,
    Scope,
    EXIT_MEANING,
)


def summarize(rows: list[dict]) -> None:
    """把档案里最有信息量的几个维度打出来。

    **为什么第一个例子就要做"汇总"而不是只 print 原始 JSON？**
    因为一次会话十几条 flow，直接看 JSON 是看不出任何东西的。
    "汇总"才是把 JSON 变成**可判断信息**的第一步——
    这也是后面规则引擎存在的理由（见 02）。
    """
    print("\n" + "=" * 78)
    print("📊 捕获汇总")
    print("=" * 78)

    total = len(rows)
    inspected = sum(1 for r in rows if r.get("inspected", True))
    errors = sum(1 for r in rows if r.get("error"))
    tunnel = total - inspected

    print(f"总 flow        : {total}")
    print(f"已检查         : {inspected}")
    print(f"未检查（隧道）  : {tunnel}")
    print(f"传输错误       : {errors}")
    if total:
        print(f"覆盖率         : {100.0 * inspected / total:.1f}%")

    # —— 状态码分布 ——
    buckets: dict[str, int] = {}
    for row in rows:
        status = int(row.get("response_status") or 0)
        if status == 0:
            label = "无响应"
        elif status < 300:
            label = "2xx 成功"
        elif status < 400:
            label = "3xx 重定向"
        elif status < 500:
            label = "4xx 客户端错"
        else:
            label = "5xx 服务端错"
        buckets[label] = buckets.get(label, 0) + 1
    print("\n状态码分布：")
    for label, count in sorted(buckets.items(), key=lambda kv: -kv[1]):
        print(f"  {label:<14} {count}")

    # —— 方法分布 ——
    methods: dict[str, int] = {}
    for row in rows:
        m = row.get("method") or "?"
        methods[m] = methods.get(m, 0) + 1
    print("\n方法分布：")
    for label, count in sorted(methods.items(), key=lambda kv: -kv[1]):
        print(f"  {label:<14} {count}")

    # —— 单条明细（只列最关键的列）——
    print("\n明细（fid / 方法 / 状态 / 耗时 / URL）：")
    for row in rows:
        status = row.get("response_status") or "---"
        note = " ⚠️未检查" if not row.get("inspected", True) else ""
        print(
            f"  {row['fid']}  {row['method']:<7} {str(status):<4} "
            f"{row.get('duration_ms', 0):>8.1f}ms  {row['url']}{note}"
        )


def show_one_flow_redacted(rows: list[dict]) -> None:
    """挑出"登录"那条 flow，把**脱敏后的原始档案**完整打出来。

    **为什么特意展示这一条？** 因为它同时包含三个必须亲眼看到的东西：

    1. `request_body` 里**没有明文口令**，只有一个指纹标记；
    2. `note` 里记着"命中了敏感字段 password"——**结论保留了，秘密没保留**；
    3. 响应头里 `Set-Cookie` 的值也被换成了指纹。

    这三样合起来就是本课的核心设计（见 README 2.7）：**先脱敏，再检测**。
    """
    target = None
    for row in rows:
        if (row.get("method") or "").upper() == "POST" and "/login" in (row.get("path") or ""):
            target = row
            break
    if target is None:
        return

    print("\n" + "=" * 78)
    print("🔍 档案原文（登录那条 flow，注意：值已脱敏，结构完整）")
    print("=" * 78)
    view = {
        "fid": target["fid"],
        "method": target["method"],
        "url": target["url"],
        "request_headers": target["request_headers"],
        "request_body": target["request_body"],          # ← 看不到明文口令
        "note": target["note"],                          # ← 但能看到"命中过 password"
        "response_status": target["response_status"],
        "response_headers": target["response_headers"],  # ← Set-Cookie 已脱敏
        "duration_ms": target["duration_ms"],
    }
    print(json.dumps(view, ensure_ascii=False, indent=2))

    print("\n💡 观察要点：")
    print("   · request_body 里的 password 值 = 指纹，不是明文")
    print("   · note 字段保住了『这里曾出现过 password』这个结论")
    print("   · 报告能证明『明文传输了』，但档案本身不构成二次泄密")


def main() -> int:
    parser = argparse.ArgumentParser(description="Day 164 · 基础用法：起靶场 + 起代理 + 抓一次会话")
    parser.add_argument("--port", type=int, default=0, help="代理监听端口（0 = 让内核分配）")
    parser.add_argument("--out", default="out/day164-basic-flows.jsonl", help="流量档案输出路径")
    parser.add_argument("--no-tunnel", action="store_true", help="不演示 CONNECT 隧道（覆盖率会变成 100%）")
    parser.add_argument("--hold", action="store_true", help="只起服务，不进会话，等你自己 curl")
    args = parser.parse_args()

    out_path = Path(args.out)
    if out_path.exists():
        out_path.unlink()          # 每次跑都是一份干净的档案，避免"上次的残留"混淆结论

    scope = Scope(ticket="LAB-164-BASIC")

    print("🔧 启动实验环境（全部只绑定 127.0.0.1）...")

    # ① 靶站：故意做出"会泄密的流量"
    # ② 假 TLS 服务：用来演示"隧道不可见"
    # ③ 代理：把两段连接接起来，并把每次往返落成一条 flow
    with LabOrigin() as origin, LabOpaqueTCP() as opaque, AuditProxy(
        out_path, port=args.port, scope=scope, verbose=True
    ) as proxy:
        print(f"   · 靶站      : {origin.base}")
        print(f"   · 假TLS服务 : 127.0.0.1:{opaque.port}")
        print(f"   · 正向代理  : {proxy.url}   ← 客户端要用这个")
        print(f"   · 档案输出  : {out_path}")

        if args.hold:
            print("\n⏸  --hold 模式：服务已就绪，按 Ctrl-C 结束。")
            try:
                import time
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n👋 收到 Ctrl-C，开始收尾。")
            return 0

        print("\n🚦 开始演示会话（全部流量经由代理）：")
        session = LabSession(proxy.url, scope=scope, rate=8.0)
        session.run_demo(origin.base, opaque_port=None if args.no_tunnel else opaque.port)

        # 从**磁盘**读回来，而不是用内存里的对象。
        # 为什么？因为"档案能读回来"本身就是一项必须验证的能力：
        # 很多 bug 只在"序列化 → 反序列化"之后才暴露（比如 JSON 里
        # 中文被转义、bytes 被存成 base64 难以辨认、时间格式不一致）。
        from mitm_core import FlowStore
        rows = FlowStore(out_path).load()

    summarize(rows)
    show_one_flow_redacted(rows)

    print("\n" + "=" * 78)
    print("✅ 基础用法演示结束")
    print("=" * 78)
    print(f"档案文件：{out_path}")
    print("下一步  ：python3 02-flow-analyze.py        # 用规则引擎把档案变成发现")
    print(f"退出码说明：{EXIT_MEANING[0]} / {EXIT_MEANING[3]} / {EXIT_MEANING[4]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
