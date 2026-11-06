#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 156 · 示例 03 —— 实战：网络探测工具（ICMP ping / traceroute / ARP 发现）
==============================================================================

运行：
    # 离线自检（不需要 root / 不需要 scapy）
    python3 03-network-probe.py --self-test

    # 真实探测（需要 sudo；目标必须落在回环或私网）
    sudo python3 03-network-probe.py ping 127.0.0.1
    sudo python3 03-network-probe.py ping 127.0.0.1 --count 4
    sudo python3 03-network-probe.py trace 127.0.0.1 --max-hops 5
    sudo python3 03-network-probe.py arp-scan 192.168.1.0/24
    sudo python3 03-network-probe.py ports 127.0.0.1 --dports 22,80,443,8080

三个子命令：
    ping      ICMP Echo Request/Reply（手写，不用系统 ping）
    trace     手写 traceroute：TTL 从 1 递增，收集 Time Exceeded
    arp-scan  对私网段发 ARP 请求，列出存活主机（IP + MAC）
    ports     半开扫描（SYN）：SYN-ACK=open / RST=closed / 无响应=filtered

⚠️ 合规护栏（写死在代码里）：
    · 目标必须是回环 / RFC1918 私网 / 链路本地地址；
    · 公网地址一律拒绝；
    · 端口扫描默认只扫回环，公网目标需要额外开关（本脚本不提供）。
    · 不提供任何源 IP 伪造功能。
