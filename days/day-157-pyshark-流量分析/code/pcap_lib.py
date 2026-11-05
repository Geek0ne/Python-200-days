#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 157 · pcap_lib —— 纯标准库实现的 PCAP 读写 / 协议解析 / 显示过滤器引擎
==============================================================================

这一层为什么存在？（这是本日「降级路径」的核心）
    pyshark 很好用，但它**依赖 tshark 这个 C 二进制**：
        · 机器上没装 Wireshark/tshark → `import pyshark` 直接 ImportError；
        · tshark 版本不同 → 某些字段名会变（比如 tcp.flags 的输出格式）；
        · 每个包都要走一次子进程管道 → 大批量分析时是性能瓶颈。
    工程上正确的做法是把「解析能力」分成两条路：

        ① 快速/全功能路径：有 tshark/pyshark 时交给它（协议覆盖全、字段上百个）
        ② 兜底路径：没有时，用标准库自己解析
           —— pcap 文件格式其实**极其简单**（24 字节文件头 + 每包 16 字节头），
              TCP/IP/DNS/HTTP 的核心字段解析也只需要几百行 Python。

    本文件就是 ②，它同时证明了「为什么 tshark 快」：
    纯 Python 逐字节解析比 C 写的 tshark 慢一个数量级以上，
    所以兜底路径的定位是——**轻量统计 + 离线自检 + 教学**，不是跑 100 万包。

本文件提供四样东西（纯标准库，Python 3.10+ 直接可跑）：
    1) PCAP / PCAPNG 读写（含**流式迭代**：内存占用恒定，不受文件大小影响）
    2) 解析：Ethernet / VLAN / ARP / IPv4 / IPv6 / TCP / UDP / ICMP / DNS / HTTP
       —— 并且会**校验 IPv4 头校验和与 TCP/UDP 校验和**（这是 pyshark 不会
          主动帮你做的事：它默认只做 dissection，不做完整性验证）
    3) 显示过滤器引擎（Wireshark display filter 的一个子集）
       —— 用户态、按协议字段过滤；与 BPF（内核态、按字节偏移过滤）是两回事
    4) 合成流量生成器：在 tempfile 目录里造一个**确定性**的 pcap，
       里面植入 5 类可被精确断言的异常（端口扫描 / SYN 洪水 / 明文凭据 /
       DNS 隧道 / C2 心跳），这样自检才能「结果准确」而不是「跑通就行」。

运行：
    python3 -B pcap_lib.py --self-test                 # 离线自检 → SELF-TEST OK
    python3 -B pcap_lib.py --write-demo /tmp/demo.pcap # 生成合成抓包文件
    python3 -B pcap_lib.py --dump /tmp/demo.pcap       # 逐包解析并打印
    python3 -B pcap_lib.py --dump /tmp/demo.pcap --filter 'tcp.flags.syn==1 and tcp.dstport==80'

⚠️ 合规：本文件的合成流量**全部是代码构造的假数据**，不含任何真实抓包，
   也不抓任何网卡（不联网、不需要 sudo）。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import socket
import struct
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Iterator, Optional

# ══════════════════════════════════════════════════════════════════════════
# 0. 常量表：这些数字必须背下来（面试常问，排错也全靠它）
# ══════════════════════════════════════════════════════════════════════════

# pcap 文件魔数。注意：魔数本身包含**字节序**信息！
#   写文件的一方按自己的字节序写 0xa1b2c3d4；
#   读文件的一方如果按小端读出来是 0xa1b2c3d4 → 文件是小端；
#   如果读出来是 0xd4c3b2a1 → 文件是大端（字节被交换了）。
#   这就是为什么同一个文件在不同架构上看不看得懂，取决于读的时候有没有判断。
PCAP_MAGIC_US = 0xA1B2C3D4      # 时间戳单位：微秒（最常见的 pcap）
PCAP_MAGIC_NS = 0xA1B23C4D      # 时间戳单位：纳秒（新版 tcpdump -j adapter_unsynced）
PCAPNG_MAGIC = 0x0A0D0D0A       # pcapng 的 Section Header Block 类型

# 链路类型（pcap 文件头里的 network 字段 / pcapng 的 IDB.linktype）
LINKTYPE_NULL = 0               # BSD loopback：包头 4 字节地址族
LINKTYPE_ETHERNET = 1           # 以太网（Linux 上抓 lo 也是这个）
LINKTYPE_RAW = 101              # 裸 IP，无链路层头
LINKTYPE_LINUX_SLL = 113        # Linux "cooked" 抓包（`any` 网卡)
LINKTYPE_IPV4 = 228
LINKTYPE_IPV6 = 229

# 以太网类型（EtherType）
ETHERTYPE_IPV4 = 0x0800
ETHERTYPE_ARP = 0x0806
ETHERTYPE_VLAN = 0x8100         # 802.1Q
ETHERTYPE_QINQ = 0x88A8         # 802.1ad（运营商 QinQ）
ETHERTYPE_IPV6 = 0x86DD

# IP 协议号（IP 头里的 proto 字段）
IPPROTO_ICMP = 1
IPPROTO_TCP = 6
IPPROTO_UDP = 17
IPPROTO_ICMPV6 = 58

IPPROTO_NAMES = {
    1: "ICMP", 2: "IGMP", 6: "TCP", 17: "UDP", 41: "IPv6", 47: "GRE",
    50: "ESP", 51: "AH", 58: "ICMPv6", 89: "OSPF", 132: "SCTP",
}

# TCP 标志位（第 13 字节的 8 个 bit，从高位到低位）
#   为什么按这个顺序？因为 Wireshark 显示顺序是 FIN,SYN,RST,PSH,ACK,URG,ECE,CWR
TCP_FLAG_BITS = [
    (0x01, "FIN"), (0x02, "SYN"), (0x04, "RST"), (0x08, "PSH"),
    (0x10, "ACK"), (0x20, "URG"), (0x40, "ECE"), (0x80, "CWR"),
]

# 应用层端口 → 协议名（只列教学常用的，真实项目用 tshark 的 dissector 表）
PORT_HINTS = {
    20: "FTP-DATA", 21: "FTP", 22: "SSH", 23: "TELNET", 25: "SMTP",
    53: "DNS", 67: "DHCP", 68: "DHCP", 69: "TFTP", 80: "HTTP",
    110: "POP3", 123: "NTP", 143: "IMAP", 161: "SNMP", 389: "LDAP",
    443: "TLS", 445: "SMB", 514: "SYSLOG", 587: "SMTP", 993: "IMAPS",
    995: "POP3S", 1433: "MSSQL", 1521: "ORACLE", 3306: "MySQL",
    3389: "RDP", 4444: "Metasploit 默认", 5432: "PostgreSQL",
    5900: "VNC", 6379: "Redis", 8080: "HTTP-alt", 8443: "HTTPS-alt",
    9200: "Elasticsearch", 27017: "MongoDB",
}

# ══════════════════════════════════════════════════════════════════════════
# 1. 校验和：16 位反码求和（ones' complement sum）
# ══════════════════════════════════════════════════════════════════════════
#
# 原理（必须理解，否则排不掉"checksum incorrect"这类问题）：
#   1) 把数据按 16 位一组看成大端整数，全部相加；
#   2) 32 位结果的高 16 位是"进位"，要**回卷**加到低 16 位上（可能卷多次）；
#   3) 最后取反码（~x & 0xFFFF）就是校验和；
#   4) 验证时：把含校验和字段的整段再算一次反码和，结果应等于 0xFFFF。
#
#   为什么用反码和而不是普通和？
#     · 反码和是**可交换、可结合**的：路由器改 TTL 只需要增量更新校验和，
#       不用重算整包（这是 IPv4 设计时的性能考虑）；
#     · 有"0 与 -0"的对称性，但这也带来一个坑：全 0 数据的校验和是 0xFFFF，
#       而"校验和字段为 0"在 UDP 里是**特殊含义**（表示不校验），见下文。


def ones_complement_sum(data: bytes, initial: int = 0) -> int:
    """计算 16 位反码和（未取反）。

    实现技巧：直接 int.from_bytes 成一个**巨大整数**再一次相加，
    比 for 循环每 2 字节加一次快得多（大整数加法是 C 实现的）。
    然后循环折叠进位，每次折叠位数减少 15 位，最多 3~4 轮就结束。
    """
    if len(data) & 1:                       # 奇数长度：末尾补一个 0 字节
        data = data + b"\x00"               # ⚠️ 踩坑：漏了这步，所有奇数载荷都算错
    total = int.from_bytes(data, "big") + initial
    while total >> 16:                      # 只要还有进位，就回卷
        total = (total & 0xFFFF) + (total >> 16)
    return total & 0xFFFF


def checksum(data: bytes, initial: int = 0) -> int:
    """反码和的补码（= 校验和字段该填的值）。"""
    return (~ones_complement_sum(data, initial)) & 0xFFFF


def ipv4_header_checksum(header: bytes) -> int:
    """IPv4 头校验和。调用前必须把 checksum 字段置 0。"""
    return checksum(header)


def verify_ipv4_checksum(header: bytes) -> bool:
    """验证 IPv4 头校验和是否正确。

    原理：正确校验和参与反码和运算后，整体结果必须是 0xFFFF
    （即再取反就是 0）。反过来，如果算出来是 0x8000 之外的其它值，
    说明这 20 字节在传输/构造过程中被改过。
    """
    return ones_complement_sum(header) == 0xFFFF


def pseudo_header_v4(src: str, dst: str, proto: int, length: int) -> bytes:
    """构造 TCP/UDP 校验和用的**伪首部**（pseudo-header）。

    伪首部只参与计算、**不会真的发出去**。它包含源/目的 IP，
    作用是：如果包被误投到别的 IP，接收端算出的校验和对不上 → 丢弃。
    这是"端到端校验"思想：防止"数据本身没错，但送到了错误的地方"。

    格式（共 12 字节）：
        源 IP(4) | 目的 IP(4) | 全 0(1) | 协议号(1) | L4 长度(2)
                                ↑ 这个 0 是为了 16 位对齐凑的字节，
                                  也是新手最容易写错的地方（常漏掉它）
    """
    return (socket.inet_aton(src) + socket.inet_aton(dst) +
            bytes([0, proto]) + struct.pack("!H", length))


def verify_l4_checksum(segment: bytes, src: str, dst: str, proto: int) -> bool:
    """验证 TCP/UDP 校验和（IPv4）。segment 必须包含完整的 L4 头+载荷。"""
    ph = pseudo_header_v4(src, dst, proto, len(segment))
    return ones_complement_sum(ph + segment) == 0xFFFF


# ══════════════════════════════════════════════════════════════════════════
# 2. 数据模型 + PCAP / PCAPNG 读写
# ══════════════════════════════════════════════════════════════════════════


@dataclass
class RawPacket:
    """一条抓包记录：**原始字节** + 元数据。此时还没解析任何协议。

    为什么要先有"原始字节"这一层？
      · dissector 可能抛异常（畸形包），但原始字节永远是对的 → 兜底
      · 解析很贵，按需解析（惰性）才能撑住大文件
      · pcap 写入/切割只需要字节，不需要解析
    """
    index: int                  # 包序号（从 1 开始，对应 Wireshark 的 No. 列）
    ts: float                   # 时间戳（Unix 秒，浮点）
    data: bytes                 # 链路层原始字节
    orig_len: int               # 线上真实长度（可能 > len(data)，因为被抓包端截断了）
    linktype: int = LINKTYPE_ETHERNET


# ── 2.1 经典 pcap 格式（libpcap，1970s 设计，至今未变）──────────────────
#
# 全局头（24 字节）：
#   magic(4) version_major(2) version_minor(2) thiszone(4)
#   sigfigs(4) snaplen(4) network(4)
# 每包头（16 字节）：
#   ts_sec(4) ts_usec(4) incl_len(4) orig_len(4)
# 然后紧跟 incl_len 字节的包数据。
# 注意：**没有任何"总包数"字段**，读文件只能一直读到 EOF（或读到不足 16 字节）。
#       这也是为什么 pcap 文件被截断时，"最后一个包"通常是残缺的。
#
# pcapng 完全不同：它是一串"块(block)"，每块 4 字节类型 + 4 字节长度 + 内容
#   + 4 字节重复长度。好处是能存多网卡、注释、纳秒时间、DNS 解析信息等。
#   Wireshark 默认保存格式就是 pcapng！（所以解析器必须能识别它）


def sniff_format(path: str) -> str:
    """只看前 4 字节判断文件格式。返回 'pcap' / 'pcapng' / 'unknown' / 'empty'。

    为什么要单独做这一步？
      · 用户给的文件常常是 Wireshark 存的 pcapng，用 pcap 解析器读会得到垃圾；
      · 提前判断并给出**明确报错**，比让用户对着一堆乱码猜要好得多。
    """
    try:
        with open(path, "rb") as f:
            head = f.read(4)
    except OSError as e:
        raise ValueError(f"无法打开文件: {path} ({e})") from e
    if len(head) < 4:
        return "empty"
    le = int.from_bytes(head, "little")
    be = int.from_bytes(head, "big")
    if le == PCAPNG_MAGIC or be == PCAPNG_MAGIC:
        return "pcapng"
    if le in (PCAP_MAGIC_US, PCAP_MAGIC_NS) or be in (PCAP_MAGIC_US, PCAP_MAGIC_NS):
        return "pcap"
    return "unknown"


def _pcap_endian(magic_le: int) -> tuple:
    """由「按小端读出来的魔数」推断 (struct 前缀, 时间戳精度)。

    这一步是 pcap 解析最容易翻车的地方：
      小端文件：按小端读魔数 == 0xa1b2c3d4
      大端文件：按小端读魔数 == 0xd4c3b2a1（字节被交换了）
    搞错了字节序，时间戳和长度会变成天文数字，然后 read() 直接吃掉整个文件。
    """
    if magic_le == PCAP_MAGIC_US:
        return "<", 1_000_000          # 微秒
    if magic_le == PCAP_MAGIC_NS:
        return "<", 1_000_000_000      # 纳秒
    if magic_le == 0xD4C3B2A1:
        return ">", 1_000_000
    if magic_le == 0x4D3CB2A1:
        return ">", 1_000_000_000
    raise ValueError(f"不是合法的 pcap 文件（魔数 0x{magic_le:08x}）")


