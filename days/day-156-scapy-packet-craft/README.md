# Day 156 — Scapy 数据包构造：从 IP/TCP 到自定义网络探测工具

> 阶段：Phase 7 — 进阶与性能优化 · 主题：Scapy 数据包构造
>
> 前置知识：Day 116 TCP/UDP 协议、Day 115 socket 编程、Day 153 端口扫描进阶、
> Day 155 mitmproxy（应用层视角）。
> 前面几天我们站在**应用层**看流量（HTTP 请求、代理改包）。
> 今天往下走两层：**亲手构造 IP / TCP / UDP / ICMP 包并丢到网络上**。

---

## ⚠️ 使用前必读：法律边界

构造原始数据包（raw packet）意味着**绕过操作系统协议栈，自己决定每一个字段**。
这意味着你可以：

- 伪造源 IP（spoofing）→ 用于反射放大攻击、绕过基于 IP 的认证；
- 构造半开连接（SYN）→ 隐蔽端口扫描；
- 构造畸形包 → 探测协议栈实现缺陷。

**这些能力本身就是"攻击能力"**，所以法律风险比前几日更高：

| 法域 | 相关法条 |
|---|---|
| 中国大陆 | 《刑法》第 285、286 条；《网络安全法》第 27 条 |
| 美国 | CFAA 18 U.S.C. § 1030 |
| 英国 | Computer Misuse Act 1990, s.1 / s.3 |
| 欧盟 | 《网络犯罪公约》相关条款 |

**允许使用本日内容的场景（白名单）：**

1. **本机回环**（`127.0.0.1`）——最安全，什么都不会流出去；
2. **你自己的私网**（`192.168.x.x` / `10.x.x.x`），且设备都是你的；
3. 授权靶场 / 实验环境（含虚拟机、容器网络、netns）；
4. 你自己写的协议实现的**单元测试**。

**本日所有示例：**

- 目标 IP 必须落在**本机或私有网段**白名单内，否则拒绝执行；
- 默认 `--dry-run`（只构造不发送），要真发必须显式 `--send`；
- **不提供**任何伪造源 IP 的示例代码。

> 学会构造包最大的价值是**理解协议**：你从此能一眼看穿
> "为什么这个连接超时""为什么这个扫描能被检测到""为什么 MTU 会让包被丢"。

---

## 一、概念解释

### 1.1 Scapy 是什么，和 `socket` 有什么本质区别

| 维度 | `socket`（Day 115） | `scapy` |
|---|---|---|
| 抽象层次 | 传输层（TCP/UDP） | **链路层到应用层（L2~L7）都能自己拼** |
| 谁能填包头 | 内核 | **你** |
| 能改 TTL / 标志位 / 校验和吗 | ❌（要 setsockopt 且有限） | ✅ 任意字段 |
| 能收到"不是发给本机"的包吗 | ❌ | ✅（混杂模式） |
| 能构造 ICMP / ARP 吗 | ❌ | ✅ |
| 性能 | 快（内核态） | 慢（纯 Python） |
| 典型用途 | 业务网络编程 | 协议分析、安全测试、网络探测、教学 |

**一句话区别：**

```
socket  → "我要和某人通话"（内核负责把话打包、寄出）
scapy   → "我要亲手写一个信封，包括信封上的每一个字，然后自己投进邮筒"
```

**为什么需要 Scapy？** 因为在很多场景下，**内核不允许你做的事情，恰恰是理解
协议或做安全测试必须做的事情**：

- 内核不允许你发源 IP 不是本机的包（防伪造）；
- 内核不允许你发 TCP 标志位组合诡异的包（防畸形包）；
- 内核不关心 ARP 层的细节（自动处理了）；
- 内核不会把"不是发给你的包"交给你（除非混杂模式 + AF_PACKET）。

### 1.2 分层封装模型：理解 `/` 运算符

Scapy 的核心心智模型是**"用 `/` 把各层叠起来"**：

