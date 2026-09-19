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

import warnings

# scapy 导入时会触发 cryptography 的 FFDH 弃用警告（与本日内容无关），
# 教学输出里不需要它 —— 只屏蔽这一条**特定消息**，不是全局静音。
warnings.filterwarnings("ignore", message=".*Diffie-Hellman over finite fields.*")

# ── scapy 是可选的：没装也能看构造结果/跑自检 ──
try:
    from scapy.all import (Ether, IP, IPv6, TCP, UDP, ICMP, Raw,  # type: ignore
                           DNS, DNSQR, send, sendp, sr1, sr, conf, hexdump,
                           rdpcap, PcapReader, wrpcap)
    HAVE_SCAPY = True
except Exception as _e:                       # ImportError 或底层库缺失
    HAVE_SCAPY = False
    _SCAPY_ERR = repr(_e)

# 允许的目标：回环 + 私网 + 链路本地
ALLOW_PRIVATE = True


# ═══════════════════════════════════════════════════════════════
# 自检辅助：失败时打印「实际值 vs 期望值」，而不是丢一个裸 AssertionError
# ═══════════════════════════════════════════════════════════════
def check_eq(actual, expected, label: str) -> None:
    """断言两者相等。失败信息里必须同时出现实际值和期望值，
    否则使用者只看到"断言失败"，还得自己去 debug 才知道差在哪。"""
    if actual != expected:
        raise AssertionError(f"{label} 不匹配：实际={actual!r} 期望={expected!r}")


