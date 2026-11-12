#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 157 · 案例 03 —— 流量分析实战：统计 + 连接跟踪 + 7 类异常检测
================================================================================

本案例把"看包"升级成"下结论"。要抓住的核心思想：

    **单包特征 ≠ 检测特征，行为特征才是。**

    看一个包，你只能说"这是一个 SYN"——完全正常。
    看 8 个 SYN 打到 8 个不同端口且**一个握手都没完成**，你才能说"这是端口扫描"。
    看 25 个 SYN 打到**同一个**端口，你才能说"这是 SYN 洪水"。
    这是本案例所有检测器的共同原理：**聚合 + 基线 + 阈值**。

七个检测器（每个都写明"为什么能这么判"和"怎么防"）：
    ① 端口扫描        SYN → 多个目的端口，且全程没有完成任何握手
    ② SYN 洪水        同一 (源, 目标, 端口) 的纯 SYN 数量远超正常
    ③ 明文凭据        HTTP 头/URI/表单里出现 Authorization / Cookie / password
    ④ DNS 隧道        超长 label + 高熵（正常域名不会有 50 个随机字符的标签）
    ⑤ C2 心跳         固定间隔（方差极小）的周期性回连 —— 机器不会这么守时
    ⑥ ARP 欺骗        同一个 IP 被两个不同 MAC 宣告
    ⑦ 校验和异常      IPv4/TCP/UDP 校验和不对（篡改/链路错误的信号）

⚠️ 这里的检测器是**教学实现**：阈值写死、不考虑基线学习、不做会话重组。
   真实 IDS（Suricata/Zeek）会做流重组、协议状态机、多包关联、基线自学习。
   但"为什么这样判"的原理是一样的，而且教学版**能把每一步都验证清楚**。

运行：
    python3 -B 03-traffic-analysis.py --self-test          # 离线自检 → SELF-TEST OK
    python3 -B 03-traffic-analysis.py --demo                # 合成抓包完整分析报告
    python3 -B 03-traffic-analysis.py --pcap /tmp/my.pcap
    python3 -B 03-traffic-analysis.py --demo --json         # 机器可读输出
    python3 -B 03-traffic-analysis.py --demo --fail-on high # 命中 high 时退出码 3（CI 门禁）
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pcap_lib as L  # noqa: E402

# 严重度排序（用于 --fail-on 门禁与报告排序）
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def finding(kind: str, severity: str, summary: str, *, evidence: dict,
            why: str, remediation: str) -> dict:
    """构造一条检测结果。

    为什么每条结果都要带 `why` 和 `remediation`？
      · why：告诉复核的人"凭什么这么判"——没有理由的告警只能被忽略；
      · remediation：告诉运维"该做什么"——检测的价值在于能修复。
    这是安全工具的基本职业素养（只报问题不给方向的工具最终会被关掉）。
    """
    return {"kind": kind, "severity": severity, "summary": summary,
            "evidence": evidence, "why": why, "remediation": remediation}


# ══════════════════════════════════════════════════════════════════════════
# 1. 统计层
# ══════════════════════════════════════════════════════════════════════════

def protocol_stats(pkts: list) -> Counter:
    c = Counter()
    for p in pkts:
        for layer in p.get("layers", []):
            c[layer] += 1
    return c


def top_talkers(pkts: list, n: int = 10) -> list:
    """按"会话方向"聚合流量（src → dst）：包数 + 总字节。

    为什么按方向而不是按 IP？因为"谁在跟谁说话"才是排障和检测的单位；
    只按 IP 聚合会把一个 IP 的所有对端混在一起，看不出谁在打谁。
    """
    agg = defaultdict(lambda: [0, 0])
    for p in pkts:
        ip = p.get("ip") or p.get("ipv6")
        if not ip:
            continue
        key = (ip["src"], ip["dst"])
        agg[key][0] += 1
        agg[key][1] += p["caplen"]
    return sorted(((k, v[0], v[1]) for k, v in agg.items()),
                  key=lambda x: (-x[2], -x[1]))[:n]


def port_stats(pkts: list, n: int = 10) -> list:
    c = Counter()
    for p in pkts:
        if "tcp" in p:
            c[("TCP", p["tcp"]["dport"])] += 1
        elif "udp" in p:
            c[("UDP", p["udp"]["dport"])] += 1
    return c.most_common(n)


def tcp_flag_stats(pkts: list) -> dict:
    """TCP 标志位分布。

    怎么看这个分布（这是真实排障里非常有用的直觉）：
      · SYN 与 SYN-ACK 数量应该**大致相等**（每个连接各一个）；
        如果 SYN 远多于 SYN-ACK → 有人在扫端口或被防火墙挡了。
      · RST 突然变多 → 有连接被拒绝（服务没起/被安全设备重置）。
      · FIN 变多 → 大量连接被正常关闭（或是慢速攻击在耐心地开合连接）。
    """
    c = Counter()
    total = pure_syn = synack = 0
    for p in pkts:
        if "tcp" not in p:
            continue
        total += 1
        for f in p["tcp"]["flag_names"]:
            c[f] += 1                      # 按"单个标志"累计（SYN 与 ACK 分开算）
        if p["tcp"]["syn"] and p["tcp"]["ack_flag"]:
            synack += 1                    # SYN+ACK = 一次"有人在应答"
        elif p["tcp"]["syn"]:
            pure_syn += 1                  # 纯 SYN = 一次"有人在发起"
    return {"total_tcp": total, "flags": c, "pure_syn": pure_syn, "syn_ack": synack}


