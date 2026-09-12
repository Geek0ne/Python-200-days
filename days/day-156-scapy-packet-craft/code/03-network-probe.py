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

try:
    from scapy.all import (IP, TCP, UDP, ICMP, Ether, ARP, sr, sr1, srp,  # type: ignore
                           conf, get_if_hwaddr)
    HAVE_SCAPY = True
except Exception as _e:
    HAVE_SCAPY = False
    _SCAPY_ERR = repr(_e)


# ═══════════════════════════════════════════════════════════════
# 合规护栏
# ═══════════════════════════════════════════════════════════════
def parse_targets(spec: str) -> list:
    """支持: 127.0.0.1 / 192.168.1.0/30 / 192.168.1.1-10"""
    out = []
    spec = spec.strip()
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
    print("离线自检")
    print("=" * 72)

    # 目标解析
    assert parse_targets("127.0.0.1") == ["127.0.0.1"]
    assert parse_targets("192.168.1.1-4") == ["192.168.1.1", "192.168.1.2",
                                              "192.168.1.3", "192.168.1.4"]
    net = parse_targets("192.168.1.0/30")
    assert net == ["192.168.1.1", "192.168.1.2"], net
    print(f"✅ parse_targets(): 单点/区间/网段都正确（/30 → {net}）")

    # 护栏
    allowed, rejected = check_targets(
        ["127.0.0.1", "10.1.2.3", "192.168.0.1", "8.8.8.8", "239.1.1.1", "bad"])
    assert "127.0.0.1" in allowed and "10.1.2.3" in allowed
    assert "192.168.0.1" in allowed
    assert len(allowed) == 3 and len(rejected) == 3, (allowed, rejected)
    reasons = dict(rejected)
    assert reasons["8.8.8.8"].startswith("公网")
    assert reasons["239.1.1.1"].startswith("组播")
    print(f"✅ check_targets(): 放行 {allowed}")
    for t, r in rejected:
        print(f"   拒绝 {t}: {r}")

    # 端口规格解析
    def parse_ports(s):
        out = []
        for part in s.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-")
                out += list(range(int(a), int(b) + 1))
            elif part:
                out.append(int(part))
        return out
    assert parse_ports("22,80,443") == [22, 80, 443]
    assert parse_ports("80,8000-8002") == [80, 8000, 8001, 8002]
    print("✅ parse_ports(): 逗号与区间混写正确")

    # SYN 结果判定逻辑（纯函数版，不联网即可验证）
    def classify(flags: str | None, icmp_type: int | None, timeout: bool):
        if timeout:
            return "filtered"
        if icmp_type is not None:
            return f"icmp-unreachable(type={icmp_type})"
        if flags and "SA" in flags:
            return "open"
        if flags and ("RA" in flags or flags == "R"):
            return "closed"
        return f"other(flags={flags})"
    assert classify(None, None, True) == "filtered"
    assert classify("SA", None, False) == "open"
    assert classify("RA", None, False) == "closed"
    assert classify("R", None, False) == "closed"
    assert classify(None, 3, False).startswith("icmp-unreachable")
    print("✅ classify(): filtered / open / closed / icmp 判定正确")

    if not HAVE_SCAPY:
        print(f"\nℹ️  未安装 scapy（{_SCAPY_ERR}），跳过报文构造自检。")
        return 0

    # 报文构造：TTL 阶梯（traceroute 的核心）
    ladder = [IP(dst="127.0.0.1", ttl=t) / ICMP() for t in range(1, 6)]
    assert [p[IP].ttl for p in ladder] == [1, 2, 3, 4, 5]
    print("✅ TTL 阶梯构造: ", [p[IP].ttl for p in ladder])

    # 一条语句让 Scapy 自动展开 TTL 范围
    p = IP(dst="127.0.0.1", ttl=(1, 3)) / ICMP()
    print(f"✅ IP(ttl=(1,3)) 等价写法: {p.summary()}（发送时展开为 3 个包）")

    # ARP 请求
    a = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst="192.168.1.0/30")
    assert a[ARP].op == 1, "默认应是 ARP 请求(1)"
    print(f"✅ ARP 请求构造: {a.summary()}")

    # SYN 包
    s = IP(dst="127.0.0.1") / TCP(dport=80, flags="S")
    assert s[TCP].flags == "S"
    print(f"✅ SYN 构造: {s.summary()}")

    print("\n全部离线自检通过。")
    print("\n真实运行（需要 sudo）：")
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
        return self_test()

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
        dports = []
        for part in args.dports.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-")
                dports += list(range(int(a), int(b) + 1))
            elif part:
                dports.append(int(part))
        return cmd_ports(args.target, dports, args.timeout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(130)