"""

from __future__ import annotations

import argparse
import ipaddress
import sys
import time

import warnings

# scapy 导入时会触发 cryptography 的 FFDH 弃用警告（与本日内容无关），
# 教学输出里不需要它 —— 只屏蔽这一条**特定消息**，不是全局静音。
warnings.filterwarnings("ignore", message=".*Diffie-Hellman over finite fields.*")

try:
    from scapy.all import (IP, TCP, UDP, ICMP, Ether, ARP, sr, sr1, srp,  # type: ignore
                           conf, get_if_hwaddr)
    HAVE_SCAPY = True
except Exception as _e:
    HAVE_SCAPY = False
    _SCAPY_ERR = repr(_e)




# ═══════════════════════════════════════════════════════════════
# 自检辅助：失败时打印「实际值 vs 期望值」
# ═══════════════════════════════════════════════════════════════
def check_eq(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label} 不匹配：实际={actual!r} 期望={expected!r}")


def check_true(cond, label: str) -> None:
    if not cond:
        raise AssertionError(f"{label} 不成立：期望为真，实际为假")


def parse_ports(spec: str) -> list:
    """解析端口规格："22,80,443" / "80,8000-8002" / "1-3,53"。

    写在模块层级（而不是塞在 main 里）是为了**可测**：
    自检能直接调它验证边界，而不是只能靠跑一遍 CLI 才敢确认。
    """
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = int(a), int(b)
            if a > b:
                a, b = b, a                 # 容错：写反了也接受
            out += list(range(a, b + 1))
        else:
            out.append(int(part))
    if not out:
        raise ValueError(f"端口规格解析为空: {spec!r}")
    if any(not 0 < p < 65536 for p in out):
        raise ValueError(f"端口越界（必须是 1-65535）: {spec!r}")
    return out


def classify_syn_result(flags: str | None, icmp_type: int | None, timed_out: bool) -> str:
    """SYN 扫描的结果判定（纯函数 → 可离线验证）。

    这是"半开扫描"的核心逻辑，把它抽成纯函数有两个好处：
      ① 不需要网卡/root 就能验证判定是否正确；
      ② 判定规则集中在一处，改阈值不用翻遍代码。
    """
    if timed_out:
        return "filtered"
    if icmp_type is not None:
        return f"icmp-unreachable(type={icmp_type})"
    if flags and "SA" in flags:
        return "open"
    if flags and ("RA" in flags or flags == "R"):
        return "closed"
    return f"other(flags={flags})"


# ═══════════════════════════════════════════════════════════════
# 合规护栏
# ═══════════════════════════════════════════════════════════════
def parse_targets(spec: str) -> list:
    """支持: 127.0.0.1 / 192.168.1.0/30 / 192.168.1.1-10 / ::1

    ⚠️ 坑：IPv6 地址里天然带 ":"，而 IPv6 的"区间"写法（fe80::1-3）
       无法用"最后一段整数递增"来表达。所以这里先判断"是不是 IPv6"，
       是就直接当单地址处理 —— 否则 rsplit(".") 会抛 ValueError 把整个脚本搞崩。
       这是"输入解析必须先分类型"的一个典型例子。
    """
    out = []
    spec = spec.strip()
    if ":" in spec:                      # IPv6：不支持区间，按单地址处理
        return [spec]
    if "/" in spec:
        net = ipaddress.ip_network(spec, strict=False)
        out = [str(ip) for ip in net.hosts()]
    elif "-" in spec and not spec.count("-") > 1:
        base, _, last = spec.partition("-")
        head = base.rsplit(".", 1)[0]
        first = int(base.rsplit(".", 1)[1])
        out = [f"{head}.{i}" for i in range(first, int(last) + 1)]
    else:
        out = [spec]
    return out


def check_targets(targets: list) -> tuple:
    """返回 (允许的列表, 拒绝的原因列表)。"""
    allowed, rejected = [], []
    for t in targets:
        try:
            ip = ipaddress.ip_address(t)
        except ValueError:
            rejected.append((t, "非法 IP"))
            continue
        if ip.is_loopback or ip.is_private or ip.is_link_local:
            allowed.append(t)
        elif ip.is_multicast:
            rejected.append((t, "组播（会影响整个网段）"))
        else:
            rejected.append((t, "公网地址（本工具只允许本机/私网）"))
    return allowed, rejected


# ═══════════════════════════════════════════════════════════════
# 子命令 1：ping
# ═══════════════════════════════════════════════════════════════
def cmd_ping(target: str, count: int = 3, timeout: float = 2.0) -> int:
    print(f"PING {target}（Scapy 手写 ICMP，共 {count} 次）")
    sent = recv = 0
    rtts = []
    for i in range(1, count + 1):
        pkt = IP(dst=target) / ICMP(type=8, id=i, seq=i) / b"day156-probe"
        t0 = time.perf_counter()
        ans = sr1(pkt, timeout=timeout, verbose=0)
        dt = (time.perf_counter() - t0) * 1000
        sent += 1
        if ans is None:
            print(f"  第 {i} 次: 超时（{timeout}s 内无响应）")
            continue
        if ans.haslayer(ICMP) and ans[ICMP].type == 0:
            recv += 1
            rtts.append(dt)
            print(f"  第 {i} 次: 来自 {ans[IP].src}  ttl={ans[IP].ttl}  "
                  f"time={dt:.1f}ms  bytes={len(ans)}")
        elif ans.haslayer(ICMP):
            print(f"  第 {i} 次: ICMP type={ans[ICMP].type} code={ans[ICMP].code} "
                  f"（非 Echo Reply，可能被目标拒绝或路由不可达）")
        else:
            print(f"  第 {i} 次: 收到非 ICMP 响应: {ans.summary()}")
    loss = (sent - recv) / sent * 100 if sent else 0
    print(f"\n--- {target} 统计 ---")
    print(f"  发送 {sent} 接收 {recv} 丢包 {loss:.0f}%")
    if rtts:
        print(f"  RTT min/avg/max = {min(rtts):.1f}/{sum(rtts)/len(rtts):.1f}/{max(rtts):.1f} ms")
    return 0 if recv else 1


# ═══════════════════════════════════════════════════════════════
# 子命令 2：traceroute（手写）
# ═══════════════════════════════════════════════════════════════
def cmd_trace(target: str, max_hops: int = 10, timeout: float = 1.5) -> int:
    print(f"TRACEROUTE {target}（手写：TTL 1..{max_hops}）")
    reached = False
    for ttl in range(1, max_hops + 1):
        pkt = IP(dst=target, ttl=ttl) / ICMP(type=8, id=ttl, seq=ttl)
        t0 = time.perf_counter()
        ans = sr1(pkt, timeout=timeout, verbose=0)
        dt = (time.perf_counter() - t0) * 1000
        if ans is None:
            print(f"  {ttl:>2}  *  (超时)")
            continue
        src = ans[IP].src if ans.haslayer(IP) else "?"
        if ans.haslayer(ICMP):
            t = ans[ICMP].type
            if t == 11:                                  # Time Exceeded
                print(f"  {ttl:>2}  {src}  time={dt:.1f}ms  (ICMP Time Exceeded)")
            elif t == 0:                                 # Echo Reply
                print(f"  {ttl:>2}  {src}  time={dt:.1f}ms  ✅ 到达目标")
                reached = True
                break
            elif t == 3:                                 # Dest Unreachable
                print(f"  {ttl:>2}  {src}  time={dt:.1f}ms  "
                      f"⚠️ 目标不可达 (code={ans[ICMP].code})")
                break
            else:
                print(f"  {ttl:>2}  {src}  time={dt:.1f}ms  (ICMP type={t})")
        else:
            print(f"  {ttl:>2}  {src}  time={dt:.1f}ms  {ans.summary()}")
            reached = True
            break
    if not reached:
        print(f"\n  未在 {max_hops} 跳内到达（可能 TTL 不够，或中间设备不回 ICMP）")
    return 0


# ═══════════════════════════════════════════════════════════════
# 子命令 3：ARP 扫描（局域网存活发现）
# ═══════════════════════════════════════════════════════════════
def cmd_arp_scan(cidr: str, iface: str | None = None, timeout: float = 2.0) -> int:
    print(f"ARP-SCAN {cidr}（链路层，比 ICMP 更可靠）")
    pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=cidr)
    try:
        ans, unans = srp(pkt, timeout=timeout, verbose=0, iface=iface)
    except Exception as e:
        print(f"❌ 失败：{type(e).__name__}: {e}")
        print("   常见原因：没有权限（需要 root）；网卡名不对；不在同一广播域")
        return 1
    print(f"\n存活主机 {len(ans)} / 探测 {len(ans)+len(unans)}")
    print(f"  {'IP':<18}{'MAC':<20}")
    print("  " + "-" * 36)
    for _snd, rcv in sorted(ans, key=lambda x: x[1].psrc):
        print(f"  {rcv.psrc:<18}{rcv.hwsrc:<20}")
    if not ans:
        print("  （没有响应：可能不在同一网段、或目标是虚拟网络）")
    return 0


# ═══════════════════════════════════════════════════════════════
# 子命令 4：半开端口扫描（SYN）
# ═══════════════════════════════════════════════════════════════
def cmd_ports(target: str, dports: list, timeout: float = 1.5, retry: int = 1) -> int:
    print(f"SYN SCAN {target} 端口 {dports}（半开，不完成握手）")
    print("⚠️  仅可用于自有资产！这就是攻击者会做的事，区别只在授权。")
    results = []
    for port in dports:
        pkt = IP(dst=target) / TCP(dport=port, flags="S", seq=1000)
        ans = sr1(pkt, timeout=timeout, verbose=0, retry=retry)
        if ans is None:
            state = "filtered"
        elif ans.haslayer(TCP):
            f = str(ans[TCP].flags)
            if "SA" in f:
                state = "open"
                # 收到 SYN-ACK 后必须发 RST，否则对方保持半开连接（资源占用 + 更明显）
                sr1(IP(dst=target) / TCP(dport=port, flags="R", seq=ans[TCP].ack),
                    timeout=0.5, verbose=0)
            elif "RA" in f or f == "R":
                state = "closed"
            else:
                state = f"other(flags={f})"
        elif ans.haslayer(ICMP):
            state = f"icmp-unreachable(type={ans[ICMP].type})"
        else:
            state = "unknown"
        results.append((port, state))
        print(f"  {port:<6} → {state}")

    open_ports = [p for p, s in results if s == "open"]
    if open_ports:
        print(f"\n开放端口: {open_ports}")
        print("自检建议：确认这些端口是否必须对外；不必要就关掉或加认证。")
    return 0


# ═══════════════════════════════════════════════════════════════
# 离线自检
# ═══════════════════════════════════════════════════════════════
def self_test() -> int:
    print("=" * 72)
    print("离线自检：护栏 / 目标解析 / 结果判定 / 报文构造（不需要 root 与网卡）")
    print("=" * 72)

    # ── 1) 目标解析 ──
    check_eq(parse_targets("127.0.0.1"), ["127.0.0.1"], "单点解析")
    check_eq(parse_targets("192.168.1.1-4"),
             ["192.168.1.1", "192.168.1.2", "192.168.1.3", "192.168.1.4"], "区间解析")
    check_eq(parse_targets("192.168.1.0/30"), ["192.168.1.1", "192.168.1.2"], "/30 网段")
    check_eq(parse_targets("::1"), ["::1"], "IPv6 单地址")
    check_eq(parse_targets("fe80::1-3"), ["fe80::1-3"], "IPv6 不做区间展开（防崩）")
    check_eq(parse_targets(" 10.0.0.5 "), ["10.0.0.5"], "首尾空格应被去掉")
    print("✅ parse_targets(): 单点/区间/网段/IPv6 全部正确，且含空格的输入被清理")

    # ── 2) 合规护栏 ──
    allowed, rejected = check_targets(
        ["127.0.0.1", "10.1.2.3", "192.168.0.1", "172.16.9.9", "8.8.8.8",
         "1.1.1.1", "239.1.1.1", "224.0.0.1", "bad", ""])
    check_eq(allowed, ["127.0.0.1", "10.1.2.3", "192.168.0.1", "172.16.9.9"],
             "放行列表（4 个私网/回环）")
    reasons = dict(rejected)
    check_eq(len(rejected), 6, "拒绝条数")
    check_true(reasons["8.8.8.8"].startswith("公网"), "公网拒绝原因")
    check_true(reasons["239.1.1.1"].startswith("组播"), "组播拒绝原因")
    check_true(reasons["bad"] == "非法 IP", "非法输入原因")
    print(f"✅ check_targets(): 放行 {allowed}")
    for t, r in rejected:
        print(f"   拒绝 {t!r}: {r}")

    # ── 3) 端口规格解析 ──
    check_eq(parse_ports("22,80,443"), [22, 80, 443], "逗号分隔")
    check_eq(parse_ports("80,8000-8002"), [80, 8000, 8001, 8002], "逗号+区间")
    check_eq(parse_ports("100-102"), [100, 101, 102], "纯区间")
    check_eq(parse_ports("8080-8080"), [8080], "单元素区间")
    check_eq(parse_ports("100-98"), [98, 99, 100], "写反的顺序也应容错")
    check_eq(parse_ports("22,,80"), [22, 80], "多余逗号应被忽略")
    for bad in ("", "   ", "0", "70000", "abc"):
        raised = False
        try:
            parse_ports(bad)
        except ValueError:
            raised = True
        check_true(raised, f"非法端口规格 {bad!r} 应抛 ValueError")
    print("✅ parse_ports(): 逗号/区间/顺序容错/越界与非法输入拦截 全部正确")

    # ── 4) SYN 扫描结果判定（半开扫描的核心逻辑）──
    check_eq(classify_syn_result(None, None, True), "filtered", "超时 → filtered")
    check_eq(classify_syn_result("SA", None, False), "open", "SYN-ACK → open")
    check_eq(classify_syn_result("RA", None, False), "closed", "RST+ACK → closed")
    check_eq(classify_syn_result("R", None, False), "closed", "纯 RST → closed")
    check_eq(classify_syn_result(None, 3, False), "icmp-unreachable(type=3)",
             "ICMP 不可达")
    check_eq(classify_syn_result("A", None, False), "other(flags=A)", "异常标志组合")
    check_true(not classify_syn_result(None, None, True).startswith("open"),
               "超时绝不能判成 open（否则会把被防火墙挡住的端口报成开放）")
    print("✅ classify_syn_result(): filtered/open/closed/icmp/other 五种结果判定正确")

    if not HAVE_SCAPY:
        print(f"\nℹ️  未安装 scapy（{_SCAPY_ERR}），跳过报文构造自检。")
        return 0

    # ── 5) 报文构造（离线，只构造不发送）──
    ladder = [IP(dst="127.0.0.1", ttl=t) / ICMP() for t in range(1, 6)]
    check_eq([p[IP].ttl for p in ladder], [1, 2, 3, 4, 5], "TTL 阶梯")
    print("✅ TTL 阶梯构造:", [p[IP].ttl for p in ladder])

    # ttl 范围写法在发送时展开成多个包（这里验证展开逻辑本身）
    from scapy.all import IP as _IP
    multi = _IP(dst="10.0.0.1", ttl=(1, 3))
    check_eq([p.ttl for p in multi], [1, 2, 3], "IP(ttl=(1,3)) 的展开结果")
    print(f"✅ IP(ttl=(1,3)) 展开为 {[p.ttl for p in multi]} 个包（traceroute 的一行写法）")

    # ARP 请求：必须是 op=1、广播、且 hwdst 全 0
    # 显式给 psrc：否则 scapy 会拿本机默认 IP 当发送方地址，
    # 自检输出就随环境变化（自检的输出必须可复现，才能写进 README 当"预期输出"）
    a = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst="192.168.1.0/30", psrc="10.0.0.1")
    check_eq(a[ARP].op, 1, "ARP 请求的 op（1=who-has）")
    check_eq(a[Ether].dst, "ff:ff:ff:ff:ff:ff", "ARP 请求必须是广播帧")
    # ⚠️ 踩坑点：scapy 的 CIDR 展开和 ipaddress.hosts() **不一样**！
    #    scapy 把 192.168.1.0/30 展开成全部 4 个地址（含网络号 .0 和广播 .3），
    #    而本文件的 parse_targets 用 ipaddress.hosts()，只取可用的 .1 和 .2。
    #    做网段扫描时这两个差异会直接决定"你扫了几个地址"。
    expanded = list(a)
    check_eq(len(expanded), 4, "scapy 对 /30 的展开个数（含网络号与广播地址）")
    check_eq([p[ARP].pdst for p in expanded[:2]], ["192.168.1.0", "192.168.1.1"],
             "scapy 展开的前两个地址")
    check_eq(parse_targets("192.168.1.0/30"), ["192.168.1.1", "192.168.1.2"],
             "本文件 parse_targets 对同一网段的展开（只取可用主机）")
    print(f"✅ ARP 请求构造: dst={a[Ether].dst} op={a[ARP].op} "
          f"（scapy 把 /30 展开成 4 个地址，hosts() 只取 2 个）")

    # SYN 包：半开扫描的最小单元 —— 只有 SYN，没有 ACK
    syn = IP(dst="127.0.0.1") / TCP(dport=80, flags="S", seq=1000)
    check_eq(syn[TCP].flags, "S", "SYN 包的标志位")
    check_true("A" not in str(syn[TCP].flags), "半开扫描的 SYN 不能带 ACK")
    check_eq(syn[IP].dst, "127.0.0.1", "SYN 包的目的地址")
    print(f"✅ SYN 构造: {syn.summary()}")

    # ICMP Echo Request / Reply 的类型号（ping 的判定依据）
    check_eq((IP(dst="127.0.0.1") / ICMP(type=8))[ICMP].type, 8, "Echo Request 类型")
    check_eq((IP(dst="127.0.0.1") / ICMP(type=0))[ICMP].type, 0, "Echo Reply 类型")
    print("✅ ICMP 类型号: 8=Echo Request / 0=Echo Reply（ping 的判定依据）")

    # 护栏：伪造源 IP 的检查 —— 示例代码里源地址必须落在白名单内
    for src in ("127.0.0.1", "10.0.0.1", "192.168.1.1"):
        check_true(check_targets([src])[0] == [src], f"本机/私网源地址 {src} 应放行")
    check_true(check_targets(["8.8.8.8"])[0] == [], "公网源地址必须被拒绝（不提供伪造功能）")
    print("✅ 源地址护栏: 只允许本机/私网（本工具不提供任何源 IP 伪造能力）")

    print("\n真实运行（需要 sudo；目标必须是本机或自己的私网）：")
    print("  sudo python3 03-network-probe.py ping 127.0.0.1")
    print("  sudo python3 03-network-probe.py trace 127.0.0.1 --max-hops 5")
    print("  sudo python3 03-network-probe.py ports 127.0.0.1 --dports 22,80,443")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Day156 网络探测工具（仅限本机/私网）")
    sub = ap.add_subparsers(dest="cmd")

    p1 = sub.add_parser("ping", help="ICMP ping")
    p1.add_argument("target")
    p1.add_argument("--count", type=int, default=3)
    p1.add_argument("--timeout", type=float, default=2.0)

    p2 = sub.add_parser("trace", help="手写 traceroute")
    p2.add_argument("target")
    p2.add_argument("--max-hops", type=int, default=10)
    p2.add_argument("--timeout", type=float, default=1.5)

    p3 = sub.add_parser("arp-scan", help="局域网存活发现")
    p3.add_argument("cidr")
    p3.add_argument("-i", "--iface", default=None)
    p3.add_argument("--timeout", type=float, default=2.0)

    p4 = sub.add_parser("ports", help="SYN 半开端口扫描")
    p4.add_argument("target")
    p4.add_argument("--dports", default="22,80,443,8080")
    p4.add_argument("--timeout", type=float, default=1.5)

    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test or not args.cmd:
        if not args.cmd:
            print("ℹ️  未指定子命令，转为离线自检。\n")
        try:
            self_test()
        except AssertionError as e:
            print(f"SELF-TEST FAIL: {e}")
            return 1
        except Exception as e:                    # noqa: BLE001
            print(f"SELF-TEST FAIL: {type(e).__name__}: {e}")
            return 1
        print("SELF-TEST OK")
        return 0

    if not HAVE_SCAPY:
        print(f"❌ 未安装 scapy：{_SCAPY_ERR}\npip install scapy")
        return 1

    # 护栏：所有子命令统一检查目标
    if args.cmd == "arp-scan":
        allowed, rejected = check_targets(parse_targets(args.cidr))
        # ARP 扫描目标是网段，只检查首个地址的代表性
        try:
            net = ipaddress.ip_network(args.cidr, strict=False)
            if not (net.is_private or net.is_loopback or net.is_link_local):
                print("⛔ 拒绝执行：ARP 扫描只允许私网/回环网段。")
                return 2
        except ValueError:
            print("⛔ 拒绝执行：网段格式非法。")
            return 2
        return cmd_arp_scan(args.cidr, args.iface, args.timeout)

    allowed, rejected = check_targets([args.target])
    if not allowed:
        print("⛔ 拒绝执行：")
        for t, r in rejected:
            print(f"   {t}: {r}")
        return 2
    if rejected:
        print("⚠️  已忽略不合规目标：", rejected)

    if args.cmd == "ping":
        return cmd_ping(args.target, args.count, args.timeout)
    if args.cmd == "trace":
        return cmd_trace(args.target, args.max_hops, args.timeout)
    if args.cmd == "ports":
        try:
            dports = parse_ports(args.dports)
        except ValueError as e:
            print(f"⛔ 端口参数非法：{e}")
            return 2
        return cmd_ports(args.target, dports, args.timeout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(130)
