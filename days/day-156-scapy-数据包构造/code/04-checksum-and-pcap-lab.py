#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 156 · 示例 04 —— 校验和与 pcap 格式实验室（纯标准库可验证）
================================================================================

为什么要有这一个文件？
    前三天的示例都依赖 Scapy 帮你把校验和算好、把 pcap 写好。
    结果就是：**你会用，但不知道下面发生了什么**。一旦遇到
        · 抓包显示 "TCP checksum incorrect"
        · 改了载荷之后对端静默丢弃
        · 自己写 pcap 时另一个工具读不出来
    就会卡住。本文件把"看不见的那一层"全部摊开：

    1) 校验和从零实现：16 位反码求和 → IPv4 头 / TCP / UDP（带伪首部）/ ICMP（不带）
    2) **和 Scapy 的字节级交叉验证**：同样的头，校验和必须一样；
       同样的 pcap 字节，Scapy 和本文件必须读出相同的包
    3) **RFC 1071 / RFC 1624**：官方测试向量 + "改一个字段如何增量更新校验和"
       （这就是路由器改 TTL 不用重算整包的原因）
    4) pcap 文件格式：24 字节全局头 + 每包 16 字节记录头，自己写、让 Scapy 读
    5) 分片与 MTU：分片后**每个分片的 IP 校验和都要重算**

运行：
    python3 -B 04-checksum-and-pcap-lab.py            # 完整讲解 + 实验
    python3 -B 04-checksum-and-pcap-lab.py --self-test # 离线自检 → SELF-TEST OK

⚠️ 本文件不发送任何数据包（分片是**内存里**做的），不需要 root，不碰网卡。
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import struct
import sys
import tempfile

import warnings

# scapy 导入时会触发 cryptography 的 FFDH 弃用警告（与本日内容无关），
# 教学输出里不需要它 —— 只屏蔽这一条**特定消息**，不是全局静音。
warnings.filterwarnings("ignore", message=".*Diffie-Hellman over finite fields.*")

try:
    # 注意：这里不导入 defrag —— 实测 scapy 2.7.0 的 defrag() 对内存分片不生效，
    # 本文件改为自己实现重组（见 reassemble_fragments），更可控也更有教学价值。
    from scapy.all import (IP, TCP, UDP, ICMP, fragment,  # type: ignore
                           rdpcap, wrpcap)
    HAVE_SCAPY = True
except Exception as _e:                       # noqa: BLE001
    HAVE_SCAPY = False
    _SCAPY_ERR = repr(_e)


# ═══════════════════════════════════════════════════════════════
# 0. 自检辅助
# ═══════════════════════════════════════════════════════════════
def check_eq(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label} 不匹配：实际={actual!r} 期望={expected!r}")


def check_true(cond, label: str) -> None:
    if not cond:
        raise AssertionError(f"{label} 不成立：期望为真，实际为假")


# ═══════════════════════════════════════════════════════════════
# 1. 校验和：16 位反码求和（RFC 1071）
# ═══════════════════════════════════════════════════════════════
#
# 算法（必须能背下来，排错全靠它）：
#   ① 数据按 16 位一组当**大端**整数相加；奇数长度末尾补一个 0x00 字节
#   ② 结果的高 16 位是"进位"，回卷加到低 16 位（可能卷多次）
#   ③ 取反码 → 这就是校验和字段该填的值
#   ④ 验证：把"含校验和字段"的整段再算一次反码和，结果必须是 0xFFFF

def ones_complement_sum(data: bytes, initial: int = 0) -> int:
    """16 位反码和（未取反）。

    实现技巧：用 int.from_bytes 把整段当一个大整数一次相加，
    再折叠进位。比 for 循环每 2 字节加一次快得多（大整数加法在 C 层完成）。
    """
    if len(data) & 1:                 # 奇数长度必须补零字节
        data = data + b"\x00"
    total = int.from_bytes(data, "big") + initial
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return total & 0xFFFF


def checksum(data: bytes, initial: int = 0) -> int:
    """反码和的补码 = 要填进校验和字段的值。"""
    return (~ones_complement_sum(data, initial)) & 0xFFFF