```python
pkt = Ether() / IP(dst="192.168.1.1") / TCP(dport=80) / b"GET / HTTP/1.0\r\n\r\n"
```

读作"**Ether 上面套 IP，IP 上面套 TCP，TCP 上面是这段载荷**"——
和网络教材里的封装图完全对应：

```
┌──────────────────────────────────────────────┐
│ 应用层数据  b"GET / HTTP/1.0\r\n\r\n"          │  ← 你提供的字节
├──────────────────────────────────────────────┤
│ TCP 头  sport=随机 dport=80 flags=S seq=...   │  ← Scapy 填
├──────────────────────────────────────────────┤
│ IP 头   src=本机 dst=192.168.1.1 ttl=64 proto=6│  ← Scapy 填
├──────────────────────────────────────────────┤
│ Ether    dst=MAC src=MAC type=0x0800          │  ← Scapy 填（或内核填）
└──────────────────────────────────────────────┘
```

**为什么用 `/` 这个运算符？** 因为 Python 的除法运算符**没有其它语义冲突**，
且视觉上就是"叠加"。Scapy 把 `/` 重载为 `__truediv__`，返回一个合并后的
`Packet` 对象。**注意：`/` 只能连接"层"，不能连接两个同层包**。

**如果你省略底层会怎样？**

- `send(IP(...)/TCP(...))`：Scapy 让**内核**帮忙补 Ether 层（走正常路由）；
- `sendp(Ether()/IP(...)/TCP(...))`：Scapy 在**链路层**直接发，
  绕过内核路由表（需要网卡名 `iface`）。

**这是 Scapy 新手最容易混淆的一组函数（`send` vs `sendp`）。**

### 1.3 发送与接收：`send*` / `sr*` 家族

| 函数 | 层次 | 发 | 收 | 一句话 |
|---|---|---|---|---|
| `send(pkt)` | L3 | ✅ | ❌ | 发 IP 包，不管回包 |
| `sendp(pkt)` | L2 | ✅ | ❌ | 发以太网帧，不管回包 |
| `sr(pkt)` | L3 | ✅ | ✅ | **发并收，返回 (answered, unanswered)** |
| `sr1(pkt)` | L3 | ✅ | ✅ | 发并收，只返回**第一个**回包 |
| `srp(pkt)` | L2 | ✅ | ✅ | 链路层版的 sr（常用于 ARP） |
| `srp1(pkt)` | L2 | ✅ | ✅ | 链路层只取第一个 |
| `srloop/sendpfast` | — | 循环 | — | 批量/高性能场景 |
| `sniff()` | — | ❌ | ✅ | 被动嗅探 |

**命名规律（记住它就不会用错）：**

```
send  / sr    → L3（IP 层，内核补 L2）
sendp / srp   → L2（链路层，自己给 L2）
带 1 后缀      → 只等第一个响应
带 loop 后缀   → 一直循环
带 flood 后缀  → 快速发送不等待
```

### 1.4 嗅探：`sniff()` 与 BPF 过滤

```python
from scapy.all import sniff

pkts = sniff(count=10, timeout=30, iface="eth0", filter="tcp port 80")
```

**为什么必须有 `filter`？** 因为不加过滤时，内核要把**每一个**包都
复制到用户态，Scapy 再用纯 Python 逐字段解析——在千兆网卡上瞬间吃满 CPU。
`filter` 使用 **BPF（Berkeley Packet Filter）** 语法，由**内核**先行过滤，
只把命中的包交给 Scapy。**这是性能生死线。**

**为什么需要 root / CAP_NET_RAW？** 因为创建 `AF_PACKET` 套接字、
把网卡切到混杂模式，都是特权操作。**这也是为什么容器里要加
`--cap-add=NET_RAW --cap-add=NET_ADMIN`。**

### 1.5 混杂模式（promiscuous）到底是什么意思

| 模式 | 网卡行为 |
|---|---|
| 普通模式 | 只把"目的 MAC 是我"的帧交给内核 |
| **混杂模式** | 把**经过网卡的所有帧**都交给内核（同网段的都能看到） |
| 监控模式（monitor） | WiFi 专用，收到所有 802.11 帧（含未关联的） |

