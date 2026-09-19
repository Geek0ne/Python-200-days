#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 157 · 案例 01 —— 读取 PCAP 并列出数据包（pyshark 主路径 + 标准库兜底路径）
================================================================================

先讲清楚**为什么要写两条路径**（这是本案例存在的全部理由）：
    pyshark 本身不是解析器，它只是 **tshark 的 Python 包装**：调用 tshark 子进程，
    再把 tshark 输出的 XML/JSON 解析成对象。于是出现三个现实问题：

      ① 机器上没装 tshark → `import pyshark` 直接 ImportError，脚本全废；
         （本案例的运行环境就是这种情况：`python3 -c "import pyshark"` 会报
           ModuleNotFoundError: No module named 'pyshark'）
      ② 每读一个包都要和子进程通信一次 → 大文件奇慢；
      ③ tshark 版本不同字段名可能变化 → 脚本脆弱。

    所以工程写法是：**先定义统一的数据结构，再让两条后端都往它上面靠**。
        有 tshark → 走 pyshark（协议覆盖全，字段几百个）
        没 tshark → 走 pcap_lib（纯标准库，覆盖本日需要的 6 个协议）
    上层业务代码（本文件的 print_packets / 02 / 03）**完全不关心**用的是哪条路径。

运行：
    # 离线自检：不联网、不需要 sudo、不依赖 pyshark，自己造 pcap 自己验
    python3 -B 01-basic-usage.py --self-test

    # 用合成抓包演示（写进临时目录，不污染仓库）
    python3 -B 01-basic-usage.py --demo

    # 分析真实抓包（自己的流量；离线解析，不碰网卡）
    python3 -B 01-basic-usage.py --pcap /tmp/my.pcap --limit 20
    python3 -B 01-basic-usage.py --pcap /tmp/my.pcap --backend stdlib

    # 装了 pyshark/tshark 时，对比两条路径的结果（交叉验证）
    python3 -B 01-basic-usage.py --demo --compare

⚠️ 隐私红线：pcap 里常含 Cookie / Authorization / 明文密码。
   本案例打印时对敏感值做**掩码 + 指纹**处理，绝不原样回显（见 pcap_lib.mask_secret）。
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

# 让本文件既能 `python3 code/01-basic-usage.py` 直接跑，
# 也能被别处 import —— 把自身目录加入 sys.path 是脚本目录工具模块的标准做法。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pcap_lib as L  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
# 1. 后端探测：pyshark 到底能不能用？
# ══════════════════════════════════════════════════════════════════════════

def probe_pyshark() -> tuple:
    """返回 (是否可用, 原因)。**不要**在导入期直接 import pyshark：

    `import pyshark` 失败会抛 ModuleNotFoundError，如果写在模块顶层，
    整个脚本（包括离线自检）连启动都启动不了。
    正确做法是"延迟导入 + 捕获异常 + 给出人话提示"。
    """
    try:
        import pyshark  # noqa: F401
    except Exception as e:                     # ImportError 或依赖缺失
        return False, f"{type(e).__name__}: {e}"
    # 光有 pyshark 还不够：它依赖 tshark 二进制。这里顺手探一下，
    # 免得等到 FileCapture 才报一个看不懂的错。
    if shutil.which("tshark") is None:
        return False, "pyshark 已安装但找不到 tshark 二进制（apt install tshark / brew install wireshark）"
    return True, "ok"


# ══════════════════════════════════════════════════════════════════════════
# 2. 统一的数据结构（后端无关的中间表示 IR）
# ══════════════════════════════════════════════════════════════════════════
#
# 字段命名直接对齐 Wireshark 的显示过滤器名（ip.src / tcp.dstport …），
# 这样：显示过滤器表达式、统计代码、两种后端**共用同一套名词**，
# 不会出现"pyshark 里叫 src_ip、标准库里叫 src"这种翻译地狱。
#
# ⚠️ 顺带纠正一个很常见的错误写法：
#     pyshark 里 IP 源地址是 `pkt.ip.src`（对应 tshark 字段 ip.src），
#     **不是** `pkt.ip.src_ip`；协议号是 `pkt.ip.proto`，不是 `pkt.ip.protocol`。
#     写成 src_ip 会直接 AttributeError —— 这是复制粘贴教程时最容易踩的坑。