def ipv4_header_checksum(header: bytes) -> int:
    """IPv4 头校验和（调用前必须把 checksum 字段置 0）。"""
    return checksum(header)


def verify_ipv4_checksum(header: bytes) -> bool:
    """IPv4 头校验和验证：含校验和字段的整段反码和应为 0xFFFF。"""
    return ones_complement_sum(header) == 0xFFFF


def pseudo_header_v4(src: str, dst: str, proto: int, length: int) -> bytes:
    """TCP/UDP 校验和用的伪首部（12 字节，**不会真的发出去**）。

        源 IP(4) | 目的 IP(4) | 全 0(1) | 协议号(1) | L4 长度(2)

    作用不是检错而是**防止误投递**：包如果被路由到错误的 IP，
    接收端算出的校验和会对不上 → 丢弃。
    这也是为什么 NAT 改 IP/端口**必须**同时改 TCP/UDP 校验和。
    """
    return (socket.inet_aton(src) + socket.inet_aton(dst) +
            bytes([0, proto]) + struct.pack("!H", length))


def l4_checksum(segment: bytes, src: str, dst: str, proto: int) -> int:
    """TCP/UDP 校验和（含伪首部）。"""
    return checksum(pseudo_header_v4(src, dst, proto, len(segment)) + segment)


def verify_l4_checksum(segment: bytes, src: str, dst: str, proto: int) -> bool:
    return ones_complement_sum(pseudo_header_v4(src, dst, proto, len(segment)) + segment) == 0xFFFF


def icmp_checksum(message: bytes) -> int:
    """ICMP 校验和：**没有伪首部**，只覆盖 ICMP 消息本身。

    这是最容易记混的一条：TCP/UDP 有伪首部、ICMP 没有。
    如果你把 ICMP 也加上伪首部，算出来的校验和对方一定不认。
    """
    return checksum(message)


def checksum_after_field_change(old_cksum: int, old_word: int, new_word: int) -> int:
    """改了一个 16 位字段后，**增量更新**校验和（RFC 1624）。

        HC' = ~( ~HC + ~m + m' )     （全程按 16 位反码算术）

    为什么要这样？因为路由器每转发一跳都要把 TTL 减 1：
      · 如果每次都重算整包 → 每跳一次遍历整个头部（IPv4 头 20~60 字节，还行）
      · 但如果是校验更大的范围，代价就上去了；
      · 反码和的**可交换/可结合**性质让"改一个字段"只需要两三次加法。
    这条正是"为什么校验和用反码和而不是普通和"的答案。
    """
    total = ((~old_cksum) & 0xFFFF) + ((~old_word) & 0xFFFF) + new_word
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


# ═══════════════════════════════════════════════════════════════
# 2. 最小 pcap 读写（标准的 24 + 16 字节结构）
# ═══════════════════════════════════════════════════════════════
def write_pcap(path: str, frames, linktype: int = 101) -> int:
    """写经典 pcap（小端、微秒）。linktype=101 是 DLT_RAW（裸 IP）。

    三个必须写对的地方：
      ① 魔数 0xA1B2C3D4（小端写出来是 d4 c3 b2 a1）；
      ② 每条记录的 incl_len / orig_len 都是**数据长度**，不含 16 字节记录头；
      ③ 时间戳拆成 秒 + 微秒 两个 32 位整数（浮点误差要保护）。
    """
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, linktype))
        for ts, data in frames:
            sec = int(ts)
            usec = int(round((ts - sec) * 1_000_000))
            if usec >= 1_000_000:              # 浮点误差保护
                sec, usec = sec + 1, usec - 1_000_000
            f.write(struct.pack("<IIII", sec, usec, len(data), len(data)))
            f.write(data)
    return len(frames)