**关键认知：**

- 交换机环境下，混杂模式**看不到别的端口**的流量（除非端口镜像/ARP 欺骗）；
- **Hub / WiFi / 虚拟机桥接**场景下，混杂模式能看到同网段的流量；
- 所以"嗅探"能拿到什么，取决于**你在网络拓扑里的位置**——
  这也是为什么面试常问"交换机如何防嗅探"（答案是：你防不了，只能防 ARP 欺骗）。

### 1.6 半开扫描（SYN scan）与 Scapy

用 `socket.connect()` 扫描会完成三次握手（留下日志、被应用层看到）；
用 Scapy 可以**只发 SYN**：

```
   扫描器                     目标
     │  SYN  ──────────────────►│
     │◄── SYN-ACK（端口开放）────│   ← 收到后立刻发 RST，不完成握手
     │  RST  ──────────────────►│
     │                          │
     │◄── RST,ACK（端口关闭）────│
     │                          │
     │  （无响应 = 被防火墙丢包） │
```

**为什么"半开"更隐蔽？** 因为在**应用层从未建立连接**，服务器的
Web/SSH 日志里不会出现这次连接。但**仍然会在网络层留下痕迹**——
IDS/防火墙能看到 SYN 而看不到后续握手（这正是 SYN 扫描的检测特征）。

**同时这也是 Scapy 的核心教学价值：** 你能亲手实现"内核不让你做的事"，
从而真正理解"为什么防火墙能看到扫描"。

### 1.7 Scapy 的定位：什么时候**不该**用它

| 场景 | 该用 Scapy 吗 | 原因 |
|---|---|---|
| 批量端口扫描生产环境 | ❌ | 太慢；用 nmap / masscan |
| 写 Web 爬虫 / API 客户端 | ❌ | 用 requests/httpx |
| 高吞吐流量采集 | ❌ | 用 dpdk / PF_RING / eBPF |
| 协议教学、报文构造 | ✅ | 无可替代 |
| 畸形包 / fuzz 测试 | ✅ | 能改任意字段 |
| ARP / ICMP / 自定义协议实验 | ✅ | 内核不给你做 |
| PCAP 解析与特征提取 | ⚠️ | 小文件可以，大文件用 dpkt/pyshark/scapy+PcapReader 流式 |

**一句话：Scapy 是"协议的显微镜"，不是"网络的流水线"。**

---
## 二、原理解释（底层机制与设计动机）

### 2.1 一次 `send()` 在内核里发生了什么

```
你的 Python 进程
   │  pkt = IP(dst="10.0.0.5")/ICMP()
   │  send(pkt)
   ▼
Scapy 序列化：把 Python 对象 → bytes（逐字段 pack，自动算校验和）
   ▼
socket(AF_INET, SOCK_RAW, IPPROTO_RAW)     ← 需要 CAP_NET_RAW
   │  sendto(bytes, (dst, 0))
   ▼
内核路由表查询 → 选出出口网卡与下一跳
   ▼
内核补上 Ether 头（源/目的 MAC 由 ARP 缓存决定）
   ▼
网卡驱动 → DMA → 物理发送
```

**关键点：**

1. `send()` 走的是 `AF_INET + SOCK_RAW`，**内核仍参与**（补 L2、查路由）；
2. `sendp()` 走的是 `AF_PACKET + SOCK_RAW`，**直接指定网卡**，
   连 Ether 头都由你决定——所以它需要 `iface` 参数；
3. 用 `SOCK_RAW` 时，有些平台（Linux）**内核会自动补 IP 校验和**，
   有些平台不会；Scapy 默认自己算，可用 `IP(len=...)` 之类手动覆盖。

**为什么必须 root？** 因为 `SOCK_RAW` / `AF_PACKET` 允许你构造任意报文，
是典型的"可绕过内核安全策略"的能力。Linux 用 capability 收窄权限：
`CAP_NET_RAW`（发原始包）、`CAP_NET_ADMIN`（改网卡配置）。