def iter_pcap(path: str) -> Iterator[RawPacket]:
    """**流式**迭代经典 pcap：一次只持有一个包，内存恒定 O(1)。

    对比 rdpcap/全量读取：那种做法把整个文件读进内存，
    50MB 的 pcap 在 Python 里能膨胀到几百 MB（每个包一个对象）。
    生产环境处理大文件必须流式。
    """
    with open(path, "rb") as f:
        gh = f.read(24)
        if len(gh) < 24:
            raise ValueError("pcap 全局头不足 24 字节，文件已损坏或被截断")
        endian, ts_div = _pcap_endian(int.from_bytes(gh[0:4], "little"))
        # version_major/minor 用于格式演进，实践中 2.4 之外的极少见
        _ver_major, _ver_minor = struct.unpack(endian + "HH", gh[4:8])
        # thiszone 恒为 0（时区修正从来没用过，历史包袱）
        _thiszone, _sigfigs, snaplen, network = struct.unpack(endian + "iIII", gh[8:24])
        if snaplen == 0:
            snaplen = 65535                # 有些老工具写 0，容错一下
        index = 0
        while True:
            ph = f.read(16)
            if len(ph) < 16:
                break                      # 正常 EOF（或尾部不足一条记录）
            ts_sec, ts_frac, incl_len, orig_len = struct.unpack(endian + "IIII", ph)
            if incl_len > 262144:
                # 单包上限 256KB：明显是文件损坏或字节序判断错了，
                # 直接报错而不是傻傻地 read() 掉半个文件
                raise ValueError(f"第 {index+1} 条记录长度异常（{incl_len} 字节），文件可能损坏")
            data = f.read(incl_len)
            if len(data) < incl_len:
                # 抓包进程被 kill 时，最后一条记录常常是残缺的。
                # 工程选择：丢弃残包并正常结束，而不是抛异常让整次分析失败。
                break
            index += 1
            yield RawPacket(index=index, ts=ts_sec + ts_frac / ts_div,
                            data=data, orig_len=orig_len, linktype=network)


def build_pcap_bytes(packets: list, *, endian: str = "<",
                     snaplen: int = 65535, linktype: int = LINKTYPE_ETHERNET) -> bytes:
    """把 RawPacket 列表序列化成 pcap 字节串（默认小端，微秒）。"""
    out = bytearray()
    out += struct.pack(endian + "IHHiIII", PCAP_MAGIC_US, 2, 4, 0, 0, snaplen, linktype)
    for p in packets:
        sec = int(p.ts)
        usec = int(round((p.ts - sec) * 1_000_000))
        if usec >= 1_000_000:              # 浮点误差保护：59.9999999 → 进位
            sec += 1
            usec -= 1_000_000
        out += struct.pack(endian + "IIII", sec, usec, len(p.data), p.orig_len)
        out += p.data
    return bytes(out)


def write_pcap(path: str, packets: list, *, linktype: int = LINKTYPE_ETHERNET) -> int:
    """写经典 pcap 文件，返回写出的包数。"""
    blob = build_pcap_bytes(packets, linktype=linktype)
    with open(path, "wb") as f:
        f.write(blob)
    return len(packets)


# ── 2.2 pcapng（Wireshark 默认格式）───────────────────────────────────────
#
# 块结构：[类型(4) | 总长度(4) | 内容... | 总长度(4)]
#   注意：总长度字段**出现两次**（头一次、尾一次），且长度包含这 12 字节本身。
#   这是 pcapng 最反直觉的设计——好处是可以从后往前遍历文件。
#
# 三种最关键的块：
#   SHB (0x0A0D0D0A) Section Header：字节序魔数 0x1A2B3C4D + 版本 + 段长度
#   IDB (0x00000001) Interface Description：linktype + snaplen + 选项
#   EPB (0x00000006) Enhanced Packet：接口号 + 时间戳(高低 32 位) + 长度 + 数据
#
# 时间戳单位由 IDB 的 if_tsresol 选项决定（选项码 9，默认 6 = 微秒）。
#   "ts_high/ts_low 拼成 64 位整数" 这个设计是为了避免 2038 问题。


def tsresol_to_div(resol: int) -> float:
    """把 pcapng 的 if_tsresol 选项值解释成"每秒多少个时间单位"。

    ⚠️ 这是 pcapng 里最阴的一个坑：同一个字节，两种含义——
      · 最高位是 0 → 分辨率 = 10^-value  （所以 value=6 表示微秒，最常见）
      · 最高位是 1 → 分辨率 = 2^-value  （value=0x80|6 → 1/64 秒，二进制钟用）
    只按 2^value 解释会让时间戳精度掉到 15.625ms，
    表现为"时间戳看起来差不多但怎么都对不齐"——本库自检就抓到过这个问题。
    """
    if resol & 0x80:
        return float(2 ** (resol & 0x7F))
    return float(10 ** resol)


def _pcapng_block(btype: int, body: bytes) -> bytes:
    """拼一个 pcapng 块（自动 4 字节对齐 + 首尾写两次长度）。"""
    body = body + b"\x00" * ((-len(body)) % 4)      # 内容必须 4 字节对齐
    total = 12 + len(body)
    return struct.pack("<II", btype, total) + body + struct.pack("<I", total)


def build_pcapng_bytes(packets: list, *, linktype: int = LINKTYPE_ETHERNET,
                       snaplen: int = 65535, ts_resol: int = 6) -> bytes:
    """把包序列化成 pcapng（用于测试我们自己的 pcapng 读取器）。

    ts_resol 是 2 的幂指数：6 → 微秒，9 → 纳秒。
    """
    shb = _pcapng_block(0x0A0D0D0A,
                        struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1))
    # IDB 选项：if_tsresol（码 9，长度 1）；选项以 code=0,len=0 结束
    idb_opts = struct.pack("<HHB", 9, 1, ts_resol) + struct.pack("<HH", 0, 0)
    idb = _pcapng_block(0x00000001,
                        struct.pack("<HHI", linktype, 0, snaplen) + idb_opts)
    out = bytearray(shb + idb)
    scale = tsresol_to_div(ts_resol)
    for p in packets:
        ticks = int(round(p.ts * scale))
        hi, lo = (ticks >> 32) & 0xFFFFFFFF, ticks & 0xFFFFFFFF
        body = (struct.pack("<IIIII", 0, hi, lo, len(p.data), p.orig_len) +
                p.data + b"\x00" * ((-len(p.data)) % 4) + struct.pack("<HH", 0, 0))
        out += _pcapng_block(0x00000006, body)
    return bytes(out)


def iter_pcapng(path: str) -> Iterator[RawPacket]:
    """流式解析 pcapng：按块遍历，只取 EPB（增强包块）。

    支持的块：SHB（定字节序）、IDB（定 linktype 与时间戳精度）、EPB、SPB（简单包块）。
    其它块（NRB/ISB/自定义）直接跳过——**未知块必须能跳过**，
    否则遇到新版本 Wireshark 加的新块就整文件读不了了。
    """
    with open(path, "rb") as f:
        index = 0
        linktypes: dict = {}        # 接口号 → (linktype, ts_div)
        while True:
            head = f.read(8)
            if len(head) < 8:
                break
            btype, blen = struct.unpack("<II", head)
            if blen < 12:
                raise ValueError(f"pcapng 块长度非法（{blen}），文件损坏")
            body = f.read(blen - 12)
            tail = f.read(4)
            if len(body) < blen - 12 or len(tail) < 4:
                break
            if btype == 0x0A0D0D0A:                     # SHB
                bom = struct.unpack("<I", body[0:4])[0]
                if bom != 0x1A2B3C4D:
                    raise ValueError("pcapng 字节序魔数不对（可能是大端 pcapng，本工具暂不支持）")
                linktypes.clear()
            elif btype == 0x00000001:                   # IDB
                lt, _res, _snaplen = struct.unpack("<HHI", body[0:8])
                ts_resol = 6
                off = 8
                while off + 4 <= len(body):             # 遍历选项
                    code, olen = struct.unpack("<HH", body[off:off + 4])
                    off += 4
                    if code == 0:
                        break
                    val = body[off:off + olen]
                    off += olen + ((-olen) % 4)
                    if code == 9 and val:
                        ts_resol = val[0]
                # 时间戳单位由 if_tsresol 决定（默认 6 = 微秒），见 tsresol_to_div
                linktypes[len(linktypes)] = (lt, tsresol_to_div(ts_resol))
            elif btype == 0x00000006:                   # EPB
                iface, hi, lo, caplen, origlen = struct.unpack("<IIIII", body[0:20])
                data = body[20:20 + caplen]
                _lt, ts_div = linktypes.get(iface, (LINKTYPE_ETHERNET, 1_000_000))
                index += 1
                yield RawPacket(index=index, ts=((hi << 32) | lo) / ts_div,
                                data=data, orig_len=origlen, linktype=_lt)
            elif btype == 0x00000003:                   # SPB（无时间戳）
                origlen = struct.unpack("<I", body[0:4])[0]
                data = body[4:4 + min(origlen, len(body) - 4)]
                index += 1
                yield RawPacket(index=index, ts=0.0, data=data,
                                orig_len=origlen, linktype=LINKTYPE_ETHERNET)
            # 其它块：跳过（未知块必须能跳过，见函数注释）


def iter_capture(path: str) -> Iterator[RawPacket]:
    """统一入口：自动识别 pcap / pcapng 并流式迭代。

    这是所有上层脚本（01/02/03）唯一需要调用的读取函数——
    把"格式判断"这个脏活收在一处，上层代码只关心包。
    """
    fmt = sniff_format(path)
    if fmt == "pcap":
        yield from iter_pcap(path)
    elif fmt == "pcapng":
        yield from iter_pcapng(path)
    elif fmt == "empty":
        raise ValueError(f"文件为空: {path}")
    else:
        raise ValueError(f"无法识别的抓包格式（既不是 pcap 也不是 pcapng）: {path}")


# ══════════════════════════════════════════════════════════════════════════
# 3. 解析器（dissector）：从字节流到"协议字段字典"
# ══════════════════════════════════════════════════════════════════════════
#
# 设计原则（这是 Wireshark 的核心思想，必须理解）：
#   · **每一层只负责剥掉自己的头，把载荷交给下一层**（和 Scapy 的 `/` 分层对应）；
#   · 解析结果用**普通字典**承载，字段名尽量对齐 Wireshark 的显示过滤器名
#     （ip.src / tcp.dstport / http.request.uri …），这样过滤表达式两边通用；
#   · 任何一层解析失败都**返回 None**而不是抛异常——真实抓包里
#     畸形包、截断包、未知协议比比皆是，一个坏包不能毁掉整次分析。


def mac_str(b: bytes) -> str:
    """字节 → MAC 字符串（小写冒号分隔，和 Wireshark 一致）。"""
    return ":".join(f"{x:02x}" for x in b)


def ipv4_str(b: bytes) -> str:
    return socket.inet_ntop(socket.AF_INET, b)


def ipv6_str(b: bytes) -> str:
    return socket.inet_ntop(socket.AF_INET6, b)


def hexdump(data: bytes, *, prefix: str = "    ", width: int = 16,
            limit: Optional[int] = None) -> str:
    """标准十六进制 dump（Wireshark 左下角那种）。

    limit 用于只打印前 N 字节——抓包里经常有超长载荷，
    全打印会把终端刷爆（也是"分析脚本不要无脑 print 原始字节"的原因）。
    """
    if limit is not None:
        data = data[:limit]
    lines = []
    for off in range(0, len(data), width):
        chunk = data[off:off + width]
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        asciipart = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{prefix}{off:04x}  {hexpart:<{width*3}}  {asciipart}")
    if limit is not None and len(data) == limit:
        lines.append(f"{prefix}... (已截断，只显示前 {limit} 字节)")
    return "\n".join(lines)


# ── 3.1 链路层 ────────────────────────────────────────────────────────────

def dissect_ethernet(data: bytes) -> Optional[dict]:
    """以太网 II 帧：目的 MAC(6) + 源 MAC(6) + 类型(2) + 载荷。

    两个必须处理的坑：
      ① **VLAN 标签**：type=0x8100 时，类型字段后面还有 4 字节 TCI
         （PCP 3 位 + DEI 1 位 + VLAN ID 12 位）。漏了它，
         后面所有协议解析全错位（这是"包看起来认识但字段全是乱的"的经典原因）。
      ② 802.1ad QinQ：两层 VLAN 标签，要循环剥。
    """
    if len(data) < 14:
        return None
    dst, src, etype = mac_str(data[0:6]), mac_str(data[6:12]), int.from_bytes(data[12:14], "big")
    off = 14
    vlans = []
    # 循环剥 VLAN 标签：QinQ 时会有两层（运营商网络常见）
    while etype in (ETHERTYPE_VLAN, ETHERTYPE_QINQ) and len(data) >= off + 4:
        tci = int.from_bytes(data[off:off + 2], "big")
        vlans.append({
            "pcp": tci >> 13,                    # 优先级（QoS），VoIP 常设 5/6
            "dei": (tci >> 12) & 1,              # 丢弃资格位
            "vid": tci & 0x0FFF,                 # VLAN ID
        })
        etype = int.from_bytes(data[off + 2:off + 4], "big")
        off += 4
    return {"dst": dst, "src": src, "ethertype": etype,
            "vlans": vlans, "header_len": off, "payload": data[off:]}


def dissect_arp(data: bytes) -> Optional[dict]:
    """ARP：IP → MAC 的解析协议，工作在链路层，**没有 IP 头**。

    字段：硬件类型(2) 协议类型(2) hlen(1) plen(1) op(2)
          sender_mac(6) sender_ip(4) target_mac(6) target_ip(4)

    op: 1=who-has(请求) 2=is-at(应答)，其它值（3=RARP 等）很少见。
    安全视角：ARP 无任何认证 → 谁都能应答"我是网关"（ARP 欺骗）。
    检测特征：**同一个 IP 被两个不同 MAC 宣告**（见 03 的异常检测）。
    """
    if len(data) < 28:
        return None
    htype, ptype, hlen, plen, op = struct.unpack("!HHBBH", data[0:8])
    if hlen != 6 or plen != 4:                 # 本工具只处理以太网+IPv4 的 ARP
        return None
    return {
        "op": op,
        "op_name": {1: "who-has", 2: "is-at", 3: "RARP-req", 4: "RARP-rep"}.get(op, str(op)),
        "sender_mac": mac_str(data[8:14]),
        "sender_ip": ipv4_str(data[14:18]),
        "target_mac": mac_str(data[18:24]),
        "target_ip": ipv4_str(data[24:28]),
        "payload": b"",
    }


# ── 3.2 网络层 ────────────────────────────────────────────────────────────