def read_pcap(path: str):
    """读经典 pcap，返回 [(ts, data), ...]。

    字节序判断：按小端读魔数 == 0xA1B2C3D4 → 小端；== 0xD4C3B2A1 → 大端。
    判错的后果是 incl_len 变成天文数字，然后 read() 一口吃掉整个文件。
    """
    out = []
    with open(path, "rb") as f:
        gh = f.read(24)
        if len(gh) < 24:
            raise ValueError("pcap 全局头不足 24 字节（文件损坏或被截断）")
        magic_le = int.from_bytes(gh[0:4], "little")
        if magic_le == 0xA1B2C3D4:
            endian, div = "<", 1_000_000
        elif magic_le == 0xA1B23C4D:
            endian, div = "<", 1_000_000_000
        elif magic_le == 0xD4C3B2A1:
            endian, div = ">", 1_000_000
        elif magic_le == 0x4D3CB2A1:
            endian, div = ">", 1_000_000_000
        else:
            raise ValueError(f"不是合法的 pcap（魔数 0x{magic_le:08x}）")
        while True:
            ph = f.read(16)
            if len(ph) < 16:
                break                          # 正常 EOF / 尾部记录残缺
            sec, frac, incl, _orig = struct.unpack(endian + "IIII", ph)
            if incl > 262144:
                raise ValueError(f"记录长度异常（{incl}），字节序可能判错")
            data = f.read(incl)
            if len(data) < incl:
                break                          # 残包丢弃，不抛异常
            out.append((sec + frac / div, data))
    return out


# ═══════════════════════════════════════════════════════════════
# 2.5 分片重组（自己实现，不依赖 scapy 的 defrag）
# ═══════════════════════════════════════════════════════════════
#
# ⚠️ 实测记录（必须写下来，否则以后会怀疑自己）：
#    在 scapy 2.7.0 上，对**内存里**用 fragment() 造出来的分片调用 defrag()，
#    并不能重组出原始包（它会把分片原样返回/丢掉 IP 层）。本文件因此自己实现
#    重组逻辑 —— 顺便这也是理解"分片重组到底在做什么"的最好方式：
#      ① 每个分片的 IP 头里 frag 字段（13 位）**单位是 8 字节** → 字节偏移 = frag × 8
#      ② 按偏移排序，去掉各自的 IP 头，把载荷首尾相接
#      ③ 第一个分片保留了原来的传输层头与 proto，末片 MF=0 表示结束

def reassemble_fragments(frags) -> bytes:
    """按 frag_offset 排序并拼接载荷，返回重组后的 IP 载荷（不含 IP 头）。"""
    if not frags:
        raise ValueError("没有分片可重组")
    ordered = sorted(frags, key=lambda f: int(f[IP].frag) * 8)
    parts = []
    expected = 0
    for f in ordered:
        off = int(f[IP].frag) * 8                     # ⚠️ 单位 8 字节
        if off != expected:
            raise ValueError(f"分片不连续：期望偏移 {expected}，实际 {off}（可能丢片）")
        # ⚠️ 不能用 f[IP].ihl —— scapy 的派生字段（ihl/len/chksum）在对象上是 **None**，
        #    真实值只在序列化后的字节里。所以从左数第 1 个字节的低 4 位取头长度。
        raw = bytes(f)
        ihl = (raw[0] & 0x0F) * 4                     # IP 头长度单位是 4 字节
        parts.append(raw[ihl:])
        expected = off + (len(bytes(f)) - ihl)
    # 除了"偏移连续"，还要检查"最后一片的 MF 必须为 0"：
    # 否则就是**丢了中间/末尾的片**，此时悄悄拼出来的字节是残缺的、比错误更危险。
    if bool(ordered[-1][IP].flags.MF):
        raise ValueError("最后一片仍带 MF 标志 → 分片不完整（可能丢片）")
    return b"".join(parts)


# ═══════════════════════════════════════════════════════════════
# 3. 讲解 + 实验
# ═══════════════════════════════════════════════════════════════
def demo_rfc1071() -> None:
    print("=" * 72)
    print("实验 1：RFC 1071 官方测试向量")
    print("=" * 72)
    data = bytes.fromhex("0001f203f4f5f6f7")
    print(f"  数据 : {data.hex(' ')}")
    print(f"  反码和 = 0x{ones_complement_sum(data):04x}   （RFC 1071 给出 ddf2）")
    print(f"  校验和 = 0x{checksum(data):04x}   （RFC 1071 给出 220d）")
    # ⚠️ 用 bytes.fromhex 而不是字面量转义：多重转义很容易写出"看起来对、
    #    实际上是 4 个 ASCII 字符"的假数据（本文件开发时就在这里踩过一次）
    odd = bytes.fromhex("01")            # 1 字节，奇数长度
    even = bytes.fromhex("0100")         # 2 字节
    print("\n  奇数长度必须补零：")
    print(f"    ones_complement_sum({odd.hex()})   = 0x{ones_complement_sum(odd):04x}"
          f"（补了一个 0x00 字节后才等于偶数长度版本）")
    print(f"    ones_complement_sum({even.hex()}) = 0x{ones_complement_sum(even):04x}")