def connection_table(pkts: list) -> dict:
    """连接跟踪（TCP 状态机）—— 检测器的基础设施。

    为什么必须有它？因为"端口扫描"和"正常访问"的差别不在单个包上，
    而在**连接有没有走完握手**。没有连接概念，就只能数包，无法判定行为。

    状态机（简化版，够教学用）：
        SYN(无 ACK)          → SYN_SENT
        SYN+ACK              → SYN_RCVD
        ACK(无载荷)          → ESTABLISHED
        带载荷               → ESTABLISHED（并累加字节数）
        FIN(任意方向)         → CLOSING
        RST                  → RESET
    键：(src, sport, dst, dport)。**真实实现需要处理乱序、重传、
    同时打开、半关闭等十几种边角情况**——这里只保留主干。
    """
    conns: dict = {}
    for p in pkts:
        if "tcp" not in p or "ip" not in p:
            continue
        t, ip = p["tcp"], p["ip"]
        key = (ip["src"], t["sport"], ip["dst"], t["dport"])
        rec = conns.setdefault(key, {
            "src": ip["src"], "sport": t["sport"], "dst": ip["dst"], "dport": t["dport"],
            "state": "NEW", "syn_ts": None, "first_ts": p["ts"], "last_ts": p["ts"],
            "packets": 0, "bytes": 0, "syn": 0, "synack": 0, "rst": False,
            "completed": False, "payload_bytes": 0,
            # established：**曾经**进入过 ESTABLISHED。为什么要单独记？
            # 因为连接最后会因为 FIN 变成 CLOSING、因为 RST 变成 RESET，
            # 只看"当前状态"会把一条正常关闭的连接误判成"没建立成功"。
            # 这属于状态机设计里典型的"终态 vs 历史"问题。
            "established": False,
        })
        rec["packets"] += 1
        rec["bytes"] += p["caplen"]
        rec["last_ts"] = p["ts"]
        rec["payload_bytes"] += t["payload_len"]
        if t["syn"] and not t["ack_flag"]:
            rec["syn"] += 1
            if rec["syn_ts"] is None:
                rec["syn_ts"] = p["ts"]
            if rec["state"] == "NEW":
                rec["state"] = "SYN_SENT"
        elif t["syn"] and t["ack_flag"]:
            rec["synack"] += 1
            rec["state"] = "SYN_RCVD"
        elif t["rst"]:
            rec["rst"] = True
            rec["state"] = "RESET"
        elif t["fin"]:
            rec["state"] = "CLOSING"
        elif t["ack_flag"]:
            if rec["state"] in ("SYN_RCVD", "SYN_SENT"):
                rec["state"] = "ESTABLISHED"
                rec["completed"] = True
                rec["established"] = True
            elif t["payload_len"] > 0:
                rec["completed"] = True
        if rec["payload_bytes"] > 0:
            rec["completed"] = True
    return conns


# ══════════════════════════════════════════════════════════════════════════
# 2. 检测器
# ══════════════════════════════════════════════════════════════════════════

def detect_port_scan(pkts: list, *, min_ports: int = 5) -> list:
    """① 端口扫描：一个源向一个目标打了很多**不同端口**的纯 SYN，且没完成握手。

    检测原理（为什么这么判）：
      · 正常人访问服务：目标端口固定（80/443），而且会完成三次握手；
      · 扫描器：为了"发现有哪些端口开着"，必然**横向铺开**到很多端口；
      · 更关键的判据是"**握手从未完成**"——这直接把正常访问排除掉，
        所以这个检测器的误报率天生很低（本案例用它证明"不误报正常会话"）。
    局限性：慢速扫描（-T0，几小时扫一个端口）用"次数阈值"抓不到，
           要靠长时间窗口的行为基线（见 README 的检测局限一节）。
    """
    syn_ports = defaultdict(set)           # (src,dst) → 打过的端口集合
    established = set()                    # (src,dst) → 是否完成过握手
    for p in pkts:
        if "tcp" not in p or "ip" not in p:
            continue
        t, ip = p["tcp"], p["ip"]
        pair = (ip["src"], ip["dst"])
        if t["syn"] and not t["ack_flag"] and t["payload_len"] == 0:
            syn_ports[pair].add(t["dport"])
        if t["syn"] and t["ack_flag"] or t["payload_len"] > 0:
            established.add(pair)
    out = []
    for (src, dst), ports in sorted(syn_ports.items()):
        if len(ports) >= min_ports and (src, dst) not in established:
            out.append(finding(
                "port_scan", "medium",
                f"{src} → {dst} 在 {len(ports)} 个端口上发纯 SYN 且未完成任何握手",
                evidence={"src": src, "dst": dst, "distinct_ports": len(ports),
                          "ports": sorted(ports)},
                why="端口扫描的行为特征不是单个 SYN，而是「横向多端口 + 握手不完成」。"
                    "正常业务访问的目标端口是固定的，且会建立连接。",
                remediation="在边界防火墙上启用端口扫描检测与速率限制；"
                            "对外暴露的服务只开必要端口；用 fail2ban/IPS 封禁反复扫描的源。"))
    return out