### 2.2 Scapy 的对象模型：`Packet` + `Field`

Scapy 每个协议层都是一个 Python 类，字段用**类属性 + 描述符**声明：

```python
class IP(Packet):
    name = "IP"
    fields_desc = [
        BitField("version", 4, 4),        # 4 位
        BitField("ihl", None, 4),         # 4 位，None = 自动计算
        ByteField("tos", 0),              # 8 位
        ShortField("len", None),          # 16 位，None = 自动计算
        ShortField("id", 1),
        FlagsField("flags", 0, 3, ["MF", "DF", "evil"]),
        BitField("frag", 0, 13),
        ByteField("ttl", 64),
        ByteEnumField("proto", 0, {1: "icmp", 6: "tcp", 17: "udp"}),
        XShortField("chksum", None),      # None = 自动计算
        IPField("src", "127.0.0.1"),
        IPField("dst", "127.0.0.1"),
    ]
```

**设计动机（这是 Scapy 最巧妙的地方）：**

- **`None` 表示"等我算"**：`len`、`chksum`、`ihl` 这些"派生字段"，
  在序列化时根据实际内容自动计算；
- **字段级联（overloading）**：`IP(dst="1.2.3.4", ttl=1)` 或
  `IP()/TCP()` 都能工作，因为 `Packet.__init__` 用**位置/关键字参数**
  匹配 `fields_desc`；
- **可变字段（`fuzz` / `RandShort()`）**：把字段设成随机生成器对象，
  每次序列化都取新值——这是 fuzz 测试的基础。

**`/` 运算符的实现：**

```python
def __truediv__(self, other):
    # 把 other 挂到 self 的 payload 上（或合并到最后一层）
    ...
```

所以 `IP()/TCP()` 得到的是"一个 IP 包，payload 是 TCP 对象"，
序列化时**自底向上**逐层 pack。

### 2.3 校验和（checksum）是怎么算出来的

IPv4 头校验和是**16 位反码求和**：

```
1. 把头部按 16 位分组
2. 全部相加（进位回卷）
3. 取反码
```

Scapy 的 `IP.chksum` 字段为 `None` 时，在 `post_build` 阶段调用
`checksum(pkt)` 计算并回填。TCP/UDP 校验和更麻烦——它需要一个
**伪首部（pseudo-header）**：

```
伪首部（仅用于计算，不真正发送）:
  ┌────────────┬────────────┬──────────┬─────────┐
  │ 源 IP (32) │ 目的 IP(32)│ 0 │proto │ TCP 长度 │
  └────────────┴────────────┴──────────┴─────────┘
                              ↑ 这里隐藏了一个经典陷阱：
                                伪首部里的 proto 字段是 8 位，但为了
                                16 位对齐，前面补 0，所以其实占了 16 位
```

**为什么 TCP 校验和要包含伪首部？** 为了**防止报文被错误投递**：
如果路由器把包投到了错误的 IP，接收方算校验和会不一致（因为源/目的 IP
参与了计算），从而丢弃。这是"端到端校验"思想的一个体现。

**常见错误**：手动改 TCP 载荷后忘了重算校验和 → 抓包看是"TCP checksum
incorrect"，服务端静默丢弃。**Scapy 的规则：用 `pkt[TCP].payload = b"..."`，
不要绕过对象直接改 `bytes`。**

### 2.4 为什么 Scapy 慢

| 环节 | 代价 |
|---|---|
| Python 对象 → bytes 序列化 | 每个字段一次 Python 函数调用 |
| bytes → Python 对象 反序列化 | 逐层猜测下一层类型（`guess_payload_class`） |
| 内省（introspection） | `fields_desc` 描述符查找 |
| 无零拷贝 | 每层都做一次内存复制 |
| 单线程 | 默认没有并行发送 |

**量级参考：**