def demo_pseudo_header() -> None:
    print("\n" + "=" * 72)
    print("实验 2：伪首部到底有没有用？（TCP 校验和忘了伪首部会怎样）")
    print("=" * 72)
    # 手工构造一个 TCP 段（SYN，sport=12345, dport=80, seq=1000）
    seg = bytearray()
    seg += struct.pack("!HH", 12345, 80)
    seg += struct.pack("!II", 1000, 0)
    seg += bytes([0x50, 0x02])                 # data offset=5, flags=SYN
    seg += struct.pack("!H", 64240)            # 窗口
    seg += b"\x00\x00"                         # 校验和占位
    seg += b"\x00\x00"                         # 紧急指针
    with_ph = l4_checksum(bytes(seg), "10.0.0.2", "10.0.0.1", 6)
    print(f"  带伪首部的正确校验和 : 0x{with_ph:04x}")
    # 如果实现者忘了伪首部，填这个值进去会怎样？
    no_ph = checksum(bytes(seg))
    print(f"  只算段本身（错误做法）: 0x{no_ph:04x}")
    seg[16:18] = struct.pack("!H", no_ph)
    print(f"  用错误值验证（带伪首部）: {verify_l4_checksum(bytes(seg), '10.0.0.2', '10.0.0.1', 6)} ← 必须失败")
    seg[16:18] = struct.pack("!H", with_ph)
    print(f"  用正确值验证（带伪首部）: {verify_l4_checksum(bytes(seg), '10.0.0.2', '10.0.0.1', 6)} ← 必须通过")
    print("\n  再换个目的 IP 试试（伪首部把 IP 也纳入了校验范围）：")
    print(f"    校验和 = 0x{l4_checksum(bytes(seg), '10.0.0.2', '10.0.0.9', 6):04x}"
          f"  ← 与 0x{with_ph:04x} 不同，说明**源/目的 IP 参与了校验**")
    print("    这正是 NAT 改地址必须改校验和的原因（改错就会出现'连接建立但数据全丢'）")


def demo_incremental_update() -> None:
    print("\n" + "=" * 72)
    print("实验 3：改一个字段，校验和能「增量更新」吗？（RFC 1624）")
    print("=" * 72)
    # 构造一个 IPv4 头（TTL=64），算好校验和
    header = bytearray(20)
    header[0] = 0x45
    header[2:4] = struct.pack("!H", 40)
    header[8] = 64                                  # TTL
    header[9] = 6                                   # proto = TCP
    header[12:16] = socket.inet_aton("10.0.0.2")
    header[16:20] = socket.inet_aton("10.0.0.1")
    header[10:12] = struct.pack("!H", ipv4_header_checksum(bytes(header)))
    old_ck = int.from_bytes(header[10:12], "big")
    print(f"  TTL=64 时校验和 = 0x{old_ck:04x}")

    # 方式 A：全量重算（TTL 减 1）
    full = bytearray(header)
    full[8] = 63
    full[10:12] = b"\x00\x00"
    full_ck = ipv4_header_checksum(bytes(full))
    # 方式 B：增量更新（只加两次法）
    old_word = int.from_bytes(header[8:10], "big")   # TTL 所在的 16 位字
    new_word = (63 << 8) | header[9]
    inc_ck = checksum_after_field_change(old_ck, old_word, new_word)
    print(f"  全量重算(TTL=63) = 0x{full_ck:04x}")
    print(f"  增量更新(TTL=63) = 0x{inc_ck:04x}")
    print(f"  两者相同？{full_ck == inc_ck}  ← 路由器就是靠这个省掉整包重算的")
    full[10:12] = struct.pack("!H", inc_ck)
    print(f"  增量结果能通过验证？{verify_ipv4_checksum(bytes(full))}")