def detect_syn_flood(pkts: list, *, min_syns: int = 20) -> list:
    """② SYN 洪水：同一 (源, 目标, 端口) 的纯 SYN 数量远超正常。

    检测原理：正常客户端一个连接只发 1 个 SYN（重传才会多几个，且时间隔开）。
    同一四元组短时间内几十上百个 SYN 只有两种可能：攻击，或者客户端在死循环重连。
    **要区分"重传"和"洪水"**：真 ST 的重传间隔是指数退避（1s/2s/4s…），
    洪水则是**匀速且密集**的——本案例用"数量 + 是否完成握手"做粗判，
    真实 IDS 还会加"时间窗口内的速率"（pps）。
    """
    c = Counter()
    for p in pkts:
        if "tcp" not in p or "ip" not in p:
            continue
        t, ip = p["tcp"], p["ip"]
        if t["syn"] and not t["ack_flag"] and t["payload_len"] == 0:
            c[(ip["src"], ip["dst"], t["dport"])] += 1
    out = []
    for (src, dst, port), n in sorted(c.items()):
        if n >= min_syns:
            out.append(finding(
                "syn_flood", "high",
                f"{src} → {dst}:{port} 发出 {n} 个纯 SYN",
                evidence={"src": src, "dst": dst, "dport": port, "syn_count": n},
                why="同一四元组的纯 SYN 数量异常，且没有对应的完成连接；"
                    "正常客户端的 SYN 只有 1 个（重传也远少于此，且间隔指数退避）。",
                remediation="启用 SYN Cookie（Linux: net.ipv4.tcp_syncookies=1）；"
                            "调小 net.ipv4.tcp_max_syn_backlog 并配合限速；"
                            "在上游做流量清洗/黑洞路由。"))
    return out


def detect_cleartext_credentials(pkts: list) -> list:
    """③ 明文凭据：HTTP（未加密）报文里出现认证信息。

    检测原理：HTTP 是明文协议，Authorization/Cookie/表单密码**在网络上裸奔**。
    这也是"为什么必须上 HTTPS"的最直接证据——本检测器能把凭据"抓出来"，
    攻击者（在同一广播域/中间人位置）当然也能。
    ⚠️ 输出**只带掩码和指纹**，绝不回显原文：安全工具自己必须先做到不制造泄露。
       指纹（sha256 前 12 位）用于"判断两次是不是同一个密码"，且不可还原。
    """
    out = []
    for p in pkts:
        h = p.get("http")
        if not h or not h.get("sensitive"):
            continue
        ip = p.get("ip", {})
        out.append(finding(
            "cleartext_credential", "high",
            f"{ip.get('src','?')} → {ip.get('dst','?')} 的明文 HTTP 请求携带凭据",
            evidence={
                "src": ip.get("src"), "dst": ip.get("dst"),
                "method": h.get("method"), "uri": h.get("uri"), "host": h.get("host"),
                "items": [{"where": s["where"], "masked": s["masked"], "fp": s["fp"]}
                          for s in h["sensitive"]],
            },
            why="HTTP 明文传输，Authorization/Cookie/密码字段可被同链路任意设备直接读取；"
                "抓包工具（包括本脚本）能取到，攻击者用同样手段也能取到。",
            remediation="全站上 HTTPS 并启用 HSTS；把会话 Cookie 设为 Secure+HttpOnly；"
                        "凭据改用短时效令牌；内网服务同样要加密（Zero Trust 不认内网）。"))
    return out