def dissect_ipv4(data: bytes) -> Optional[dict]:
    """IPv4 头解析 + **校验和验证**。

    头布局（20 字节固定 + 可选选项）：
      0  ver/ihl | 1 tos | 2-3 total_len | 4-5 id | 6-7 flags/frag
      8 ttl | 9 proto | 10-11 checksum | 12-15 src | 16-19 dst | 20+ options

    必须理解的 4 个字段：
      · ihl：头长度，**单位是 4 字节**（不是字节！ihl=5 → 20 字节）。
             忘了乘 4 是最经典的分片/选项解析错误。
      · total_len：整个 IP 包（头+载荷）的长度。
             坑：以太网帧有最小 46 字节载荷限制，小包会被**填充(padding)**，
             所以**不能**用 len(以太网载荷) 当 IP 包长度，必须以 total_len 为准，
             否则你会在 DNS/ARP 后面看到莫名其妙的填充字节。
      · flags/frag：MF(还有分片) / DF(禁止分片) / 13 位偏移（**单位 8 字节**）。
             frag_offset != 0 或 MF=1 → 这是分片包，传输层头可能不存在，
             直接按 TCP 解析会得到垃圾（分片是躲 IDS 的老手段）。
      · ttl：每过一个路由器减 1，到 0 回 ICMP Time Exceeded。
    """
    if len(data) < 20:
        return None
    ver_ihl = data[0]
    version, ihl_words = ver_ihl >> 4, ver_ihl & 0x0F
    if version != 4 or ihl_words < 5:
        return None
    ihl = ihl_words * 4                              # ⚠️ 单位是 4 字节，必须乘 4
    if len(data) < ihl:
        return None
    total_len = int.from_bytes(data[2:4], "big")
    ident = int.from_bytes(data[4:6], "big")
    flags_frag = int.from_bytes(data[6:8], "big")
    ttl, proto = data[8], data[9]
    cksum = int.from_bytes(data[10:12], "big")
    src, dst = ipv4_str(data[12:16]), ipv4_str(data[16:20])
    # 载荷以 total_len 为准（见上面"填充"的说明）；total_len 异常时退回实际长度
    end = total_len if ihl <= total_len <= len(data) else len(data)
    header = data[:ihl]
    return {
        "version": version,
        "header_len": ihl,
        "total_len": total_len,
        "id": ident,
        "df": bool(flags_frag & 0x4000),            # Don't Fragment
        "mf": bool(flags_frag & 0x2000),            # More Fragments
        "frag_offset": (flags_frag & 0x1FFF) * 8,   # ⚠️ 单位 8 字节，乘 8 才是字节偏移
        "ttl": ttl,
        "proto": proto,
        "proto_name": IPPROTO_NAMES.get(proto, f"IP-{proto}"),
        "checksum": cksum,
        # 校验和验证：pyshark 默认**不做**这件事，这是本库的增值点
        "checksum_ok": verify_ipv4_checksum(header),
        "options": header[20:ihl],
        "src": src,
        "dst": dst,
        "payload": data[ihl:end],
    }


def dissect_ipv6(data: bytes) -> Optional[dict]:
    """IPv6 固定头（40 字节）+ 基础扩展头跳过。

    与 IPv4 的三个关键区别（面试必问）：
      ① 头长度固定 40 字节，没有 ihl/checksum 字段
         → 校验和交给上层（TCP/UDP/ICMPv6 用伪首部，且**强制**校验）；
      ② 用**扩展头链**(next_header)替代 IPv4 的 options；
         常见链：Hop-by-Hop(0) → Routing(43) → Fragment(44) → TCP(6)
         → 扩展头链是"IPv6 躲避 IDS"的常见手法，本函数只做基础跳过；
      ③ 地址 128 位，格式用 socket.inet_ntop 标准化（:: 压缩）。
    """
    if len(data) < 40:
        return None
    if data[0] >> 4 != 6:
        return None
    payload_len = int.from_bytes(data[4:6], "big")
    next_hdr, hop_limit = data[6], data[7]
    src, dst = ipv6_str(data[8:24]), ipv6_str(data[24:40])
    off = 40
    ext_headers = []
    # 只跳过最常见的两种扩展头（Hop-by-Hop / Routing / Fragment），避免无限循环
    for _ in range(4):
        if next_hdr in (0, 43, 60):          # 长度 = (hdr_ext_len + 1) * 8 字节
            if len(data) < off + 8:
                break
            nh = data[off]
            ext_len = (data[off + 1] + 1) * 8
            ext_headers.append({"type": next_hdr, "len": ext_len})
            next_hdr, off = nh, off + ext_len
        elif next_hdr == 44:                 # Fragment 头固定 8 字节
            if len(data) < off + 8:
                break
            nh = data[off]
            ext_headers.append({"type": 44, "len": 8})
            next_hdr, off = nh, off + 8
        else:
            break
    end = off + payload_len if off + payload_len <= len(data) else len(data)
    return {
        "version": 6, "payload_len": payload_len, "next_header": next_hdr,
        "hop_limit": hop_limit, "src": src, "dst": dst,
        "ext_headers": ext_headers,
        "proto": next_hdr,
        "proto_name": IPPROTO_NAMES.get(next_hdr, f"IP-{next_hdr}"),
        "checksum_ok": None,                 # IPv6 无头校验和（见注释①）
        "payload": data[off:end],
    }


# ── 3.3 传输层 ────────────────────────────────────────────────────────────

def _parse_tcp_options(data: bytes) -> list:
    """解析 TCP 选项（长度是可变的，必须按 kind 逐项走）。

    为什么关心选项？**MSS / 窗口缩放 这些选项决定了性能**，
    也是"指纹识别"的重要素材（不同 OS 的选项组合不一样）：
        · MSS(2)：最大段长度，通常是 MTU-40（以太网 1460）
        · SAckOK(4)：选择性确认，长肥管道必备
        · TS(8)：时间戳，用于 RTT 计算与 PAWS 防重放
        · WScale(3)：窗口缩放因子，把 16 位窗口扩展到最多 1GB
    坑：kind=0(EOL) 结束，kind=1(NOP) 只有 1 字节无长度字段
        —— 把 NOP 当"有长度字段"解析，后面全错位。
    """
    opts = []
    i = 0
    while i < len(data):
        kind = data[i]
        if kind == 0:                        # EOL
            break
        if kind == 1:                        # NOP（只占 1 字节，没有长度字段）
            opts.append({"kind": 1, "name": "NOP", "value": None})
            i += 1
            continue
        if i + 1 >= len(data):
            break
        olen = data[i + 1]
        if olen < 2 or i + olen > len(data):
            break
        val = data[i + 2:i + olen]
        name = {2: "MSS", 3: "WScale", 4: "SAckOK", 5: "SAck", 8: "Timestamps",
                28: "UTO"}.get(kind, f"opt-{kind}")
        if kind == 2 and len(val) == 2:
            val = int.from_bytes(val, "big")
        elif kind == 3 and len(val) == 1:
            val = val[0]
        opts.append({"kind": kind, "name": name, "value": val})
        i += olen
    return opts


def dissect_tcp(data: bytes, ip_src: str, ip_dst: str, *, verify: bool = True) -> Optional[dict]:
    """TCP 头解析 + 校验和验证（需要 IP 地址构造伪首部）。

    头布局：sport(2) dport(2) seq(4) ack(4) data_offset(4bit)+reserved(4bit)
            flags(8bit 其实是 9 位，含 NS) window(2) checksum(2) urgptr(2) options

    必须理解的 3 件事：
      ① data_offset 单位是 **4 字节**（同 IPv4 的 ihl 坑）；
      ② flags 显示顺序：FIN,SYN,RST,PSH,ACK,URG,ECE,CWR。
         注意 SYN 占 1 个序号，FIN 也占 1 个 → 这就是为什么
         "带数据的 SYN"和"纯 SYN"在连接跟踪里要区别对待；
      ③ 校验和覆盖范围 = 伪首部 + TCP 头 + 载荷。**只算头是错的**，
         而"改完载荷忘了重算校验和"是抓包时最常见的排查项。
    """
    if len(data) < 20:
        return None
    sport, dport = struct.unpack("!HH", data[0:4])
    seq, ack = struct.unpack("!II", data[4:12])
    data_off = (data[12] >> 4) * 4                    # ⚠️ 单位 4 字节
    if data_off < 20 or data_off > len(data):
        return None
    flags_byte = data[13]
    names = [name for bit, name in TCP_FLAG_BITS if flags_byte & bit]
    window = int.from_bytes(data[14:16], "big")
    cksum = int.from_bytes(data[16:18], "big")
    urgptr = int.from_bytes(data[18:20], "big")
    payload = data[data_off:]
    ok = verify_l4_checksum(data, ip_src, ip_dst, IPPROTO_TCP) if verify else None
    return {
        "sport": sport, "dport": dport,
        "seq": seq, "ack": ack,
        "data_offset": data_off,
        "flags_raw": flags_byte,
        "flags": ",".join(names) if names else "NONE",
        "flag_names": names,
        "syn": bool(flags_byte & 0x02), "ack_flag": bool(flags_byte & 0x10),
        "fin": bool(flags_byte & 0x01), "rst": bool(flags_byte & 0x04),
        "psh": bool(flags_byte & 0x08), "urg": bool(flags_byte & 0x20),
        "window": window,
        "checksum": cksum,
        "checksum_ok": ok,
        "urgptr": urgptr,
        "options": _parse_tcp_options(data[20:data_off]),
        "header_len": data_off,
        "payload": payload,
        "payload_len": len(payload),
    }


def dissect_udp(data: bytes, ip_src: str, ip_dst: str, *, verify: bool = True) -> Optional[dict]:
    """UDP 头（固定 8 字节）+ 校验和验证。

    坑（UDP 独有，务必记住）：
      · UDP 头里的 length 字段包含头本身（= 8 + 载荷长度）；
      · UDP 校验和**可以为 0**，含义是"发送方没算校验和"（IPv4 允许，IPv6 禁止）。
        所以验证时发现 cksum==0 要判定为"未提供"，而不是"错误"——
        很多工具在这里误报"UDP checksum incorrect"。
      · UDP 载荷是**数据报**，不像 TCP 是字节流，边界天然保留。
    """
    if len(data) < 8:
        return None
    sport, dport, length, cksum = struct.unpack("!HHHH", data[0:8])
    payload = data[8:]
    if cksum == 0:
        ok = None                                     # 未提供校验和（合法）
    elif verify:
        ok = verify_l4_checksum(data, ip_src, ip_dst, IPPROTO_UDP)
    else:
        ok = None
    return {"sport": sport, "dport": dport, "length": length, "checksum": cksum,
            "checksum_ok": ok, "payload": payload, "payload_len": len(payload),
            "header_len": 8}


def dissect_icmp(data: bytes) -> Optional[dict]:
    """ICMP（IPv4）：type(1) code(1) checksum(2) + 类型相关字段。

    注意：ICMP 校验和**没有伪首部**（和 TCP/UDP 不同），
    直接对整个 ICMP 消息做反码和即可。这个差异要背下来。

    type 速查：0=Echo Reply 3=Dest Unreachable 5=Redirect
               8=Echo Request 11=Time Exceeded
    """
    if len(data) < 4:
        return None
    itype, code, cksum = struct.unpack("!BBH", data[0:4])
    names = {0: "Echo Reply", 3: "Destination Unreachable", 5: "Redirect",
             8: "Echo Request", 11: "Time Exceeded", 12: "Parameter Problem",
             13: "Timestamp Request", 14: "Timestamp Reply"}
    return {
        "type": itype, "code": code, "checksum": cksum,
        "type_name": names.get(itype, str(itype)),
        # ICMP 校验和：无伪首部，整体验一次即可
        "checksum_ok": ones_complement_sum(data) == 0xFFFF,
        "id": int.from_bytes(data[4:6], "big") if len(data) >= 6 else None,
        "seq": int.from_bytes(data[6:8], "big") if len(data) >= 8 else None,
        "payload": data[8:] if len(data) > 8 else b"",
    }


# ── 3.4 应用层：DNS ───────────────────────────────────────────────────────

def _dns_name(data: bytes, off: int, *, depth: int = 0) -> tuple:
    """解析 DNS 域名（label 序列），返回 (name, 结束后的偏移)。

    DNS 名字的三种形态（这是 DNS 解析最容易写错的地方）：
      ① 普通 label：长度字节 + 内容，直到 0x00 结束 → "www""example""com"0
      ② **压缩指针**：高 2 位是 11 → 后 14 位是"从报文开头算的偏移"，
         指向别处已经出现过的名字。这是 DNS 报文能很小的原因。
      ③ 根域：单个 0x00 表示 ""（根）
    坑：压缩指针可以**指向另一个指针**（理论上能成环），
        所以必须限制递归深度，否则恶意报文能让解析器栈溢出（DoS）。
    """
    labels = []
    end = None
    while True:
        if off >= len(data) or depth > 20:
            break
        length = data[off]
        if length == 0:
            off += 1
            if end is None:
                end = off
            break
        if length & 0xC0 == 0xC0:                  # 压缩指针
            if off + 1 >= len(data):
                break
            ptr = ((length & 0x3F) << 8) | data[off + 1]
            if end is None:
                end = off + 2                      # 指针占 2 字节，名字在此结束
            sub, _ = _dns_name(data, ptr, depth=depth + 1)
            if sub:
                labels.append(sub)
            break
        else:
            off += 1
            labels.append(data[off:off + length].decode("ascii", "replace"))
            off += length
    return ".".join(labels), (end if end is not None else off)


def dissect_dns(data: bytes) -> Optional[dict]:
    """DNS 报文解析（UDP/TCP 载荷）。

    头（12 字节）：id(2) flags(2) qdcount(2) ancount(2) nscount(2) arcount(2)
      flags 位：QR(1) Opcode(4) AA(1) TC(1) RD(1) RA(1) Z(3) RCODE(4)
        QR=0 查询 / QR=1 应答；RCODE=3 表示 NXDOMAIN
    """
    if len(data) < 12:
        return None
    txid, flags = struct.unpack("!HH", data[0:4])
    qd, an, ns, ar = struct.unpack("!HHHH", data[4:12])
    out = {
        "id": txid,
        "response": bool(flags & 0x8000),
        "opcode": (flags >> 11) & 0xF,
        "aa": bool(flags & 0x0400), "tc": bool(flags & 0x0200),
        "rd": bool(flags & 0x0100), "ra": bool(flags & 0x0080),
        "rcode": flags & 0xF,
        "counts": {"questions": qd, "answers": an, "authority": ns, "additional": ar},
        "questions": [], "answers": [],
    }
    off = 12
    for _ in range(min(qd, 32)):                  # 上限保护：畸形报文可能写 qd=65535
        name, off = _dns_name(data, off)
        if off + 4 > len(data):
            break
        qtype, qclass = struct.unpack("!HH", data[off:off + 4])
        off += 4
        out["questions"].append({
            "name": name, "type": qtype, "class": qclass,
            "type_name": {1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR",
                          15: "MX", 16: "TXT", 28: "AAAA", 33: "SRV",
                          255: "ANY"}.get(qtype, str(qtype)),
        })
    for _ in range(min(an, 64)):
        name, off = _dns_name(data, off)
        if off + 10 > len(data):
            break
        rtype, rclass, ttl, rdlen = struct.unpack("!HHIH", data[off:off + 10])
        off += 10
        rdata = data[off:off + rdlen]
        off += rdlen
        value = None
        if rtype == 1 and rdlen == 4:
            value = ipv4_str(rdata)
        elif rtype == 28 and rdlen == 16:
            value = ipv6_str(rdata)
        elif rtype in (5, 2, 12):
            value, _ = _dns_name(data, off - rdlen)
        elif rtype == 16:
            value = rdata[1:].decode("ascii", "replace") if rdata else ""
        out["answers"].append({"name": name, "type": rtype, "ttl": ttl,
                               "rdlength": rdlen, "value": value})
    out["qry_name"] = out["questions"][0]["name"] if out["questions"] else ""
    out["answers_a"] = [a["value"] for a in out["answers"] if a["type"] == 1 and a["value"]]
    return out