def demo_pcap_cross(path: str) -> None:
    print("\n" + "=" * 72)
    print("实验 4：pcap 格式 —— 自己写，让 Scapy 读（交叉验证）")
    print("=" * 72)
    if not HAVE_SCAPY:
        print(f"  ℹ️ 未安装 scapy（{_SCAPY_ERR}），跳过 Scapy 交叉验证部分。")
        return
    frames = [
        (1700000000.0, bytes(IP(dst="127.0.0.1") / ICMP(type=8) / b"day156-lab")),
        (1700000000.25, bytes(IP(dst="127.0.0.1") / TCP(dport=80, flags="S"))),
        (1700000000.5, bytes(IP(dst="127.0.0.1") / UDP(dport=53) / b"\x00\x01")),
    ]
    n = write_pcap(path, frames, linktype=101)
    print(f"  已写出 {n} 个包 → {path}（{os.path.getsize(path)} 字节）")
    # ① 我们读自己写的
    mine = read_pcap(path)
    check_mine = [(round(ts, 6), len(d)) for ts, d in mine]
    print(f"  本文件读回 : {check_mine}")
    # ② Scapy 读我们写的
    theirs = rdpcap(path)
    print(f"  Scapy 读回 : {[(round(float(p.time), 6), len(bytes(p))) for p in theirs]}")
    for i, (pkt, (ts, data)) in enumerate(zip(theirs, mine)):
        check_true(bytes(pkt) == data, f"第 {i+1} 包字节一致")
    print("  ✅ 两种实现读出的字节完全一致 —— 说明 pcap 格式我们理解对了")
    # ③ Scapy 写，我们读
    p2 = path + ".scapy.pcap"
    wrpcap(p2, [IP(dst="127.0.0.1") / ICMP() / b"x", IP(dst="127.0.0.1") / TCP(dport=443)])
    back = read_pcap(p2)
    check_eq(len(back), 2, "本文件读 Scapy 写出的 pcap 的包数")
    print(f"  ✅ 反向验证：Scapy 写出的 pcap，我们读回 {len(back)} 个包")


def demo_fragment() -> None:
    print("\n" + "=" * 72)
    print("实验 5：分片与 MTU —— 分片后每个分片的 IP 校验和都要重算")
    print("=" * 72)
    if not HAVE_SCAPY:
        print(f"  ℹ️ 未安装 scapy（{_SCAPY_ERR}），跳过（分片演示依赖 scapy）。")
        return
    payload = b"A" * 4000
    pkt = IP(dst="127.0.0.1") / ICMP() / payload
    frags = fragment(pkt, fragsize=1480)
    print(f"  原始包：{len(bytes(pkt))} 字节（IP 头 20 + ICMP 8 + 载荷 4000）")
    print(f"  分片数：{len(frags)}  （fragsize=1480 → 每片载荷必须是 8 的倍数）")
    print(f"  {'#':<3}{'frag_offset':>12}{'MF':>5}{'总长':>7}  IP校验和验证")
    for i, f in enumerate(frags, 1):
        raw = bytes(f)
        ok = verify_ipv4_checksum(raw[:20])
        print(f"  {i:<3}{f[IP].frag:>12}{str(bool(f[IP].flags.MF)):>5}{len(raw):>7}  "
              f"{'✅ 通过' if ok else '❌ 失败'}")
        check_true(ok, f"第 {i} 个分片的 IP 校验和")
    print("\n  为什么每片的校验和都不同？因为**分片改变了 IP 头**（总长、标志、偏移），")
    print("  改了头就必须重算校验和 —— 这也是「分片重组」类攻击容易留下痕迹的原因。")
    joined = reassemble_fragments(frags)
    check_true(joined == bytes(pkt)[20:], "自己实现的重组结果必须与原始 IP 载荷一致")
    print(f"  ✅ 自己实现重组：拼回 {len(joined)} 字节，与原始 IP 载荷字节级一致")
    print("  （实测：scapy 2.7.0 的 defrag() 对内存里造的分片不生效，"
          "所以这里自己按 frag_offset 拼——这也是理解重组的最好方式）")


