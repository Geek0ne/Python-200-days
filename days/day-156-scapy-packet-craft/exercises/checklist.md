# Day 156 — Scapy 数据包构造 · 完成清单与练习

> 阶段：Phase 7 — 进阶与性能优化
> 目标：能亲手构造 IP/TCP/UDP/ICMP/ARP 包，解释校验和与封装原理，
> 并用 Scapy 复现 ping / traceroute / ARP 发现。

---

## ✅ 今日完成清单

### 理解层面

- [ ] 能说出 `socket` 与 `scapy` 的**本质区别**（谁填包头、谁能看非本机流量）
- [ ] 能解释 `/` 运算符的作用，并画出 `Ether/IP/TCP/Raw` 的嵌套关系
- [ ] 能解释 `send` 与 `sendp` 的区别（内核参与程度），并说出各自何时用
- [ ] 能说出 `sr` / `sr1` / `srp` / `srp1` 的命名规律与返回差异
- [ ] 能解释为什么 `IP(chksum=None)` 是设计（而不是缺陷）
- [ ] 能说明 TCP 校验和里**伪首部**的作用
- [ ] 能说出 `show()` 与 `show2()` 的区别，并解释原因
- [ ] 能解释 `sniff(store=False)` 为什么是长期嗅探的必备参数
- [ ] 能解释 BPF 过滤为什么能救 CPU（内核态过滤 vs 用户态过滤）
- [ ] 能解释混杂模式在**交换机环境**下为什么看不到别的端口
- [ ] 能用 TTL 逐跳原理讲清 traceroute 是怎么实现的
- [ ] 能说出 SYN 半开扫描的**检测特征**（为什么 IDS 能识别）
- [ ] 能写出 16 位反码求和的算法，并说明**为什么奇数长度要补零**
- [ ] 能说出 IPv4 / TCP / UDP / ICMP 校验和各自的覆盖范围（谁有伪首部）
- [ ] 能解释 RFC 1624 的"增量更新"为什么成立（路由器改 TTL 不用重算整包）
- [ ] 能逐字节说出 pcap 的 24 字节全局头 + 16 字节记录头
- [ ] 能解释"魔数里怎么藏着字节序"，判错会发生什么
- [ ] 能说出分片的三个要点：偏移单位 8 字节、非末片 MF=1、每片都要重算校验和

### 操作层面

- [ ] `pip install scapy` 成功（**不装也能跑自检**：依赖 scapy 的断言会自动跳过）
- [ ] 跑通 `python3 -B code/01-scapy-basics.py --show`（不需要 root）
- [ ] `python3 -B code/01-scapy-basics.py --self-test` → `SELF-TEST OK`
- [ ] `python3 -B code/02-sniff-pitfalls.py --self-test` → `SELF-TEST OK`
- [ ] `python3 -B code/03-network-probe.py --self-test` → `SELF-TEST OK`
- [ ] `python3 -B code/04-checksum-and-pcap-lab.py --self-test` → `SELF-TEST OK`
- [ ] `python3 -B code/04-checksum-and-pcap-lab.py`（5 个实验讲解版）跑通
- [ ] 用 `sudo ... 01-scapy-basics.py --send --dst 127.0.0.1` 真发过包并收到响应
- [ ] 用 `sudo ... 02-sniff-pitfalls.py --sniff -i lo -f icmp -t 20` 抓到包
- [ ] 跑通 `python3 -B code/03-network-probe.py ping 127.0.0.1`（需 sudo）
- [ ] 跑通 `python3 -B code/03-network-probe.py ports 127.0.0.1 --dports 22,80,443`（需 sudo）
- [ ] 用 `tcpdump -w /tmp/x.pcap` 抓包（写进临时目录），再用 `rdpcap` / `PcapReader` 读回来分析
- [ ] 验证护栏：`python3 -B code/01-scapy-basics.py --show --dst 8.8.8.8` 应被拒绝（退出码 2）

> ⚠️ 所有自检都输出 `SELF-TEST OK` 且 **exit 0**；失败时打印"实际值 vs 期望值"并 exit 1。
> 自检**不需要 sudo、不需要网卡、不联网**：把"可验证"与"需权限"彻底分开。

### 产出物

- [ ] 一份自己抓的 pcap（仅含自己的流量；放 `/tmp`，别提交进仓库）
- [ ] 一张手绘的"封装层次图"
- [ ] 一张手绘的"校验和覆盖范围图"（IPv4 / TCP-UDP / ICMP 三张）
- [ ] 一份 traceroute 输出（目标必须是自己/私网）
- [ ] 一份"我写的 pcap 被 scapy 读回来"的实验记录（04 实验 4 的输出）

---

## 📝 基础练习（必做）

<details>
<summary>点击展开答案要点</summary>

### Q1 填充：封装顺序