# ── 3.5 应用层：HTTP（明文）───────────────────────────────────────────────
#
# 为什么 HTTP 分析还这么重要？因为：
#   · 大量内网系统仍是 HTTP（明文），抓包能直接看到凭据/token（本日要检测的）；
#   · HTTPS 时代 HTTP 分析的价值转向"元数据"：Host、User-Agent、URI 结构、
#     响应码、Content-Type —— 这些即使加密看不到，也能从 TLS SNI/证书里拿到影子。
#   · 更现实的原因：**恶意软件回连**（C2）常用裸 HTTP，特征就是固定 URI + 规律心跳。

# 会被"脱敏处理"的敏感头（只做检测和掩码，绝不原样打印）
SENSITIVE_HEADERS = {
    "authorization", "proxy-authorization", "cookie", "set-cookie",
    "x-api-key", "x-auth-token", "x-csrf-token", "api-key",
}
# 请求体/URI 里常见的凭据参数名（弱口令爆破、表单登录的典型特征）
SENSITIVE_PARAM_HINTS = ("password", "passwd", "pwd", "secret", "token",
                         "api_key", "apikey", "access_key", "private_key")


def mask_secret(s: str) -> str:
    """把敏感值变成"可核对但不可还原"的形式：保留首尾 2 字符 + 长度。

    为什么不用哈希？因为分析人员需要**肉眼比对**"是不是同一个密码"，
    也需要知道长度（判断是否是弱口令线索）；哈希长度固定，看不出这些。
    为什么保留首尾？因为这已经足够定位"是不是同一个值"，
    同时又不足以还原（配合"绝不外发"的流程）。
    """
    if len(s) <= 4:
        return "*" * len(s) + f"(len={len(s)})"
    return f"{s[:2]}{'*' * (len(s) - 4)}{s[-2:]}(len={len(s)})"


def fingerprint(s: str) -> str:
    """值的指纹（sha256 前 12 位十六进制）。

    用途：在**不外发原文**的前提下，判定"两次出现的是不是同一个密码"。
    这是日志/流量分析里"可关联但不泄露"的标准手法。
    """
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:12]


HTTP_METHODS = (b"GET", b"POST", b"PUT", b"DELETE", b"HEAD", b"OPTIONS",
                b"PATCH", b"TRACE", b"CONNECT")


def dissect_http(data: bytes) -> Optional[dict]:
    """解析 HTTP/1.x 明文报文（请求或响应）。

    判定依据：以 HTTP/1. → 响应；以方法名开头 → 请求。
    注意 HTTP/2 是二进制帧（不是文本），本函数**不处理**——
    这也是"抓包里看不到 http 层"的常见原因（h2 要按 http2 dissector 解）。
    """
    if not data:
        return None
    head, sep, body = data.partition(b"\r\n\r\n")
    if not sep:
        head, body = data, b""                     # 没有空行：可能只有头
    if b"\r\n" not in head and b"\n" not in head:
        return None
    lines = head.replace(b"\r\n", b"\n").split(b"\n")
    first = lines[0].strip()
    out: dict = {"is_request": None, "headers": {}, "headers_raw": {}, "body_len": len(body)}
    if first.startswith(b"HTTP/"):
        parts = first.split(b" ", 2)
        out["is_request"] = False
        out["version"] = parts[0].decode("ascii", "replace")
        out["response_code"] = parts[1].decode("ascii", "replace") if len(parts) > 1 else ""
        out["response_phrase"] = parts[2].decode("utf-8", "replace") if len(parts) > 2 else ""
    elif any(first.startswith(m) for m in HTTP_METHODS):
        parts = first.split(b" ", 2)
        out["is_request"] = True
        out["method"] = parts[0].decode("ascii", "replace")
        out["uri"] = parts[1].decode("utf-8", "replace") if len(parts) > 1 else ""
        out["version"] = parts[2].decode("ascii", "replace") if len(parts) > 2 else "HTTP/1.0"
    else:
        return None                                # 不是 HTTP（可能是 TLS 记录层等）
    for line in lines[1:]:
        if not line.strip():
            continue
        k, s, v = line.partition(b":")
        if not s:
            continue
        key = k.decode("latin-1", "replace").strip().lower()
        val = v.decode("latin-1", "replace").strip()
        out["headers"][key] = val
        out["headers_raw"].setdefault(key, []).append(val)
    out["host"] = out["headers"].get("host", "")
    out["user_agent"] = out["headers"].get("user-agent", "")
    # ── 敏感信息检测（**只出指纹与掩码，绝不回传原文**）──
    sensitive = []
    # ⚠️ 用 sorted() 而不是直接遍历集合：Python 的 set 迭代顺序受哈希随机化影响，
    # 同一份抓包在不同进程里可能给出不同的"命中顺序" —— 那样输出就不可复现，
    # 也没法写进 README 当"预期输出"。**任何要展示的结果都必须先排序**。
    for h in sorted(SENSITIVE_HEADERS):
        if h in out["headers"]:
            sensitive.append({"where": f"header:{h}", "masked": mask_secret(out["headers"][h]),
                              "fp": fingerprint(out["headers"][h])})
    uri = out.get("uri", "")
    qs = uri.partition("?")[2]
    for pair in qs.split("&") if qs else []:
        k, s, v = pair.partition("=")
        if s and any(h in k.lower() for h in SENSITIVE_PARAM_HINTS):
            sensitive.append({"where": f"query:{k}", "masked": mask_secret(v),
                              "fp": fingerprint(v)})
    low_body = body[:4096].lower()
    for hint in SENSITIVE_PARAM_HINTS:
        idx = low_body.find(b"name=\"" + hint.encode()) if low_body else -1
        if idx >= 0 or (low_body and (hint.encode() + b"=") in low_body):
            sensitive.append({"where": "body:form", "masked": "(省略)",
                              "fp": fingerprint(body[:256].decode("latin-1", "replace"))})
            break
    out["sensitive"] = sensitive
    out["body"] = body
    return out


# ══════════════════════════════════════════════════════════════════════════
# 4. 顶层解析：原始字节 → 完整分层字典
# ══════════════════════════════════════════════════════════════════════════

def dissect_packet(raw: RawPacket) -> dict:
    """把一条 RawPacket 解析成分层字典（等价于 pyshark 的 Packet 对象）。

    返回字典的键与 Wireshark 层名对应：ether / vlan / arp / ip / ipv6 /
    tcp / udp / icmp / dns / http，外加 frame 级元数据。
    **任何一层解析失败都只是少一个键，不会抛异常** —— 真实抓包里
    "有一个坏包"是常态，分析脚本必须能继续跑完。
    """
    pkt = {
        "number": raw.index, "ts": raw.ts, "caplen": len(raw.data),
        "origlen": raw.orig_len, "linktype": raw.linktype, "layers": [],
    }
    ethertype: Optional[int] = None
    payload = raw.data

    # ── 链路层：不同 linktype 的头长度不同，这是"换了抓包方式就解析不了"的根因 ──
    if raw.linktype == LINKTYPE_ETHERNET:
        eth = dissect_ethernet(payload)
        if eth:
            pkt["ether"] = eth
            ethertype, payload = eth["ethertype"], eth["payload"]
    elif raw.linktype == LINKTYPE_NULL:
        # BSD loopback：前 4 字节是地址族（2=IPv4，小端在前）
        if len(payload) >= 4:
            fam = int.from_bytes(payload[:4], "little")
            ethertype = {2: ETHERTYPE_IPV4, 24: ETHERTYPE_IPV6,
                         28: ETHERTYPE_IPV6, 30: ETHERTYPE_IPV6}.get(fam)
            payload = payload[4:]
    elif raw.linktype in (LINKTYPE_RAW, LINKTYPE_IPV4):
        ethertype = ETHERTYPE_IPV4
    elif raw.linktype == LINKTYPE_IPV6:
        ethertype = ETHERTYPE_IPV6
    elif raw.linktype == LINKTYPE_LINUX_SLL:
        # Linux "cooked" 头 16 字节：pkt_type(2) arphrd(2) addrlen(2) addr(8) proto(2)
        if len(payload) >= 16:
            ethertype = int.from_bytes(payload[14:16], "big")
            payload = payload[16:]
    if ethertype is None and payload:
        # 兜底：靠首字节的版本号猜（4 → IPv4，6 → IPv6）
        ver = payload[0] >> 4
        if ver == 4:
            ethertype = ETHERTYPE_IPV4
        elif ver == 6:
            ethertype = ETHERTYPE_IPV6

    # ── 网络层 ──
    ip = None
    if ethertype == ETHERTYPE_IPV4:
        ip = dissect_ipv4(payload)
        if ip:
            pkt["ip"] = ip
            payload = ip["payload"]
    elif ethertype == ETHERTYPE_IPV6:
        ip = dissect_ipv6(payload)
        if ip:
            pkt["ipv6"] = ip
            payload = ip["payload"]
    elif ethertype == ETHERTYPE_ARP:
        arp = dissect_arp(payload)
        if arp:
            pkt["arp"] = arp
        payload = b""

    # ── 传输层 ──
    # 分片包的处理：只有第一个分片（frag_offset==0）才含传输层头，
    # 后续分片的"载荷"其实是上层数据的中间片段，按 TCP 解析会得到垃圾。
    fragmented_tail = bool(ip and ip.get("frag_offset", 0) != 0)
    src_ip = ip["src"] if ip else ""
    dst_ip = ip["dst"] if ip else ""
    app_payload = b""
    if ip and not fragmented_tail:
        proto = ip.get("proto")
        if proto == IPPROTO_TCP:
            tcp = dissect_tcp(payload, src_ip, dst_ip)
            if tcp:
                pkt["tcp"] = tcp
                app_payload = tcp["payload"]
        elif proto == IPPROTO_UDP:
            udp = dissect_udp(payload, src_ip, dst_ip)
            if udp:
                pkt["udp"] = udp
                app_payload = udp["payload"]
        elif proto == IPPROTO_ICMP:
            icmp = dissect_icmp(payload)
            if icmp:
                pkt["icmp"] = icmp
                app_payload = icmp["payload"]
    if fragmented_tail:
        pkt["fragmented"] = True

    # ── 应用层：按端口 + 内容双重判定（只看端口会被非标端口骗过，
    #    只看内容又会被二进制数据误判，所以两者都要）──
    sport = (pkt.get("tcp") or pkt.get("udp") or {}).get("sport")
    dport = (pkt.get("tcp") or pkt.get("udp") or {}).get("dport")
    if app_payload:
        if 53 in (sport, dport):
            dns = dissect_dns(app_payload)
            if dns:
                pkt["dns"] = dns
        if 80 in (sport, dport) or 8080 in (sport, dport) or 8000 in (sport, dport):
            http = dissect_http(app_payload)
            if http:
                pkt["http"] = http
        elif app_payload.lstrip()[:4] in HTTP_METHODS or app_payload.startswith(b"HTTP/"):
            http = dissect_http(app_payload)     # 非标端口上的 HTTP（C2 常见）
            if http:
                pkt["http"] = http
    pkt["app_payload"] = app_payload

    # ── 层名列表（对齐 Wireshark 的 Protocol 列）──
    layers = []
    for key in ("ether", "ip", "ipv6", "arp", "tcp", "udp", "icmp", "dns", "http"):
        if key in pkt:
            layers.append(key)
    pkt["layers"] = layers
    pkt["protocols"] = ":".join(layers)
    return pkt


def pkt_summary(pkt: dict) -> str:
    """一行摘要（对应 Wireshark 的 Info 列）。"""
    parts = [f"#{pkt['number']:<4} {pkt['ts']:.6f}"]
    ip = pkt.get("ip") or pkt.get("ipv6")
    if ip:
        parts.append(f"{ip['src']} → {ip['dst']}")
    if "tcp" in pkt:
        t = pkt["tcp"]
        parts.append(f"TCP {t['sport']}→{t['dport']} [{t['flags']}] "
                     f"seq={t['seq']} ack={t['ack']} win={t['window']} len={t['payload_len']}")
    elif "udp" in pkt:
        u = pkt["udp"]
        parts.append(f"UDP {u['sport']}→{u['dport']} len={u['length']}")
    elif "icmp" in pkt:
        i = pkt["icmp"]
        parts.append(f"ICMP {i['type_name']} (type={i['type']} code={i['code']})")
    elif "arp" in pkt:
        a = pkt["arp"]
        parts.append(f"ARP {a['op_name']} {a['sender_ip']} ({a['sender_mac']}) → {a['target_ip']}")
    if "dns" in pkt:
        d = pkt["dns"]
        kind = "Response" if d["response"] else "Query"
        parts.append(f"DNS {kind} {d['qry_name']} "
                     f"{('→ ' + ','.join(d['answers_a'])) if d['answers_a'] else ''}")
    if "http" in pkt:
        h = pkt["http"]
        if h["is_request"]:
            parts.append(f"HTTP {h['method']} {h['uri']} Host={h['host']}")
        else:
            parts.append(f"HTTP {h['response_code']} {h['response_phrase']}")
    return "  ".join(parts)


# ══════════════════════════════════════════════════════════════════════════
# 5. 显示过滤器引擎（Wireshark display filter 的子集）
# ══════════════════════════════════════════════════════════════════════════
#
# 必须先分清两件事（这是本日最容易混淆的概念，也是面试高频题）：
#
#   ┌──────────────┬───────────────────────────┬─────────────────────────┐
#   │              │ BPF（bpf_filter）          │ display filter          │
#   ├──────────────┼───────────────────────────┼─────────────────────────┤
#   │ 在哪执行      │ **内核**（抓包时）           │ **用户态**（抓完之后）     │
#   │ 过滤依据      │ 原始字节偏移 tcp[2:2]==80   │ 协议字段 tcp.port == 80  │
#   │ 语法来源      │ libpcap 表达式              │ Wireshark 自有语法       │
#   │ 能否回看已抓包 │ ❌ 没抓到的就永远没了         │ ✅ 对已有包重新过滤        │
#   │ 性能          │ 极高（不命中的包不进用户态）   │ 一般（每个包都要解析+求值） │
#   │ 能力          │ 只能看**头部的固定偏移**      │ 能看任意解析出来的字段     │
#   └──────────────┴───────────────────────────┴─────────────────────────┘
#
#   BPF 为什么只能看固定偏移？因为它工作在**解析之前**：
#     内核不知道也不关心"这是 HTTP 请求的第 7 个字节"，
#     它只认"从 TCP 头开始的第 2 个字节是目的端口"这种偏移表达式。
#   所以 `port 80` 在 BPF 里其实等价于：
#     tcp[2:2]==80 or tcp[4:2]==80 or udp[2:2]==80 or udp[4:2]==80
#     （再加 ip 分片、vlan 偏移的处理——这就是为什么复杂 BPF 极难手写正确）