def self_test(tmpdir: str) -> None:
    print("=" * 72)
    print("离线自检：校验和 / RFC 向量 / 增量更新 / pcap 往返 / 分片")
    print("=" * 72)

    # ① RFC 1071 官方向量
    rfc = bytes.fromhex("0001f203f4f5f6f7")
    check_eq(ones_complement_sum(rfc), 0xDDF2, "RFC1071 反码和")
    check_eq(checksum(rfc), 0x220D, "RFC1071 校验和")
    check_eq(ones_complement_sum(b"\x01"), 0x0100, "奇数长度补零")
    check_eq(ones_complement_sum(b""), 0x0000, "空输入")
    print("✅ 校验和：RFC 1071 向量（ddf2 / 220d）+ 奇数长度 + 空输入 一致")

    # ② 与 Scapy 的字节级交叉验证
    if HAVE_SCAPY:
        hdr = bytes(IP(src="10.0.0.2", dst="10.0.0.1", id=1, ttl=64, flags=0) /
                    TCP(sport=12345, dport=80, flags="S", seq=1000, window=64240))[:20]
        # ⚠️ 比较前必须把校验和字段**清零**再算 —— 校验和的定义是
        #    "把该字段置 0 后对整头求反码和的补码"。直接拿含值的头去算会得到 0，
        #    这是新手最容易搞错的一步（本文件开发时就在这里踩过一次）。
        zeroed = bytearray(hdr)
        zeroed[10:12] = b"\x00\x00"
        check_eq(int.from_bytes(hdr[10:12], "big"), ipv4_header_checksum(bytes(zeroed)),
                 "我方（置零后）算出的 IPv4 校验和 vs Scapy 写在字节里的值")
        check_eq(hdr[10:12].hex(), "66cd", "IPv4 校验和字节（Scapy 值）")
        check_true(verify_ipv4_checksum(hdr), "自洽验证")
        # TCP 段（Scapy 的完整 40 字节包 = IP 20 + TCP 20）
        full = bytes(IP(src="10.0.0.2", dst="10.0.0.1", id=1, ttl=64, flags=0) /
                     TCP(sport=12345, dport=80, flags="S", seq=1000, window=64240))
        seg = full[20:]
        seg_zeroed = bytearray(seg)
        seg_zeroed[16:18] = b"\x00\x00"          # 同样要先把校验和字段清零
        check_eq(int.from_bytes(seg[16:18], "big"),
                 l4_checksum(bytes(seg_zeroed), "10.0.0.2", "10.0.0.1", 6),
                 "我方（置零后）算的 TCP 校验和 vs Scapy 的值")
        check_eq(int.from_bytes(seg[16:18], "big"), 0x6C7E, "TCP 校验和（Scapy 值 0x6c7e）")
        check_true(verify_l4_checksum(seg, "10.0.0.2", "10.0.0.1", 6), "TCP 校验和验证")
        # 改成别的目的 IP → 必须失败（证明伪首部生效）
        check_true(not verify_l4_checksum(seg, "10.0.0.2", "10.0.0.9", 6),
                   "改目的 IP 后验证必须失败（伪首部生效）")
        print("✅ 与 Scapy 交叉验证：IPv4 头 0x66cd、TCP 段 0x6c7e 完全一致")
    else:
        print(f"ℹ️  未安装 scapy（{_SCAPY_ERR}），跳过 Scapy 交叉验证（其余断言照常执行）")

    # ③ 忘了伪首部 → 验证必须失败（这是真实的 bug 模式）
    seg = bytearray()
    seg += struct.pack("!HH", 12345, 80)
    seg += struct.pack("!II", 1000, 0)
    seg += bytes([0x50, 0x02])
    seg += struct.pack("!H", 64240) + b"\x00\x00" + b"\x00\x00"
    seg[16:18] = struct.pack("!H", checksum(bytes(seg)))       # 错误：漏了伪首部
    check_true(not verify_l4_checksum(bytes(seg), "10.0.0.2", "10.0.0.1", 6),
               "漏掉伪首部的校验和必须验证失败")
    # 重算前**必须清零**校验和字段（否则是把"错误值"再算进去）
    seg[16:18] = b"\x00\x00"
    seg[16:18] = struct.pack("!H", l4_checksum(bytes(seg), "10.0.0.2", "10.0.0.1", 6))
    check_true(verify_l4_checksum(bytes(seg), "10.0.0.2", "10.0.0.1", 6),
               "正确校验和必须验证通过")
    print("✅ 伪首部：漏掉它一定验证失败，加上它一定通过")

    # ④ ICMP 没有伪首部
    msg = struct.pack("!BBHHH", 8, 0, 0, 1, 1) + b"ping"
    body = msg[:2] + struct.pack("!H", icmp_checksum(msg)) + msg[4:]
    check_true(ones_complement_sum(body) == 0xFFFF, "ICMP 校验和自洽（无伪首部）")
    check_true(icmp_checksum(msg) != l4_checksum(msg, "10.0.0.1", "10.0.0.2", 1),
               "ICMP 校验和必须与'假想带伪首部'的结果不同")
    print("✅ ICMP：无伪首部，与 TCP/UDP 的算法不同（这条最容易记混）")

    # ⑤ RFC 1624 增量更新 == 全量重算
    for ttl_from, ttl_to in ((64, 63), (63, 62), (255, 254), (2, 1)):
        header = bytearray(20)
        header[0], header[2:4] = 0x45, struct.pack("!H", 40)
        header[8], header[9] = ttl_from, 6
        header[12:16] = socket.inet_aton("10.0.0.2")
        header[16:20] = socket.inet_aton("10.0.0.1")
        header[10:12] = struct.pack("!H", ipv4_header_checksum(bytes(header)))
        old_ck = int.from_bytes(header[10:12], "big")
        old_word = int.from_bytes(header[8:10], "big")
        new_word = (ttl_to << 8) | header[9]
        inc = checksum_after_field_change(old_ck, old_word, new_word)
        full = bytearray(header)
        full[8] = ttl_to
        full[10:12] = b"\x00\x00"
        check_eq(inc, ipv4_header_checksum(bytes(full)),
                 f"TTL {ttl_from}→{ttl_to} 的增量更新结果")
        full[10:12] = struct.pack("!H", inc)
        check_true(verify_ipv4_checksum(bytes(full)),
                   f"TTL {ttl_from}→{ttl_to} 增量结果可验证")
    print("✅ RFC 1624：TTL 递减的增量更新结果 == 全量重算（4 组向量）")

    # ⑥ pcap 往返（自写自读 + Scapy 交叉）
    frames = [(1700000000.0, b"\x45" + b"\x00" * 19 + b"payload"),
              (1700000000.999999, b"\x45" + b"\x01" * 19 + b"x" * 100)]
    path = os.path.join(tmpdir, "lab.pcap")
    write_pcap(path, frames)
    back = read_pcap(path)
    check_eq(len(back), 2, "pcap 读回包数")
    check_eq(back[0][1], frames[0][1], "第 1 包字节")
    check_eq(back[1][1], frames[1][1], "第 2 包字节")
    check_eq(round(back[1][0] - back[0][0], 6), 0.999999, "时间戳差（微秒精度）")
    if HAVE_SCAPY:
        theirs = rdpcap(path)
        check_eq(len(theirs), 2, "Scapy 读同一文件的包数")
        check_eq(bytes(theirs[1]), frames[1][1], "Scapy 读出的第 2 包字节（交叉验证）")
    print("✅ pcap 往返：自写自读 + Scapy 交叉读，字节与时间戳一致")

    # 大端 pcap：判错字节序是最经典的读文件事故
    be_path = os.path.join(tmpdir, "be.pcap")
    with open(be_path, "wb") as f:
        f.write(struct.pack(">IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 101))
        for ts, data in frames:
            sec = int(ts)
            usec = int(round((ts - sec) * 1_000_000))
            f.write(struct.pack(">IIII", sec, usec, len(data), len(data)))
            f.write(data)
    check_eq(len(read_pcap(be_path)), 2, "大端 pcap 读回的包数")
    print("✅ 大端 pcap：魔数 0xd4c3b2a1 被识别，字节序自动切换")

    # 截断的 pcap：必须丢残包而不是抛异常
    trunc = os.path.join(tmpdir, "trunc.pcap")
    blob = open(path, "rb").read()
    with open(trunc, "wb") as f:
        f.write(blob[:-10])                     # 砍掉最后一个包的尾部
    check_eq(len(read_pcap(trunc)), 1, "截断文件应只读出完整的包")
    print("✅ 截断容错：尾部残包被丢弃，不抛异常（抓包进程被 kill 时的常态）")

    # ⑦ 分片：每片校验和都正确、重组后与原始一致
    if HAVE_SCAPY:
        pkt = IP(dst="127.0.0.1") / ICMP() / (b"A" * 4000)
        frags = fragment(pkt, fragsize=1480)
        check_eq(len(frags), 3, "4000 字节载荷 / fragsize=1480 的分片数")
        for i, f in enumerate(frags, 1):
            check_true(verify_ipv4_checksum(bytes(f)[:20]),
                       f"第 {i} 片 IP 校验和")
        check_eq([f[IP].frag for f in frags], [0, 185, 370],
                 "各分片的字节偏移（185 = 1480/8）")
        check_true(bool(frags[0][IP].flags.MF) and not bool(frags[-1][IP].flags.MF),
                   "非末片 MF=1、末片 MF=0")
        # 自己实现的重组（不依赖 scapy defrag，见 reassemble_fragments 注释）
        joined = reassemble_fragments(frags)
        check_eq(joined, bytes(pkt)[20:], "重组后的 IP 载荷")
        check_eq(len(joined), 8 + 4000, "重组载荷长度（ICMP 头 8 + 4000 字节）")
        # 乱序分片也必须能重组（真实网络里分片就是会乱序到达）
        shuffled = [frags[2], frags[0], frags[1]]
        check_eq(reassemble_fragments(shuffled), joined, "乱序分片的重组结果")
        # 缺片必须报错（而不是悄悄拼出一个残缺的包）
        for incomplete, why in ((frags[:2], "只给前两片（末尾 MF 仍为 1）"),
                                ([frags[0]], "只给第一片"),
                                ([frags[1], frags[2]], "丢掉第一个分片（偏移不连续）")):
            try:
                reassemble_fragments(incomplete)
            except ValueError:
                continue
            raise AssertionError(f"缺片场景应当报错：{why}")
        # 分片偏移单位的交叉验证：scapy 的 frag 字段是"8 字节为单位"的原始值
        check_eq([p[IP].frag for p in frags], [0, 185, 370], "分片偏移（单位 8 字节）")
        check_eq([int(p[IP].frag) * 8 for p in frags], [0, 1480, 2960],
                 "换算成字节偏移")
        print(f"✅ 分片：{len(frags)} 片、偏移 {[f[IP].frag for f in frags]}、"
              f"每片校验和正确、乱序可重组、缺片报错")
    else:
        print("ℹ️  未安装 scapy，跳过分片自检")


def main() -> int:
    ap = argparse.ArgumentParser(description="Day156 示例04：校验和与 pcap 格式实验室")
    ap.add_argument("--self-test", action="store_true", help="离线自检（输出 SELF-TEST OK）")
    args = ap.parse_args()

    tmpdir = tempfile.mkdtemp(prefix="day156-04-")
    try:
        if args.self_test:
            try:
                self_test(tmpdir)
            except AssertionError as e:
                print(f"SELF-TEST FAIL: {e}")
                return 1
            except Exception as e:               # noqa: BLE001
                print(f"SELF-TEST FAIL: {type(e).__name__}: {e}")
                return 1
            print("SELF-TEST OK")
            return 0

        demo_rfc1071()
        demo_pseudo_header()
        demo_incremental_update()
        demo_pcap_cross(os.path.join(tmpdir, "lab.pcap"))
        demo_fragment()
        print("\n" + "=" * 72)
        print("小结：校验和不是「魔法」，它是 16 位反码求和 + 三种覆盖范围")
        print("      （IPv4 只看头 / TCP-UDP 带伪首部 / ICMP 只看自己）。")
        print("      pcap 也不是「黑盒」，就是 24 字节头 + 每包 16 字节记录头。")
        print("=" * 72)
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