def normalize_pyshark(pkt, only_summaries: bool) -> dict:
    """把 pyshark 的 Packet/Summary 对象转成本库的字典结构。"""
    out: dict = {"backend": "pyshark"}
    if only_summaries:
        # only_summaries=True 时拿到的是 Summary 对象：
        #   只有 number / time / source / destination / protocol / length / info
        #   **没有** ip/tcp/http 这些层对象！下面 02 会用自检证明这一点。
        out["number"] = int(pkt.number)
        out["ts"] = float(pkt.time)
        out["caplen"] = int(pkt.length)
        out["protocols"] = str(getattr(pkt, "protocol", "")).lower()
        out["summary"] = str(getattr(pkt, "info", ""))
        out["src"] = str(getattr(pkt, "source", ""))
        out["dst"] = str(getattr(pkt, "destination", ""))
        return out
    out["number"] = int(pkt.number)
    out["ts"] = float(pkt.sniff_time.timestamp()) if hasattr(pkt, "sniff_time") else 0.0
    out["caplen"] = int(pkt.length)
    layers = []
    if hasattr(pkt, "eth"):
        out["eth"] = {"src": getattr(pkt.eth, "src", ""), "dst": getattr(pkt.eth, "dst", "")}
        layers.append("ether")
    if hasattr(pkt, "ip"):
        out["ip"] = {
            "src": pkt.ip.src, "dst": pkt.ip.dst,
            "ttl": int(getattr(pkt.ip, "ttl", 0)),
            "proto": int(getattr(pkt.ip, "proto", 0)),
            "proto_name": getattr(pkt.ip, "protocol", ""),
        }
        layers.append("ip")
    if hasattr(pkt, "ipv6"):
        out["ipv6"] = {"src": pkt.ipv6.src, "dst": pkt.ipv6.dst}
        layers.append("ipv6")
    if hasattr(pkt, "arp"):
        out["arp"] = {
            "op": int(getattr(pkt.arp, "opcode", 0)),
            "sender_ip": getattr(pkt.arp, "src_proto_ipv4", ""),
            "sender_mac": getattr(pkt.arp, "src_hw_mac", ""),
        }
        layers.append("arp")
    if hasattr(pkt, "tcp"):
        flags = str(getattr(pkt.tcp, "flags", ""))       # tshark 给的是 0x00xx
        out["tcp"] = {
            "sport": int(pkt.tcp.srcport), "dport": int(pkt.tcp.dstport),
            "seq": int(getattr(pkt.tcp, "seq", 0)),
            "ack": int(getattr(pkt.tcp, "ack", 0)),
            "window": int(getattr(pkt.tcp, "window_size_value", 0) or 0),
            "flags_raw": flags,
            "flags": getattr(pkt.tcp, "flags_str", flags),
            "payload_len": int(getattr(pkt.tcp, "len", 0) or 0),
        }
        layers.append("tcp")
    if hasattr(pkt, "udp"):
        out["udp"] = {"sport": int(pkt.udp.srcport), "dport": int(pkt.udp.dstport),
                      "length": int(getattr(pkt.udp, "length", 0))}
        layers.append("udp")
    if hasattr(pkt, "icmp"):
        out["icmp"] = {"type": int(getattr(pkt.icmp, "type", -1))}
        layers.append("icmp")
    out["layers"] = layers
    out["protocols"] = ":".join(layers)
    return out


def iter_pyshark(path: str, *, display_filter: str | None = None,
                 only_summaries: bool = False):
    """pyshark 读取（生成器）。**必须显式 close()** —— 否则 tshark 子进程残留。"""
    import pyshark  # 延迟导入：只有真的要用它时才 import
    cap = pyshark.FileCapture(path,
                              display_filter=display_filter or None,
                              only_summaries=only_summaries)
    try:
        for pkt in cap:
            yield normalize_pyshark(pkt, only_summaries)
    finally:
        cap.close()          # ← 不写这句，进程里会堆积一串僵尸 tshark


def iter_stdlib(path: str, *, display_filter: str | None = None):
    """标准库兜底路径：用 pcap_lib 自己解析。"""
    ast = L.compile_filter(display_filter) if display_filter else None
    for raw in L.iter_capture(path):
        pkt = L.dissect_packet(raw)
        if ast is not None and not L.eval_filter(ast, pkt):
            continue
        pkt["backend"] = "stdlib"
        yield pkt


