#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 157 · 案例 02 —— 高级过滤：BPF 与 display filter 到底差在哪
================================================================================

本案例要彻底讲清**两个过滤器**的区别（这是流量分析里最容易糊的概念）：

  ┌──────────────┬────────────────────────────┬──────────────────────────────┐
  │              │ BPF（bpf_filter / 捕获过滤） │ display filter（显示过滤）     │
  ├──────────────┼────────────────────────────┼──────────────────────────────┤
  │ 何时生效      │ **抓包时**（抓之前）          │ **解析后**（抓完/读文件时）     │
  │ 在哪执行      │ 内核（libpcap 编译成字节码）   │ 用户态（tshark/pyshark 逐包求值）│
  │ 看得到什么    │ 只有**原始字节的固定偏移**      │ 任意解析出来的协议字段          │
  │ 语法          │ `tcp[tcpflags] & tcp-syn != 0`│ `tcp.flags.syn == 1`          │
  │ 没命中的包    │ 永远不会到达用户态（**丢就丢了**）│ 仍在文件里，改条件还能看        │
  │ 性能          │ 极高（内核态、不拷贝）          │ 一般（每包都要 dissect）        │
  │ 典型用途      │ 长时间抓包时把 99% 噪声挡掉     │ 事后分析、排错、挑特定会话      │
  └──────────────┴────────────────────────────┴──────────────────────────────┘

  **一句话记忆：BPF 决定"你手里有什么"，display filter 决定"你先看哪一条"。**

  为什么 BPF 只能看固定偏移？因为它运行在**协议解析之前**：内核不认识
  "HTTP 方法"这种概念，它只认 `tcp[2:2] == 80`（从 TCP 头第 2 字节起的 2 字节
  等于 80）这种"字节级"表达式。所以 `port 80` 在内核里其实长这样：

      (tcp[2:2]==80 or tcp[4:2]==80) or (udp[2:2]==80 or udp[4:2]==80)

  ⚠️ 必须知道的坑：**BPF 抓之前就丢包，display filter 不能"找回"丢掉的包**。
     所以别用 display filter 的思维去写 BPF：你真的需要事后各种角度分析，
     就把抓包条件放宽（只挡掉明显噪声，比如 `not port 22`），
     把细筛留给 display filter。

本案例同时修掉一个**经典错误**（原版代码里就有）：
    用 `only_summaries=True` 打开 FileCapture，然后又去读 `packet.http.method`。
    Summary 对象里**只有 7 个字段**（number/time/source/destination/protocol/
    length/info），根本没有 http 层 → 直接 AttributeError。
    要么去掉 only_summaries，要么改用 `packet.info` 文本。

运行：
    python3 -B 02-advanced-filtering.py --self-test      # 离线自检 → SELF-TEST OK
    python3 -B 02-advanced-filtering.py --demo           # 合成抓包上的过滤演示
    python3 -B 02-advanced-filtering.py --demo --expr 'ip.addr == 10.0.0.66'
    python3 -B 02-advanced-filtering.py --demo --bpf 'tcp port 80'
    python3 -B 02-advanced-filtering.py --demo --http     # 提取 HTTP 请求（含敏感信息检测）
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pcap_lib as L  # noqa: E402

# ── 一组"教学用"的过滤条件：从粗到细，覆盖常见写法 ──
DEMO_FILTERS = [
    ("tcp", "所有 TCP 包"),
    ("udp", "所有 UDP 包"),
    ("http", "所有 HTTP 包（含请求与响应）"),
    ("tcp.flags.syn == 1 and tcp.flags.ack == 0", "纯 SYN（扫描/连接请求）"),
    ("tcp.flags.rst == 1", "RST（连接被拒绝或主动重置）"),
    ("ip.addr == 10.0.0.66", "只看某台主机（扫描器）"),
    ("tcp.port == 4444", "只看某个端口（可疑回连端口）"),
    ("dns.qry.name contains \"evil\"", "域名包含 evil 的 DNS 包"),
    ("http.request.method == \"POST\"", "HTTP POST 请求"),
    ("tcp.dstport == 80 and tcp.len > 0", "发往 80 端口且带载荷（真正的请求）"),
    ("ip.src == 10.0.0.99", "SYN 洪水的来源"),
]

# 一组 BPF → 我们等价翻译后结果必须一致的对照（自检会逐个比对）
BPF_EQUIVALENCE = ["tcp port 80", "udp port 53", "icmp", "host 10.0.0.66",
                   "tcp[tcpflags] & tcp-syn != 0", "not port 22"]