def shannon_entropy(text: str) -> float:
    """香农熵（比特/字符）。用来量化"这串东西像不像人写的域名"。

    原理：随机/编码数据的字符分布接近均匀 → 熵高（接近 log2(字符集大小)）；
          自然单词有大量重复字母 → 熵低（英文大约 2.5~3.5）。
    坑：熵只是辅助判据，**不能单靠它**——base64 编码的图片文件名、CDN 的长
        哈希子域也会高熵。必须和"超长 label + 高频查询 + 陌生父域"一起看。
    """
    if not text:
        return 0.0
    counts = Counter(text)
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def detect_dns_tunneling(pkts: list, *, min_label_len: int = 40,
                         min_queries: int = 1) -> list:
    """④ DNS 隧道：超长 label + 高熵的域名查询。

    攻击原理（这是"攻击方式·原理"部分的核心）：
      DNS 是几乎**不会被封**的协议（封了 DNS 就没法上网），
      于是攻击者把数据编码进域名标签里（base32/base64），
      通过查询把数据**送出去**（外泄），通过 TXT/A 应答把指令**带回来**。
      一个典型隧道查询长这样：
        aGVsbG8gd29ybGQ.tunnel.evil.example
      —— 前面那串就是编码后的数据，DNS 服务器那边由攻击者控制并解码。

    检测原理（三条一起看，缺一个都不要轻易下结论）：
      ① label 长度异常（正常域名标签极少超过 20 字符）
      ② label 熵高（编码数据接近均匀分布）
      ③ 同一父域的查询频率高、子域每次不同（缓存穿透，正常 CDN 有复用）
    本案例的合成流量就是按①②构造的，且只打 3 次，用来验证阈值逻辑。
    """
    hits = defaultdict(lambda: {"labels": [], "entropies": [], "ts": []})
    for p in pkts:
        d = p.get("dns")
        if not d or d["response"] or not d["qry_name"]:
            continue
        qname = d["qry_name"]
        labels = [x for x in qname.split(".") if x]
        if not labels:
            continue
        longest = max(labels, key=len)
        if len(longest) < min_label_len:
            continue
        # 父域 = 去掉最长的那个 label（那才是"数据"），剩下的就是隧道出口域名
        parent = ".".join([x for x in labels if x != longest][-3:])
        rec = hits[(p["ip"]["src"], parent)]
        rec["labels"].append(longest)
        rec["entropies"].append(round(shannon_entropy(longest), 2))
        rec["ts"].append(round(p["ts"], 3))
    out = []
    for (src, parent), rec in sorted(hits.items()):
        if len(rec["labels"]) < min_queries:
            continue
        out.append(finding(
            "dns_tunneling", "high",
            f"{src} 向陌生父域 {parent} 发起 {len(rec['labels'])} 次超长/高熵 DNS 查询",
            evidence={"src": src, "parent_domain": parent,
                      "query_count": len(rec["labels"]),
                      "max_label_len": max(len(x) for x in rec["labels"]),
                      "avg_entropy_bits_per_char": round(sum(rec["entropies"]) / len(rec["entropies"]), 2),
                      "sample_label": L.mask_secret(rec["labels"][0])},
            why="DNS 是少数「不能一封了之」的协议，数据编码进域名标签即可双向传输；"
                "超长 label + 高熵 + 每次子域都不同的组合，正常业务几乎不会出现。",
            remediation="DNS 出口只允许走内部解析器（拒绝直连 8.8.8.8 等）；"
                        "在解析器上限制标签长度与响应大小并做信誉拦截；"
                        "对高熵子域做采样告警，对已知隧道域名做黑洞。"))
    return out


def detect_beaconing(pkts: list, *, min_count: int = 4, min_interval: float = 5.0,
                     max_jitter: float = 0.10) -> list:
    """⑤ C2 心跳：固定间隔的周期性回连。

    检测原理（为什么"规整"反而可疑）：**机器比人守时**。
      人点网页的时间间隔是随机的；而恶意程序为了"随时能收到指令"，
      会以固定周期（如每 60 秒 ±几毫秒）回连 C2。这个"过于规整"就是特征。
    判据：同一 (源, 目标, 端口) 出现 ≥ 4 次连接，且间隔的**抖动系数**很小。
      抖动系数 = 间隔的标准差 / 平均间隔；C2 通常在 5% 以内。
    注意：DNS/HTTPS 心跳也能用同一套逻辑检测（只需换成"查询时间序列"），
         这就是"检测的是行为，不是协议"的体现。
    """
    seq = defaultdict(list)
    for p in pkts:
        if "tcp" not in p or "ip" not in p:
            continue
        t, ip = p["tcp"], p["ip"]
        if t["syn"] and not t["ack_flag"]:
            seq[(ip["src"], ip["dst"], t["dport"])].append(round(p["ts"], 3))
    out = []
    for (src, dst, port), ts in sorted(seq.items()):
        if len(ts) < min_count:
            continue
        ts = sorted(ts)
        intervals = [b - a for a, b in zip(ts, ts[1:])]
        if not intervals:
            continue
        mean = sum(intervals) / len(intervals)
        if mean < min_interval:
            continue
        var = sum((x - mean) ** 2 for x in intervals) / len(intervals)
        jitter = math.sqrt(var) / mean
        if jitter <= max_jitter:
            out.append(finding(
                "c2_beacon", "high",
                f"{src} → {dst}:{port} 出现 {len(ts)} 次周期为 {mean:.1f}s 的规律回连",
                evidence={"src": src, "dst": dst, "dport": port, "connections": len(ts),
                          "mean_interval_s": round(mean, 3),
                          "jitter_ratio": round(jitter, 4),
                          "intervals_s": [round(x, 3) for x in intervals]},
                why="人体行为的时间间隔是随机的；固定周期（抖动 <10%）的回连"
                    "高度符合 C2 心跳特征。检测的是**时间规律**，与协议无关。",
                remediation="对出站连接做白名单；限制内网主机直连可疑端口/地址；"
                            "用 DNS/流量指纹做信誉拦截；对周期性外连做人工复核。"))
    return out