把下面的层按"从外到内"排序，并写出每层的代表字段：

`Raw` / `Ether` / `TCP` / `IP`

**答案：** `Ether`（dst MAC, src MAC, type）→ `IP`（src, dst, ttl, proto）
→ `TCP`（sport, dport, flags, seq）→ `Raw`（load）

**要点：** Scapy 的书写顺序是**从左到右 = 从外到内**，与网络教材一致。

### Q2 选择：该用哪个函数？

| 场景 | 用哪个 | 理由 |
|---|---|---|
| 发一个 ICMP 包，不管回包 | `send` | L3，不需等响应 |
| 发 ARP 请求并收集响应 | `srp` | 链路层，需要响应 |
| 只要第一个响应 | `sr1` | 省时间 |
| 发自定义 Ether 帧到指定网卡 | `sendp` | 需要自己控制 L2 + iface |
| 被动抓包不发送 | `sniff` | 只收 |

### Q3 改包：把 TTL 改成 1 并观察

```python
from scapy.all import IP, ICMP, sr1

p = IP(dst="127.0.0.1", ttl=1) / ICMP()
ans = sr1(p, verbose=0, timeout=2)
print(ans.summary() if ans else "no reply")
```

**在回环上 TTL=1 也能收到回包**（因为不经过任何路由器）。
**要点：** TTL 只在"被转发"时递减；回环是本地路由，不递减。

### Q4 写一个"只看 SYN 包"的嗅探器

```python
from scapy.all import sniff

def show_syn(p):
    if p.haslayer("TCP") and "S" in str(p["TCP"].flags):
        print(f"SYN {p['IP'].src}:{p['TCP'].sport} → "
              f"{p['IP'].dst}:{p['TCP'].dport}")

sniff(iface="lo", filter="tcp[tcpflags] & tcp-syn != 0",
      prn=show_syn, store=False, count=5)
```

**要点：** `store=False`（不攒内存）+ `filter`（内核过滤）+ `count`（自动停）。

### Q5 解释：为什么这个断言会失败？

```python
p = IP(dst="127.0.0.1") / TCP(dport=80)
bytes(p)
assert p[IP].chksum is not None     # ← AssertionError!
```

**答案要点：** Scapy 的 `build()` 把算好的校验和写进**字节串**，
**不回写** Python 对象。要看到算好的值，必须：

```python
q = IP(bytes(p))        # 重新 dissect（也就是 show2 做的事）
assert q.chksum is not None
```

这也是为什么必须用 `show2()` 而不是 `show()` 来"看真实校验和"。

### Q6 用 Scapy 解析一段十六进制报文

```python
from scapy.all import Ether

raw = bytes.fromhex(
    "ffffffffffff" "001122334455" "0806"          # Ether: 广播 ARP
    "0001080006040001"                             # ARP 头（部分）
    "001122334455" "c0a80101" "000000000000" "c0a80164"
)
p = Ether(raw)
p.show()
```

**要点：** `Ether(bytes)` 会自动 dissect 出下层；这就是"pcap 解析"的最小模型。

</details>

---

## 🚀 进阶挑战（选做）

<details>
<summary>点击展开</summary>

### C1 手写一个"有限并发的 SYN 扫描器"

需求：

1. 用 `ThreadPoolExecutor` 并发（**默认 5 并发**，不是 500）；
2. 必须限速（`inter` 参数或 `time.sleep`），避免被当成 SYN Flood；
3. 结果分类：`open` / `closed` / `filtered`；
4. **只允许回环与私网目标**；
5. 输出 JSON。

**提示：** Scapy 的 `sr()` 本身是同步阻塞的，用线程池包一层；
或者用 `AsyncSniffer` + `send()` 自己配对（更难但更快）。

### C2 用 `fragment()` 理解 MTU（**已修正**：不要用 `defrag()`）

> ⚠️ 实测记录：在 **scapy 2.7.0** 上，对内存里用 `fragment()` 造出来的分片调用
> `defrag()` **不能**重组出原始包（它会把分片原样返回）。
> 因此这里改成**自己按偏移拼**（这也是理解重组的最好方式），
> `04-checksum-and-pcap-lab.py` 的 `reassemble_fragments()` 就是这个实现。

```python
from scapy.all import IP, ICMP, fragment

p = IP(dst="127.0.0.1") / ICMP() / (b"A" * 4000)
frags = fragment(p, fragsize=1480)
print("分片数:", len(frags))                       # 3
for f in frags:
    raw = bytes(f)
    ihl = (raw[0] & 0x0F) * 4                      # ⚠️ 不能用 f[IP].ihl（它是 None！）
    print(f"frag={f[IP].frag:<4} 字节偏移={f[IP].frag*8:<5} MF={bool(f[IP].flags.MF)} "
          f"长度={len(raw)}")

# 自己重组：按 frag 字段（单位 8 字节）排序后拼接载荷
ordered = sorted(frags, key=lambda f: f[IP].frag * 8)
joined = b"".join(bytes(f)[(bytes(f)[0] & 0x0F) * 4:] for f in ordered)
assert joined == bytes(p)[20:], "重组结果必须等于原始 IP 载荷"
print("✅ 自己实现的重组成功")
```