- Scapy 构造 1 万个包：约几秒；
- 用 `sendpfast`（底层调 tcpreplay）或 `AsyncSniffer` 会快不少；
- nmap 用 C 写的扫描一个 C 段只要几秒，Scapy 同样任务要几分钟。

**结论：** 教学/实验/低频探测用 Scapy，**量大用专用工具**。

### 2.5 `sniff()` 的内核路径与丢包

```
网卡收到帧
   ▼
内核 netif_receive_skb
   ├─→ 协议栈（正常的 TCP/IP 处理）
   └─→ AF_PACKET 套接字（Scapy 的 socket）
          │  ① BPF 过滤（如果设置了 filter）
          │  ② 放入环形缓冲区（默认 208KB！）
          │  ③ 用户态 recvfrom()
          ▼
       Scapy 逐层解析 → Packet 对象
```

**丢包的三个原因：**

1. **环形缓冲区太小**：默认 `net.core.rmem_default` / `rmem_max` 约 200KB，
   突发流量下瞬间写满 → 内核直接丢；
2. **用户态处理太慢**：Scapy 解析速度跟不上包速率；
3. **没有 BPF 过滤**：全部包都往用户态搬。

**解决：**

```bash
# 放大缓冲区（需要 root）
sysctl -w net.core.rmem_max=26214400
sysctl -w net.core.rmem_default=26214400
```

```python
# Scapy 侧：用 PcapReader / AsyncSniffer + 只处理必要字段
from scapy.all import AsyncSniffer
sniffer = AsyncSniffer(iface="eth0", filter="tcp", prn=handler, store=False)
sniffer.start()
```

**为什么 `store=False` 很重要？** 默认 `sniff()` 会把**所有**包存在
一个 list 里返回——长时间嗅探时内存会无限增长直到 OOM。
**`store=False` 是长时间嗅探的必备参数。**

### 2.6 TTL 与 traceroute 原理

traceroute 的原理极其优雅：

```
TTL=1 的包 → 第一跳路由器收到，TTL 减到 0 → 回 ICMP Time Exceeded
TTL=2 的包 → 第二跳路由器 → 回 ICMP Time Exceeded
...
TTL=N 的包 → 到达目标 → 回 ICMP Echo Reply（或目标端口的响应）
```

**逐跳递增 TTL，收集每一跳的源 IP，就得到了路径。**
Scapy 自带 `traceroute()`，也可以手写（本日示例 03 会用 Scapy 复现）：

```python
ans, unans = sr(IP(dst=target, ttl=(1, 10)) / ICMP(), timeout=1)
```

**为什么会有 `*`（超时）？** 三种情况：
① 该跳路由器配置了"不发送 ICMP 超时"（隐蔽路由）；
② 丢包；
③ 链路太长/超时太短。

### 2.7 ARP 与局域网发现

ARP 是"IP → MAC"的解析协议，工作在**链路层**（无 IP 头）：

```
"谁是 192.168.1.1？请告诉 192.168.1.100"
  → 广播帧（目的 MAC = ff:ff:ff:ff:ff:ff）
  ← 单播应答："192.168.1.1 是 aa:bb:cc:dd:ee:ff"
```

**用 Scapy 做局域网存活发现（本日示例 03 的第二个功能）：**

```python
ans, unans = srp(Ether(dst="ff:ff:ff:ff:ff:ff") /
                 ARP(pdst="192.168.1.0/24"), timeout=2)
for snd, rcv in ans:
    print(rcv.psrc, rcv.hwsrc)      # IP + MAC
```

**为什么比 ping 扫描快且准？**

- ARP 走链路层，**不受主机防火墙"禁 ICMP"影响**（很多主机不回 ping 但必须回 ARP）；
- 交换机必须转发 ARP 广播，响应是单播，速度快。

**安全警示：** ARP 没有认证，所以可以**伪造 ARP 应答**（ARP 欺骗），
这也是抓包/中间人的经典手段。**本日不提供任何 ARP 欺骗示例**——
只做"查询"，不做"应答"。

---