def detect_arp_conflict(pkts: list) -> list:
    """⑥ ARP 欺骗：同一个 IP 被两个不同 MAC 宣告。

    攻击原理：ARP 协议**没有任何认证**，"谁是 192.168.1.1"的应答谁都可以发。
    攻击者只要不停广播"网关 192.168.1.1 的 MAC 是我"，就能让全网的流量
    先经过他（中间人），再转发给真网关——这就是局域网抓包/改包的基础。
    检测原理：网关 IP 与 MAC 应该是**稳定一对一**的；
             同一个 IP 出现两个 MAC ⇒ 有人抢答（或真的换了网卡/双机热备，
             所以要结合资产表判断，这也是"检测结果必须人工复核"的例子）。
    """
    seen = defaultdict(set)
    for p in pkts:
        a = p.get("arp")
        if not a:
            continue
        # 只看"宣告自己是谁"的包：is-at 应答，以及 who-has 里的发送者信息
        seen[a["sender_ip"]].add(a["sender_mac"])
    out = []
    for ip, macs in sorted(seen.items()):
        if len(macs) >= 2:
            out.append(finding(
                "arp_spoof", "critical",
                f"IP {ip} 同时被 {len(macs)} 个 MAC 宣告",
                evidence={"ip": ip, "macs": sorted(macs)},
                why="ARP 无认证，任何主机都能应答「我是某 IP」；同一 IP 对应多个 MAC "
                    "是 ARP 欺骗（中间人）最直接的信号。",
                remediation="交换机开启动态 ARP 检测（DAI）+ DHCP Snooping；"
                            "关键网关/IP 做静态 ARP 绑定；"
                            "启用端口安全限制每端口 MAC 数；用 arpwatch 长期监控。"))
    return out


def detect_bad_checksums(pkts: list) -> list:
    """⑦ 校验和异常：IPv4/TCP/UDP 校验和不正确。

    该关心它的两个理由：
      · **篡改**：中间设备/攻击工具改了 IP 头字段却忘了重算校验和
        （本案例的植入坏包就是这么造的）；
      · **链路/网卡问题**：网卡卸载（TSO/LRO/checksum offload）会
        让抓包看到的校验和是"未填状态"，这属于**误报**——
        所以真实分析中要排除捕获点的 offload 影响（这也是 tshark 会提示
        "checksum not available/offload" 的原因）。
    """
    bad = []
    for p in pkts:
        ip = p.get("ip")
        if not ip:
            continue
        if not ip["checksum_ok"]:
            bad.append({"number": p["number"], "layer": "ip",
                        "src": ip["src"], "dst": ip["dst"],
                        "proto": ip["proto_name"]})
    out = []
    if bad:
        out.append(finding(
            "bad_checksum", "low",
            f"检测到 {len(bad)} 个 IPv4 头校验和错误的包",
            evidence={"count": len(bad), "packets": bad[:10]},
            why="校验和错说明 IPv4 头被改动后未重算（篡改），或者抓包点受网卡卸载影响。"
                "pyshark/tshark 默认只做 dissection，**不会主动告诉你**这一点。",
            remediation="先确认抓包点是否开启 checksum offload（若开则属误报）；"
                        "排除误报后，检查中间设备/安全设备是否在改写报文头。"))
    return out


DETECTORS = [
    ("端口扫描", detect_port_scan),
    ("SYN 洪水", detect_syn_flood),
    ("明文凭据", detect_cleartext_credentials),
    ("DNS 隧道", detect_dns_tunneling),
    ("C2 心跳", detect_beaconing),
    ("ARP 欺骗", detect_arp_conflict),
    ("校验和异常", detect_bad_checksums),
]


def analyze(pkts: list) -> dict:
    """跑完整分析，返回报告字典。"""
    conns = connection_table(pkts)
    findings = []
    for _name, fn in DETECTORS:
        findings.extend(fn(pkts))
    findings.sort(key=lambda f: -SEVERITY_ORDER[f["severity"]])
    return {
        "packets": len(pkts),
        "protocols": dict(protocol_stats(pkts)),
        "top_talkers": [{"src": s, "dst": d, "packets": n, "bytes": b}
                        for (s, d), n, b in top_talkers(pkts)],
        "top_ports": [{"proto": p, "port": port, "packets": n}
                      for (p, port), n in port_stats(pkts)],
        "tcp_flags": {k: v for k, v in tcp_flag_stats(pkts)["flags"].most_common()},
        # 这三个是"行为指标"，比单个标志计数有用得多：
        #   pure_syn（发起）与 syn_ack（应答）数量应大致相等，
        #   差得多就说明有人在"只发起不等应答"（扫描/洪水）
        "tcp_flag_summary": {
            "total_tcp": tcp_flag_stats(pkts)["total_tcp"],
            "pure_syn": tcp_flag_stats(pkts)["pure_syn"],
            "syn_ack": tcp_flag_stats(pkts)["syn_ack"],
        },
        "connections": sorted(
            ({"src": r["src"], "sport": r["sport"], "dst": r["dst"], "dport": r["dport"],
              "state": r["state"], "packets": r["packets"], "bytes": r["bytes"],
              "syn": r["syn"], "synack": r["synack"], "completed": r["completed"],
              "established": r["established"]}
             for r in conns.values()),
            key=lambda r: (-r["packets"], r["src"])),
        "findings": findings,
    }