class FilterError(ValueError):
    """过滤器语法错误（带人话提示，而不是让人去猜）。"""


# 协议名 → pkt 里的键（用于"裸协议名"谓词，如 `tcp`、`http`）
PROTO_KEYS = {
    "eth": "ether", "ether": "ether", "arp": "arp", "ip": "ip", "ipv4": "ip",
    "ipv6": "ipv6", "tcp": "tcp", "udp": "udp", "icmp": "icmp", "icmpv6": "ipv6",
    "dns": "dns", "http": "http",
}


def _both(keys):
    """取 src/dst 两个方向的字段（ip.addr / tcp.port 这种"任何一方命中就算"）。"""
    def getter(pkt):
        layer = None
        for k in keys:
            layer = pkt.get(k)
            if layer:
                break
        if not layer:
            return []
        out = []
        for f in ("src", "dst", "sport", "dport", "sender_ip", "target_ip"):
            if f in layer and layer[f] is not None:
                out.append(layer[f])
        return out
    return getter


def _one(layer_key, field, default=None):
    def getter(pkt):
        layer = pkt.get(layer_key)
        if not layer or layer.get(field) is None:
            return [] if default is None else [default]
        return [layer[field]]
    return getter


def _multi_all(layer_key, fields):
    def getter(pkt):
        layer = pkt.get(layer_key)
        if not layer:
            return []
        return [layer[f] for f in fields if layer.get(f) is not None]
    return getter


FIELD_GETTERS = {
    # frame.* 是顶层标量字段（不是"层字典"），必须单独取，不能走 _one()
    "frame.number": lambda p: [p["number"]],
    "frame.len": lambda p: [p["caplen"]],
    "frame.time": lambda p: [p["ts"]],
    "frame.protocols": lambda p: [p["protocols"]],
    "eth.src": _one("ether", "src"),
    "eth.dst": _one("ether", "dst"),
    "eth.type": _one("ether", "ethertype"),
    "arp.op": _one("arp", "op"),
    "arp.src.proto_ipv4": _one("arp", "sender_ip"),
    "arp.dst.proto_ipv4": _one("arp", "target_ip"),
    "arp.src.hw_mac": _one("arp", "sender_mac"),
    "ip.src": _one("ip", "src"),
    "ip.dst": _one("ip", "dst"),
    "ip.addr": _one("ip", "src"),
    "ip.ttl": _one("ip", "ttl"),
    "ip.proto": _one("ip", "proto"),
    "ip.len": _one("ip", "total_len"),
    "ip.id": _one("ip", "id"),
    "ip.flags.df": _one("ip", "df"),
    "ipv6.src": _one("ipv6", "src"),
    "ipv6.dst": _one("ipv6", "dst"),
    "ipv6.addr": _one("ipv6", "src"),
    "ipv6.hlim": _one("ipv6", "hop_limit"),
    "tcp.srcport": _one("tcp", "sport"),
    "tcp.dstport": _one("tcp", "dport"),
    "tcp.port": _one("tcp", "sport"),
    "tcp.seq": _one("tcp", "seq"),
    "tcp.ack": _one("tcp", "ack"),
    "tcp.window": _one("tcp", "window"),
    "tcp.len": _one("tcp", "payload_len"),
    "tcp.flags": _one("tcp", "flags_raw"),
    "tcp.flags.str": _one("tcp", "flags"),
    "tcp.flags.syn": _one("tcp", "syn"),
    "tcp.flags.ack": _one("tcp", "ack_flag"),
    "tcp.flags.fin": _one("tcp", "fin"),
    "tcp.flags.rst": _one("tcp", "rst"),
    "tcp.flags.psh": _one("tcp", "psh"),
    "udp.srcport": _one("udp", "sport"),
    "udp.dstport": _one("udp", "dport"),
    "udp.port": _one("udp", "sport"),
    "udp.length": _one("udp", "length"),
    "icmp.type": _one("icmp", "type"),
    "icmp.code": _one("icmp", "code"),
    "dns.qry.name": _one("dns", "qry_name"),
    "dns.flags.response": _one("dns", "response"),
    "dns.a": _one("dns", "answers_a"),
    "http.request.method": _one("http", "method"),
    "http.host": _one("http", "host"),
    "http.request.uri": _one("http", "uri"),
    "http.response.code": _one("http", "response_code"),
    "http.user_agent": _one("http", "user_agent"),
}
# 多值字段（源和目的任意一侧命中即算命中）
MULTI_FIELDS = {
    "ip.addr": ("ip", "ipv6"),
    "tcp.port": ("tcp",),
    "udp.port": ("udp",),
    "arp.addr": ("arp",),
}


def field_values(pkt: dict, name: str) -> list:
    """取字段值列表。未知字段抛 FilterError（明确报错 > 静默返回空）。"""
    if name in MULTI_FIELDS:
        return _both(MULTI_FIELDS[name])(pkt)
    getter = FIELD_GETTERS.get(name)
    if getter is None:
        raise FilterError(
            f"不支持的字段名 {name!r}。本引擎是 Wireshark display filter 的子集，"
            "已支持：ip.*/tcp.*/udp.*/icmp.*/dns.*/http.*/eth.*/arp.*/frame.*")
    return getter(pkt)


def _proto_present(name: str, pkt: dict) -> bool:
    key = PROTO_KEYS.get(name)
    if key is None:
        raise FilterError(f"不认识的协议名 {name!r}（可用：{', '.join(sorted(PROTO_KEYS))}）")
    if name == "icmpv6":
        return pkt.get("ipv6") is not None and pkt["ipv6"].get("proto") == IPPROTO_ICMPV6
    return key in pkt


def _as_number(text: str) -> Optional[int]:
    """把字面量解析成整数（支持 0x 十六进制）；不是数字返回 None。"""
    try:
        return int(text, 0)
    except (ValueError, TypeError):
        return None


def _cmp_one(value, op: str, literal: str) -> bool:
    """单个值 vs 字面量的比较（自动处理 bool/int/str 类型差异）。"""
    if isinstance(value, bool):
        lhs = 1 if value else 0
        rhs = _as_number(literal)
        if rhs is None:
            rhs = 1 if literal.strip().lower() in ("true", "yes") else 0
    elif isinstance(value, int):
        rhs = _as_number(literal)
        if rhs is None:
            return False
        lhs = value
    elif isinstance(value, str):
        num = _as_number(literal)
        if num is not None and value.strip().lstrip("-").isdigit():
            lhs, rhs = int(value.strip()), num
        else:
            lhs, rhs = value.lower(), literal.lower()
    else:
        return False
    if op == "==":
        return lhs == rhs
    if op == "!=":
        return lhs != rhs
    if op == ">":
        return lhs > rhs
    if op == "<":
        return lhs < rhs
    if op == ">=":
        return lhs >= rhs
    if op == "<=":
        return lhs <= rhs
    raise FilterError(f"不支持的运算符 {op!r}")


def _eval_cmp(pkt: dict, name: str, op: str, literal: str) -> bool:
    values = field_values(pkt, name)
    if op == "contains":
        return any(literal.lower() in str(v).lower() for v in values)
    if not values:
        return False
    # CIDR 支持：ip.addr == 10.0.0.0/8
    if "/" in literal:
        import ipaddress
        try:
            net = ipaddress.ip_network(literal, strict=False)
        except ValueError:
            net = None
        if net is not None:
            for v in values:
                try:
                    if ipaddress.ip_address(str(v).split("%")[0]) in net:
                        return True
                except ValueError:
                    continue
            return False
    if op == "!=":
        # "不等于"的语义是"所有值都不等于"（否则多值字段会永远为真）
        return all(not _cmp_one(v, "==", literal) for v in values)
    return any(_cmp_one(v, op, literal) for v in values)


def _tokenize(expr: str) -> list:
    """把过滤表达式切成 token。规则很少，关键是**多字符运算符要先匹配**。"""
    toks: list = []
    i, n = 0, len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        if c in "()":
            toks.append(c)
            i += 1
            continue
        two = expr[i:i + 2]
        if two in ("==", "!=", ">=", "<=", "&&", "||"):
            toks.append({"&&": "and", "||": "or"}.get(two, two))
            i += 2
            continue
        if c in "<>":
            toks.append(c)
            i += 1
            continue
        if c == "!":
            toks.append("not")            # 单目取反
            i += 1
            continue
        if c == '"':
            j = expr.find('"', i + 1)
            if j < 0:
                raise FilterError("引号没有闭合")
            toks.append(("str", expr[i + 1:j]))
            i = j + 1
            continue
        j = i
        while j < n and not expr[j].isspace() and expr[j] not in '()"<>':
            if expr[j:j + 2] in ("==", "!=", ">=", "<=", "&&", "||"):
                break
            j += 1
        word = expr[i:j]
        # and / or / not 这三个词是**运算符**，必须转成运算符 token，
        # 否则会被当成普通标识符（这是一个非常容易漏的 bug：
        # 表达式会"解析成功前半段，然后在 and 处报多余内容"）
        toks.append(word.lower() if word.lower() in ("and", "or", "not") else ("id", word))
        i = j
    return toks


def _peek(toks: list, i: int):
    return toks[i] if i < len(toks) else None


def _parse_or(toks: list, i: int) -> tuple:
    node, i = _parse_and(toks, i)
    while _peek(toks, i) == "or":
        rhs, i = _parse_and(toks, i + 1)
        node = ("or", node, rhs)
    return node, i


def _parse_and(toks: list, i: int) -> tuple:
    node, i = _parse_unary(toks, i)
    while _peek(toks, i) == "and":
        rhs, i = _parse_unary(toks, i + 1)
        node = ("and", node, rhs)
    return node, i


def _parse_unary(toks: list, i: int) -> tuple:
    tok = _peek(toks, i)
    if tok == "not":
        node, i = _parse_unary(toks, i + 1)
        return ("not", node), i
    if tok == "(":
        node, i = _parse_or(toks, i + 1)
        if _peek(toks, i) != ")":
            raise FilterError("括号不配对：缺少 )")
        return node, i + 1
    if not isinstance(tok, tuple):
        raise FilterError(f"表达式不完整或位置意外：{tok!r}")
    if tok[0] == "str":
        raise FilterError("表达式不能以字符串字面量开头")
    name = tok[1]
    i += 1
    nxt = _peek(toks, i)
    if isinstance(nxt, tuple) and nxt[1] in ("contains", "matches"):
        i += 1
        val = _peek(toks, i)
        if not isinstance(val, tuple):
            raise FilterError(f"{nxt[1]} 后面缺少值")
        i += 1
        if nxt[1] == "matches":
            raise FilterError("matches（正则）本引擎不支持，请用 contains")
        return ("cmp", name, "contains", val[1]), i
    if isinstance(nxt, str) and nxt in ("==", "!=", ">", "<", ">=", "<="):
        i += 1
        val = _peek(toks, i)
        if not isinstance(val, tuple):
            raise FilterError(f"运算符 {nxt} 后面缺少值")
        i += 1                     # ⚠️ 别忘了把"值"也吃掉，否则会被判为多余 token
        return ("cmp", name, nxt, val[1]), i
    return ("proto", name), i


def _validate(node: tuple) -> None:
    """编译期校验字段名/协议名（**fail fast**）。

    为什么要在编译期校验，而不是等求值时才发现？
      过滤一个 10 万包的文件要几十秒，如果字段名拼错了，
      求值期的报错要等到"第一个包"才炸——等于白等。
      编译期校验让错误在毫秒级暴露，这也是所有查询引擎（SQL/Wireshark）
      的标准做法：**先绑定 schema，再执行**。
    """
    kind = node[0]
    if kind in ("and", "or"):
        _validate(node[1])
        _validate(node[2])
    elif kind == "not":
        _validate(node[1])
    elif kind == "proto":
        if node[1] not in PROTO_KEYS:
            raise FilterError(
                f"不认识的协议名 {node[1]!r}（可用：{', '.join(sorted(PROTO_KEYS))}）")
    elif kind == "cmp":
        if node[1] not in FIELD_GETTERS and node[1] not in MULTI_FIELDS:
            raise FilterError(
                f"不支持的字段名 {node[1]!r}。已支持：frame.* / eth.* / arp.* / "
                "ip.* / ipv6.* / tcp.* / udp.* / icmp.* / dns.* / http.*")
    else:
        raise FilterError(f"未知的 AST 节点：{kind}")


def compile_filter(expr: str) -> tuple:
    """编译过滤表达式为 AST（含字段名校验）。**编译一次，反复求值** ——
    这是性能关键：如果每个包都重新解析字符串，几万个包就会慢得离谱。"""
    if not expr or not expr.strip():
        raise FilterError("表达式为空")
    toks = _tokenize(expr)
    node, i = _parse_or(toks, 0)
    if i != len(toks):
        raise FilterError(f"表达式有多余内容：{toks[i]!r}")
    _validate(node)
    return node


def eval_filter(node: tuple, pkt: dict) -> bool:
    """对单个包（已解析的字典）求值。"""
    kind = node[0]
    if kind == "and":
        return eval_filter(node[1], pkt) and eval_filter(node[2], pkt)
    if kind == "or":
        return eval_filter(node[1], pkt) or eval_filter(node[2], pkt)
    if kind == "not":
        return not eval_filter(node[1], pkt)
    if kind == "proto":
        return _proto_present(node[1], pkt)
    if kind == "cmp":
        return _eval_cmp(pkt, node[1], node[2], node[3])
    raise FilterError(f"未知的 AST 节点：{kind}")


def apply_filter(packets, expr: str):
    """对已解析的包序列应用过滤（生成器，惰性求值）。"""
    ast = compile_filter(expr)
    for pkt in packets:
        if eval_filter(ast, pkt):
            yield pkt


# ── 5.1 BPF 子集 → display filter 的"教学翻译器" ──────────────────────────
#
# ⚠️ 这不是一个真正的 BPF 编译器！
#   真 BPF 会被 libpcap 编译成**内核字节码**，在网卡驱动之后、
#   进入协议栈之前执行；它能引用的只有"相对某个固定偏移的若干字节"。
#   本函数只是把常见写法**翻译成等效的 display filter**，
#   目的是让你直观看到"同一个意思，两种表达"的对应关系。

_BPF_SIMPLE = {
    "icmp": "icmp", "icmp6": "icmpv6", "tcp": "tcp", "udp": "udp",
    "arp": "arp", "ip": "ip", "ip6": "ipv6", "ipv6": "ipv6",
}


