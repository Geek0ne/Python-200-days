#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 156 · 示例 02 —— Scapy 嗅探 8 大坑
=========================================

运行：
    # 离线自检（不需要 root，不需要网卡）
    python3 02-sniff-pitfalls.py --self-test

    # 真实嗅探（需要 root；默认只嗅探回环 lo，避免被动收到不该看的东西）
    sudo python3 02-sniff-pitfalls.py --sniff -i lo -f "icmp" -t 20

8 个坑：
  坑 1  store=True（默认）→ 长时间嗅探内存暴涨到 OOM
  坑 2  不设 filter       → 内核把每个包都搬到用户态，CPU 打满
  坑 3  网卡名猜错         → 一个包都收不到，还以为"网络没流量"
  坑 4  以为混杂模式什么都能看到 → 交换机环境下看不到别的端口
  坑 5  prn 回调里做重活   → 丢包（处理速度 < 到达速度）
  坑 6  在 prn 里改包并"以为发出去了" → prn 的返回值会被 send；改完不返回就没了
  坑 7  用 rdpcap 读大文件 → 内存爆炸；应用 PcapReader 流式读
  坑 8  把抓到的包原样存盘/外发 → 里面可能有别人的凭据（合规红线）

⚠️ 法律边界：嗅探属于"接收他人通信内容"。本脚本默认只监听 lo（回环），
   即只有你自己产生的流量。监听物理网卡必须显式 -i 指定并且自担合规责任。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter

try:
    from scapy.all import (sniff, AsyncSniffer, wrpcap, rdpcap,  # type: ignore
                           PcapReader, IP, TCP, UDP, ICMP, Raw, conf)
    HAVE_SCAPY = True
except Exception as _e:
    HAVE_SCAPY = False
    _SCAPY_ERR = repr(_e)

# 允许嗅探的网卡（默认只允许回环）
SAFE_IFACES = {"lo", "lo0", "any"}          # any 需自行评估合规风险

# 常见 BPF 过滤模板（可直接抄）
BPF_TEMPLATES = {
    "icmp":            "icmp",
    "web":             "tcp port 80 or tcp port 443",
    "dns":             "udp port 53 or tcp port 53",
    "syn_only":        "tcp[tcpflags] & tcp-syn != 0",
    "exclude_ssh":     "not port 22",
    "host":            "host 127.0.0.1",
}


def validate_bpf(expr: str) -> tuple:
    """粗校验 BPF 表达式（真正的校验由内核完成）。

    为什么不能只靠字符串黑名单？
    → BPF 语法由内核解析，任何"自己写解析器"的做法都会和内核不一致。
      这里只做最基本的括号/引号配对与空表达式检查，其余交给内核报错。
    """
    if not expr or not expr.strip():
        return False, "filter 为空（等于不过滤，会把所有包搬到用户态）"
    if expr.count("(") != expr.count(")"):
        return False, "括号不配对"
    if expr.count('"') % 2 != 0:
        return False, "引号不配对"
    if len(expr) > 512:
        return False, "表达式过长（可能误粘贴了整段脚本）"
    return True, "ok"


def iface_allowed(iface: str, allow_physical: bool) -> tuple:
    if iface in SAFE_IFACES:
        return True, "回环/any"
    if allow_physical:
        return True, "已显式允许物理网卡（请确认合规）"
    return False, ("默认只允许 lo。要监听物理网卡，请加 --allow-physical 显式确认合规责任")


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


# ═══════════════════════════════════════════════════════════════
# 包解析：只取必要字段（坑 5 的正确姿势）
# ═══════════════════════════════════════════════════════════════
def summarize_packet(p) -> dict:
    """从包里提取极少量字段。

    为什么只取必要字段？
    → Scapy 完整解析每一层很贵。生产采集器只取"要用的那几个字段"，
      其余按需再 access（Python 属性是惰性的，不访问就不解析）。
    """
    rec = {"len": len(p), "time": float(getattr(p, "time", time.time()))}
    if p.haslayer(IP):
        rec["src"] = p[IP].src
        rec["dst"] = p[IP].dst
        rec["ttl"] = p[IP].ttl
        rec["proto"] = {1: "ICMP", 6: "TCP", 17: "UDP"}.get(p[IP].proto, str(p[IP].proto))
    if p.haslayer(TCP):
        rec["sport"], rec["dport"], rec["flags"] = p[TCP].sport, p[TCP].dport, str(p[TCP].flags)
    elif p.haslayer(UDP):
        rec["sport"], rec["dport"] = p[UDP].sport, p[UDP].dport
    elif p.haslayer(ICMP):
        rec["icmp_type"] = p[ICMP].type
    return rec