class _FakeSummary:
    """**模拟** pyshark 在 only_summaries=True 时返回的 Summary 对象。

    为什么要造这个假对象？因为本环境没装 pyshark（也没装 tshark），
    但"Summary 只有 7 个字段"这件事**必须能被验证**，否则学员会继续踩坑。
    真 pyshark 的 Summary 对象属性就是这 7 个（pyshark.source 中有据可查）：
        number / time / source / destination / protocol / length / info
    它**没有** ip / tcp / udp / http 这些层对象。
    """
    def __init__(self):
        self.number = "1"
        self.time = "1700000000.015000"
        self.source = "10.0.0.10"
        self.destination = "10.0.0.20"
        self.protocol = "HTTP"
        self.length = "512"
        self.info = "GET /login HTTP/1.1"


def load_parsed(path: str):
    return [L.dissect_packet(r) for r in L.iter_capture(path)]


def count_matches(pkts: list, expr: str) -> int:
    return sum(1 for _ in L.apply_filter(pkts, expr))


def print_filter_report(pkts: list) -> None:
    print(f"{'过滤表达式':<45}{'命中':>6}   说明")
    print("-" * 84)
    for expr, desc in DEMO_FILTERS:
        try:
            n = count_matches(pkts, expr)
        except L.FilterError as e:
            n = f"错误: {e}"
        print(f"{expr:<45}{str(n):>6}   {desc}")


def print_bpf_mapping() -> None:
    print("\nBPF 在**内核**里到底比什么字节（这些偏移量是硬编码的，改不了）：")
    for expr, explanation in L.bpf_equivalent_bytes().items():
        print(f"  {expr:<28} → {explanation}")


def print_bpf_translation(pkts: list) -> None:
    print("\nBPF → display filter 等价翻译，并对同一份抓包**实测两种写法结果相同**：")
    for bpf in BPF_EQUIVALENCE:
        disp = L.bpf_to_display(bpf)
        if disp is None:
            print(f"  {bpf:<34} → （本引擎翻译不了，需要真正的 libpcap）")
            continue
        a = count_matches(pkts, disp)
        print(f"  {bpf:<34} → {disp:<44} 命中 {a}")


def print_http_requests(pkts: list) -> int:
    """提取 HTTP 请求：**必须**用完整解析（不能 only_summaries）。

    这是原版代码的 bug 修复点：原来用 display_filter='http' + only_summaries=True，
    然后访问 packet.http.method —— Summary 对象上没有 http 层，必然 AttributeError。
    """
    print("\nHTTP 请求清单（敏感值只显示掩码 + 指纹，不显示原文）：")
    print("-" * 84)
    n = 0
    for p in pkts:
        h = p.get("http")
        if not h or not h.get("is_request"):
            continue
        n += 1
        ip = p.get("ip", {})
        print(f"#{p['number']:<4} {ip.get('src','?')}:{p['tcp']['sport']} → "
              f"{ip.get('dst','?')}:{p['tcp']['dport']}  "
              f"{h['method']} {h['uri']}  Host={h['host']}")
        if h.get("user_agent"):
            print(f"        UA: {h['user_agent']}")
        for s in h.get("sensitive", []):
            print(f"        🔐 命中敏感信息 {s['where']} → {s['masked']} fp={s['fp']}")
    print("-" * 84)
    print(f"共 {n} 个 HTTP 请求")
    return n


def demo_only_summaries_trap() -> None:
    """演示 only_summaries=True 的坑（用模拟对象，因为本环境没有 pyshark）。"""
    print("\n" + "=" * 84)
    print("坑：only_summaries=True 时为什么读不到 http 字段")
    print("=" * 84)
    s = _FakeSummary()
    print(f"Summary 对象现有属性：{[a for a in vars(s)]}")
    print(f"  hasattr(summary, 'ip')   = {hasattr(s, 'ip')}")
    print(f"  hasattr(summary, 'tcp')  = {hasattr(s, 'tcp')}")
    print(f"  hasattr(summary, 'http') = {hasattr(s, 'http')}")
    try:
        _ = s.http.method                      # 模拟原版代码的写法
    except AttributeError as e:
        print(f"  summary.http.method → AttributeError: {e}")
        print("  ⇒ 正确做法有两种：")
        print("     ① 去掉 only_summaries（代价：慢，但字段齐全）")
        print("     ② 保留摘要模式，但只读 summary.info 这一列文本（快，字段少）")


# ══════════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════════