def load_packets(path: str, backend: str = "auto", *, display_filter: str | None = None,
                 limit: int = 0, allow_summaries: bool = False):
    """统一入口：返回 (包列表, 实际使用的后端名, 说明)。

    backend:
        auto   → 能用 pyshark 就用，否则静默降级到 stdlib
        pyshark→ 强制用（不可用则报错，让"依赖没装"暴露出来而不是被悄悄降级）
        stdlib → 强制用标准库（**确定性最高，推荐用于 CI 和自检**）
    """
    ok, why = probe_pyshark()
    used = backend
    note = ""
    if backend == "auto":
        used = "pyshark" if ok else "stdlib"
        note = "" if ok else f"⚠️ pyshark 不可用（{why}），已自动降级到标准库解析"
    elif backend == "pyshark" and not ok:
        raise RuntimeError(f"指定了 --backend pyshark，但它不可用：{why}\n"
                           "安装：pip install pyshark && apt install tshark")
    elif backend == "stdlib":
        note = "" if not ok else "（已显式指定标准库路径，pyshark 未参与）"

    pkts = []
    if used == "pyshark":
        src = iter_pyshark(path, display_filter=display_filter,
                           only_summaries=allow_summaries)
    else:
        src = iter_stdlib(path, display_filter=display_filter)
    for i, pkt in enumerate(src):
        if limit and i >= limit:
            break
        pkts.append(pkt)
    return pkts, used, note


# ══════════════════════════════════════════════════════════════════════════
# 3. 打印
# ══════════════════════════════════════════════════════════════════════════

def format_packet(pkt: dict) -> str:
    """一行摘要。两种后端都能用（字段名已经统一）。"""
    if pkt.get("backend") == "pyshark" and "summary" in pkt:
        return (f"#{pkt['number']:<4} {pkt['src']} → {pkt['dst']}  "
                f"[{pkt.get('protocols', '')}]  {pkt['summary']}")
    return L.pkt_summary(pkt)


def print_packets(pkts: list, *, show_sensitive: bool = False) -> None:
    for pkt in pkts:
        print(format_packet(pkt))
        if pkt.get("sensitive"):
            for s in pkt["sensitive"]:
                # 敏感信息只出"位置 + 掩码 + 指纹"，绝不回显原文
                print(f"        🔐 {s['where']}: {s['masked']} fp={s['fp']}")


def print_stats(pkts: list) -> None:
    from collections import Counter
    proto = Counter()
    for p in pkts:
        for layer in p.get("layers", []):
            proto[layer] += 1
        if not p.get("layers") and p.get("protocols"):
            proto[str(p["protocols"]).upper()] += 1
    print("\n层/协议分布：")
    for name, n in proto.most_common():
        print(f"  {name:<8} {n}")


# ══════════════════════════════════════════════════════════════════════════
# 4. 离线自检
# ══════════════════════════════════════════════════════════════════════════