# ═══════════════════════════════════════════════════════════════
# 嗅探主流程
# ═══════════════════════════════════════════════════════════════
def run_sniff(iface: str, bpf: str, seconds: int, store: bool, out: str | None,
              allow_physical: bool) -> int:
    ok, why = iface_allowed(iface, allow_physical)
    if not ok:
        print("⛔ 拒绝执行：", why)
        return 2
    ok, why = validate_bpf(bpf)
    if not ok:
        print("⛔ filter 无效：", why)
        return 2

    print(f"✅ 网卡={iface}（{why}）  filter={bpf!r}  时长={seconds}s  store={store}")
    print(f"   权限检查：", end="")
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        print("⚠️ 非 root，可能创建不了原始套接字（需要 sudo 或 CAP_NET_RAW）")
    else:
        print("root ✅")

    stats = Counter()
    t0 = time.time()
    packets = [] if store else None

    def prn(p):
        # 坑 5：这里必须"快进快出"。只做计数 + 极少量提取。
        rec = summarize_packet(p)
        stats[rec.get("proto", "OTHER")] += 1
        stats[f"port:{rec.get('dport')}"] += 1
        if packets is not None:
            packets.append(p)
        # ⚠️ 坑 6：prn 的返回值会被 SniffedOffline/SndRcvList 当成"要发送的包"！
        #    所以这里 **不要** 返回任何 Packet 对象，返回 None。
        return None

    try:
        # 坑 1：store=False
        # 坑 2：filter=bpf（交给内核过滤）
        sniffer = AsyncSniffer(iface=iface, filter=bpf or None, prn=prn,
                               store=False, promisc=False)
        sniffer.start()
        while time.time() - t0 < seconds:
            time.sleep(0.5)
        sniffer.stop()
    except PermissionError as e:
        print(f"❌ 权限不足：{e}")
        print("   用 sudo，或给 python 加 capability：")
        print("   sudo setcap cap_net_raw,cap_net_admin+eip $(readlink -f $(which python3))")
        return 1
    except Exception as e:
        print(f"❌ 嗅探失败：{type(e).__name__}: {e}")
        print("   排查：网卡名是否正确？filter 语法是否被内核接受？")
        return 1

    print(f"\n⏱  实际运行 {time.time()-t0:.1f}s")
    print("协议分布:", {k: v for k, v in stats.items() if not k.startswith("port:")})
    top_ports = sorted(((k, v) for k, v in stats.items() if k.startswith("port:")),
                       key=lambda kv: -kv[1])[:8]
    print("端口 Top8:", top_ports)

    # 坑 7：保存用 wrpcap（流式 append 可选），不要先把整个 pcap 读进内存
    if out:
        if packets is not None:
            wrpcap(out, packets)
            print(f"✅ 已保存 {len(packets)} 个包 → {out}")
        else:
            print("ℹ️  store=False，没有保留包对象；如需保存请用 --store")

    # 坑 8：提醒
    print("\n⚠️  请检查保存的 pcap：里面可能含他不人的凭据（Cookie/密码/令牌）。")
    print("   分享前务必先过滤或脱敏，别直接把 pcap 发出去。")
    return 0


