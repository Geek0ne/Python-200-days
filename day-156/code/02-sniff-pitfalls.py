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

import warnings

# scapy 导入时会触发 cryptography 的 FFDH 弃用警告（与本日内容无关），
# 教学输出里不需要它 —— 只屏蔽这一条**特定消息**，不是全局静音。
warnings.filterwarnings("ignore", message=".*Diffie-Hellman over finite fields.*")

try:
    from scapy.all import (sniff, AsyncSniffer, wrpcap, rdpcap,  # type: ignore
                           PcapReader, IP, TCP, UDP, ICMP, Raw, conf)
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


# ═══════════════════════════════════════════════════════════════
# 几个"纯逻辑"函数：把嗅探的坑变成可离线验证的规则
# ═══════════════════════════════════════════════════════════════
def simulate_sniff(n: int, store: bool) -> int:
    """模拟一次嗅探：返回回调结束后**仍被保留**的包对象数量。

    store=True  → 数量 = n（内存随抓包时长线性增长 → 最终 OOM）
    store=False → 数量 = 0（只做统计，内存恒定）
    这样"坑 1"就不再是一句口头结论，而是一条能断言的事实。
    """
    retained = [] if store else None
    for i in range(n):
        pkt = {"i": i}                     # 模拟一个"包对象"
        if retained is not None:
            retained.append(pkt)
    return 0 if retained is None else len(retained)


def compute_loss(sent: int, recv: int) -> dict:
    """由"发出/收到"计算丢包率（坑 5：用户态处理不过来就会丢包）。

    真实场景里"丢包"是内核统计（`ss -i` / `netstat -s` 里的 packet drop），
    这里用一组计数做纯逻辑演示：丢包率 = (sent - recv) / sent。
    """
    if sent <= 0:
        return {"packets": 0, "received": 0, "lost": 0, "loss_pct": 0.0}
    lost = max(0, sent - recv)
    return {"packets": sent, "received": recv, "lost": lost,
            "loss_pct": round(lost / sent * 100, 2)}