# ══════════════════════════════════════════════════════════════════════════
# 3. 报告渲染
# ══════════════════════════════════════════════════════════════════════════

SEV_ICON = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}


def render_report(rep: dict, *, max_conns: int = 12) -> str:
    lines = []
    lines.append("=" * 84)
    lines.append(f"流量分析报告 —— 共 {rep['packets']} 个包")
    lines.append("=" * 84)

    lines.append("\n【协议分布】(层计数，一个包可能同时含 ip 与 tcp)")
    for name, n in sorted(rep["protocols"].items(), key=lambda kv: -kv[1]):
        lines.append(f"  {name:<8} {n}")

    lines.append("\n【最活跃的会话】(按字节数降序)")
    lines.append(f"  {'源':<16}{'目标':<16}{'包数':>6}{'字节':>8}")
    for t in rep["top_talkers"][:10]:
        lines.append(f"  {t['src']:<16}{t['dst']:<16}{t['packets']:>6}{t['bytes']:>8}")

    lines.append("\n【目的端口 Top10】")
    for p in rep["top_ports"]:
        lines.append(f"  {p['proto']}:{p['port']:<6} {p['packets']} 个包")

    lines.append("\n【TCP 标志分布】")
    for flag, n in rep["tcp_flags"].items():
        lines.append(f"  {flag:<6} {n}")
    s_ = rep["tcp_flag_summary"]
    lines.append(f"  ── 行为指标：纯 SYN {s_['pure_syn']} 个 vs SYN+ACK {s_['syn_ack']} 个"
                 f"（正常应大致相等；差值 = 只发起不完成的可疑连接）")

    lines.append(f"\n【连接跟踪】(共 {len(rep['connections'])} 条，显示前 {max_conns} 条)")
    lines.append(f"  {'源':<16}{'端口':>6} → {'目标':<16}{'端口':>6}  {'状态':<12}{'SYN/SA':>8}  完成")
    for c in rep["connections"][:max_conns]:
        lines.append(f"  {c['src']:<16}{c['sport']:>6} → {c['dst']:<16}{c['dport']:>6}  "
                     f"{c['state']:<12}{str(c['syn']) + '/' + str(c['synack']):>8}  "
                     f"{'✅' if c['completed'] else '❌'}")

    lines.append(f"\n【检测结果】(共 {len(rep['findings'])} 条)")
    if not rep["findings"]:
        lines.append("  未发现异常。")
    for i, f in enumerate(rep["findings"], 1):
        lines.append(f"\n  {i}. {SEV_ICON.get(f['severity'], '·')} [{f['severity'].upper()}] "
                     f"{f['kind']} — {f['summary']}")
        lines.append(f"     证据: {json.dumps(f['evidence'], ensure_ascii=False)}")
        lines.append(f"     为什么这么判: {f['why']}")
        lines.append(f"     怎么修/怎么防: {f['remediation']}")
    return "\n".join(lines)


def gate_exit_code(rep: dict, fail_on: str) -> int:
    """CI 门禁：命中不低于 fail_on 的严重度时返回 3，否则 0。"""
    if fail_on == "none":
        return 0
    threshold = SEVERITY_ORDER[fail_on]
    for f in rep["findings"]:
        if SEVERITY_ORDER[f["severity"]] >= threshold:
            return 3
    return 0


# ══════════════════════════════════════════════════════════════════════════
# 4. 离线自检
# ══════════════════════════════════════════════════════════════════════════