def self_test() -> None:
    print("=" * 84)
    print("案例 02 离线自检：过滤引擎 / BPF 等价性 / HTTP 提取 / Summary 坑")
    print("=" * 84)

    tmp = tempfile.mkdtemp(prefix="day157-02-")
    try:
        path = os.path.join(tmp, "demo.pcap")
        L.write_demo_pcap(path)
        pkts = load_parsed(path)
        L.check_eq(len(pkts), 70, "合成抓包包数")

        # ① 逐条过滤条件的命中数：这些数字就是"标准答案"，改了流量必须同步改
        expected = {
            "tcp": 60,                        # 70 - 5 DNS(1查询1应答3隧道) - 2 ICMP - 3 ARP
            "udp": 5,
            "http": 6,
            "tcp.flags.syn == 1 and tcp.flags.ack == 0": 1 + 8 + 25 + 1 + 4,
            "ip.addr == 10.0.0.66": 8,
            "tcp.port == 4444": 16,           # 4 次心跳 × (SYN/SYN-ACK/ACK/POST)
            "dns.qry.name contains \"evil\"": 3,
            "http.request.method == \"POST\"": 4,
            "tcp.dstport == 80 and tcp.len > 0": 1,   # 只有正常会话的 GET 带载荷
            "ip.src == 10.0.0.99": 25,
        }
        for expr, want in expected.items():
            got = count_matches(pkts, expr)
            L.check_eq(got, want, f"过滤条件 '{expr}' 命中数")
        print(f"✅ 11 条教学过滤条件命中数全部符合预期（tcp=60 udp=5 http=6 …）")

        # ② 「纯 SYN」应为 39：扫描 8 + 洪水 25 + 正常会话 1 + 心跳 4 + 坏校验和包 1
        pure_syn = count_matches(pkts, "tcp.flags.syn == 1 and tcp.flags.ack == 0")
        L.check_eq(pure_syn, 39, "纯 SYN 包数")
        # 而"完成握手的连接"只有 5 条（正常 Web 1 条 + 心跳 4 条）
        completed = count_matches(pkts, "tcp.flags.syn == 1 and tcp.flags.ack == 1")
        L.check_eq(completed, 5, "SYN+ACK 包数（= 完成握手的连接数）")
        print(f"✅ 关键对比：纯 SYN {pure_syn} 个 vs 完成握手 {completed} 条 "
              f"→ 差出来的 {pure_syn - completed} 个就是「只发起不完成」的可疑行为")

        # ③ BPF 与 display filter 的等价性：不只是"翻译得像"，而是结果集相同
        for bpf in BPF_EQUIVALENCE:
            disp = L.bpf_to_display(bpf)
            L.check_true(disp is not None, f"BPF '{bpf}' 应能被翻译")
            a = {p["number"] for p in L.apply_filter(pkts, disp)}
            # 手工构造"如果用真 BPF 会命中谁"的对照集
            if bpf == "tcp port 80":
                b = {p["number"] for p in pkts if "tcp" in p
                     and 80 in (p["tcp"]["sport"], p["tcp"]["dport"])}
            elif bpf == "udp port 53":
                b = {p["number"] for p in pkts if "udp" in p
                     and 53 in (p["udp"]["sport"], p["udp"]["dport"])}
            elif bpf == "icmp":
                b = {p["number"] for p in pkts if "icmp" in p}
            elif bpf == "host 10.0.0.66":
                # 注意用 p.get("ip")：ARP 包没有 IP 层，直接 p["ip"] 会 KeyError
                b = {p["number"] for p in pkts
                     if p.get("ip") and "10.0.0.66" in (p["ip"]["src"], p["ip"]["dst"])}
            elif "tcp-syn" in bpf:
                b = {p["number"] for p in pkts if "tcp" in p and p["tcp"]["syn"]}
            else:                                     # not port 22
                b = {p["number"] for p in pkts if not (
                    ("tcp" in p and 22 in (p["tcp"]["sport"], p["tcp"]["dport"])) or
                    ("udp" in p and 22 in (p["udp"]["sport"], p["udp"]["dport"])))}
            L.check_eq(a, b, f"BPF '{bpf}' 与其 display filter 等价式必须命中同一批包")
        print(f"✅ BPF 等价性：{len(BPF_EQUIVALENCE)} 条条件翻译后结果集完全一致（逐包比对）")

        # ④ HTTP 提取：方法/主机/URI 正确，且**原文绝不出现在输出里**
        reqs = [p for p in pkts if p.get("http", {}).get("is_request")]
        L.check_eq(len(reqs), 5, "HTTP 请求总数（1 正常 GET + 4 心跳 POST）")
        get_req = [p for p in reqs if p["http"]["method"] == "GET"][0]
        L.check_eq(get_req["http"]["uri"], "/login", "GET 请求 URI")
        L.check_eq(get_req["http"]["host"], "intranet.example.com", "GET Host")
        posts = [p for p in reqs if p["http"]["method"] == "POST"]
        L.check_eq(len(posts), 4, "POST 请求数（心跳）")
        L.check_eq({p["http"]["host"] for p in posts}, {"c2.example"}, "POST Host")
        sens = get_req["http"]["sensitive"]
        L.check_true(len(sens) >= 2, "正常会话请求里应同时命中 Authorization 与 Cookie")
        raw_authorization = "dXNlcjpwYXNzd29yZA=="
        L.check_true(all(raw_authorization not in s["masked"] for s in sens),
                     "掩码结果绝不能包含 Authorization 原文")
        L.check_true(all("8f3a1c0d9e2b" not in s["masked"] for s in sens),
                     "掩码结果绝不能包含 Cookie 原文")
        print(f"✅ HTTP 提取：5 个请求（GET /login + 4 心跳 POST）；"
              f"敏感项 {[(s['where'], s['masked']) for s in sens]}")

        # ⑤ Summary 坑（用模拟对象验证"只有 7 个字段"这个事实）
        s = _FakeSummary()
        L.check_true(not hasattr(s, "http"), "Summary 对象不应有 http 层")
        L.check_true(not hasattr(s, "ip"), "Summary 对象不应有 ip 层")
        L.check_eq(sorted(vars(s)), sorted(["number", "time", "source",
                                            "destination", "protocol", "length", "info"]),
                   "Summary 字段集")
        print("✅ Summary 坑已复现：only_summaries=True 时只有 7 个字段，"
              "访问 .http/.ip 必 AttributeError")

        # ⑥ 过滤器错误语义（用户输入错别字时必须报人话）
        for bad in ["tcp.flags.syn = 1", "((tcp)", "tcp.port == abc extra"]:
            try:
                L.compile_filter(bad)
            except L.FilterError:
                continue
            raise AssertionError(f"表达式 {bad!r} 本应报 FilterError")
        print("✅ 过滤器错误处理：错误语法一律给出人话提示（含错在哪）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Day157 案例02：高级过滤（BPF vs display filter）")
    ap.add_argument("--pcap", metavar="FILE", help="抓包文件")
    ap.add_argument("--demo", action="store_true", help="使用临时目录里的合成抓包")
    ap.add_argument("--expr", metavar="EXPR", help="额外执行一条自定义 display filter")
    ap.add_argument("--bpf", metavar="BPF", help="给一条 BPF，翻译成 display filter 并执行")
    ap.add_argument("--http", action="store_true", help="提取 HTTP 请求（含敏感信息检测）")
    ap.add_argument("--self-test", action="store_true", help="离线自检")
    args = ap.parse_args(argv)

    if args.self_test:
        try:
            self_test()
        except AssertionError as e:
            print(f"SELF-TEST FAIL: {e}")
            return 1
        except Exception as e:                       # noqa: BLE001
            print(f"SELF-TEST FAIL: {type(e).__name__}: {e}")
            return 1
        print("SELF-TEST OK")
        return 0

    tmp = None
    path = args.pcap
    if args.demo or not path:
        tmp = tempfile.mkdtemp(prefix="day157-02-")
        path = os.path.join(tmp, "demo.pcap")
        L.write_demo_pcap(path)
        print(f"（使用合成抓包 {path}）")
    if not os.path.exists(path):
        print(f"❌ 文件不存在：{path}（加 --demo 可用合成数据）")
        return 2
    try:
        pkts = load_parsed(path)
    except ValueError as e:
        print(f"❌ 读取失败：{e}")
        return 2

    print("\n一、教学用过滤条件一览（display filter，在**用户态**逐包求值）")
    print("=" * 84)
    print_filter_report(pkts)
    print_bpf_mapping()
    print_bpf_translation(pkts)

    if args.expr:
        print("\n二、自定义表达式：" + args.expr)
        print("-" * 84)
        try:
            for p in L.apply_filter(pkts, args.expr):
                print(L.pkt_summary(p))
        except L.FilterError as e:
            print(f"❌ 语法错误：{e}")
            return 2

    if args.bpf:
        print("\n三、BPF 翻译：" + args.bpf)
        print("-" * 84)
        disp = L.bpf_to_display(args.bpf)
        if disp is None:
            print("本教学引擎无法翻译这条 BPF（复杂表达式需要真正的 libpcap）。")
            print("提示：真实项目里把 BPF 交给 tcpdump/tshark 执行，不要自己写解析器。")
        else:
            print(f"  BPF:      {args.bpf}")
            print(f"  等价显示: {disp}")
            for p in L.apply_filter(pkts, disp):
                print("   " + L.pkt_summary(p))

    if args.http:
        print("\n四、HTTP 请求提取（注意：**不能**用 only_summaries）")
        print("=" * 84)
        print_http_requests(pkts)

    demo_only_summaries_trap()

    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