def check_true(cond, label: str) -> None:
    """断言为真（用于无法用等值表达的条件）。"""
    if not cond:
        raise AssertionError(f"{label} 不成立：期望为真，实际为假")



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
def self_test() -> None:
    print("=" * 72)
    print("离线自检")
    print("=" * 72)

    # 目标护栏（离线、纯逻辑，不需要网卡/root）
    for ok_ip in ("127.0.0.1", "192.168.1.10", "10.0.0.5", "172.16.5.5",
                  "169.254.1.1", "::1"):
        check_true(check_target(ok_ip)[0], f"应放行的目标 {ok_ip}（实际被拒绝）")
    for bad_ip in ("8.8.8.8", "1.1.1.1", "239.0.0.1", "224.0.0.1", "not-an-ip", ""):
        check_true(not check_target(bad_ip)[0], f"应拒绝的目标 {bad_ip}（实际被放行）")
    check_eq(check_target("8.8.8.8")[1].startswith("8.8.8.8"), True, "公网拒绝原因")
    check_eq(check_target("239.0.0.1")[1].startswith("组播"), True, "组播拒绝原因")
    print(f"✅ check_target(): 放行 6 个回环/私网/链路本地地址，"
          f"拒绝 6 个公网/组播/非法输入（说明：{check_target('8.8.8.8')[1][:24]}…）")

    if not HAVE_SCAPY:
        print(f"\nℹ️  未安装 scapy（{_SCAPY_ERR}），跳过构造自检。")
        print("    安装：pip install scapy")
        return 0

    pkts = build_examples("127.0.0.1")
    check_true("tcp_syn" in pkts and pkts["tcp_syn"].haslayer(TCP), "tcp_syn 演示包应含 TCP 层")
    check_eq(len(pkts), 7, "演示包个数")
    print(f"✅ build_examples(): 构造了 {len(pkts)} 个演示包 {sorted(pkts)}")

    p = pkts["tcp_syn"]
    check_eq(p[IP].dst, "127.0.0.1", "tcp_syn 的目的地址")
    check_eq(p[TCP].flags, "S", "tcp_syn 的标志位")
    check_eq(str(p[TCP].dport), "80", "tcp_syn 的目的端口")
    p[IP].ttl = 32
    check_eq(p[IP].ttl, 32, "改字段后的 TTL")
    print("✅ 字段读写: dst/flags/dport/ttl 全部正确")

    # 分层顺序（注意：要用 layers()，直接 for 遍历包拿不到所有层）
    names = [c.__name__ for c in p.layers()]
    check_eq(names, ["IP", "TCP"], "IP/TCP 的分层顺序")
    check_eq([c.__name__ for c in pkts["tcp_http"].layers()], ["IP", "TCP", "Raw"],
             "IP/TCP/Raw 的分层顺序")
    print(f"✅ 分层顺序: {names}；带载荷的包: {[c.__name__ for c in pkts['tcp_http'].layers()]}")

    # 序列化 + 自动算长度（注意：build 的结果在字节串里，不在原对象上）
    raw = bytes(p)
    rp = IP(raw)                      # 重新 dissect 才能看到算好的 len/chksum
    check_eq(rp.len, len(raw), "重新解析后的 IP.len（应等于整包长度）")
    check_true(rp.chksum is not None, "dissect 后 IP.chksum 应有值（build 不回写原对象）")
    print(f"✅ 序列化: {len(raw)} 字节，IP.len = {rp.len}，"
          f"chksum = 0x{rp.chksum:04x}（build 不回写原对象，需 dissect）")

    # 载荷变化 → 长度变化 → 校验和变化
    c1 = bytes(IP(dst="127.0.0.1") / ICMP() / b"A")
    c2 = bytes(IP(dst="127.0.0.1") / ICMP() / b"AAAAAAAA")
    r1, r2 = IP(c1), IP(c2)
    check_true(len(c1) != len(c2), "不同载荷应产生不同长度")
    check_eq(len(c2) - len(c1), 7, "载荷长度差（8 - 1 = 7）")
    check_true(r1.chksum is not None and r2.chksum is not None, "两侧校验和都应有值")
    check_true(r1.chksum != r2.chksum, "载荷不同 → IP 校验和必须不同")
    print(f"✅ 载荷变化影响长度（{len(c1)} vs {len(c2)}），"
          f"IP.chksum = 0x{r1.chksum:04x} vs 0x{r2.chksum:04x}")

    # UDP/DNS 构造
    d = pkts["udp_dns"]
    check_true(d.haslayer(UDP) and d.haslayer(DNS), "udp_dns 包应含 UDP 与 DNS 两层")
    check_eq(d[UDP].dport, 53, "DNS 目的端口")
    check_eq(d[DNS].qd.qname, b"example.com.", "DNS 查询名（注意 scaky 会补根域的点）")
    print("✅ UDP/DNS 构造: ", d.summary())

    # ── 纯标准库复核校验和（不依赖 scapy 的算法，用来证明"校验和是算出来的"）──
    def _ones_complement_sum(data: bytes) -> int:
        """16 位反码求和（纯 Python，和 Day157 的 pcap_lib 是同一套算法）。"""
        if len(data) & 1:
            data += b"\x00"
        total = int.from_bytes(data, "big")
        while total >> 16:
            total = (total & 0xFFFF) + (total >> 16)
        return total & 0xFFFF

    hdr = bytes(IP(dst="10.0.0.1", src="10.0.0.2") / TCP(sport=12345, dport=80,
                                                         flags="S", seq=1000))[:20]
    check_eq(_ones_complement_sum(hdr), 0xFFFF,
             "含校验和的 IPv4 头做反码和（正确校验和应得 0xFFFF）")
    broken = bytearray(hdr)
    broken[8] ^= 0x01                    # 改 TTL 一位
    check_true(_ones_complement_sum(bytes(broken)) != 0xFFFF,
               "改一位后校验和必须不再自洽")
    # scapy 对同样的头算出 0x66cd（本文件开发时实测，见 README）
    check_eq(hdr[10:12].hex(), "66cd", "IPv4 头校验和字节（scapy 计算值）")
    print(f"✅ 纯标准库复核：IPv4 头反码和 = 0x{_ones_complement_sum(hdr):04x}（应为 0xffff），"
          f"校验和字段 = 0x{hdr[10:12].hex()}（与 scapy 一致）")

    # ── pcap 往返：用标准库写、用 scapy 读回来（格式理解的双向验证）──
    import struct as _struct
    import tempfile as _tempfile
    import os as _os

    def _write_pcap(path: str, frames, linktype: int = 101) -> None:
        """最小 pcap 写入器：24 字节全局头 + 每包 16 字节记录头（全小端）。

        linktype=101 是 **DLT_RAW**（裸 IP，没有链路层头）。这里故意用它，
        因为写起来最省事；同时也是提醒：**pcap 的 network 字段决定了解析起点**
        —— 同样的字节，标成 1(Ethernet) 就会被当成"有 14 字节以太头"来解析，
        字段全错位。这就是"换一种抓包方式就读不出字段"的根本原因。
        """
        with open(path, "wb") as f:
            f.write(_struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, linktype))
            for ts, data in frames:
                sec = int(ts)
                usec = int(round((ts - sec) * 1_000_000))
                f.write(_struct.pack("<IIII", sec, usec, len(data), len(data)))
                f.write(data)

    tmpdir = _tempfile.mkdtemp(prefix="day156-01-")
    try:
        pcap_path = _os.path.join(tmpdir, "roundtrip.pcap")
        frames = [(1700000000.0, bytes(IP(dst="127.0.0.1") / ICMP() / b"day156")),
                  (1700000000.5, bytes(IP(dst="127.0.0.1") / TCP(dport=80, flags="S")))]
        _write_pcap(pcap_path, frames)
        back = rdpcap(pcap_path)          # 让 scapy（外部实现）读我们自己写的文件
        check_eq(len(back), 2, "scapy 读回的包数")
        check_eq(back[0][IP].dst, "127.0.0.1", "第 1 包目的 IP")
        check_eq(len(bytes(back[0])), len(frames[0][1]), "第 1 包长度（字节级一致）")
        check_eq(back[0][ICMP].type, 8, "第 1 包 ICMP 类型（8=Echo Request）")
        check_eq(back[0][Raw].load, b"day156", "第 1 包载荷")
        check_eq(back[1][TCP].dport, 80, "第 2 包目的端口")
        check_eq(back[1][TCP].flags, "S", "第 2 包 TCP 标志")
        check_eq(round(float(back[1].time) - float(back[0].time), 6), 0.5,
                 "两个包的时间差（微秒精度）")
        print(f"✅ pcap 往返：标准库写入 2 个包 → scapy rdpcap 读回，"
              f"字段/载荷/时间戳全部一致（linktype=101 DLT_RAW）")
    finally:
        import shutil as _shutil
        _shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Day156 Scapy 基础示例（默认 dry-run）")
    ap.add_argument("--dst", default="127.0.0.1", help="目标 IP（默认回环）")
    ap.add_argument("--show", action="store_true", help="打印构造结果")
    ap.add_argument("--send", action="store_true", help="真的发送（需 root）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        try:
            self_test()
        except AssertionError as e:
            print(f"SELF-TEST FAIL: {e}")
            return 1
        except Exception as e:                    # noqa: BLE001 —— 自检要报告任何异常
            print(f"SELF-TEST FAIL: {type(e).__name__}: {e}")
            return 1
        print("SELF-TEST OK")
        return 0

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