def bpf_to_display(bpf: str) -> Optional[str]:
    """把 BPF 常见子集翻译成 display filter；无法翻译返回 None。

    支持：协议名、port/portrange、host/ src host / dst host、net、not/and/or、
         以及最经典的 `tcp[tcpflags] & tcp-syn != 0`。
    """
    expr = " ".join(bpf.strip().split())
    if not expr:
        return None
    low = expr.lower()
    # 先处理最经典的"只看 SYN"写法（这是最常被问到的一条）
    compact = low.replace(" ", "")
    if compact in ("tcp[tcpflags]&tcp-syn!=0", "tcp[tcpflags]&(tcp-syn)!=0"):
        return "tcp.flags.syn == 1"
    if compact in ("tcp[tcpflags]&tcp-ack!=0",):
        return "tcp.flags.ack == 1"
    # 递归处理 and / or（从左到右切分，教学够用）
    for sep, op in ((" or ", "or"), (" and ", "and")):
        if sep in low:
            parts = expr.split(sep)
            translated = [bpf_to_display(p) for p in parts]
            if any(t is None for t in translated):
                return None
            return "(" + f" {op} ".join(f"({t})" for t in translated) + ")"
    tokens = expr.split()
    if len(tokens) == 1:
        return _BPF_SIMPLE.get(low, None)
    if tokens[0] == "not" or tokens[0] == "!":
        sub = bpf_to_display(" ".join(tokens[1:]))
        return f"(not ({sub}))" if sub else None
    # 两词形式：<qualifier> <value>（注意限定符取 tokens[0]，不是整条表达式）
    if len(tokens) == 2:
        qual, value = tokens[0].lower(), tokens[1]
        if qual == "port":
            return f"(tcp.port == {value} or udp.port == {value})"
        if qual == "tcp":
            return f"tcp.port == {value}"
        if qual == "udp":
            return f"udp.port == {value}"
        if qual in ("host", "net"):
            return f"ip.addr == {value}"
        return None
    # 三词形式：tcp port 80 / src host 1.2.3.4 / dst host 1.2.3.4
    if len(tokens) == 3:
        a, b, c = tokens[0].lower(), tokens[1].lower(), tokens[2]
        if a == "tcp" and b == "port":
            return f"tcp.port == {c}"
        if a == "udp" and b == "port":
            return f"udp.port == {c}"
        if b == "host":
            if a == "src":
                return f"ip.src == {c}"
            if a == "dst":
                return f"ip.dst == {c}"
        if b == "port" and a in ("src", "dst"):
            field = "tcp.srcport" if a == "src" else "tcp.dstport"
            return f"({field} == {c})"
        if b == "net":
            return f"ip.addr == {c}"
    return None


def bpf_equivalent_bytes() -> dict:
    """用字节偏移视角解释 BPF：`port 80` 到底在内核里比什么。

    返回 {表达式: 说明}，供 README 与自检引用。
    """
    return {
        "tcp port 80":
            "ip proto 6 and (tcp[2:2] == 80 or tcp[4:2] == 80)   "
            "# [2:2] = 从 TCP 头起第 2 字节开始的 2 字节 = 源端口，[4:2] = 目的端口",
        "port 80":
            "(tcp[2:2] == 80 or tcp[4:2] == 80) or (udp[2:2] == 80 or udp[4:2] == 80)",
        "icmp":
            "ip proto 1",
        "host 10.0.0.1":
            "ip[12:4] == 10.0.0.1 or ip[16:4] == 10.0.0.1   # 12 = 源IP偏移，16 = 目的IP偏移",
        "tcp[tcpflags] & tcp-syn != 0":
            "tcp[13] & 2 != 0   # TCP 头第 13 字节的 bit1 就是 SYN",
    }


# ══════════════════════════════════════════════════════════════════════════
# 6. 报文构造器（相当于"标准库版 Scapy"，只够本日教学用）
# ══════════════════════════════════════════════════════════════════════════
# 为什么要自己造包？因为自检必须**离线、确定性、不依赖任何抓包工具**：
#   抓真流量做不到"每次跑结果都一样"，而断言检测结果需要一个**已知答案**的
#   数据集。合成流量就是这个"考试卷"——题干和标准答案都是我们写的。


def mac_bytes(mac: str) -> bytes:
    return bytes.fromhex(mac.replace(":", "").replace("-", ""))


def build_eth_frame(dst_mac: str, src_mac: str, ethertype: int, payload: bytes) -> bytes:
    """以太网 II 帧。注意最小帧长 60 字节（不含 FCS），
    短包需要填充——真实网卡会自动补，我们用代码造包时**故意不补**，
    以便在自检里演示"用 total_len 而不是 len(帧) 判断 IP 载荷长度"。"""
    return (mac_bytes(dst_mac) + mac_bytes(src_mac) +
            struct.pack("!H", ethertype) + payload)


