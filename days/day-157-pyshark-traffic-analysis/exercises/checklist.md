# Day 157 — 流量分析（PCAP / pyshark / 标准库）· 完成清单与练习

> 目标：能解释 pcap/pcapng 的字节结构，能用**两条路径**（pyshark / 标准库）
> 分析抓包文件，并能从一堆包得出"扫描 / 隧道 / 心跳 / 欺骗"的可复核结论。
>
> 本日所有自检与演示**不需要 pyshark、不需要 tshark、不需要 sudo、不联网**。

---

## ✅ 今日完成清单

### 理解层面

- [ ] 能画出 pcap 的"24 字节全局头 + 每包 16 字节记录头"结构
- [ ] 能说出魔数为什么能判断**字节序**，判错会发生什么（`incl_len` 变成天文数字）
- [ ] 能说出 `incl_len` 与 `orig_len` 的区别（snaplen 截断）
- [ ] 能说出 pcapng 的 SHB/IDB/EPB 三种块各存什么
- [ ] 能解释 pcapng 的块长度为什么写两次
- [ ] 能解释 `if_tsresol` 的 10⁻ⁿ / 2⁻ⁿ 双重含义与踩坑后果
- [ ] 能说出 pyshark 与 tshark 的关系（谁在做真正的解析）
- [ ] 能说出 pyshark / scapy / dpkt / tshark / 标准库各自适合什么
- [ ] 能说清 **BPF 与 display filter** 在"执行位置 / 看什么 / 丢包语义 / 性能"上的差异
- [ ] 能解释为什么 BPF 只能看固定字节偏移（解析之前）
- [ ] 能说出 IPv4 / TCP / UDP / ICMP 校验和的覆盖范围差异（谁有伪首部）
- [ ] 能解释 VLAN 标签、IP 分片、TCP 选项对齐这三类"错位类" bug
- [ ] 能解释为什么 `only_summaries=True` 时读不到 `pkt.http`
- [ ] 能说出七个检测器各自的**判据**与**误报来源**

### 操作层面（全部离线可完成）

- [ ] `python3 -B code/pcap_lib.py --self-test` → `SELF-TEST OK`
- [ ] `python3 -B code/01-basic-usage.py --self-test` → `SELF-TEST OK`
- [ ] `python3 -B code/02-advanced-filtering.py --self-test` → `SELF-TEST OK`
- [ ] `python3 -B code/03-traffic-analysis.py --self-test` → `SELF-TEST OK`
- [ ] `python3 -B code/pcap_lib.py --write-demo /tmp/demo.pcap`（生成 70 个包的合成抓包）
- [ ] `python3 -B code/pcap_lib.py --dump /tmp/demo.pcap --filter 'tcp.flags.syn==1'`
- [ ] `python3 -B code/01-basic-usage.py --demo --limit 10`
- [ ] `python3 -B code/02-advanced-filtering.py --demo --http`
- [ ] `python3 -B code/03-traffic-analysis.py --demo --json | head -40`
- [ ] `python3 -B code/03-traffic-analysis.py --demo; echo $?`（应为 0）
- [ ] `python3 -B code/03-traffic-analysis.py --demo --fail-on high; echo $?`（应为 3）
- [ ] 把自己写的规则加上：在 `02` 的 `DEMO_FILTERS` 里加一条，并同步自检期望值

### 进阶（需要 tshark 才能做）

- [ ] 安装 `pyshark` + `tshark` 后跑 `01-basic-usage.py --demo --compare`，
      确认两条后端包数与字段一致
- [ ] 用 `tshark -r /tmp/demo.pcap -T fields -e ip.src -e tcp.dstport` 导出字段，
      与 `pcap_lib --dump` 的输出对照
- [ ] 抓一段自己的流量（`tcpdump -i lo -c 200 -w /tmp/my.pcap`）并分析

### 产出物

- [ ] 一份自己抓的 pcap（**只含自己的流量**）
- [ ] 一份 03 生成的 JSON 报告
- [ ] 一张手绘的"pcap 字节布局图"

---