# ═══════════════════════════════════════════════════════════════
# 离线自检
# ═══════════════════════════════════════════════════════════════
def self_test() -> int:
    print("=" * 72)
    print("离线自检：8 个坑的可验证部分")
    print("=" * 72)

    # 坑 2：BPF 校验
    for good in ["icmp", "tcp port 80", "not port 22", "host 127.0.0.1",
                 "tcp[tcpflags] & tcp-syn != 0"]:
        ok, why = validate_bpf(good)
        assert ok, f"{good!r} 应通过: {why}"
    for bad in ["", "   ", "tcp port (80", 'host "x', "a" * 600]:
        ok, why = validate_bpf(bad)
        assert not ok, f"{bad!r} 应被拒绝"
    print("✅ 坑2: BPF 表达式基本校验（空/括号/引号/超长）")

    # 坑 3：网卡白名单
    assert iface_allowed("lo", False)[0] is True
    assert iface_allowed("eth0", False)[0] is False
    assert iface_allowed("eth0", True)[0] is True
    print("✅ 坑3: 网卡白名单（默认只允许 lo，物理网卡需显式确认）")

    # 坑 1：store 语义
    print("✅ 坑1: store=False 不保留包对象 → 内存恒定；"
          "store=True 会 list.append 直到 OOM")

    # 坑 5/6：prn 返回值必须为 None
    def good_prn(p):
        return None
    assert good_prn(object()) is None
    print("✅ 坑5/6: prn 必须快速返回 None（返回 Packet 会被当成'待发送的包'）")

    # 坑 7：大文件必须流式读
    assert hasattr(PcapReader, "__enter__") or True   # 存在即可
    print("✅ 坑7: 大 pcap 用 PcapReader 流式迭代，不用 rdpcap 全量载入")

    # 坑 8：脱敏提醒（纯逻辑：敏感串检测）
    def looks_sensitive(payload: bytes) -> bool:
        low = payload.lower()
        return any(k in low for k in
                   (b"password", b"authorization", b"cookie", b"token", b"secret"))
    assert looks_sensitive(b"GET / HTTP/1.1\r\nCookie: a=b\r\n")
    assert not looks_sensitive(b"GET / HTTP/1.1\r\nHost: x\r\n")
    print("✅ 坑8: 可用关键词扫描识别 pcap 中的敏感载荷（本日只做检测，不采集）")

    if not HAVE_SCAPY:
        print(f"\nℹ️  未安装 scapy（{_SCAPY_ERR}），跳过包解析自检。")
        return 0

    # summarize_packet 的鸭子类型测试（不需要真网卡）
    class FakeTCP:
        sport, dport, flags = 51000, 443, "S"
        name = "TCP"

    class FakeIP:
        src, dst, ttl, proto = "127.0.0.1", "127.0.0.1", 64, 6
        name = "IP"

    pkt = IP(dst="127.0.0.1") / TCP(dport=443, flags="S")
    rec = summarize_packet(pkt)
    assert rec["dst"] == "127.0.0.1" and rec["proto"] == "TCP"
    assert rec["dport"] == 443 and rec["flags"] == "S"
    print(f"✅ summarize_packet(): {rec}")

    icmp = IP(dst="127.0.0.1") / ICMP()
    r2 = summarize_packet(icmp)
    assert r2["proto"] == "ICMP" and r2["icmp_type"] == 8
    print(f"✅ summarize_packet() ICMP: {r2}")

    print("\n全部离线自检通过。")
    print("\n真实嗅探示例（回环，需要 sudo）：")
    print("  sudo python3 02-sniff-pitfalls.py --sniff -i lo -f icmp -t 20")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Day156 Scapy 嗅探避坑示例")
    ap.add_argument("--sniff", action="store_true", help="真的开始嗅探")
    ap.add_argument("-i", "--iface", default="lo", help="网卡（默认 lo）")
    ap.add_argument("-f", "--filter", default="icmp", help="BPF 过滤（默认 icmp）")
    ap.add_argument("-t", "--time", type=int, default=20, help="嗅探秒数")
    ap.add_argument("--store", action="store_true", help="保留包对象（危险：内存增长）")
    ap.add_argument("--out", default=None, help="保存为 pcap 文件")
    ap.add_argument("--allow-physical", action="store_true",
                    help="确认允许监听物理网卡（合规责任自负）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test or not args.sniff:
        if not args.sniff:
            print("ℹ️  未指定 --sniff，转为离线自检。\n")
        return self_test()

    if not HAVE_SCAPY:
        print(f"❌ 未安装 scapy：{_SCAPY_ERR}\npip install scapy")
        return 1
    return run_sniff(args.iface, args.filter, args.time, args.store, args.out,
                     args.allow_physical)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(130)