**思考：**
1. `fragsize` 必须是 8 的倍数，为什么？（提示：偏移字段以 8 字节为单位）
2. 为什么**每个分片的 IP 校验和都不一样**？（提示：分片改写了 IP 头的哪些字段）
3. 如果丢掉中间一片，重组应该报错还是"尽力拼"？为什么？
   （提示：残缺数据比报错更危险 —— 后续解析会得出错误结论）

### C3 复现 traceroute 并画出路径

需求：写一个函数，返回 `[(hop, ip, rtt_ms), ...]`，
并用 ASCII 画出一条路径图：

```
127.0.0.1 ──(0.3ms)──► 192.168.1.1 ──(1.2ms)──► * ──(2.1ms)──► 8.8.8.8
```

**注意：** 目标是公网时，本日代码的护栏会拒绝。折中做法：
只在**你的实验环境**（如 netns / 虚拟机网络）里做，或把目标换成私网。

### C4 写一个"ARP 表监视器"

需求：周期性发 ARP 查询，检测**同一 IP 的 MAC 是否变化**（ARP 欺骗的典型特征）：

```python
import time
from scapy.all import Ether, ARP, srp

def arp_table(cidr):
    ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=cidr),
                 timeout=2, verbose=0)
    return {rcv.psrc: rcv.hwsrc for _, rcv in ans}

prev = arp_table("192.168.1.0/24")      # 改成你自己的网段
while True:
    time.sleep(60)
    now = arp_table("192.168.1.0/24")
    for ip, mac in now.items():
        if ip in prev and prev[ip] != mac:
            print(f"🚨 ARP 变化: {ip} {prev[ip]} → {mac}（疑似 ARP 欺骗）")
    prev = now
```

**这是防御工具，不是攻击工具**——这正是安全工程师该做的事：
把攻击特征变成监控指标。

### C4b 把校验和实验室扩展成"自造 pcap 工具链"

需求（都在 `/tmp` 里做，不污染仓库）：

1. 用 `04` 里的 `write_pcap()` 写一个含 100 个随机 IP 包的 pcap；
2. 用 `read_pcap()` 读回来，逐包**验证 IPv4 头校验和**（自己实现的反码和）；
3. 故意改掉其中 5 个包的 TTL（不重算校验和），断言"恰好 5 个包验证失败"；
4. 再对那 5 个包做 **RFC 1624 增量更新**，断言"改完后全部验证通过"。

**这一题把 04 的三个实验串成了一条完整的证据链**：
写文件 → 读文件 → 验完整性 → 定位篡改 → 修复校验和。

### C5 对比 Scapy 与 socat/nmap 的性能

需求：用三种方式扫描回环上的 100 个端口，记录耗时：

1. Scapy `sr1` 串行；
2. Scapy 线程池 10 并发；
3. `nmap -sT -p1-100 127.0.0.1`（如果装了）。

**结论预期：** nmap 快一个数量级以上。
**这就是"Scapy 是显微镜，不是流水线"的实证。**

</details>

---

## 📌 今日自检的五个问题

1. `send` 和 `sendp` 差在哪一条内核路径上？为什么 `sendp` 必须给 `iface`？
2. 为什么 `IP().chksum` 是 `None`？这个设计解决了什么问题？
3. 你写了个 SYN 扫描器，**为什么它会被 IDS 发现**？
   如果让你做防御方，你会怎么降低误报？
4. 校验和为什么要用**反码和**而不是普通求和？
   （提示：想想路由器每跳都要改 TTL）
5. pcap 的魔数为什么能表示字节序？把大端文件按小端读会发生什么？
   （提示：`incl_len` 会变成什么，然后 `read()` 会做什么）

---

## 🚫 今日红线

- ❌ 不扫描/嗅探任何**不属于你**的网络与设备；
- ❌ 不伪造源 IP（本日代码不提供该功能，请不要自己加）；
- ❌ 不在生产网段跑 ARP 扫描（会触发网络告警，且可能被当成攻击）；
- ❌ 不把抓到的 pcap 直接外发（里面可能有他人的凭据/隐私）；
- ❌ 不用 Scapy 对**公网**目标做任何测试；
- ❌ 不把演示产物（pcap / 日志）留在仓库工作树里 —— 一律写进 `tempfile` 临时目录；
- ✅ 拿不准时，**只打 127.0.0.1**。