## 📝 基础练习（必做）

<details>
<summary>点击展开答案要点</summary>

### Q1 手算 pcap 全局头

一个 24 字节的 pcap 全局头，十六进制如下，请指出每一项的含义：

```
d4 c3 b2 a1  02 00  04 00  00 00 00 00  00 00 00 00  ff ff 00 00  01 00 00 00
```

**答案：**
- `d4 c3 b2 a1`：魔数 `0xa1b2c3d4` 的**大端序**写法 → 这个文件是**大端**、
  时间戳是**微秒**（按小端读出来是 0xd4c3b2a1）；
- `02 00` / `04 00`：版本 2.4（大端读作 0x0002/0x0004）；
- `0…0` ×2：thiszone=0、sigfigs=0（历史字段，永远是 0）；
- `ff ff 00 00`：snaplen = 65535；
- `01 00 00 00`：network = 1 = Ethernet。

**要点：** 判断字节序**只看魔数**，不要靠"猜"。

### Q2 判断字段：BPF 还是 display filter？

| 表达式 | 类型 | 为什么 |
|---|---|---|
| `tcp port 80` | BPF | 没有协议字段语法，是 `tcp[2:2]==80 …` 的简写 |
| `tcp.dstport == 80` | display | 使用了协议字段名 |
| `icmp` | 两者都有这个名字 | BPF 里等价于 `ip proto 1`；display 里是"有 icmp 层" |
| `not port 22` | BPF | `port` 是 BPF 关键字 |
| `dns.qry.name contains "evil"` | display | 需要解析出 DNS 字段才能判断 |
| `tcp[tcpflags] & tcp-syn != 0` | BPF | 直接操作字节偏移 |

### Q3 为什么读不到 HTTP 字段？（本日修掉的真实 bug）

```python
cap = pyshark.FileCapture('x.pcap', display_filter='http', only_summaries=True)
for pkt in cap:
    print(pkt.http.method)      # 为什么报错？
```

**答案：** `only_summaries=True` 时 pyshark 返回的是 Summary 对象，
**只有 7 个属性**：`number/time/source/destination/protocol/length/info`，
没有 `ip`/`tcp`/`http` 这些层对象 → `AttributeError`。

**正确做法：**
- 要字段 → 去掉 `only_summaries`（慢但全）；
- 要速度 → 保留摘要，只读 `pkt.info` 这一列文本。

### Q4 校验和：为什么这个包"看起来对"却丢了？

现象：手工改了一个 TCP 包的载荷，抓包看是
`TCP checksum incorrect`，服务端静默丢弃。

**答案要点：** TCP 校验和覆盖"伪首部 + TCP 头 + **载荷**"。
改了载荷不重算校验和 → 接收端验证失败 → 丢弃。
用 Scapy 时应该 `pkt[TCP].payload = b"..."` 再 `bytes(pkt)`，
**不要**直接改 `bytes`。

### Q5 为什么 ARP 欺骗能成功？

**答案要点：** ARP 没有认证机制，任何主机都能发送 "is-at" 应答。
交换机只按 MAC 转发，不检查"这个 IP 是不是你的"。
防御：DHCP Snooping + 动态 ARP 检测（DAI）+ 静态绑定 + 端口安全。

### Q6 用标准库读一个 pcap 的最小代码

```python
import struct
with open('/tmp/demo.pcap', 'rb') as f:
    gh = f.read(24)
    endian = '<' if int.from_bytes(gh[0:4], 'little') == 0xA1B2C3D4 else '>'
    snaplen, linktype = struct.unpack(endian + 'II', gh[16:24])
    print('linktype =', linktype)
    while True:
        ph = f.read(16)
        if len(ph) < 16:
            break
        sec, usec, incl, orig = struct.unpack(endian + 'IIII', ph)
        data = f.read(incl)
        print(f'#{sec}.{usec:06d} {incl}B {data[:14].hex()}')
```

**要点：** 这就是 `pcap_lib.iter_pcap` 的核心。**pcap 格式真的只有这么简单。**

</details>

---