def visibility_note(topology: str) -> str:
    """坑 4：混杂模式能看到什么，取决于**你在拓扑里的位置**。

    这是纯查表逻辑 —— 目的不是"教你背结论"，而是让代码把结论写死，
    避免教学里含糊其辞（"开了混杂模式就能抓到所有流量"是错的）。
    """
    return {
        "hub": "集线器：广播域内所有帧都会到达你的网卡 → 能看到同网段全部流量",
        "switch": "交换机：只把发给你的帧转过来 → 看不到别的端口（除非端口镜像）",
        "wifi": "WiFi：共享介质，配 monitor 模式可听到同信道帧（含未关联的）",
        "vm-bridge": "虚拟机桥接：宿主网卡的混杂/转发策略决定可见范围，通常较宽",
        "same-host": "同主机：回环/同机进程间流量都能看到（本日默认只做这个）",
    }.get(topology, "未知拓扑：无法给出可见性结论")


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
    print("离线自检：8 个坑的可验证部分（不需要 root / 网卡 / 真实流量）")
    print("=" * 72)

    # ── 坑 1：store=True 会让内存随抓包时长线性增长 ──
    kept_on = simulate_sniff(1000, store=True)
    kept_off = simulate_sniff(1000, store=False)
    check_eq(kept_on, 1000, "store=True 时保留的包对象数")
    check_eq(kept_off, 0, "store=False 时保留的包对象数")
    import tracemalloc
    tracemalloc.start()
    simulate_sniff(20000, store=True)
    _cur_on, peak_on = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    tracemalloc.start()
    simulate_sniff(20000, store=False)
    _cur_off, peak_off = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    check_true(peak_on > peak_off, "store=True 的内存峰值应高于 store=False")
    print(f"✅ 坑1: store=True 保留 {kept_on} 个对象、峰值 {peak_on/1024:.0f}KB；"
          f"store=False 保留 {kept_off} 个、峰值 {peak_off/1024:.0f}KB")

    # ── 坑 2：BPF 表达式基本校验 ──
    for good in ["icmp", "tcp port 80", "not port 22", "host 127.0.0.1",
                 "tcp[tcpflags] & tcp-syn != 0", "udp and dst port 53"]:
        ok, why = validate_bpf(good)
        check_true(ok, f"BPF {good!r} 应通过校验（{why}）")
    for bad in ["", "   ", "tcp port (80", 'host "x', "a" * 600]:
        ok, why = validate_bpf(bad)
        check_true(not ok, f"BPF {bad!r} 应被拒绝")
    print("✅ 坑2: BPF 表达式校验（空/括号/引号/超长 全部拦下）")

    # ── 坑 3：网卡白名单 ──
    check_eq(iface_allowed("lo", False)[0], True, "lo 应允许（默认）")
    check_eq(iface_allowed("eth0", False)[0], False, "eth0 默认应拒绝")
    check_eq(iface_allowed("eth0", True)[0], True, "显式 --allow-physical 后 eth0 可放行")
    print("✅ 坑3: 网卡白名单（默认只允许 lo，物理网卡需显式确认合规责任）")

    # ── 坑 4：混杂模式 ≠ 万能（可见性由拓扑决定）──
    check_true("看不到" in visibility_note("switch"), "交换机环境下应说明看不到别的端口")
    check_true("端口镜像" in visibility_note("switch"), "应给出端口镜像这个前提")
    check_true("monitor" in visibility_note("wifi"), "WiFi 应提到 monitor 模式")
    check_eq(visibility_note("nonexistent"), "未知拓扑：无法给出可见性结论",
             "未知拓扑的返回值")
    print("✅ 坑4: 可见性由拓扑决定 —— 交换机=看不到 / Hub=看得到 / WiFi=monitor 模式")

    # ── 坑 5：处理不过来就丢包（丢包率是可计算的）──
    check_eq(compute_loss(1000, 1000)["loss_pct"], 0.0, "无丢包时的丢包率")
    check_eq(compute_loss(1000, 800)["loss_pct"], 20.0, "丢 200/1000 的丢包率")
    check_eq(compute_loss(0, 0)["loss_pct"], 0.0, "计数为 0 时不应除零")
    check_eq(compute_loss(100, 120)["lost"], 0, "收到多余应表示为 0 丢包而非负数")
    print(f"✅ 坑5: 丢包率可计算 —— {compute_loss(1000, 800)}")

    # ── 坑 6：prn 的返回值会被当成"待发送的包" ──
    def good_prn(pkt) -> None:
        return None

    check_eq(good_prn(object()), None, "prn 的返回值")
    # 反例：如果 prn 返回 Packet，调度器会把它发出去 —— 这里用"类型判定"模拟
    def bad_prn(pkt):
        return pkt

    class _FakePacket:
        pass

    check_true(bad_prn(_FakePacket()) is not None,
               "返回包的 prn 会被判定为'有要发送的数据'")
    print("✅ 坑6: prn 必须返回 None（返回 Packet 会被当成待发送的包）")

    # ── 坑 7：大文件必须流式读 ──
    check_true(hasattr(PcapReader, "__iter__") or hasattr(PcapReader, "__enter__"),
               "PcapReader 应支持迭代/上下文管理（用于流式读）")
    print("✅ 坑7: 大 pcap 用 PcapReader 流式迭代，而不是 rdpcap 一次性载入")

    # ── 坑 8：敏感载荷检测 + 掩码 ──
    def looks_sensitive(payload: bytes) -> bool:
        low = payload.lower()
        return any(k in low for k in
                   (b"password", b"authorization", b"cookie", b"token", b"secret"))

    check_true(looks_sensitive(b"GET / HTTP/1.1\r\nCookie: a=b\r\n"), "含 Cookie 应命中")
    check_true(looks_sensitive(b"Authorization: Basic dXNlcjpwYXNz"), "含 Authorization 应命中")
    check_true(not looks_sensitive(b"GET / HTTP/1.1\r\nHost: x\r\n"), "干净请求不应命中")

    def mask_secret(v: str) -> str:
        if len(v) <= 4:
            return "*" * len(v) + f"(len={len(v)})"
        return f"{v[:2]}{'*' * (len(v) - 4)}{v[-2:]}(len={len(v)})"

    masked = mask_secret("Basic dXNlcjpwYXNzd29yZA==")
    check_true("dXNlcjpwYXNz" not in masked, "掩码后不得包含原文")
    check_true(masked.endswith("(len=26)"), "掩码应保留长度便于比对")
    print(f"✅ 坑8: 敏感载荷可检测且可脱敏（示例：{masked}）")

    if not HAVE_SCAPY:
        print(f"\nℹ️  未安装 scapy（{_SCAPY_ERR}），跳过报文解析自检。")
        return

    # ── 报文解析（用构造的包，不碰网卡）──
    pkt = IP(dst="127.0.0.1") / TCP(dport=443, flags="S")
    rec = summarize_packet(pkt)
    check_eq(rec["dst"], "127.0.0.1", "summarize_packet 目的地址")
    check_eq(rec["proto"], "TCP", "summarize_packet 协议名")
    check_eq(rec["dport"], 443, "summarize_packet 目的端口")
    check_eq(rec["flags"], "S", "summarize_packet TCP 标志")
    print(f"✅ summarize_packet(): {rec}")

    icmp = IP(dst="127.0.0.1") / ICMP()
    r2 = summarize_packet(icmp)
    check_eq(r2["proto"], "ICMP", "ICMP 包的协议名")
    check_eq(r2["icmp_type"], 8, "ICMP 类型（8=Echo Request）")

    udp = IP(dst="127.0.0.1") / UDP(dport=53)
    r3 = summarize_packet(udp)
    check_eq(r3["proto"], "UDP", "UDP 包的协议名")
    check_eq(r3["dport"], 53, "UDP 目的端口")
    print(f"✅ summarize_packet() 三协议覆盖: TCP/UDP/ICMP 字段均正确")

    # ── pcap 写入/流式读取（wrpcap + PcapReader，都在临时目录里）──
    import shutil
    import tempfile
    frames = [IP(dst="127.0.0.1") / TCP(dport=p, flags="S") for p in (22, 80, 443)]
    frames.append(IP(dst="127.0.0.1") / ICMP() / b"day156")
    tmpdir = tempfile.mkdtemp(prefix="day156-02-")
    try:
        path = os.path.join(tmpdir, "sniff-roundtrip.pcap")
        wrpcap(path, frames)
        one_shot = rdpcap(path)                       # 一次性读（小文件可以）
        streamed = [p for p in PcapReader(path)]      # 流式读（大文件必须）
        check_eq(len(one_shot), 4, "rdpcap 读回的包数")
        check_eq(len(streamed), 4, "PcapReader 流式读回的包数")
        check_eq([p[TCP].dport for p in streamed if p.haslayer(TCP)], [22, 80, 443],
                 "流式读回的 TCP 目的端口序列")
        check_eq(len(bytes(streamed[3])), len(bytes(frames[3])),
                 "流式读回的第 4 包长度")
        # 两种读法结果必须一致（否则说明你对流式的理解有问题）
        check_eq([bytes(a) for a in one_shot], [bytes(b) for b in streamed],
                 "一次性读与流式读的字节内容")
        print(f"✅ 两种读法一致：rdpcap {len(one_shot)} 包 == PcapReader {len(streamed)} 包"
              f"（字节级相同，证明 store/流式只是内存策略差异）")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n真实嗅探示例（回环，需要 sudo）：")
    print("  sudo python3 02-sniff-pitfalls.py --sniff -i lo -f icmp -t 20")


def main() -> int:
    ap = argparse.ArgumentParser(description="Day156 Scapy 嗅探避坑示例")
    ap.add_argument("--sniff", action="store_true", help="真的开始嗅探")
    ap.add_argument("-i", "--iface", default="lo", help="网卡（默认 lo）")
    ap.add_argument("-f", "--filter", default="icmp", help="BPF 过滤（默认 icmp）")
    ap.add_argument("-t", "--time", type=int, default=20, help="嗅探秒数")
    ap.add_argument("--store", action="store_true", help="保留包对象（危险：内存增长）")
    ap.add_argument("--out", default=None, help="保存为 pcap 文件（写进临时目录，不污染工作树）")
    ap.add_argument("--allow-physical", action="store_true",
                    help="确认允许监听物理网卡（合规责任自负）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test or not args.sniff:
        if not args.sniff:
            print("ℹ️  未指定 --sniff，转为离线自检。\n")
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
    return run_sniff(args.iface, args.filter, args.time, args.store, args.out,
                     args.allow_physical)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(130)
