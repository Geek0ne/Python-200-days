#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 156 · 示例 01 —— Scapy 分层构造基础
==========================================

运行：
    # 只构造 + 打印，不发包（不需要 root）
    python3 01-scapy-basics.py --show
    python3 01-scapy-basics.py --show --self-test

    # 真的发到回环（需要 root / CAP_NET_RAW，且要显式 --send）
    sudo python3 01-scapy-basics.py --send --dst 127.0.0.1

本文件教你 5 件事：
    1) Ether / IP / TCP / UDP / ICMP / Raw 怎么用 `/` 叠起来
    2) 字段怎么读写（p[IP].ttl）、层怎么索引
    3) show() vs show2() 的区别（后者才会回填校验和）
    4) send / sendp / sr1 的区别与使用场合
    5) 目标地址的合规护栏（只允许本机与私网）

⚠️ 法律边界：本脚本只允许目标是回环或 RFC1918 私网地址；
   默认 dry-run，不发送任何数据包。真实发送必须显式 --send。
"""

from __future__ import annotations

import argparse
import ipaddress
import sys

# ── scapy 是可选的：没装也能看构造结果/跑自检 ──
try:
    from scapy.all import (Ether, IP, IPv6, TCP, UDP, ICMP, Raw,  # type: ignore
                           DNS, DNSQR, send, sendp, sr1, sr, conf, hexdump)
    HAVE_SCAPY = True
except Exception as _e:                       # ImportError 或底层库缺失
    HAVE_SCAPY = False
    _SCAPY_ERR = repr(_e)

# 允许的目标：回环 + 私网 + 链路本地
ALLOW_PRIVATE = True


def check_target(dst: str) -> tuple:
    """返回 (是否允许, 原因)。只允许回环与私网地址。"""
    try:
        ip = ipaddress.ip_address(dst)
    except ValueError:
        return False, f"无法解析为 IP 地址: {dst}"
    if ip.is_loopback:
        return True, "回环地址（最安全）"
    if ip.is_private:
        return True, "RFC1918 私网地址"
    if ip.is_link_local:
        return True, "链路本地地址"
    if ip.is_multicast:
        return False, "组播地址（可能影响整个网段，禁止）"
    return False, (
        f"{dst} 是公网地址。本示例只允许回环/私网目标。"
        "如确需测试，请使用你自己的靶场环境。")


# ═══════════════════════════════════════════════════════════════
# 1. 分层构造
# ═══════════════════════════════════════════════════════════════
def build_examples(dst: str = "127.0.0.1") -> dict:
    """构造一组演示包。返回 {名字: pkt}。不发送任何数据。"""
    if not HAVE_SCAPY:
        return {}
    pkts = {}

    # ① 最简 ICMP Echo Request（ping）
    pkts["icmp_echo"] = IP(dst=dst) / ICMP(type=8, code=0) / b"day156"

    # ② TCP SYN（半开扫描的最小单元）
    pkts["tcp_syn"] = IP(dst=dst) / TCP(dport=80, flags="S", seq=1000)

    # ③ TCP 完整请求（带载荷）
    pkts["tcp_http"] = (IP(dst=dst) / TCP(dport=80, flags="PA", seq=1000, ack=1) /
                        (b"GET / HTTP/1.0\r\nHost: " + dst.encode() + b"\r\n\r\n"))

    # ④ UDP + DNS 查询（注意 DNSQR 的 qtype 用字符串）
    pkts["udp_dns"] = IP(dst=dst) / UDP(dport=53) / DNS(rd=1, qd=DNSQR(qname="example.com"))

    # ⑤ 带 Ether 层的完整帧（sendp 用）
    pkts["ether_icmp"] = (Ether(dst="ff:ff:ff:ff:ff:ff") /
                          IP(dst=dst) / ICMP())

    # ⑥ 多目标 / 多端口：Scapy 会自动展开成多个包
    pkts["tcp_multi"] = IP(dst=dst) / TCP(dport=[80, 443, 8080], flags="S")

    # ⑦ fuzz 风格：字段用随机生成器（每次序列化都不同）
    from scapy.all import RandShort
    pkts["tcp_random"] = IP(dst=dst) / TCP(dport=[22, 80], sport=RandShort(), flags="S")

    return pkts


def demo_structure(pkts: dict) -> None:
    """演示字段读写、层索引、haslayer。"""
    print("=" * 72)
    print("一、分层结构：用 `/` 叠加，用 [] 索引")
    print("=" * 72)

    p = pkts["tcp_http"]
    print("1) summary()   :", p.summary())
    print("2) 层列表      :", [c.__name__ for c in p.layers()])   # IP → TCP → Raw
    print("3) haslayer TCP:", p.haslayer(TCP), "| haslayer UDP:", p.haslayer(UDP))
    print("4) 读字段      : p[IP].ttl =", p[IP].ttl,
          "| p[TCP].dport =", p[TCP].dport,
          "| p[TCP].flags =", p[TCP].flags)
    print("5) 改字段      : p[IP].ttl = 32")
    p[IP].ttl = 32
    print("   再读         :", p[IP].ttl)
    print("6) 取载荷      :", bytes(p[Raw].load)[:32], "...")

    print("\n7) 未回填校验和时间的样子（show 只显示对象字段）：")
    print(f"   IP.chksum = {p[IP].chksum!r}（None 表示'等我算'）")
    print(f"   IP.len    = {p[IP].len!r}")


def demo_show2(pkts: dict) -> None:
    """show2() = 先序列化再重新解析，因此能看到自动填好的校验和。"""
    print("\n" + "=" * 72)
    print("二、show() vs show2()：为什么校验和是 None")
    print("=" * 72)
    p = pkts["tcp_syn"]
    print("show() 打印的是 Python 对象 → chksum 还是 None")
    print("show2() 先 build 再 dissect → chksum 已是真实值")
    print("\n--- pkt.show2() ---")
    p.show2()
    print("\n--- hexdump(pkt) ---")
    hexdump(p)


def demo_bytes(pkts: dict) -> None:
    print("\n" + "=" * 72)
    print("三、序列化：对象 → 字节")
    print("=" * 72)
    p = pkts["icmp_echo"]
    b = bytes(p)
    print(f"len(bytes(pkt)) = {len(b)}")
    print(f"原对象 p[IP].len = {p[IP].len!r}   ← 仍是 None！")
    # 关键：build 阶段算出的值写在"字节"里，不回写到原对象；
    # 想看到它，必须把字节重新 dissect 成一个新对象。
    reparsed = IP(b)
    print(f"重新解析后 IP.len = {reparsed.len}（不含 Ether，与总长一致）")
    print(f"重新解析后 IP.chksum = 0x{reparsed.chksum:04x}")
    print("前 32 字节:", b[:32].hex(" "))
    print("\n📌 关键：改字段后必须重新 bytes() 才能得到新字节；")
    print("   校验和由 Scapy 在序列化时自动计算（但不会回写原对象）。")


def demo_expand(pkts: dict) -> None:
    print("\n" + "=" * 72)
    print("四、多值字段自动展开")
    print("=" * 72)
    p = pkts["tcp_multi"]
    print("原始: ", p.summary())
    print("⚠️ 注意：直接 for 遍历一个包【不会】得到所有层；")
    print("   要拿层列表请用 pkt.layers()（返回类）或 pkt.payload 逐层下钻：")
    chain, cur = [], p
    while cur is not None:
        chain.append(cur.__class__.__name__)
        cur = cur.payload if cur.payload and cur.payload.__class__.__name__ != "NoPayload" else None
    print("   layers():", [c.__name__ for c in p.layers()])
    print("   payload 链:", chain)
    print("\n真正的展开发生在发送时：send(pkt) 会把 dport=[80,443,8080] 拆成 3 个包。")
    print("想自己控制展开，就手动循环：")
    for port in [80, 443, 8080]:
        q = IP(dst=p[IP].dst) / TCP(dport=port, flags="S")
        print(f"   展开: {q.summary()}")


# ═══════════════════════════════════════════════════════════════
# 2. 发送
# ═══════════════════════════════════════════════════════════════
def do_send(dst: str) -> None:
    print("\n" + "=" * 72)
    print("五、真实发送（本机回环）")
    print("=" * 72)

    print("\n[1] send() —— L3，内核补 Ether 层")
    pkt = IP(dst=dst) / ICMP()
    send(pkt, verbose=0, count=1)
    print(f"    已发送: {pkt.summary()}")

    print("\n[2] sr1() —— 发并收，只取第一个响应")
    ans = sr1(IP(dst=dst) / ICMP(), timeout=2, verbose=0)
    if ans:
        print(f"    收到: {ans.summary()}")
        print(f"    ICMP type={ans[ICMP].type} "
              f"({'Echo Reply ✅' if ans[ICMP].type == 0 else '其它'})")
    else:
        print("    无响应（回环上通常一定能收到；若在容器里可能被禁）")

    print("\n[3] sr() —— 发并收，返回 (answered, unanswered)")
    ans, unans = sr(IP(dst=dst) / TCP(dport=[80, 443], flags="S"), timeout=1, verbose=0)
    print(f"    answered={len(ans)} unanswered={len(unans)}")
    for snd, rcv in ans:
        print(f"    dport={snd[TCP].dport} ← {rcv.summary()}"
              f"  flags={rcv[TCP].flags if rcv.haslayer(TCP) else '-'}")

    print("\n[4] sendp() —— L2，需要显式指定 iface")
    try:
        iface = "lo"
        sendp(Ether() / IP(dst=dst) / ICMP(), iface=iface, verbose=0, count=1)
        print(f"    已在 {iface} 上发送 Ether/IP/ICMP")
    except Exception as e:
        print(f"    sendp 失败（通常是没有权限或网卡名不对）: {e}")


# ═══════════════════════════════════════════════════════════════
# 离线自检（不需要 root；scapy 未安装时会跳过构造部分）
# ═══════════════════════════════════════════════════════════════
def self_test() -> int:
    print("=" * 72)
    print("离线自检")
    print("=" * 72)

    # 目标护栏
    assert check_target("127.0.0.1")[0] is True
    assert check_target("192.168.1.10")[0] is True
    assert check_target("10.0.0.5")[0] is True
    assert check_target("8.8.8.8")[0] is False, "公网地址必须被拒绝"
    assert check_target("239.0.0.1")[0] is False, "组播必须被拒绝"
    assert check_target("not-an-ip")[0] is False
    print("✅ check_target(): 回环/私网放行，公网/组播/非法输入拒绝")

    if not HAVE_SCAPY:
        print(f"\nℹ️  未安装 scapy（{_SCAPY_ERR}），跳过构造自检。")
        print("    安装：pip install scapy")
        return 0

    pkts = build_examples("127.0.0.1")
    assert "tcp_syn" in pkts and pkts["tcp_syn"].haslayer(TCP)
    print(f"✅ build_examples(): 构造了 {len(pkts)} 个演示包")

    p = pkts["tcp_syn"]
    assert p[IP].dst == "127.0.0.1"
    assert p[TCP].flags == "S", p[TCP].flags
    assert str(p[TCP].dport) == "80"
    p[IP].ttl = 32
    assert p[IP].ttl == 32
    print("✅ 字段读写: dst/flags/dport/ttl 全部正确")

    # 分层顺序（注意：要用 layers()，直接 for 遍历包拿不到所有层）
    names = [c.__name__ for c in p.layers()]
    assert names == ["IP", "TCP"], names
    print(f"✅ 分层顺序: {names}")

    # 序列化 + 自动算长度（注意：build 的结果在字节串里，不在原对象上）
    raw = bytes(p)
    rp = IP(raw)                      # 重新 dissect 才能看到算好的 len/chksum
    assert rp.len == len(raw), f"{rp.len} != {len(raw)}"
    assert rp.chksum is not None, "dissect 后校验和应有值"
    print(f"✅ 序列化: {len(raw)} 字节，IP.len = {rp.len}，"
          f"chksum = 0x{rp.chksum:04x}（build 不回写原对象，需 dissect）")

    # 载荷变化 → 长度变化 → 校验和变化
    c1 = bytes(IP(dst="127.0.0.1") / ICMP() / b"A")
    c2 = bytes(IP(dst="127.0.0.1") / ICMP() / b"AAAAAAAA")
    r1, r2 = IP(c1), IP(c2)
    assert len(c1) != len(c2)
    assert r1.chksum is not None and r2.chksum is not None
    print(f"✅ 载荷变化影响长度（{len(c1)} vs {len(c2)}），"
          f"IP.chksum = 0x{r1.chksum:04x} vs 0x{r2.chksum:04x}")

    # UDP/DNS 构造
    d = pkts["udp_dns"]
    assert d.haslayer(UDP) and d.haslayer(DNS)
    assert d[UDP].dport == 53
    print("✅ UDP/DNS 构造: ", d.summary())

    print("\n全部离线自检通过。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Day156 Scapy 基础示例（默认 dry-run）")
    ap.add_argument("--dst", default="127.0.0.1", help="目标 IP（默认回环）")
    ap.add_argument("--show", action="store_true", help="打印构造结果")
    ap.add_argument("--send", action="store_true", help="真的发送（需 root）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not HAVE_SCAPY:
        print(f"❌ 未安装 scapy：{_SCAPY_ERR}")
        print("   pip install scapy")
        print("   或先跑离线自检：python3 01-scapy-basics.py --self-test")
        return 1

    ok, why = check_target(args.dst)
    if not ok:
        print("⛔ 拒绝执行：", why)
        return 2
    print(f"✅ 目标 {args.dst} 通过合规检查（{why}）")

    pkts = build_examples(args.dst)
    if args.show or not args.send:
        demo_structure(pkts)
        demo_show2(pkts)
        demo_bytes(pkts)
        demo_expand(pkts)

    if args.send:
        do_send(args.dst)
    else:
        print("\n" + "=" * 72)
        print("ℹ️  dry-run 模式：没有发送任何数据包。")
        print("   要真实发送（先确认目标是回环或自己的私网）：")
        print(f"   sudo python3 {sys.argv[0]} --send --dst {args.dst}")
        print("=" * 72)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