def self_test() -> None:
    print("=" * 74)
    print("案例 01 离线自检：合成 pcap → 走两条路径解析 → 核对已知答案")
    print("=" * 74)

    tmp = tempfile.mkdtemp(prefix="day157-01-")
    try:
        path = os.path.join(tmp, "demo.pcap")
        L.write_demo_pcap(path)

        # ① 标准库路径（**自检必须走这条**：不依赖 pyshark / tshark）
        pkts, used, note = load_packets(path, backend="stdlib")
        L.check_eq(used, "stdlib", "自检必须使用标准库后端")
        L.check_eq(len(pkts), 70, "合成抓包包数")
        first = pkts[0]
        L.check_eq(first["ip"]["src"], "10.0.0.10", "第 1 包源 IP")
        L.check_eq(first["ip"]["dst"], "10.0.0.53", "第 1 包目的 IP")
        L.check_eq(first["dns"]["qry_name"], "intranet.example.com", "第 1 包 DNS 查询名")
        print(f"✅ 标准库路径：{len(pkts)} 个包，首包 = {L.pkt_summary(first)}")

        # ② 端口 / 标志 / HTTP 字段都能取到（这就是"列出基本信息"的验收点）
        http_pkts = [p for p in pkts if "http" in p]
        get_reqs = [p for p in http_pkts if p["http"].get("is_request")
                    and p["http"]["method"] == "GET"]
        L.check_eq(len(get_reqs), 1, "GET 请求数")
        req = get_reqs[0]
        L.check_eq(req["http"]["host"], "intranet.example.com", "HTTP Host")
        L.check_eq(req["http"]["uri"], "/login", "HTTP URI")
        L.check_eq(req["tcp"]["dport"], 80, "HTTP 请求目的端口")
        L.check_true(req["http"]["sensitive"], "明文凭据必须被识别")
        print(f"✅ HTTP 提取：{req['http']['method']} {req['http']['uri']} "
              f"Host={req['http']['host']}，敏感项 {len(req['http']['sensitive'])} 条"
              f"（掩码示例 {req['http']['sensitive'][0]['masked']}）")

        # ③ display_filter 参数在标准库路径同样生效
        syn = load_packets(path, backend="stdlib",
                           display_filter="tcp.flags.syn == 1 and tcp.dstport == 80")[0]
        L.check_eq(len(syn), 28, "SYN 且 dport=80 的包数")
        print(f"✅ display_filter 生效：'tcp.flags.syn == 1 and tcp.dstport == 80' → {len(syn)} 个包")

        # ④ limit 参数
        L.check_eq(len(load_packets(path, backend="stdlib", limit=7)[0]), 7, "--limit 生效")
        print("✅ --limit 生效：只解析前 7 个包")

        # ⑤ pyshark 可用性：**不可用不算失败**，但要把原因讲清楚（这是本案例的核心承诺）
        ok, why = probe_pyshark()
        if ok:
            ng, used2, _ = load_packets(path, backend="pyshark")
            L.check_eq(len(ng), 70, "pyshark 路径包数应与标准库一致")
            L.check_eq(int(ng[0]["ip"]["proto"]), 17, "pyshark 首包协议号（UDP=17）")
            std_first = pkts[0]
            L.check_eq(str(ng[0]["ip"]["src"]), str(std_first["ip"]["src"]),
                       "两条后端首包源 IP 交叉验证")
            print(f"✅ 交叉验证：pyshark 与标准库对同一文件得到一致的包数与首包字段")
        else:
            print(f"ℹ️  pyshark 不可用（{why}）")
            print("    → 本自检**故意不依赖它**：上面的断言全部走标准库路径。")
            print("    → 想跑联机路径：pip install pyshark 并安装 tshark，再执行 --compare")

        # ⑥ 强制指定 pyshark 时必须"明确报错"，而不是悄悄降级
        if not ok:
            raised = False
            try:
                load_packets(path, backend="pyshark")
            except RuntimeError:
                raised = True
            L.check_true(raised, "--backend pyshark 不可用时必须抛 RuntimeError（不许静默降级）")
            print("✅ 降级策略：auto 静默降级、显式 pyshark 明确报错 —— 两条语义都对")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Day157 案例01：读取 PCAP 并列出数据包")
    ap.add_argument("--pcap", metavar="FILE", help="要分析的 pcap/pcapng 文件")
    ap.add_argument("--demo", action="store_true", help="用临时目录里的合成抓包演示")
    ap.add_argument("--backend", choices=["auto", "pyshark", "stdlib"], default="auto",
                    help="解析后端（auto=有 pyshark 就用，否则标准库）")
    ap.add_argument("--filter", dest="display_filter", default=None,
                    help="显示过滤器，例如 'tcp.flags.syn==1'")
    ap.add_argument("--limit", type=int, default=0, help="最多显示多少包（0=全部）")
    ap.add_argument("--only-summaries", action="store_true",
                    help="pyshark 只取摘要（更快，但拿不到 ip/tcp/http 字段）")
    ap.add_argument("--compare", action="store_true", help="两种后端对比同一文件")
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
        tmp = tempfile.mkdtemp(prefix="day157-01-")
        path = os.path.join(tmp, "demo.pcap")
        L.write_demo_pcap(path)
        print(f"（本轮使用合成抓包：{path}，共 70 个包；分析完会删除）\n")
    if not os.path.exists(path):
        print(f"❌ 文件不存在：{path}")
        print("   提示：原版脚本硬编码 example_traffic.pcap，文件不存在就直接崩；")
        print("        这里改成显式报错 + --demo 生成合成数据。")
        return 2

    try:
        pkts, used, note = load_packets(path, backend=args.backend,
                                        display_filter=args.display_filter,
                                        limit=args.limit,
                                        allow_summaries=args.only_summaries)
    except (RuntimeError, ValueError) as e:
        print(f"❌ {e}")
        return 2
    if note:
        print(note)
    print(f"文件: {path}\n后端: {used}   过滤器: {args.display_filter or '(无)'}\n"
          + "=" * 74)
    print_packets(pkts)
    print("=" * 74)
    print(f"共 {len(pkts)} 个数据包")
    print_stats(pkts)

    if args.compare:
        ok, why = probe_pyshark()
        if not ok:
            print(f"\n⚠️ 无法对比：pyshark 不可用（{why}）")
        else:
            ng, _, _ = load_packets(path, backend="pyshark", limit=args.limit or 0)
            print(f"\n对比结果：标准库 {len(pkts)} 包 vs pyshark {len(ng)} 包")
            for i in range(min(3, len(pkts), len(ng))):
                print(f"  #{i+1} 标准库: {format_packet(pkts[i])}")
                print(f"     pyshark: {format_packet(ng[i])}")

    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