def build_ipv4(src: str, dst: str, proto: int, payload: bytes, *, ttl: int = 64,
               ident: int = 0, flags_frag: int = 0, options: bytes = b"",
               bad_checksum: bool = False) -> bytes:
    """构造 IPv4 头 + 载荷（校验和自动计算；bad_checksum=True 时故意写错）。

    为什么要有 bad_checksum？为了在自检里证明"**我们真的在验校验和**"，
    而 pyshark/tshark 默认只做 dissection，不会告诉你这个包是错的
    （Wireshark 会用 `ip.checksum.status == "Bad"` 标出来，但要你显式去看）。
    """
    ihl = 20 + len(options)
    total_len = ihl + len(payload)
    header = bytearray()
    header += bytes([(4 << 4) | (ihl // 4)])
    header += b"\x00"                                  # tos：老式 ToS，现在多是 DSCP/ECN
    header += struct.pack("!H", total_len)
    header += struct.pack("!H", ident & 0xFFFF)
    header += struct.pack("!H", flags_frag & 0xFFFF)
    header += bytes([ttl, proto])
    header += b"\x00\x00"                              # 校验和占位，稍后回填
    header += socket.inet_aton(src) + socket.inet_aton(dst)
    header += options
    ck = ipv4_header_checksum(bytes(header))
    if bad_checksum:
        ck = (~ck) & 0xFFFF                            # 取反 → 保证算出"错误"
    header[10:12] = struct.pack("!H", ck)
    return bytes(header) + payload


def build_tcp(src: str, dst: str, sport: int, dport: int, *, seq: int = 0, ack: int = 0,
              flags: int = 0x02, window: int = 64240, payload: bytes = b"",
              options: bytes = b"") -> bytes:
    """构造 TCP 段（校验和含伪首部，自动计算）。flags 用位掩码：SYN=0x02 ACK=0x10 …

    ⚠️ 硬约束：**TCP 头长度必须是 4 字节的整数倍**（data offset 字段只以 4 字节为单位
       计数，装不下"6 字节选项"这种长度）。如果选项不是 4 的倍数，
       接收端算出的 data offset 会偏小，把选项字节当成**载荷**读出来
       —— 这就是"明明没有数据，tcp.len 却不等于 0"的经典错位 bug。
       标准做法是在选项末尾补 NOP(0x01) 凑齐 4 字节。
       本函数直接报错而不是自动补，避免把错误数据悄悄塞进"教学用流量"里。
    """
    if len(options) % 4:
        raise ValueError(
            f"TCP 选项长度必须是 4 的倍数（当前 {len(options)} 字节）。"
            "请在末尾补 NOP（0x01）对齐，例如 b'\\x02\\x04\\x05\\xb4\\x04\\x02\\x01\\x01'")
    data_off = 20 + len(options)
    seg = bytearray()
    seg += struct.pack("!HH", sport, dport)
    seg += struct.pack("!II", seq & 0xFFFFFFFF, ack & 0xFFFFFFFF)
    seg += bytes([(data_off // 4) << 4, flags & 0xFF])
    seg += struct.pack("!H", window)
    seg += b"\x00\x00"                                 # 校验和占位
    seg += b"\x00\x00"                                 # urgent pointer（URG 才用）
    seg += options
    seg += payload
    ck = checksum(pseudo_header_v4(src, dst, IPPROTO_TCP, len(seg)) + bytes(seg))
    seg[16:18] = struct.pack("!H", ck)
    return bytes(seg)


def build_udp(src: str, dst: str, sport: int, dport: int, payload: bytes = b"") -> bytes:
    """构造 UDP 数据报（校验和含伪首部）。"""
    length = 8 + len(payload)
    seg = bytearray()
    seg += struct.pack("!HHHH", sport, dport, length, 0)
    seg += payload
    ck = checksum(pseudo_header_v4(src, dst, IPPROTO_UDP, len(seg)) + bytes(seg))
    seg[6:8] = struct.pack("!H", ck)
    return bytes(seg)


def build_icmp(itype: int, icode: int, ident: int = 0, seq: int = 0,
               payload: bytes = b"") -> bytes:
    """构造 ICMP（校验和**不含伪首部**，只覆盖 ICMP 消息本身）。"""
    body = struct.pack("!BBHHH", itype, icode, 0, ident, seq) + payload
    ck = checksum(body)
    return body[:2] + struct.pack("!H", ck) + body[4:]


def dns_encode_name(name: str) -> bytes:
    """域名 → DNS 线上的 label 编码（每段前面加长度字节，末尾一个 0x00）。"""
    out = bytearray()
    for label in name.split("."):
        if label:
            out += bytes([len(label)]) + label.encode("ascii", "replace")
    out += b"\x00"
    return bytes(out)


def build_dns_query(txid: int, qname: str, qtype: int = 1) -> bytes:
    """构造 DNS 查询（rd=1 表示递归查询）。"""
    return (struct.pack("!HHHHHH", txid, 0x0100, 1, 0, 0, 0) +
            dns_encode_name(qname) + struct.pack("!HH", qtype, 1))


def build_dns_response(txid: int, qname: str, answer_ip: str, *,
                       qtype: int = 1, ttl: int = 300) -> bytes:
    """构造 DNS 应答。名字用**压缩指针 0xC00C**指回偏移 12（问题段起始），
    这正好覆盖了自检里"压缩指针解析"这条路径。"""
    question = dns_encode_name(qname) + struct.pack("!HH", qtype, 1)
    answer = (b"\xc0\x0c" + struct.pack("!HHIH", qtype, 1, ttl, 4) +
              socket.inet_aton(answer_ip))
    return struct.pack("!HHHHHH", txid, 0x8180, 1, 1, 0, 0) + question + answer


def build_arp(op: int, sender_mac: str, sender_ip: str,
              target_mac: str, target_ip: str) -> bytes:
    """构造 ARP（无 IP 头，直接挂在 Ether 的 0x0806 上）。"""
    return (struct.pack("!HHBBH", 1, 0x0800, 6, 4, op) +
            mac_bytes(sender_mac) + socket.inet_aton(sender_ip) +
            mac_bytes(target_mac) + socket.inet_aton(target_ip))


# ── 6.1 合成流量：一份"带标准答案"的考卷 ──────────────────────────────────
#
# 这份流量里**故意植入**了 6 类可检测现象（括号里是自检断言的目标）：
#   ① 正常 Web 会话             → 用来证明检测器**不误报**（最重要）
#   ② ARP 欺骗（同一 IP 两个 MAC）
#   ③ SYN 端口扫描（8 个端口，纯 SYN，无握手完成）
#   ④ SYN 洪水（同一目标端口 25 个 SYN）
#   ⑤ 明文凭据（HTTP Authorization + Cookie）
#   ⑥ DNS 隧道查询（超长 label）
#   ⑦ C2 心跳（每 60s 一次的固定间隔回连）
#   ⑧ 校验和错误的包（证明"我们真的在验完整性"）

DEMO_FACTS = {
    "client_ip": "10.0.0.10",
    "web_server_ip": "10.0.0.20",
    "gateway_ip": "10.0.0.1",
    "scanner_ip": "10.0.0.66",
    "scanned_ports": [21, 22, 23, 25, 80, 443, 3306, 8080],
    "flooder_ip": "10.0.0.99",
    "flood_target": "10.0.0.20",
    "flood_port": 80,
    "flood_syn_count": 25,
    "tunnel_client": "10.0.0.88",
    "tunnel_qnames": [
        "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v.tunnel.evil.example",
        "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w.tunnel.evil.example",
        "c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2wx.tunnel.evil.example",
    ],
    "tunnel_suffix": ".tunnel.evil.example",
    "beacon_src": "10.0.0.77",
    "beacon_dst": "10.0.0.40",
    "beacon_port": 4444,
    "beacon_count": 4,
    "beacon_interval": 60.0,
    "arp_conflict_ip": "10.0.0.1",
    "arp_conflict_macs": ["aa:00:00:00:00:01", "aa:00:00:00:de:ad"],
    "credential_host": "intranet.example.com",
    "credential_uri": "/login",
    "bad_checksum_count": 1,
    "normal_http_method": "GET",
}

# 固定基准时间戳：自检必须**可复现**，绝不能用 time.time()
DEMO_BASE_TS = 1_700_000_000.0


def build_demo_packets(base_ts: float = DEMO_BASE_TS) -> list:
    """构造合成抓包。返回值是 RawPacket 列表（尚未序列化）。"""
    pkts: list = []
    ident = [0]

    def add(ts: float, frame: bytes) -> None:
        pkts.append(RawPacket(index=len(pkts) + 1, ts=base_ts + ts,
                              data=frame, orig_len=len(frame)))

    def next_id() -> int:
        ident[0] = (ident[0] + 1) & 0xFFFF
        return ident[0]

    C, S = DEMO_FACTS["client_ip"], DEMO_FACTS["web_server_ip"]
    C_MAC, S_MAC = "aa:00:00:00:00:10", "aa:00:00:00:00:20"
    DNS_IP, DNS_MAC = "10.0.0.53", "aa:00:00:00:00:53"

    def l3(src, dst, proto, seg, *, bad=False, ttl=64):
        return build_ipv4(src, dst, proto, seg, ttl=ttl, ident=next_id(),
                          bad_checksum=bad)

    def tcp_frame(dmac, smac, src, dst, sport, dport, **kw):
        bad = kw.pop("bad_checksum", False)
        seg = build_tcp(src, dst, sport, dport, **kw)
        return build_eth_frame(dmac, smac, ETHERTYPE_IPV4, l3(src, dst, 6, seg, bad=bad))

    # ── ① 正常 Web 会话：DNS → TCP 握手 → HTTP 请求/响应 → 挥手 ──
    add(0.000, build_eth_frame(DNS_MAC, C_MAC, ETHERTYPE_IPV4,
        l3(C, DNS_IP, 17, build_udp(C, DNS_IP, 53124, 53,
                                    build_dns_query(0x1234, "intranet.example.com")))))
    add(0.012, build_eth_frame(C_MAC, DNS_MAC, ETHERTYPE_IPV4,
        l3(DNS_IP, C, 17, build_udp(DNS_IP, C, 53, 53124,
                                    build_dns_response(0x1234, "intranet.example.com", S)))))
    HTTP_REQ = (b"GET /login HTTP/1.1\r\n"
                b"Host: intranet.example.com\r\n"
                b"User-Agent: Mozilla/5.0 (day157 demo)\r\n"
                b"Accept: text/html\r\n"
                b"Authorization: Basic dXNlcjpwYXNzd29yZA==\r\n"
                b"Cookie: SESSION=8f3a1c0d9e2b; theme=dark\r\n"
                b"Connection: keep-alive\r\n\r\n")
    HTTP_RESP = (b"HTTP/1.1 200 OK\r\n"
                 b"Server: nginx/1.24.0\r\n"
                 b"Content-Type: text/html; charset=utf-8\r\n"
                 b"Content-Length: 52\r\n\r\n"
                 b"<html><body><h1>Welcome back</h1></body></html>")
    add(0.013, tcp_frame(S_MAC, C_MAC, C, S, 49152, 80, seq=1000, flags=0x02,
                         options=b"\x02\x04\x05\xb4"))            # SYN + MSS 1460
    # SYN-ACK 带两个选项：MSS(4 字节) + SAckOK(2 字节) —— 加起来 6 字节不是 4 的倍数，
    # 所以必须再补两个 NOP(0x01) 凑成 8 字节，否则 data offset 与实际头长不符（见 build_tcp 注释）
    add(0.014, tcp_frame(C_MAC, S_MAC, S, C, 80, 49152, seq=5000, ack=1001, flags=0x12,
                         options=b"\x02\x04\x05\xb4\x04\x02\x01\x01"))
    add(0.014, tcp_frame(S_MAC, C_MAC, C, S, 49152, 80, seq=1001, ack=5001, flags=0x10))
    add(0.015, tcp_frame(S_MAC, C_MAC, C, S, 49152, 80, seq=1001, ack=5001, flags=0x18,
                         payload=HTTP_REQ))                        # PSH+ACK 带请求
    add(0.016, tcp_frame(C_MAC, S_MAC, S, C, 80, 49152, seq=5001,
                         ack=1001 + len(HTTP_REQ), flags=0x10))    # 服务端 ACK
    add(0.030, tcp_frame(C_MAC, S_MAC, S, C, 80, 49152, seq=5001,
                         ack=1001 + len(HTTP_REQ), flags=0x18, payload=HTTP_RESP))
    add(0.031, tcp_frame(S_MAC, C_MAC, C, S, 49152, 80, seq=1001 + len(HTTP_REQ),
                         ack=5001 + len(HTTP_RESP), flags=0x10))
    add(0.032, tcp_frame(S_MAC, C_MAC, C, S, 49152, 80, seq=1001 + len(HTTP_REQ),
                         ack=5001 + len(HTTP_RESP), flags=0x11))   # FIN+ACK
    add(0.033, tcp_frame(C_MAC, S_MAC, S, C, 80, 49152, seq=5001 + len(HTTP_RESP),
                         ack=1002 + len(HTTP_REQ), flags=0x11))
    add(0.034, tcp_frame(S_MAC, C_MAC, C, S, 49152, 80, seq=1002 + len(HTTP_REQ),
                         ack=5002 + len(HTTP_RESP), flags=0x10))

    # ── ICMP ping（教学：ICMP 校验和无伪首部）──
    add(1.000, build_eth_frame(S_MAC, C_MAC, ETHERTYPE_IPV4,
        l3(C, S, 1, build_icmp(8, 0, ident=0x0001, seq=1, payload=b"day157-demo"))))
    add(1.001, build_eth_frame(C_MAC, S_MAC, ETHERTYPE_IPV4,
        l3(S, C, 1, build_icmp(0, 0, ident=0x0001, seq=1, payload=b"day157-demo"))))

    # ── ② ARP：正常应答 + 一条**伪造应答**（同一 IP 另一个 MAC）──
    GW_MAC = DEMO_FACTS["arp_conflict_macs"][0]
    add(2.000, build_eth_frame("ff:ff:ff:ff:ff:ff", C_MAC, ETHERTYPE_ARP,
        build_arp(1, C_MAC, C, "00:00:00:00:00:00", DEMO_FACTS["gateway_ip"])))
    add(2.001, build_eth_frame(C_MAC, GW_MAC, ETHERTYPE_ARP,
        build_arp(2, GW_MAC, DEMO_FACTS["gateway_ip"], C_MAC, C)))
    add(2.400, build_eth_frame(C_MAC, DEMO_FACTS["arp_conflict_macs"][1], ETHERTYPE_ARP,
        build_arp(2, DEMO_FACTS["arp_conflict_macs"][1],
                  DEMO_FACTS["gateway_ip"], C_MAC, C)))     # ← 攻击者伪造

    # ── ③ SYN 端口扫描：8 个端口各一个 SYN，绝不完成握手 ──
    for i, port in enumerate(DEMO_FACTS["scanned_ports"]):
        add(3.000 + i * 0.05, tcp_frame(S_MAC, "aa:00:00:00:00:66", DEMO_FACTS["scanner_ip"],
                                        S, 40000, port, seq=7000 + i, flags=0x02))

    # ── ④ SYN 洪水：同一目标端口 25 个 SYN ──
    for i in range(DEMO_FACTS["flood_syn_count"]):
        add(4.000 + i * 0.001,
            tcp_frame(S_MAC, "aa:00:00:00:00:99", DEMO_FACTS["flooder_ip"], S,
                      50000 + i, DEMO_FACTS["flood_port"], seq=100 + i, flags=0x02))

    # ── ⑤ DNS 隧道：超长 label（base32 风格编码数据），来自独立主机 10.0.0.88 ──
    T = DEMO_FACTS["tunnel_client"]
    for i, qname in enumerate(DEMO_FACTS["tunnel_qnames"]):
        add(5.0 + i * 0.1, build_eth_frame(DNS_MAC, "aa:00:00:00:00:88", ETHERTYPE_IPV4,
            l3(T, DNS_IP, 17, build_udp(T, DNS_IP, 53200 + i, 53,
                                        build_dns_query(0x2000 + i, qname)))))

    # ── ⑦ C2 心跳：每 60 秒一次，固定目标端口 4444 ──
    beacon_req = (b"POST /ping HTTP/1.1\r\nHost: c2.example\r\n"
                  b"User-Agent: curl/8.5.0\r\nContent-Length: 16\r\n\r\n"
                  b"id=7f3a&state=ok")
    for i in range(DEMO_FACTS["beacon_count"]):
        t = 10.0 + i * DEMO_FACTS["beacon_interval"]
        add(t, tcp_frame("aa:00:00:00:00:40", "aa:00:00:00:00:77",
                         DEMO_FACTS["beacon_src"], DEMO_FACTS["beacon_dst"],
                         44000 + i, DEMO_FACTS["beacon_port"], seq=8000, flags=0x02))
        add(t + 0.002, tcp_frame("aa:00:00:00:00:77", "aa:00:00:00:00:40",
                                 DEMO_FACTS["beacon_dst"], DEMO_FACTS["beacon_src"],
                                 DEMO_FACTS["beacon_port"], 44000 + i, seq=9000,
                                 ack=8001, flags=0x12))
        add(t + 0.003, tcp_frame("aa:00:00:00:00:40", "aa:00:00:00:00:77",
                                 DEMO_FACTS["beacon_src"], DEMO_FACTS["beacon_dst"],
                                 44000 + i, DEMO_FACTS["beacon_port"], seq=8001,
                                 ack=9001, flags=0x10))
        add(t + 0.004, tcp_frame("aa:00:00:00:00:40", "aa:00:00:00:00:77",
                                 DEMO_FACTS["beacon_src"], DEMO_FACTS["beacon_dst"],
                                 44000 + i, DEMO_FACTS["beacon_port"], seq=8001,
                                 ack=9001, flags=0x18, payload=beacon_req))

    # ── ⑧ 一个校验和错误的包（IPv4 头被改过）──
    add(200.0, tcp_frame(S_MAC, C_MAC, C, S, 49152, 80, seq=9999, flags=0x02,
                         bad_checksum=True))
    return pkts


def write_demo_pcap(path: str, base_ts: float = DEMO_BASE_TS) -> int:
    """把合成抓包写进文件（供上层脚本与自检使用）。"""
    return write_pcap(path, build_demo_packets(base_ts))


def demo_pcap_in_tempdir(prefix: str = "day157-") -> str:
    """在系统临时目录里生成合成 pcap，返回路径。

    为什么必须落 tempfile 而不是仓库里？
      · 不污染工作树（本日代码是"可运行示例"，不该把产物提交进仓库）；
      · tempfile 目录每次重启系统会清理，适合放"一次性的假数据"；
      · 也避免多个脚本互相覆盖同一个固定文件名（原版脚本硬编码
        example_traffic.pcap 就是这个坑：文件不存在时整个脚本直接崩）。
    """
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".pcap")
    os.close(fd)
    write_demo_pcap(path)
    return path


# ══════════════════════════════════════════════════════════════════════════
# 7. 自检（离线 / 确定性 / 不依赖第三方库）
# ══════════════════════════════════════════════════════════════════════════

def check_eq(actual, expected, label: str) -> None:
    """断言相等；失败时把**实际值 vs 期望值**都打出来（而不是只抛 AssertionError）。"""
    if actual != expected:
        raise AssertionError(f"{label} 不匹配：实际={actual!r} 期望={expected!r}")


def check_true(cond, label: str) -> None:
    if not cond:
        raise AssertionError(f"{label} 应为真，但为假")


def self_test(tmpdir: Optional[str] = None) -> None:
    """自检全流程。任何断言失败都会抛 AssertionError（由 main 转成 exit 1）。"""
    print("=" * 74)
    print("pcap_lib 离线自检：校验和 / 格式读写 / 解析 / 过滤器 / 合成流量")
    print("=" * 74)

    # ── 1) 校验和：先对着 RFC 1071 的官方例子，再对着 scapy 交叉验证的值 ──
    rfc_example = bytes.fromhex("0001f203f4f5f6f7")
    check_eq(ones_complement_sum(rfc_example), 0xDDF2, "RFC1071 例子反码和")
    check_eq(checksum(rfc_example), 0x220D, "RFC1071 例子校验和")
    # 奇数长度：末尾必须补 0x00 再算（漏了这步会得到完全不同的结果）
    check_eq(ones_complement_sum(b"\x00\x01"), 0x0001, "偶数长度")
    check_eq(ones_complement_sum(b"\x01"), 0x0100, "奇数长度补零")
    # scapy 2.7.0 交叉验证（本文件开发时实测，命令见 README）：
    #   IP(src=10.0.0.2,dst=10.0.0.1,id=1,flags=0)/TCP(sport=12345,dport=80,flags="S",
    #                                                 seq=1000,window=64240)
    #   → IP.chksum = 0x66cd，TCP.chksum = 0x6c7e，且**整包 40 字节与本库逐字节一致**
    # 注意 window 必须和本库默认值 64240 相同，否则 TCP 校验和会变（0x476f 是
    # scapy 默认 window=8192 时的值 —— 这正是"改一个字段就要重算校验和"的实证）。
    my_seg = build_tcp("10.0.0.2", "10.0.0.1", 12345, 80, seq=1000, flags=0x02)
    check_eq(int.from_bytes(my_seg[16:18], "big"), 0x6C7E,
             "TCP 校验和（scapy 交叉验证值 0x6c7e）")
    my_ip = build_ipv4("10.0.0.2", "10.0.0.1", 6, my_seg, ident=1)
    check_eq(int.from_bytes(my_ip[10:12], "big"), 0x66CD,
             "IPv4 头校验和（scapy 交叉验证值 0x66cd）")
    check_eq(my_ip[:20].hex(" "),
             "45 00 00 28 00 01 00 00 40 06 66 cd 0a 00 00 02 0a 00 00 01",
             "IPv4 头逐字节（与 scapy 输出一致）")
    check_true(verify_ipv4_checksum(my_ip[:20]), "自造 IPv4 头校验和自洽")
    broken = bytearray(my_ip[:20])
    broken[8] ^= 0x01                                   # 改 TTL 一位
    check_true(not verify_ipv4_checksum(bytes(broken)), "改一位后校验和必须失败")
    print("✅ 校验和：RFC 1071 例子 + scapy 交叉验证 + 奇数长度 + 篡改检测 全部一致")

    # ── 2) 解析器逐层字段（用手工构造的、已知内容的包）──
    frame = build_eth_frame("aa:00:00:00:00:20", "aa:00:00:00:00:10", ETHERTYPE_IPV4,
                            build_ipv4("10.0.0.2", "10.0.0.1", 6,
                                       build_tcp("10.0.0.2", "10.0.0.1", 12345, 80,
                                                 seq=1000, flags=0x12,
                                                 options=b"\x02\x04\x05\xb4"),
                                       ttl=55))
    pkt = dissect_packet(RawPacket(index=1, ts=1.0, data=frame, orig_len=len(frame)))
    check_eq(pkt["ether"]["src"], "aa:00:00:00:00:10", "以太网源 MAC")
    check_eq(pkt["ether"]["ethertype"], ETHERTYPE_IPV4, "以太网类型")
    check_eq(pkt["ip"]["ttl"], 55, "IP TTL")
    check_eq(pkt["ip"]["proto_name"], "TCP", "IP 协议名")
    check_true(pkt["ip"]["checksum_ok"], "IP 校验和验证通过")
    check_eq(pkt["ip"]["header_len"], 20, "IP 头长度（ihl*4）")
    check_eq(pkt["tcp"]["sport"], 12345, "TCP 源端口")
    check_eq(pkt["tcp"]["dport"], 80, "TCP 目的端口")
    check_eq(pkt["tcp"]["flags"], "SYN,ACK", "TCP 标志显示顺序")
    check_true(pkt["tcp"]["syn"] and pkt["tcp"]["ack_flag"], "SYN/ACK 位")
    check_true(pkt["tcp"]["checksum_ok"], "TCP 校验和（含伪首部）验证通过")
    check_eq(pkt["tcp"]["options"][0]["name"], "MSS", "TCP 选项名")
    check_eq(pkt["tcp"]["options"][0]["value"], 1460, "MSS 值")
    check_eq(pkt["protocols"], "ether:ip:tcp", "协议栈层名")
    print(f"✅ 解析：ether/ip/tcp 字段、标志顺序、选项、校验和 —— {pkt_summary(pkt)}")

    # VLAN：手工在 Ether 头后插入 4 字节 802.1Q 标签，验证"必须剥 VLAN 才不会错位"
    inner = build_ipv4("10.0.0.2", "10.0.0.1", 6, build_tcp("10.0.0.2", "10.0.0.1", 1, 2))
    tagged = (mac_bytes("aa:00:00:00:00:20") + mac_bytes("aa:00:00:00:00:10") +
              struct.pack("!HHH", ETHERTYPE_VLAN, 100, ETHERTYPE_IPV4) + inner)
    t_pkt = dissect_packet(RawPacket(index=1, ts=1.0, data=tagged, orig_len=len(tagged)))
    check_eq(t_pkt["ether"]["vlans"][0]["vid"], 100, "VLAN ID")
    check_eq(t_pkt["ip"]["dst"], "10.0.0.1", "剥掉 VLAN 后的 IP 目的地址")
    print("✅ VLAN：0x8100 标签被正确剥离（vid=100），内层 IP 未错位")

    # 分片：frag_offset 单位是 8 字节，解析时必须乘 8
    frag_frame = build_eth_frame("aa:00:00:00:00:20", "aa:00:00:00:00:10", ETHERTYPE_IPV4,
                                 build_ipv4("10.0.0.2", "10.0.0.1", 6, b"A" * 24,
                                            flags_frag=0x2000 | 3))
    f_pkt = dissect_packet(RawPacket(index=1, ts=1.0, data=frag_frame,
                                     orig_len=len(frag_frame)))
    check_eq(f_pkt["ip"]["frag_offset"], 24, "分片偏移（3*8）")
    check_true(f_pkt["ip"]["mf"], "MF 标志")
    check_true("tcp" not in f_pkt, "非首片不应被当成 TCP 解析")
    print("✅ 分片：frag_offset=24（3×8）、MF=1，且非首片不误判为 TCP")

    # UDP / DNS
    dns_q = build_dns_query(0xABCD, "www.example.com")
    check_eq(dissect_dns(dns_q)["qry_name"], "www.example.com", "DNS 查询名")
    check_eq(dissect_dns(dns_q)["questions"][0]["type_name"], "A", "DNS 查询类型")
    dns_r = build_dns_response(0xABCD, "www.example.com", "93.184.216.34")
    r = dissect_dns(dns_r)
    check_true(r["response"], "DNS 应答 QR 位")
    check_eq(r["answers_a"], ["93.184.216.34"], "DNS 应答 A 记录（压缩指针解析）")
    uframe = build_eth_frame("aa:00:00:00:00:53", "aa:00:00:00:00:10", ETHERTYPE_IPV4,
                             build_ipv4("10.0.0.10", "10.0.0.53", 17,
                                        build_udp("10.0.0.10", "10.0.0.53", 53124, 53, dns_q)))
    u_pkt = dissect_packet(RawPacket(index=1, ts=1.0, data=uframe, orig_len=len(uframe)))
    check_eq(u_pkt["udp"]["sport"], 53124, "UDP 源端口")
    check_true(u_pkt["udp"]["checksum_ok"], "UDP 校验和（含伪首部）验证通过")
    check_eq(u_pkt["dns"]["qry_name"], "www.example.com", "顶层解析出的 DNS 查询名")
    print("✅ UDP/DNS：端口、A 记录、压缩指针、校验和 —— 全部正确")

    # ICMP：校验和**不含伪首部**（这条最容易和 TCP/UDP 搞混）
    icmp = build_icmp(8, 0, ident=7, seq=9, payload=b"hello")
    check_true(ones_complement_sum(icmp) == 0xFFFF, "ICMP 校验和（无伪首部）自洽")
    check_eq(dissect_icmp(icmp)["type_name"], "Echo Request", "ICMP 类型名")
    print("✅ ICMP：校验和自洽（无伪首部，与 TCP/UDP 的算法不同）")

    # HTTP：请求解析 + **敏感头必须被掩码而不是原样输出**
    req = (b"POST /api/login?user=admin&password=hunter2 HTTP/1.1\r\n"
           b"Host: app.example.com\r\nCookie: SID=deadbeefcafe\r\n"
           b"Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig\r\n\r\n"
           b"user=admin&password=hunter2")
    h = dissect_http(req)
    check_eq(h["method"], "POST", "HTTP 方法")
    check_eq(h["host"], "app.example.com", "HTTP Host")
    check_eq(h["uri"], "/api/login?user=admin&password=hunter2", "HTTP URI")
    check_true(len(h["sensitive"]) >= 3, f"敏感信息条数 ≥3，实际 {len(h['sensitive'])}")
    check_true(all("hunter2" not in s["masked"] for s in h["sensitive"]),
               "掩码后的值不得包含原始密码")
    check_true(all("deadbeefcafe" not in s["masked"] for s in h["sensitive"]),
               "掩码后的值不得包含原始 Cookie")
    check_eq(dissect_http(b"HTTP/1.1 404 Not Found\r\nServer: x\r\n\r\n")["response_code"],
             "404", "HTTP 响应码")
    check_true(dissect_http(b"\x16\x03\x01\x00\x50garbage") is None, "TLS 记录不应被当 HTTP")
    print(f"✅ HTTP：请求/响应解析正常；敏感值全部掩码（例：{h['sensitive'][0]['masked']}）")

    # 畸形/截断包：必须"返回 None 或跳过该层"，而不是抛异常
    check_true(dissect_ethernet(b"\x00" * 4) is None, "截断以太网帧返回 None")
    check_true(dissect_ipv4(b"\x45\x00") is None, "截断 IP 头返回 None")
    check_true(dissect_tcp(b"\x00" * 5, "1.1.1.1", "2.2.2.2") is None, "截断 TCP 返回 None")
    short = dissect_packet(RawPacket(index=1, ts=0.0, data=b"\x45\x00\x00", orig_len=3))
    check_eq(short["layers"], [], "畸形包不应崩溃，层列表为空")
    print("✅ 健壮性：截断/畸形包返回 None 或被跳过，解析器不崩溃")

    # ── 3) pcap / pcapng 读写往返 ──
    tmp = tmpdir or tempfile.mkdtemp(prefix="day157-selftest-")
    os.makedirs(tmp, exist_ok=True)
    sample = build_demo_packets()

    p1 = os.path.join(tmp, "roundtrip.pcap")
    check_eq(write_pcap(p1, sample), len(sample), "写出的包数")
    back = list(iter_capture(p1))
    check_eq(len(back), len(sample), "读回的包数")
    check_eq([p.orig_len for p in back], [p.orig_len for p in sample], "orig_len 一致")
    check_eq([p.data for p in back][:5], [p.data for p in sample][:5], "前 5 包字节一致")
    check_eq(round(back[3].ts - back[1].ts, 6), round(sample[3].ts - sample[1].ts, 6),
             "时间戳间隔（微秒精度）")
    print(f"✅ pcap 往返：{len(sample)} 包字节级一致（含时间戳）")

    # 大端 pcap：字节序判断错了会读出天文数字，这里显式验证两条分支
    p2 = os.path.join(tmp, "be.pcap")
    with open(p2, "wb") as f:
        f.write(build_pcap_bytes(sample[:12], endian=">"))
    check_eq(len(list(iter_capture(p2))), 12, "大端 pcap 读取包数")
    print("✅ 大端 pcap：魔数 0xd4c3b2a1 被正确识别，字节序切换到 >")

    # pcapng（Wireshark 默认格式）：块结构与时间戳 64 位拼接
    p3 = os.path.join(tmp, "roundtrip.pcapng")
    with open(p3, "wb") as f:
        f.write(build_pcapng_bytes(sample[:20]))
    ng = list(iter_capture(p3))
    check_eq(len(ng), 20, "pcapng 读回包数")
    check_eq(ng[5].data, sample[5].data, "pcapng 第 6 包字节一致")
    check_eq(round(ng[5].ts - ng[0].ts, 6), round(sample[5].ts - sample[0].ts, 6),
             "pcapng 时间戳（EPB 高低 32 位拼接）")
    check_eq(sniff_format(p3), "pcapng", "格式自动识别")
    print("✅ pcapng：SHB/IDB/EPB 块解析 + 时间戳拼接正确（自动识别格式）")

    # ── 4) 显示过滤器引擎 ──
    demo = os.path.join(tmp, "demo.pcap")
    write_demo_pcap(demo)
    parsed = [dissect_packet(r) for r in iter_capture(demo)]
    check_eq(len(parsed), len(sample), "合成流量包数")

    def count(expr):
        return sum(1 for p in apply_filter(parsed, expr))

    check_eq(count("tcp"), sum(1 for p in parsed if "tcp" in p), "tcp 裸协议名")
    syn80 = count("tcp.flags.syn == 1 and tcp.dstport == 80")
    expect_syn80 = (1 +                                    # 正常会话 SYN
                    DEMO_FACTS["flood_syn_count"] +        # 洪水
                    1 +                                    # bad checksum 包
                    1)                                     # 扫描里的 80 端口
    check_eq(syn80, expect_syn80, "SYN 且目的端口 80 的包数")
    check_eq(count("ip.addr == 10.0.0.66"), len(DEMO_FACTS["scanned_ports"]) + 0,
             "按 IP 过滤（扫描器发出的全部包）")
    check_eq(count("ip.addr == 10.0.0.20 and tcp.port == 80"),
             sum(1 for p in parsed if "tcp" in p and
                 ("10.0.0.20" in (p["ip"]["src"], p["ip"]["dst"])) and
                 (80 in (p["tcp"]["sport"], p["tcp"]["dport"]))),
             "ip+tcp 组合过滤")
    # 有 http 层的包 = 正常 GET 请求(1) + 200 响应(1) + 4 次心跳 POST(4) = 6
    check_eq(count("http"), 6, "HTTP 包数（1 请求 + 1 响应 + 4 次心跳 POST）")
    print(f"✅ 过滤器：tcp={count('tcp')}  syn&dport80={syn80}  "
          f"ip.addr==10.0.0.66={count('ip.addr == 10.0.0.66')}")

    # 过滤器的错误处理必须是"人话"，不能静默返回空
    for bad_expr, why in [("tcp.port == ", "运算符后缺值"),
                          ("(tcp", "括号不配对"),
                          ("no_such_field == 1", "未知字段名"),
                          ("tcp.port == 80 extra", "多余 token")]:
        try:
            compile_filter(bad_expr)
        except FilterError:
            pass
        else:
            raise AssertionError(f"表达式 {bad_expr!r}（{why}）本应报错却通过了")
    print("✅ 过滤器错误处理：缺值/括号/未知字段/多余 token 全部报 FilterError")

    # ── 5) BPF → display filter 的等价翻译（教学用）──
    check_eq(bpf_to_display("tcp port 80"), "tcp.port == 80", "BPF: tcp port 80")
    check_eq(bpf_to_display("icmp"), "icmp", "BPF: icmp")
    check_eq(bpf_to_display("port 53"), "(tcp.port == 53 or udp.port == 53)", "BPF: port 53")
    check_eq(bpf_to_display("host 10.0.0.1"), "ip.addr == 10.0.0.1", "BPF: host")
    check_eq(bpf_to_display("tcp[tcpflags] & tcp-syn != 0"), "tcp.flags.syn == 1",
             "BPF: 只看 SYN")
    check_eq(bpf_to_display("tcp and not port 22"),
             "((tcp) and ((not ((tcp.port == 22 or udp.port == 22)))))", "BPF: and/not 组合")
    check_true(bpf_to_display("ether proto 0x888e") is None, "不支持的 BPF 应返回 None")
    # 翻译结果必须真的等价：用"只看 SYN"的 BPF 与 display filter 结果对比
    bpf_equiv = sum(1 for p in 
                    apply_filter(parsed, bpf_to_display("tcp[tcpflags] & tcp-syn != 0"))
                    if "tcp" in p)
    check_eq(bpf_equiv, count("tcp.flags.syn == 1"), "BPF 与 display filter 等价性")
    print("✅ BPF 翻译：常见写法可等价映射到 display filter（含 SYN/port/host/not）")

    # ── 6) 合成流量本身的一致性（给 03 的检测器当"标准答案"）──
    check_eq(len(sample), 70, "合成流量总包数（改流量必须同步改这里）")
    check_eq(sum(1 for p in parsed if "http" in p), 6,
             "HTTP 包数（1 正常请求 + 1 响应 + 4 次心跳 POST）")
    check_eq(sum(1 for p in parsed if "dns" in p), 5, "DNS 包数：1 查询 + 1 应答 + 3 隧道")
    check_eq(sum(1 for p in parsed if "arp" in p), 3, "ARP 包数")
    check_eq(sum(1 for p in parsed if "icmp" in p), 2, "ICMP 包数")
    check_eq(sum(1 for p in parsed if p.get("ip") and not p["ip"]["checksum_ok"]), 1,
             "校验和错误的包数（正好 1 个植入的坏包）")
    print(f"✅ 合成流量：{len(sample)} 包 / HTTP 6 / DNS 5 / ARP 3 / ICMP 2 / 坏校验和 1")

    if tmpdir is None:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════
# 8. CLI
# ══════════════════════════════════════════════════════════════════════════

def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(
        description="pcap_lib：纯标准库的 pcap/pcapng 解析与显示过滤器引擎")
    ap.add_argument("--self-test", action="store_true", help="离线自检（输出 SELF-TEST OK）")
    ap.add_argument("--dump", metavar="FILE", help="逐包解析并打印摘要")
    ap.add_argument("--filter", metavar="EXPR", default=None,
                    help="显示过滤器表达式，例如 'tcp.flags.syn==1 and tcp.dstport==80'")
    ap.add_argument("--limit", type=int, default=0, help="最多打印多少个包（0=全部）")
    ap.add_argument("--write-demo", metavar="PATH", default=None,
                    help="生成合成抓包到指定路径（不给则写进临时目录）")
    ap.add_argument("--show-hex", type=int, default=0, metavar="N",
                    help="每个包额外打印前 N 字节十六进制")
    args = ap.parse_args(argv)

    if args.self_test:
        try:
            self_test()
        except AssertionError as e:
            print(f"SELF-TEST FAIL: {e}")
            return 1
        except Exception as e:                      # noqa: BLE001 —— 自检要报告任何异常
            print(f"SELF-TEST FAIL: {type(e).__name__}: {e}")
            return 1
        print("SELF-TEST OK")
        return 0

    if args.write_demo:
        n = write_demo_pcap(args.write_demo)
        print(f"已生成合成抓包：{args.write_demo}（{n} 个包，"
              f"{os.path.getsize(args.write_demo)} 字节）")
        return 0

    if not args.dump:
        ap.print_help()
        return 0

    try:
        ast = compile_filter(args.filter) if args.filter else None
    except FilterError as e:
        print(f"❌ 过滤器语法错误：{e}")
        return 2
    shown = matched = 0
    try:
        for raw in iter_capture(args.dump):
            pkt = dissect_packet(raw)
            if ast is not None and not eval_filter(ast, pkt):
                continue
            matched += 1
            if args.limit and shown >= args.limit:
                continue
            shown += 1
            print(pkt_summary(pkt))
            if args.show_hex:
                print(hexdump(raw.data, limit=args.show_hex))
    except ValueError as e:
        print(f"❌ 读取失败：{e}")
        return 2
    print(f"\n匹配 {matched} 个包" + (f"（已打印前 {shown} 个）" if args.limit else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