def self_test() -> None:
    print("=" * 84)
    print("案例 03 离线自检：统计 / 连接跟踪 / 7 个检测器 vs 已知植入的异常")
    print("=" * 84)

    tmp = tempfile.mkdtemp(prefix="day157-03-")
    try:
        path = os.path.join(tmp, "demo.pcap")
        L.write_demo_pcap(path)
        pkts = [L.dissect_packet(r) for r in L.iter_capture(path)]
        F = L.DEMO_FACTS
        L.check_eq(len(pkts), 70, "合成抓包包数")
        rep = analyze(pkts)

        # ① 统计层
        L.check_eq(rep["protocols"]["tcp"], 60, "TCP 包数")
        L.check_eq(rep["protocols"]["udp"], 5, "UDP 包数")
        L.check_eq(rep["protocols"]["arp"], 3, "ARP 包数")
        L.check_eq(rep["protocols"]["icmp"], 2, "ICMP 包数")
        L.check_eq(rep["top_talkers"][0]["src"], F["flooder_ip"],
                   "字节数最多的会话应是 SYN 洪水源")
        # 注意 tcp_flags 统计的是"含该标志的包"，所以 SYN 计数把 SYN,ACK 也算进去了：
        #   纯 SYN 39 个 + SYN,ACK 5 个 = 44。这正是"统计口径必须写清楚"的现实例子。
        L.check_eq(rep["tcp_flags"]["SYN"], 44, "SYN 计数（含 SYN,ACK 的包）")
        L.check_eq(rep["tcp_flag_summary"]["pure_syn"], 39, "纯 SYN 计数")
        L.check_eq(rep["tcp_flag_summary"]["syn_ack"], 5, "SYN+ACK 计数")
        print(f"✅ 统计：tcp=60 udp=5 arp=3 icmp=2；SYN=44（含 5 个 SYN,ACK）；"
              f"最活跃会话 = {rep['top_talkers'][0]['src']} → {rep['top_talkers'][0]['dst']}")

        # ② 连接跟踪：正常会话必须 ESTABLISHED，扫描连接必须"没完成"
        def conn_of(src, dst, dport):
            return [c for c in rep["connections"]
                    if c["src"] == src and c["dst"] == dst and c["dport"] == dport]

        web = conn_of(F["client_ip"], F["web_server_ip"], 80)
        L.check_eq(len(web), 1, "正常 Web 连接条数（同一个四元组只应有一条）")
        # 正常会话最终状态是 CLOSING（因为演示了四次挥手），
        # 所以要看"是否曾进入 ESTABLISHED"，而不是看终态 —— 见 connection_table 注释
        L.check_true(web[0]["established"], "正常 Web 连接必须曾进入 ESTABLISHED")
        L.check_true(web[0]["completed"], "正常 Web 连接完成标记")
        L.check_eq(web[0]["state"], "CLOSING", "正常 Web 连接终态（演示了四次挥手）")
        scan_conns = [c for c in rep["connections"] if c["src"] == F["scanner_ip"]]
        L.check_eq(len(scan_conns), len(F["scanned_ports"]), "扫描产生的连接条数")
        L.check_true(all(c["state"] == "SYN_SENT" for c in scan_conns),
                     "扫描连接必须停留在 SYN_SENT（握手中断）")
        L.check_true(all(not c["completed"] for c in scan_conns),
                     "扫描连接不得标记为完成")
        print(f"✅ 连接跟踪：正常 Web 会话曾进入 ESTABLISHED 并正常关闭（终态 "
              f"{web[0]['state']}）；扫描的 {len(scan_conns)} 条全部停在 SYN_SENT（未完成）")

        # ③ 逐检测器核对"标准答案"——这是本自检的核心价值
        by_kind = defaultdict(list)
        for f in rep["findings"]:
            by_kind[f["kind"]].append(f)

        scan = by_kind["port_scan"]
        L.check_eq(len(scan), 1, "端口扫描告警条数（只应有扫描器那一条）")
        L.check_eq(scan[0]["evidence"]["src"], F["scanner_ip"], "端口扫描源 IP")
        L.check_eq(scan[0]["evidence"]["ports"], sorted(F["scanned_ports"]),
                   "被扫描的端口列表")
        L.check_eq(scan[0]["evidence"]["distinct_ports"], 8, "端口数量")

        flood = by_kind["syn_flood"]
        L.check_eq(len(flood), 1, "SYN 洪水告警条数")
        L.check_eq(flood[0]["evidence"]["syn_count"], F["flood_syn_count"], "SYN 洪水包数")
        L.check_eq(flood[0]["evidence"]["dport"], F["flood_port"], "SYN 洪水目标端口")

        creds = by_kind["cleartext_credential"]
        L.check_eq(len(creds), 1, "明文凭据告警条数（只有 /login 那次）")
        L.check_eq(creds[0]["evidence"]["host"], F["credential_host"], "凭据泄露的主机")
        L.check_eq(creds[0]["evidence"]["uri"], F["credential_uri"], "凭据泄露的 URI")
        L.check_true(len(creds[0]["evidence"]["items"]) >= 2, "凭据项 ≥2（Auth + Cookie）")
        cred_blob = json.dumps(creds[0], ensure_ascii=False)
        L.check_true("dXNlcjpwYXNzd29yZA==" not in cred_blob,
                     "报告里绝不能出现 Authorization 原文")
        L.check_true("8f3a1c0d9e2b" not in cred_blob, "报告里绝不能出现 Cookie 原文")

        dns = by_kind["dns_tunneling"]
        L.check_eq(len(dns), 1, "DNS 隧道告警条数（按父域聚合后 1 条）")
        L.check_eq(dns[0]["evidence"]["src"], F["tunnel_client"], "隧道查询来源主机")
        L.check_eq(dns[0]["evidence"]["parent_domain"], F["tunnel_suffix"].lstrip("."),
                   "隧道出口父域")
        L.check_eq(dns[0]["evidence"]["query_count"], len(F["tunnel_qnames"]), "隧道查询次数")
        L.check_true(dns[0]["evidence"]["avg_entropy_bits_per_char"] > 4.0,
                     f"隧道 label 熵应 >4.0，实际 {dns[0]['evidence']['avg_entropy_bits_per_char']}")
        # 正常域名的熵明显更低 —— 这正是"高熵"能当判据的原因
        normal_entropy = shannon_entropy("intranet")
        L.check_true(normal_entropy < 3.0,
                     f"正常词 'intranet' 熵应 <3.0，实际 {normal_entropy:.2f}")
        L.check_true(dns[0]["evidence"]["avg_entropy_bits_per_char"] > normal_entropy + 1.0,
                     "隧道熵必须显著高于正常域名")
        print(f"✅ DNS 隧道：{dns[0]['evidence']['query_count']} 次查询，"
              f"label 最长 {dns[0]['evidence']['max_label_len']} 字符，"
              f"熵 {dns[0]['evidence']['avg_entropy_bits_per_char']} "
              f"vs 正常域名 {normal_entropy:.2f}")

        beacon = by_kind["c2_beacon"]
        L.check_eq(len(beacon), 1, "C2 心跳告警条数")
        L.check_eq(beacon[0]["evidence"]["src"], F["beacon_src"], "心跳源 IP")
        L.check_eq(beacon[0]["evidence"]["dst"], F["beacon_dst"], "心跳目标 IP")
        L.check_eq(beacon[0]["evidence"]["dport"], F["beacon_port"], "心跳端口")
        L.check_eq(beacon[0]["evidence"]["connections"], F["beacon_count"], "心跳次数")
        L.check_eq(round(beacon[0]["evidence"]["mean_interval_s"]), 60, "心跳平均间隔")
        L.check_eq(beacon[0]["evidence"]["jitter_ratio"], 0.0, "心跳抖动应为 0")

        arp = by_kind["arp_spoof"]
        L.check_eq(len(arp), 1, "ARP 欺骗告警条数")
        L.check_eq(arp[0]["evidence"]["ip"], F["arp_conflict_ip"], "ARP 冲突 IP")
        L.check_eq(sorted(arp[0]["evidence"]["macs"]), sorted(F["arp_conflict_macs"]),
                   "冲突的两个 MAC")

        ck = by_kind["bad_checksum"]
        L.check_eq(len(ck), 1, "校验和异常告警条数")
        L.check_eq(ck[0]["evidence"]["count"], F["bad_checksum_count"], "坏校验和包数")
        print(f"✅ 七个检测器全部命中预设异常："
              f"{ {k: len(v) for k, v in sorted(by_kind.items())} }")

        # ④ 误报控制（最重要的一条）：正常 Web 会话不能被误判
        noise = [f for f in rep["findings"]
                 if f["kind"] in ("port_scan", "syn_flood", "c2_beacon",
                                  "dns_tunneling", "arp_spoof")
                 and F["client_ip"] in json.dumps(f["evidence"])]
        L.check_eq(noise, [], f"正常客户端 {F['client_ip']} 不得被这些检测器误报")
        L.check_eq(sum(1 for f in rep["findings"] if f["severity"] == "critical"), 1,
                   "critical 级告警只应有 ARP 欺骗这一条")
        print("✅ 误报控制：正常 Web 会话（含 1 次 SYN、正常 DNS 查询）未被任何"
              "扫描/洪水/心跳/隧道检测器误报")

        # ⑤ 熵函数的边界
        L.check_eq(shannon_entropy(""), 0.0, "空串熵为 0")
        L.check_eq(shannon_entropy("aaaa"), 0.0, "单一字符熵为 0")
        L.check_eq(round(shannon_entropy("ab"), 2), 1.0, "两字符等概率熵为 1 bit")
        print("✅ 熵函数：空串=0、'aaaa'=0、'ab'=1.0 bit（边界正确）")

        # ⑥ 门禁退出码
        L.check_eq(gate_exit_code(rep, "none"), 0, "fail-on=none 不拦截")
        L.check_eq(gate_exit_code(rep, "critical"), 3, "fail-on=critical 命中 ARP 欺骗")
        L.check_eq(gate_exit_code(rep, "high"), 3, "fail-on=high 命中")
        L.check_eq(gate_exit_code({"findings": []}, "low"), 0, "无告警时通过")
        print("✅ 门禁：fail-on none/critical/high 的退出码判定正确")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Day157 案例03：流量分析 + 异常检测")
    ap.add_argument("--pcap", metavar="FILE", help="抓包文件")
    ap.add_argument("--demo", action="store_true", help="使用临时目录里的合成抓包")
    ap.add_argument("--json", action="store_true", help="输出 JSON（机器可读）")
    ap.add_argument("--fail-on", choices=["none", "low", "medium", "high", "critical"],
                    default="none", help="CI 门禁：命中不低于该严重度时退出码 3")
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
        tmp = tempfile.mkdtemp(prefix="day157-03-")
        path = os.path.join(tmp, "demo.pcap")
        L.write_demo_pcap(path)
    if not os.path.exists(path):
        print(f"❌ 文件不存在：{path}（加 --demo 可用合成数据）")
        return 2
    try:
        pkts = [L.dissect_packet(r) for r in L.iter_capture(path)]
    except ValueError as e:
        print(f"❌ 读取失败：{e}")
        return 2
    if not pkts:
        print("⚠️ 抓包里没有任何数据包")
        return 0

    rep = analyze(pkts)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(render_report(rep))
        print("\n提醒：检测结果是**复核线索**，不是结论。")
        print("      ARP 冲突可能是双机热备；心跳可能是监控探针；高熵域名可能是 CDN。")
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return gate_exit_code(rep, args.fail_on)


if __name__ == "__main__":
    sys.exit(main())