## 🚀 进阶练习（选做）

<details>
<summary>点击展开</summary>

### C1 给 `pcap_lib` 加一个 PCAPNG 写入选项

需求：`write_pcap(path, pkts, fmt="pcapng")`，用 `build_pcapng_bytes` 实现，
并**顺手让 `pcap_lib.py --self-test` 的往返断言同时覆盖两种格式**。

提示：注意 `ts_resol=6`（微秒）时，`int(round(ts * 1e6))` 的浮点误差
（时间戳很大时尤其明显）。

### C2 手写"TCP flags 分布异常"检测器

需求：当 `SYN 数量 / SYN+ACK 数量 > 3` 时告警。
在本日合成抓包上应该**命中**（39 vs 5 = 7.8 倍），
在"只用正常会话构造的小流量"上应该**不命中**。
（这正是"同一个检测器，换个数据集就该换个结论"的练习。）

### C3 给 DNS 隧道检测加"高频"判据

现在的实现只用"label 长度 + 熵"。请加一条"同一父域在 60 秒内出现 ≥ N 次"。
构造测试数据时注意：**合成流量必须能被精确断言**（用固定时间戳，
不要用 `time.time()`）。

### C4 用 scapy 交叉验证你的解析器

```python
from scapy.all import rdpcap
import pcap_lib as L
pkts_scapy = rdpcap('/tmp/demo.pcap')
pkts_lib = [L.dissect_packet(r) for r in L.iter_capture('/tmp/demo.pcap')]
assert len(pkts_scapy) == len(pkts_lib)
for s, m in zip(pkts_scapy, pkts_lib):
    if s.haslayer('IP'):
        assert s['IP'].src == m['ip']['src'] and s['IP'].ttl == m['ip']['ttl']
print("两侧解析一致")
```

**思考：** scapy 的 `IP.chksum` 是 `None`（未回填），而本库直接给出校验和验证结果。
这个差异说明了什么？（提示：`show()` vs `show2()`，Day156 讲过）

### C5 做一个小型的"流量分析 CLI 平台"

把本日三个脚本合成一个入口（类似 Day159/160 的 `audit-toolkit`）：

```
pcap-tool list   <file>           列出包
pcap-tool filter <file> --expr …  过滤
pcap-tool stats  <file>           统计
pcap-tool detect <file> --fail-on high
pcap-tool self-test
```

要求：`detect` 的退出码即门禁结果（0/3），并且 `self-test` 完全离线。

### C6 对比两种后端的性能（需要 pyshark）

用同一份文件（可用 `pcap_lib` 生成 1 万包的合成流量：把 `build_demo_packets`
循环 150 次并错开时间戳），分别测：
1. `pcap_lib.iter_capture` 纯解析耗时；
2. `pyshark.FileCapture` 全字段耗时；
3. `pyshark.FileCapture(only_summaries=True)` 耗时。

预期结论：**摘要模式最快、纯 Python 全字段最慢**，
但纯 Python 省掉了进程间通信，在**小文件**上反而可能不差。
这就是"没有银弹，按场景选工具"的具体体现。

</details>

---

## 📌 今日自检的三个问题

1. pcap 与 pcapng 最本质的结构差异是什么？为什么 pcapng 的长度字段要写两次？
2. BPF 与 display filter 的本质区别是什么？为什么"丢掉的包 display filter 找不回来"？
3. 你写了一个检测器，跑在真实环境里误报很多。你会从哪三个方向改进？
   （提示：基线、白名单、把"单特征"升级成"多特征组合"）

---

## 🚫 今日红线

- ❌ 不分析**不属于你**的抓包文件（里面可能有他人的凭据与隐私）；
- ❌ 不抓任何未经授权的网络流量；
- ❌ 不把未脱敏的 pcap 外发（本日所有输出都对敏感值做了掩码）；
- ❌ 不把本日的检测器当成生产 IDS 用（它不做流重组、不做解密，见 README 第八章）；
- ✅ 拿不准时，**只在临时目录里用合成流量**（本日默认就是这么做的）。
