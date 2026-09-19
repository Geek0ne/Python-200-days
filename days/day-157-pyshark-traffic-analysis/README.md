# Day 157 — 流量分析：PCAP 格式、pyshark/tshark 与标准库解析双路径

> 阶段：Phase 10 — 网络安全开发 · 主题：PCAP 文件分析（pyshark 及标准库实现）
>
> 前置知识：Day 115 socket 编程、Day 116 TCP/UDP、Day 153 端口扫描进阶、
> Day 156 Scapy 数据包构造（**建议先看 156**：那里讲"怎么造包"，这里讲"怎么读包/下结论"）。
>
> 本日要解决三个现实问题：
> 1. **PCAP/PCAPNG 文件到底是什么字节结构？**（能自己解析，才算真懂）
> 2. **pyshark 为什么依赖 tshark？没装 tshark 的机器怎么活？**（工程上的降级设计）
> 3. **怎么从一堆包得出"有人在扫描 / 有人在隧道外泄 / 主机被 C2 控制"的结论？**
>    （检测原理 + 误报控制）

---

## 目录

- [一、概念解释](#一概念解释)
- [二、底层原理与机制](#二底层原理与机制)
- [三、攻击方式·手段·原理 与 检测原理](#三攻击方式手段原理-与-检测原理)
- [四、防护/修复原理](#四防护修复原理)
- [五、代码案例逐节说明](#五代码案例逐节说明)
- [六、运行命令 + 预期输出](#六运行命令--预期输出)
- [七、常见陷阱速查表](#七常见陷阱速查表)
- [八、局限（必须知道）](#八局限必须知道)
- [九、思考题](#九思考题)
- [附：本日文件清单](#附本日文件清单)

---

## 一、概念解释

### 1.1 PCAP 是什么

**PCAP（Packet CAPture）是"抓包结果"的标准文件格式**，由 libpcap（tcpdump 背后的库）
定义。它的设计极其简单，简单到**24 字节文件头 + 每包 16 字节记录头**：

```
┌──────────────── 全局头 24 字节 ────────────────┐
│ magic(4) version(4) thiszone(4) sigfigs(4)    │
│ snaplen(4) network(4)                          │
├──────────────── 每个包一条记录 ────────────────┤
│ ts_sec(4) ts_usec(4) incl_len(4) orig_len(4)  │
│ 包数据（incl_len 字节）                          │
├──────────────── 下一条记录 … ──────────────────┤
```

关键特性（后面每个坑都从这里长出来）：

| 特性 | 后果 |
|---|---|
| 魔数里带**字节序**信息 | 读之前必须先判断大小端，判错会读出天文数字长度 |
| **没有任何"总包数"字段** | 只能读到文件尾；抓包进程被 kill 时最后一条记录是残缺的 |
| 每条记录有 `incl_len` 与 `orig_len` 两个长度 | 抓包时可以用 `-s` 只抓前 N 字节（snaplen），此时 `incl_len < orig_len`，**载荷是被截断的** |
| 时间戳有**微秒/纳秒**两种魔数 | 精度不同，混着用会差 1000 倍 |

> **PCAPNG** 是下一代格式（Wireshark 默认保存格式）。它是一串"块(block)"：
> 每块 = `类型(4) + 总长度(4) + 内容 + 总长度(4)`（长度出现两次，方便从后往前遍历）。
> 好处：支持多网卡、接口注释、纳秒时间戳、上游进程信息。
> **代价：格式复杂得多，而且初学者经常把 pcapng 喂给只认 pcap 的解析器**
> —— 这正是本日 `sniff_format()` 第一步就做的事（先认格式，再解析）。

### 1.2 pyshark 是什么：它不是一个解析器

**pyshark 本质上是 tshark（Wireshark 的命令行版）的 Python 包装**。

```
        ┌──────────────┐   subprocess   ┌──────────────────┐
PCAP ──►│    tshark    │ ─────────────► │ XML / JSON 文本   │──► pyshark 解析成对象
        │（C 解析引擎） │  （-T ek / -T pdml）                  │
        └──────────────┘                                       ▼
                                                        你的 Python 代码
```

三个必须记住的结论：

1. **pyshark 的解析能力 = tshark 的解析能力**：tshark 认识 3000+ 协议，
   所以 pyshark 也认识；但要清楚这是**借来的能力**。
2. **它没有 tshark 就完全不能工作**：`import pyshark` 在没装 Wireshark 的机器上
   直接 `ModuleNotFoundError`。本日运行环境就是这种情况——`python3 -c "import pyshark"`
   会报错，所以**本日的自检被设计成完全不依赖它**。
3. **它每读一批包都要和子进程通信**：进程间管道 + 文本解析 → 大文件慢。
   真正高性能场景用 Zeek、dpkt 或自己做流式解析。

### 1.3 五个工具的分工（别用错工具）

| 工具 | 谁在解析 | 能读 | 能写/发包 | 速度 | 适合 |
|---|---|---|---|---|---|
| **tshark** | C（Wireshark 引擎） | pcap/pcapng | 转换格式 | 快 | 命令行快速挑包、批量字段导出 |
| **pyshark** | tshark + Python 包装 | pcap/pcapng | ❌ | 中 | Python 里用 Wireshark 的全协议能力 |
| **scapy**（Day156） | 纯 Python | pcap/pcapng | ✅ 能造包发包 | 慢 | 造包、改包、协议实验 |
| **dpkt** | 纯 Python | pcap/pcapng | 有限 | 中 | 高性能纯 Python 解析（无外部依赖） |
| **标准库 pcap_lib**（本日） | 纯 Python | pcap/pcapng | ✅ 能造包 | 慢 | **离线自检、教学、无依赖兜底** |

> 一句话选择：**要全协议 → pyshark/tshark；要造包 → scapy；
> 要"在任何机器上都能跑的自检和轻量统计" → 标准库自己写（本日重点）。**

### 1.4 先把两个"过滤"分清：BPF 与 display filter

这是本日**最容易糊涂**的概念。很多人写了三年抓包命令，也没分清：

| 维度 | BPF（`bpf_filter` / 捕获过滤） | display filter（显示过滤） |
|---|---|---|
| 何时生效 | **抓包时**（包进入内核的那一刻） | **解析后**（读文件/拿到包之后） |
| 在哪执行 | **内核**（libpcap 把表达式编译成字节码） | **用户态**（tshark/pyshark/本库逐包求值） |
| 看到的是什么 | **原始字节的固定偏移** | 任意**解析出来的协议字段** |
| 写法 | `tcp[tcpflags] & tcp-syn != 0` | `tcp.flags.syn == 1` |
| 没命中的包 | **永远不会到达用户态**（丢了就是丢了） | 还在文件里，改条件就能看 |
| 性能 | 极高（不命中的包 0 拷贝） | 一般（每包都要 dissect） |
| 典型用途 | 长时间抓包时挡掉 99% 噪声 | 事后从各个角度挑包 |

**一句话记忆：BPF 决定"你手里有什么"，display filter 决定"你先看哪一条"。**

**为什么 BPF 只能看固定偏移？** 因为它运行在**协议解析之前**。内核不认识
"HTTP 方法"是什么，它只认"从 TCP 头开始第 2 个字节的 2 字节等于 80"。
所以 `port 80` 在内核里其实展开成这样：

```
(tcp[2:2]==80 or tcp[4:2]==80) or (udp[2:2]==80 or udp[4:2]==80)
```

### 1.5 本日的双路径设计（为什么自检不依赖 pyshark）

```
                    ┌──────────────────────────────┐
   统一数据结构 IR   │ number/ts/ip/tcp/udp/http …  │  ← 字段名对齐 Wireshark 显示过滤器名
                    └──────────────▲───────────────┘
                                   │
        ┌──────────────────────────┴──────────────────────────┐
        │                                                     │
 ┌──────┴──────┐                                     ┌────────┴────────┐
 │  pyshark 路 │  import pyshark → FileCapture        │  标准库路 pcap_lib│
 │  （全协议） │  依赖 tshark 二进制                   │  纯 stdlib，零依赖 │
 └─────────────┘                                     └─────────────────┘
```

上层代码（统计、检测、报告）**完全不关心**用的是哪条路径：
`--backend auto` 有 pyshark 就用，没有就自动降级；`--backend pyshark` 则
**明确报错而不是静默降级**（否则你永远不知道自己在跑哪条路）。

---

## 二、底层原理与机制

### 2.1 pcap 文件头逐字节（为什么字节序判断是第一道坎）

```
偏移  长度  字段            说明
0     4     magic           0xa1b2c3d4(微秒) / 0xa1b23c4d(纳秒)
4     2     version_major   2
6     2     version_minor   4
8     4     thiszone        时区修正，**永远是 0**（历史包袱，从未使用）
12    4     sigfigs         时间戳精度，**永远是 0**
16    4     snaplen         抓包时每个包最多抓多少字节
20    4     network         链路类型：1=Ethernet, 0=NULL(BSD lo), 113=Linux SLL(any 网卡)
```

**魔数陷阱（必须理解）**：写文件的一方按自己的 CPU 字节序写入 `0xa1b2c3d4`。
读的时候如果按小端读：

| 读出来的值 | 含义 | 后续 struct 前缀 |
|---|---|---|
| `0xa1b2c3d4` | 小端文件、微秒 | `<` |
| `0xd4c3b2a1` | **大端文件**（字节被交换） | `>` |
| `0xa1b23c4d` | 小端文件、**纳秒** | `<`（时间戳 ÷1e9） |
| `0x4d3cb2a1` | 大端文件、纳秒 | `>`（÷1e9） |

判错的后果非常具体：`incl_len` 会变成一个天文数字，然后
`f.read(incl_len)` **一口吃掉大半个文件**，后面的解析全乱。
本库因此加了一个保险：单包长度 > 256KB 直接报错并提示"字节序可能判错了"。

### 2.2 pcapng 的块结构与 `if_tsresol` 深坑

```
Section Header Block (SHB, 0x0A0D0D0A)
  ├ 字节序魔数 0x1A2B3C4D（用来判断这个段是大端还是小端）
  ├ 版本 1.0
  └ 段长度（-1 = 未知，读到 EOF 为止）
Interface Description Block (IDB, 0x00000001)
  ├ linktype(2) 保留(2) snaplen(4)
  └ 选项：if_tsresol(码 9)、if_name、if_speed …
Enhanced Packet Block (EPB, 0x00000006)
  ├ 接口号(4) 时间戳高32位(4) 时间戳低32位(4) caplen(4) origlen(4)
  └ 包数据（**必须 4 字节对齐填充**）+ 选项
```

**`if_tsresol` 这个 1 字节的值有双重含义**（本库自检真的抓到过这个 bug）：

- 最高位 = 0 → 分辨率 = **10⁻ⁿ**（`n=6` 就是微秒，最常见的默认值）
- 最高位 = 1 → 分辨率 = **2⁻ⁿ**（`0x80|6` → 1/64 秒，某些二进制时钟的设备）

我第一版实现按 `2ⁿ` 处理，结果时间戳精度掉到 **15.625ms**
（表现为"时间戳看着差不多，但怎么都对不齐"）。修正后 1:1 复现原始时间戳。
**这类 bug 的可怕之处是它不报错，只是数字微错** —— 所以自检必须断言时间差。

另一个点：**未知块必须能跳过**。文件里会出现 NRB(名字解析)、ISB(统计)、
厂商自定义块；如果解析器"遇到不认识的块就报错"，等 Wireshark 升级加个新块，
你的工具就废了。本库只认 SHB/IDB/EPB/SPB，其余按长度跳过。

### 2.3 dissection 模型：逐层剥头 + 猜下一层

pyshark（以及本库）的核心思想都是"**剥洋葱**"：

```
以太网头 → 看 ethertype → 0x0800 就交给 IPv4，0x86DD 交给 IPv6，0x0806 交给 ARP
IPv4 头  → 看 proto     → 6 交给 TCP，17 交给 UDP，1 交给 ICMP
TCP 头   → 看端口       → 53 交给 DNS，80 交给 HTTP
```

每一步都要处理"**我怎么知道下一层是什么**"这个问题：

| 层 | 判断依据 | 坑 |
|---|---|---|
| 链路层 | EtherType | VLAN(0x8100) 会在中间插 4 字节，**不剥就会全错位** |
| 网络层 | IP 头 `proto` 字段 | 分片包（frag_offset≠0）没有传输层头，硬解会得到垃圾 |
| 传输层 | 端口号 | 非标端口（8080、8443）需要靠**内容特征**兜底 |
| 应用层 | 内容特征 | HTTP/2 是二进制帧，按文本解会失败；TLS 更是完全加密 |

这就是"为什么排障时经常看到 `[Malformed Packet]`"：
解析器按规则猜下一层，猜错就把后面的字节当成别的协议头。

### 2.4 校验和：三种算法，一篇讲透

| 协议 | 校验和覆盖范围 | 有没有伪首部 | 备注 |
|---|---|---|---|
| IPv4 | **只有 IP 头**（20~60 字节） | ❌ | 每跳 TTL 递减都要增量更新 |
| TCP | 伪首部 + TCP 头 + 载荷 | ✅ | **改载荷必须重算** |
| UDP | 伪首部 + UDP 头 + 载荷 | ✅ | 值为 0 表示"发送方没算"，不算错 |
| ICMP | **整条 ICMP 消息** | ❌ | 和 TCP/UDP 不同，容易记混 |
| IPv6 | 无头校验和 | — | 交给上层，且**强制**校验 |

**算法（16 位反码求和）**：

```
1) 数据按 16 位一组当大端整数相加（奇数长度末尾补一个 0x00 字节！）
2) 结果的高 16 位是进位，回卷加到低 16 位（可能卷多次）
3) 取反码 → 这就是要填进校验和字段的值
4) 验证时：把"含校验和字段"的整段再算一次反码和，结果应为 0xFFFF
```

**为什么用反码和而不是普通和？** 因为它**可结合、可交换**：
路由器只需要"减掉旧 TTL、加上新 TTL"就能增量更新校验和，
不用重算整包——这是 1970 年代为路由器性能做的设计取舍。

**伪首部为什么存在？** 它包含源/目的 IP，作用不是检错而是**防误投递**：
如果包被错误路由到别的 IP，接收端算出的校验和对不上 → 丢弃。
（延伸：这也解释了为什么 NAT 改 IP/端口**必须**同时改 TCP/UDP 校验和，
改错就变成"连接能建但数据全丢"的玄学故障。）

### 2.5 为什么 tshark 快、纯 Python 慢

| 环节 | tshark（C） | 纯 Python（本库） |
|---|---|---|
| 字节 → 字段 | 指针偏移 + 位运算 | 每个字段一次 `int.from_bytes` |
| 字符串/对象开销 | 无（写固定缓冲区） | 每包多个 dict/str 对象，有 GC 压力 |
| 状态机（流重组） | 有（且很强） | 本教学库**没有** |
| 量级 | 百万包/秒级 | 万包/秒级（差 2 个数量级以上） |

**这正是"双路径"存在的理由**：pyshark 用于全协议、大批量；
标准库路径用于**离线自检、无依赖环境、轻量统计**（本日 70 个包的演示场景
纯 Python 完全够用）。

### 2.6 为什么内核态过滤能救 CPU

```
网卡收到帧
   │
   ▼
内核 netif_receive_skb
   ├──────────────────────────► 正常协议栈（TCP/IP）
   └──► AF_PACKET 套接字（抓包）
            │
            │ ① BPF 过滤 ← 不命中的包在这里就被扔掉，**零拷贝到用户态**
            ▼
        ② 环形缓冲区（默认约 208KB）  ← 突发流量写满即丢包
            ▼
        ③ 用户态 recvfrom() → dissect（贵）
            ▼
        ④ 存进列表（store=True）      ← 内存无限增长 → OOM
```

一次抓包命令的开销排序是 **③ > ① > ②**。所以：
**能用 BPF 挡掉的，绝不要留给用户态**；display filter 是"事后精挑"，不是性能手段。

### 2.7 时间戳：为什么分析里它比内容还重要

本日 03 的三个检测器（SYN 洪水、C2 心跳、端口扫描速率）**全都依赖时间**：

- C2 心跳靠"间隔的**抖动系数**"（标准差 / 平均值）判定，与内容无关；
- 端口扫描靠"短时间内铺开多少端口"；
- 洪水靠"每秒多少个 SYN"。

所以分析脚本里**永远不要丢时间戳**（也不要用 `time.time()` 代替包的 `ts`），
否则你只能做"有没有"的判断，做不了"是不是有规律"的判断。

---

## 三、攻击方式·手段·原理 与 检测原理

> 本日所有实验都在**本地临时目录里的合成抓包**上做：
> 不联网、不抓真网卡、不需要 sudo。合成流量里植入了 6 类异常，
> 每一类都对应一个可精确断言的检测器（这就是"结果准确且可复现"的实现方式）。

### 3.0 先说总纲：单包特征 ≠ 检测特征

```
看一个包   → "这是一个 SYN"          → 完全正常，无法判断
看 8 个 SYN→ 打到 8 个不同端口，
             且一个握手都没完成     → "这是端口扫描"
看 25 个 SYN→ 打同一个端口          → "这是 SYN 洪水"
看 4 次连接→ 间隔精确 60.000s       → "这是 C2 心跳"
```

**检测 = 聚合 + 基线 + 阈值**。三者缺一：
无聚合则看不到行为；无基线则不知道"多少算多"；无阈值则给不出结论。
后面每个检测器都会明确写出这三样。

### 3.1 半开端口扫描（SYN Scan）

**手段与原理**：只用 `socket.connect()` 扫描会完成三次握手，应用层日志会留下记录。
改成"只发 SYN、收到 SYN-ACK 后直接发 RST 断开"，则：

```
   扫描器                     目标                    IDS/防火墙
     │  SYN  ─────────────────►│                      │
     │◄── SYN-ACK（开放）───────│                      │ 记录：SYN 无后续
     │  RST  ─────────────────►│（连接从未建立）         │
     │                         │                      │
     │  SYN  ─────────────────►│                      │
     │◄── RST,ACK（关闭）───────│                      │
     │                         │                      │
     │  SYN  ─────────────────►│  （被丢弃）            │ 大量同源 SYN ⇒ 速率告警
     │     超时 ⇒ filtered      │                      │
```

**为什么隐蔽**：应用层（Web/SSH 日志）**没有任何记录**，因为连接从未建立。
**为什么仍然会被发现**：网络层留下了"**只有 SYN、没有握手**"的模式，
而且必然伴随"**同一源在短时间打到很多不同端口**"。

**检测原理（本日实现）**：

| 判据 | 取值 | 为什么 |
|---|---|---|
| 纯 SYN（SYN 且无 ACK、无载荷）打到不同目的端口的数量 | ≥ 5 | 正常访问目标端口固定 |
| 该 (源,目标) 是否**完成过任何握手** | 必须为"无" | 这条把正常访问完全排除，误报极低 |

**误报分析**：CDN 健康检查、负载均衡探测、漏洞扫描器（授权的）都可能有这种模式
→ 所以要结合资产表与授权名单做白名单（见第四章）。

### 3.2 SYN 洪水（SYN Flood）

**手段与原理**：TCP 三次握手里，服务端收到 SYN 后会分配一块
**半连接队列（SYN backlog）** 内存并回 SYN-ACK。攻击者只发 SYN 不完成握手，
服务端的半连接队列被占满 → **正常用户再也连不上**（典型的资源耗尽型 DoS）。

```
攻击者 ── 10000 个 SYN（源 IP 可能还是伪造的）──► 服务端
服务端：每个 SYN 分配一块 TCB，回 SYN-ACK，等最后一个 ACK……
       队列满了 ⇒ 新连接被丢弃 ⇒ 正常用户看到"连接超时"
```

注意：**伪造源 IP 的洪水是单向的**（SYN-ACK 回给受害者），
所以"看回包"没用，只能在**被打的那一侧**看 SYN 速率。

**检测原理**：同一 `(源, 目标, 端口)` 的纯 SYN 数量 ≥ 阈值（本日 25）。
**关键区分（重传 vs 洪水）**：

| | 正常重传 | SYN 洪水 |
|---|---|---|
| 数量 | 几个 | 几十~几万 |
| 间隔 | **指数退避**（1s→2s→4s…） | 密集、匀速 |
| 来源 | 单一真实源 | 单源或大量分散源 |

### 3.3 明文凭据嗅探（Cleartext Credentials）

**手段与原理**：HTTP 是明文协议。`Authorization: Basic <base64>` 里的
base64 **不是加密**（`echo dXNlcjpwYXNzd29yZA== | base64 -d` 一行就解出来）。
Cookie、表单密码同理。只要攻击者处于：
`同一广播域`（ARP 欺骗后做中间人）或`你上游的某个设备`，
他就能直接读到凭据——**本日的分析脚本做的就是同一件事**。

```
GET /login HTTP/1.1
Host: intranet.example.com
Authorization: Basic dXNlcjpwYXNzd29yZA==     ← 直接解出 user:password
Cookie: SESSION=8f3a1c0d9e2b                  ← 拿到它等于拿到你的登录态
```

**检测原理**：在 HTTP 头里匹配敏感字段名（authorization/cookie/x-api-key…）、
URI 查询参数（`password=`/`token=`…）、请求体（表单字段）。
**检测工具自身的纪律**：输出**只给掩码 + 指纹**，绝不回显原文——
安全工具如果自己泄露凭据，那就是最大的问题。

### 3.4 DNS 隧道（DNS Tunneling）

**手段与原理**：DNS 是极少数"**不可能被整体封掉**"的协议（封了就没法上网）。
于是攻击者把数据编码进域名：

```
外泄（出站）：aGVsbG8gd29ybGQ.tunnel.evil.example   ← 编码后的数据放在 label 里
             解析请求会一路走到攻击者控制的权威 DNS，他那边解码即可
回传（入站）：查询 TXT 记录，应答里带指令
```

**为什么难防**：它长得就是正常的 DNS 流量（UDP/53），
端口白名单、协议白名单全部放行。

**检测原理**（三个特征一起看，**只靠一个都不够**）：

| 特征 | 正常域名 | 隧道域名 |
|---|---|---|
| 最长 label 长度 | 通常 ≤ 15 | 40~180（要装数据） |
| label 的香农熵 | 英文单词约 2.5~3.5 bit/char | 编码数据 4.5~6 bit/char |
| 子域是否复用 | 有复用（缓存友好） | **每次都不同**（故意穿透缓存） |
| 查询频率 | 不稳定 | 高频且规律 |

本日实现用"label 长度 ≥ 40"筛出候选，再用**香农熵**打分（演示中隧道 label
熵 = 4.91，正常词 `intranet` = 2.50）。**熵只是辅助判据**：
CDN 的长哈希子域、base64 编码的文件名也会高熵，所以必须和"陌生父域 +
高频 + 不复用"组合判断。

### 3.5 C2 心跳（Beaconing）

**手段与原理**：被植入的恶意程序需要"随时能接到指令"，但攻击者无法主动连入内网，
所以让木马**周期性主动回连**（如每 60 秒一次），这就是 beacon。
为了隐蔽，周期往往固定、目标往往是 443/8443 之类的常见端口，
甚至伪装成正常 HTTP 请求（比如 `POST /ping`）。

**检测原理：机器比人守时。**

```
人的行为：点网页的间隔是随机的（0.3s / 5s / 200s …）
木马行为：60.000s / 60.001s / 59.999s  ← 抖动 < 0.1%

抖动系数 jitter = 间隔的标准差 / 平均值；C2 通常 < 5%
```

本日实现：同一 `(源, 目标, 端口)` 的连接 ≥ 4 次，平均间隔 ≥ 5s，
且 jitter ≤ 0.10 → 告警。demo 里 4 次连接间隔 `[60.0, 60.0, 60.0]`，jitter = 0.0。

**这个检测器与协议无关**：DNS 查询、HTTPS 连接、ICMP 都能用同一套时间序列逻辑
——这就是"**检测行为，而不是检测协议**"的体现。

### 3.6 ARP 欺骗（ARP Spoofing）

**手段与原理**：ARP 协议没有任何认证，谁都可以发"我是 192.168.1.1"。
攻击者持续广播伪造应答，让全网把网关 MAC 指向他：

```
正常：  主机 ──► 网关 MAC aa:..:01 ──► 真实网关
欺骗后：主机 ──► 攻击者 MAC aa:..:de:ad ──► 攻击者转发 ──► 真实网关
                                          （他看得见全部流量，可抓包可改包）
```

**检测原理**：同一个 IP 被**两个不同 MAC** 宣告。
本日 demo 里 `10.0.0.1` 同时被 `aa:00:00:00:00:01`（真网关）和
`aa:00:00:00:de:ad`（攻击者）宣告 → critical 级告警。

**误报**：双机热备（VRRP）、网卡更换、容器重建都会造成 MAC 变化
→ 必须结合资产表与时间窗口判断（这就是为什么检测结果是"线索"不是"结论"）。

### 3.7 报文头篡改与校验和

**手段与原理**：中间设备或攻击工具修改 IP 头字段（改地址、改 TTL、
做分片绕过 IDS）时，如果**忘记重算校验和**，接收端/分析人员就能发现。
反过来，攻击者如果重算了校验和，你就抓不到——所以这条检测**只是一条线索**。

**检测原理**：重算 IPv4 头校验和并比对。**重要的误报来源**：
网卡卸载（TSO/LRO/checksum offload）会让抓到的包校验和字段是"未填"状态，
在**本机抓出去的包**上尤其常见。tshark 会提示 "checksum not available"，
分析时必须先排除这个因素。

### 3.8 检测器的共同工程要求

| 要求 | 为什么 |
|---|---|
| 每条告警带**证据**（源/目标/端口/时间戳） | 没有证据的告警无法复核 |
| 每条告警带**为什么这么判** | 让复核者能验证判据是否成立 |
| 每条告警带**怎么修/怎么防** | 检测的价值在于能被修复 |
| 每条告警带**严重度** | 决定响应优先级（ARP 欺骗 > 校验和异常） |
| **必须有误报控制** | 本日自检里有一条断言专门保证"正常 Web 会话不被误报" |

---

## 四、防护/修复原理

> 按"从最根本到最具体"的顺序排列。**先做能根治的，再做缓解的。**

### 4.1 加密：把"明文嗅探"这一类问题整体消掉

- **全站 HTTPS + HSTS**：让 Authorization/Cookie 不再裸奔；
  HSTS 防止降级到 HTTP（否则一次 http:// 跳转就漏一次）。
- **Cookie 加 `Secure; HttpOnly; SameSite`**：即使被 XSS，也拿不到会话。
- **内网同样要加密**：不要相信"内网可信"。本日 demo 的被窃凭据就在内网主机之间。
  Zero Trust 的核心就是"不因为在内网就免除加密与认证"。
- **注意加密后的残余可见性**：TLS 仍会暴露 SNI、证书、包长/时序特征
  → 所以 C2 心跳这类**行为检测在加密流量上依然有效**（这也是为什么行为检测重要）。

### 4.2 网络分段与访问控制

- 按业务划分 VLAN/子网，**阻断横向移动**（ARP 欺骗的影响面被限制在一个广播域内）。
- 内网服务之间也要做**最小权限**：数据库不该对所有网段开放 3306。
- 出站默认拒绝（egress filtering）：木马回连最难的就是"找不到能出去的路"。

### 4.3 交换机侧（防 ARP 欺骗三件套）

| 措施 | 原理 |
|---|---|
| **DHCP Snooping** | 只信任连 DHCP 服务器的端口，防止私接 DHCP 服务器 |
| **动态 ARP 检测（DAI）** | 依据 DHCP Snooping 建立的"IP-MAC-端口"绑定表丢弃伪造 ARP |
| **端口安全 / MAC 数量限制** | 一个接入口出现大量 MAC ⇒ 后面挂了交换机/被攻陷 |

补充：关键网关/服务器做**静态 ARP 绑定**（简单有效，维护成本高）。

### 4.4 DNS 出口治理（防 DNS 隧道）

1. **强制走内部递归解析器**：防火墙只放行到内部 DNS 的 53，
   **禁止主机直连 8.8.8.8 等外部解析器**（这一步能挡掉绝大多数隧道）。
2. 在解析器上做**响应大小与 label 长度限制**，对高熵子域采样告警。
3. 用**信誉/威胁情报**拦截已知隧道域名与其父域。
4. 记录全量 DNS 日志（存查询名 + 客户端 + 应答），用于事后回溯。

### 4.5 防 SYN 洪水 / 端口扫描

| 目标 | 措施 |
|---|---|
| 抗 SYN 洪水 | `net.ipv4.tcp_syncookies=1`（半连接队列满时用 cookie 免分配）；合理设置 `tcp_max_syn_backlog`；上游做流量清洗 |
| 减少暴露面 | 只开必要端口；管理口不对外；用防火墙限制源 |
| 反扫描 | 边界启用扫描检测与速率限制；fail2ban/IPS 封禁；对扫描源做 Tarpit |
| 检测侧 | 监控"SYN 与 SYN-ACK 数量比"，比值异常即告警 |

### 4.6 检测工程本身（容易被忽略的"防护"）

- **误报控制优先于检出率**：一个误报率高的规则会被运维直接关掉，等于没有。
  本日自检里专门断言"正常 Web 会话不被误报"。
- **阈值要有基线**：固定阈值只在固定环境有效；生产要按"每周同时段"做基线。
- **保留原始数据**：pcap 保留期与容量要提前规划（见 4.7）。
- **规则可解释**：每条规则都要有 why/remediation，否则无法维护。

### 4.7 合规：抓包文件本身是敏感数据

pcap 里可能有 Cookie、Token、明文密码、内网拓扑、个人信息。
**抓包 = 收集他人通信内容**，务必：

1. 只抓已有授权的范围（自己的资产、自己的流量）；
2. 存储加密 + 访问控制 + 最小化留存（按天/周清理）；
3. 对外分享前**先脱敏**（本日的 `mask_secret` / `fingerprint` 就是干这个的）；
4. 保留操作审计（谁在什么时候抓了什么）。

---

## 五、代码案例逐节说明

本日代码共 4 个文件（**每个都支持 `--self-test`，且自检完全不依赖 pyshark/tshark**）：

```
code/
├── pcap_lib.py              核心引擎：pcap/pcapng 读写 + 解析 + 过滤器 + 合成流量（被下面三个 import）
├── 01-basic-usage.py        读文件、列包、两条后端统一
├── 02-advanced-filtering.py 过滤（BPF vs display filter）、HTTP 提取、Summary 坑
└── 03-traffic-analysis.py   统计 + 连接跟踪 + 7 类异常检测 + 报告 + CI 门禁
```

### 5.1 `pcap_lib.py` —— 核心引擎（逐节）

| 节 | 内容 | 关键点（为什么这么写） |
|---|---|---|
| 0 | 常量表 | EtherType / IP proto / TCP 标志位 / 端口提示。**这些数字必须背**，排错全靠它 |
| 1 | 校验和 | `ones_complement_sum` 用 `int.from_bytes` 一次求和再折叠进位（比逐 2 字节循环快得多）；**奇数长度必须补 0** |
| 2 | pcap/pcapng 读写 | `sniff_format()` 先认格式；`iter_pcap` **流式**（内存 O(1)）；容错"最后一条记录残缺"；pcapng 未知块可跳过 |
| 3 | 解析器 | 每层只剥自己的头；VLAN 循环剥离；分片包不当传输层解；TCP 选项按 kind 走（NOP 只有 1 字节） |
| 4 | 顶层解析 | `dissect_packet()` 把字节变成"对齐 Wireshark 字段名"的字典；**任何一层失败只少一个键，不抛异常** |
| 5 | 过滤器引擎 | 手写 tokenizer + 递归下降解析（or→and→not→比较）；**编译期校验字段名**（fail fast） |
| 5.1 | BPF 翻译器 | 把常见 BPF 子集映射到 display filter，并给出"BPF 在比哪些字节"的对照 |
| 6 | 报文构造器 | 相当于"标准库版 Scapy"，用于造合成流量；`build_tcp` **强制校验选项 4 字节对齐** |
| 6.1 | 合成流量 | `build_demo_packets()` 70 个包，植入 6 类异常 + 1 个坏校验和包，`DEMO_FACTS` 记录"标准答案" |
| 7-8 | 自检 + CLI | `check_eq` 打印"实际 vs 期望"；CLI 支持 `--self-test/--dump/--filter/--write-demo` |

**几个值得单独讲的实现细节**：

```python
# ① 校验和：奇数长度必须补零，否则所有奇数载荷都算错
if len(data) & 1:
    data = data + b"\x00"

# ② 分片：frag_offset 字段单位是 8 字节，忘乘 8 是最经典的分片解析错误
"frag_offset": (flags_frag & 0x1FFF) * 8

# ③ IPv4 载荷长度以 total_len 为准，不能用 len(以太网载荷)
#    因为以太网最小帧 46 字节载荷，小包会被填充（padding）
end = total_len if ihl <= total_len <= len(data) else len(data)

# ④ TCP/UDP 校验和要带伪首部；ICMP 不带
verify_l4_checksum(segment, src, dst, IPPROTO_TCP)   # 伪首部 + 段
ones_complement_sum(data) == 0xFFFF                  # ICMP 直接整条验
```

### 5.2 `01-basic-usage.py` —— 读取与列出数据包

```
probe_pyshark()      延迟探测 pyshark 与 tshark，**不在模块顶层 import**
normalize_pyshark()  把 pyshark 对象转成统一 dict（字段名对齐 ip.src / tcp.dstport）
iter_pyshark()       生成器 + finally close()（不写 close 会残留 tshark 子进程）
iter_stdlib()        走 pcap_lib
load_packets()       统一入口：backend=auto/pyshark/stdlib，返回 (包列表, 实际后端, 说明)
```

**两个必须记住的写法**：

1. **`import pyshark` 绝不能写在模块顶层**：没装 tshark 的机器上，
   如果顶层 import 失败，连 `--self-test` 都跑不起来（脚本直接崩）。
   正确姿势是"延迟导入 + 捕获异常 + 给人话提示"。
2. **字段名是 `pkt.ip.src`，不是 `pkt.ip.src_ip`**（tshark 字段 `ip.src`）；
   协议号是 `pkt.ip.proto`，不是 `ip.protocol`。写成 `src_ip` 必 AttributeError
   —— 这是抄教程时最常见的坑。

### 5.3 `02-advanced-filtering.py` —— 过滤的两种语义

```
DEMO_FILTERS        11 条教学过滤条件（从粗到细）
print_bpf_mapping() 打印 BPF 在**内核**里比的字节（tcp[2:2]==80 …）
print_bpf_translation() 把 BPF 翻译成 display filter，并**逐包比对结果集相同**
print_http_requests()   提取 HTTP 请求 + 敏感信息检测（掩码输出）
demo_only_summaries_trap() 复现"Summary 只有 7 个字段"的坑
```

**原版代码的 bug 与修复**（这是本案例的教学重点之一）：

```python
# ❌ 原版写法：only_summaries=True 拿不到 http 层，却在读 packet.http.method
cap = pyshark.FileCapture(f, display_filter='http', only_summaries=True)
for pkt in cap:
    print(pkt.http.method)        # AttributeError！

# ✅ 修复：要么不用摘要模式（字段齐全、慢），要么只读摘要列
cap = pyshark.FileCapture(f, display_filter='http')          # 全字段
cap = pyshark.FileCapture(f, only_summaries=True)            # 只读 pkt.info
```

### 5.4 `03-traffic-analysis.py` —— 从包到结论

```
protocol_stats / top_talkers / port_stats / tcp_flag_stats   统计层
connection_table(pkts)                                       连接跟踪（TCP 状态机）
detect_port_scan / detect_syn_flood / detect_cleartext_credentials
detect_dns_tunneling / detect_beaconing / detect_arp_conflict
detect_bad_checksums                                         七个检测器
shannon_entropy(text)                                        熵（DNS 隧道辅助判据）
analyze(pkts) → report                                      报告数据
render_report(rep) / gate_exit_code(rep, fail_on)            人类可读 + CI 门禁
```

**连接跟踪的状态机设计要点**：

```python
# 为什么要单独记 established 而不只看 state？
# 因为正常连接关闭后 state 会变成 CLOSING，如果只比对 "state == ESTABLISHED"，
# 就会把一条正常关闭的连接误判成"没建立成功"。这是状态机里典型的"终态 vs 历史"问题。
"established": False    # 曾经进入过 ESTABLISHED
"state": "CLOSING"      # 当前状态
```

**告警的通用结构**（每条都必须是自解释的）：

```python
finding(kind, severity, summary,
        evidence={...},      # 证据：源/目标/端口/时间戳/计数
        why="...",           # 凭什么这么判（复核者要能验证）
        remediation="...")   # 怎么修/怎么防
```

---

## 六、运行命令 + 预期输出

### 6.1 环境与依赖

```bash
# 本日**只需 Python 3.10+ 标准库**就能完成全部自检与演示（不需要联网/不需要 sudo）
python3 -V          # 本环境：Python 3.12.3

# 可选的"全协议"路径（本环境未安装；装不装都不影响自检）
pip install pyshark         # 还要有 tshark 二进制：
sudo apt install tshark      # Debian/Ubuntu
brew install wireshark       # macOS
```

### 6.2 全部自检（**必须逐个跑，输出 SELF-TEST OK 才算通过**）

```bash
cd /root/code/Learn-Python
python3 -B days/day-157-pyshark-traffic-analysis/code/pcap_lib.py --self-test
python3 -B days/day-157-pyshark-traffic-analysis/code/01-basic-usage.py --self-test
python3 -B days/day-157-pyshark-traffic-analysis/code/02-advanced-filtering.py --self-test
python3 -B days/day-157-pyshark-traffic-analysis/code/03-traffic-analysis.py --self-test
```

**真实输出（本环境实测，`pcap_lib.py`）**：

```text
==========================================================================
pcap_lib 离线自检：校验和 / 格式读写 / 解析 / 过滤器 / 合成流量
==========================================================================
✅ 校验和：RFC 1071 例子 + scapy 交叉验证 + 奇数长度 + 篡改检测 全部一致
✅ 解析：ether/ip/tcp 字段、标志顺序、选项、校验和 —— #1  1.000000  10.0.0.2 → 10.0.0.1  TCP 12345→80 [SYN,ACK] seq=1000 ack=0 win=64240 len=0
✅ VLAN：0x8100 标签被正确剥离（vid=100），内层 IP 未错位
✅ 分片：frag_offset=24（3×8）、MF=1，且非首片不误判为 TCP
✅ UDP/DNS：端口、A 记录、压缩指针、校验和 —— 全部正确
✅ ICMP：校验和自洽（无伪首部，与 TCP/UDP 的算法不同）
✅ HTTP：请求/响应解析正常；敏感值全部掩码（例：Be***********************************ig(len=39)）
✅ 健壮性：截断/畸形包返回 None 或被跳过，解析器不崩溃
✅ pcap 往返：70 包字节级一致（含时间戳）
✅ 大端 pcap：魔数 0xd4c3b2a1 被正确识别，字节序切换到 >
✅ pcapng：SHB/IDB/EPB 块解析 + 时间戳拼接正确（自动识别格式）
✅ 过滤器：tcp=60  syn&dport80=28  ip.addr==10.0.0.66=8
✅ 过滤器错误处理：缺值/括号/未知字段/多余 token 全部报 FilterError
✅ BPF 翻译：常见写法可等价映射到 display filter（含 SYN/port/host/not）
✅ 合成流量：70 包 / HTTP 6 / DNS 5 / ARP 3 / ICMP 2 / 坏校验和 1
SELF-TEST OK
```

**`01-basic-usage.py --self-test`**：

```text
==========================================================================
案例 01 离线自检：合成 pcap → 走两条路径解析 → 核对已知答案
==========================================================================
✅ 标准库路径：70 个包，首包 = #1  1700000000.000000  10.0.0.10 → 10.0.0.53  UDP 53124→53 len=46  DNS Query intranet.example.com
✅ HTTP 提取：GET /login Host=intranet.example.com，敏感项 2 条（掩码示例 Ba**********************==(len=26)）
✅ display_filter 生效：'tcp.flags.syn == 1 and tcp.dstport == 80' → 28 个包
✅ --limit 生效：只解析前 7 个包
ℹ️  pyshark 不可用（ModuleNotFoundError: No module named 'pyshark'）
    → 本自检**故意不依赖它**：上面的断言全部走标准库路径。
    → 想跑联机路径：pip install pyshark 并安装 tshark，再执行 --compare
✅ 降级策略：auto 静默降级、显式 pyshark 明确报错 —— 两条语义都对
SELF-TEST OK
```

**`02-advanced-filtering.py --self-test`**：

```text
====================================================================================
案例 02 离线自检：过滤引擎 / BPF 等价性 / HTTP 提取 / Summary 坑
====================================================================================
✅ 11 条教学过滤条件命中数全部符合预期（tcp=60 udp=5 http=6 …）
✅ 关键对比：纯 SYN 39 个 vs 完成握手 5 条 → 差出来的 34 个就是「只发起不完成」的可疑行为
✅ BPF 等价性：6 条条件翻译后结果集完全一致（逐包比对）
✅ HTTP 提取：5 个请求（GET /login + 4 心跳 POST）；敏感项 [('header:authorization', 'Ba***…==(len=26)'), ('header:cookie', 'SE***…rk(len=32)')]
✅ Summary 坑已复现：only_summaries=True 时只有 7 个字段，访问 .http/.ip 必 AttributeError
✅ 过滤器错误处理：错误语法一律给出人话提示（含错在哪）
SELF-TEST OK
```

**`03-traffic-analysis.py --self-test`**：

```text
====================================================================================
案例 03 离线自检：统计 / 连接跟踪 / 7 个检测器 vs 已知植入的异常
====================================================================================
✅ 统计：tcp=60 udp=5 arp=3 icmp=2；SYN=44（含 5 个 SYN,ACK）；最活跃会话 = 10.0.0.99 → 10.0.0.20
✅ 连接跟踪：正常 Web 会话曾进入 ESTABLISHED 并正常关闭（终态 CLOSING）；扫描的 8 条全部停在 SYN_SENT（未完成）
✅ DNS 隧道：3 次查询，label 最长 43 字符，熵 4.91 vs 正常域名 2.50
✅ 七个检测器全部命中预设异常：{'arp_spoof': 1, 'bad_checksum': 1, 'c2_beacon': 1, 'cleartext_credential': 1, 'dns_tunneling': 1, 'port_scan': 1, 'syn_flood': 1}
✅ 误报控制：正常 Web 会话（含 1 次 SYN、正常 DNS 查询）未被任何扫描/洪水/心跳/隧道检测器误报
✅ 熵函数：空串=0、'aaaa'=0、'ab'=1.0 bit（边界正确）
✅ 门禁：fail-on none/critical/high 的退出码判定正确
SELF-TEST OK
```

### 6.3 合成抓包演示（不碰网卡、不落仓库工作树）

```bash
# 生成一份"带标准答案"的抓包到临时目录
python3 -B days/day-157-pyshark-traffic-analysis/code/pcap_lib.py \
        --write-demo /tmp/day157demo.pcap
```

```text
已生成合成抓包：/tmp/day157demo.pcap（70 个包，5942 字节）
```

```bash
# 逐包解析 + 显示过滤器（就像 tshark -r ... -Y ...）
python3 -B days/day-157-pyshark-traffic-analysis/code/pcap_lib.py \
        --dump /tmp/day157demo.pcap --filter 'tcp.flags.syn==1 and tcp.dstport==80' --limit 3
```

```text
#3    1700000000.013000  10.0.0.10 → 10.0.0.20  TCP 49152→80 [SYN] seq=1000 ack=0 win=64240 len=0
#22   1700000003.200000  10.0.0.66 → 10.0.0.20  TCP 40000→80 [SYN] seq=7004 ack=0 win=64240 len=0
#26   1700000004.000000  10.0.0.99 → 10.0.0.20  TCP 50000→80 [SYN] seq=100 ack=0 win=64240 len=0

匹配 28 个包（已打印前 3 个）
```

**`01-basic-usage.py --demo --limit 6`**（列出数据包）：

```text
（本轮使用合成抓包：/tmp/day157-01-73e8q22n/demo.pcap，共 70 个包；分析完会删除）
（`day157-01-` 后面那串随机字符每次都不同 —— 这是 mkdtemp 的行为，属于正常现象）

⚠️ pyshark 不可用（ModuleNotFoundError: No module named 'pyshark'），已自动降级到标准库解析
文件: /tmp/day157-01-73e8q22n/demo.pcap
后端: stdlib   过滤器: (无)
==========================================================================
#1    1700000000.000000  10.0.0.10 → 10.0.0.53  UDP 53124→53 len=46  DNS Query intranet.example.com
#2    1700000000.012000  10.0.0.53 → 10.0.0.10  UDP 53→53124 len=62  DNS Response intranet.example.com → 10.0.0.20
#3    1700000000.013000  10.0.0.10 → 10.0.0.20  TCP 49152→80 [SYN] seq=1000 ack=0 win=64240 len=0
#4    1700000000.014000  10.0.0.20 → 10.0.0.10  TCP 80→49152 [SYN,ACK] seq=5000 ack=1001 win=64240 len=0
#5    1700000000.014000  10.0.0.10 → 10.0.0.20  TCP 49152→80 [ACK] seq=1001 ack=5001 win=64240 len=0
#6    1700000000.015000  10.0.0.10 → 10.0.0.20  TCP 49152→80 [PSH,ACK] seq=1001 ack=5001 win=64240 len=218  HTTP GET /login Host=intranet.example.com
==========================================================================
共 6 个数据包
```

**`02-advanced-filtering.py --demo`**（过滤对照表）：

```text
过滤表达式                                            命中   说明
------------------------------------------------------------------------------------
tcp                                              60   所有 TCP 包
udp                                               5   所有 UDP 包
http                                              6   所有 HTTP 包（含请求与响应）
tcp.flags.syn == 1 and tcp.flags.ack == 0        39   纯 SYN（扫描/连接请求）
tcp.flags.rst == 1                                0   RST（连接被拒绝或主动重置）
ip.addr == 10.0.0.66                              8   只看某台主机（扫描器）
tcp.port == 4444                                 16   只看某个端口（可疑回连端口）
dns.qry.name contains "evil"                      3   域名包含 evil 的 DNS 包
http.request.method == "POST"                     4   HTTP POST 请求
tcp.dstport == 80 and tcp.len > 0                 1   发往 80 端口且带载荷（真正的请求）
ip.src == 10.0.0.99                              25   SYN 洪水的来源

BPF 在**内核**里到底比什么字节（这些偏移量是硬编码的，改不了）：
  tcp port 80                  → ip proto 6 and (tcp[2:2] == 80 or tcp[4:2] == 80)
  port 80                      → (tcp[2:2] == 80 or tcp[4:2] == 80) or (udp[2:2] == 80 or udp[4:2] == 80)
  icmp                         → ip proto 1
  host 10.0.0.1                → ip[12:4] == 10.0.0.1 or ip[16:4] == 10.0.0.1
  tcp[tcpflags] & tcp-syn != 0 → tcp[13] & 2 != 0   # TCP 头第 13 字节的 bit1 就是 SYN

BPF → display filter 等价翻译，并对同一份抓包**实测两种写法结果相同**：
  tcp port 80                        → tcp.port == 80                               命中 37
  udp port 53                        → udp.port == 53                               命中 5
  icmp                               → icmp                                         命中 2
  host 10.0.0.66                     → ip.addr == 10.0.0.66                         命中 8
  tcp[tcpflags] & tcp-syn != 0       → tcp.flags.syn == 1                           命中 44
  not port 22                        → (not ((tcp.port == 22 or udp.port == 22)))   命中 69
```

**`03-traffic-analysis.py --demo`**（完整分析报告，节选）：

```text
====================================================================================
流量分析报告 —— 共 70 个包
====================================================================================

【协议分布】(层计数，一个包可能同时含 ip 与 tcp)
  ether    70
  ip       67
  tcp      60
  http     6
  udp      5
  dns      5
  arp      3
  icmp     2

【最活跃的会话】(按字节数降序)
  源               目标                  包数      字节
  10.0.0.99       10.0.0.20           25    1350
  10.0.0.77       10.0.0.40           12    1052
  10.0.0.10       10.0.0.20            8     653

【TCP 标志分布】
  SYN    44
  ACK    21
  PSH    6
  FIN    2
  ── 行为指标：纯 SYN 39 个 vs SYN+ACK 5 个（正常应大致相等；差值 = 只发起不完成的可疑连接）

【连接跟踪】(共 43 条，显示前 12 条)
  源                   端口 → 目标                  端口  状态            SYN/SA  完成
  10.0.0.10        49152 → 10.0.0.20           80  CLOSING          2/0  ✅
  10.0.0.77        44000 → 10.0.0.40         4444  ESTABLISHED      1/0  ✅
  10.0.0.66        40000 → 10.0.0.20           21  SYN_SENT         1/0  ❌

【检测结果】(共 7 条)

  1. 🔴 [CRITICAL] arp_spoof — IP 10.0.0.1 同时被 2 个 MAC 宣告
     证据: {"ip": "10.0.0.1", "macs": ["aa:00:00:00:00:01", "aa:00:00:00:de:ad"]}
     为什么这么判: ARP 无认证，任何主机都能应答「我是某 IP」；同一 IP 对应多个 MAC 是 ARP 欺骗（中间人）最直接的信号。
     怎么修/怎么防: 交换机开启动态 ARP 检测（DAI）+ DHCP Snooping；关键网关/IP 做静态 ARP 绑定；…

  2. 🟠 [HIGH] syn_flood — 10.0.0.99 → 10.0.0.20:80 发出 25 个纯 SYN
  3. 🟠 [HIGH] cleartext_credential — 10.0.0.10 → 10.0.0.20 的明文 HTTP 请求携带凭据
     证据: {… "items": [{"where": "header:authorization", "masked": "Ba***…==(len=26)", "fp": "9c06d532edf0"},
                        {"where": "header:cookie", "masked": "SE***…rk(len=32)", "fp": "b46364b716c8"}]}
  4. 🟠 [HIGH] dns_tunneling — 10.0.0.88 向陌生父域 tunnel.evil.example 发起 3 次超长/高熵 DNS 查询
     证据: {"src": "10.0.0.88", "parent_domain": "tunnel.evil.example", "query_count": 3,
            "max_label_len": 43, "avg_entropy_bits_per_char": 4.91, "sample_label": "a1***…1v(len=43)"}
  5. 🟠 [HIGH] c2_beacon — 10.0.0.77 → 10.0.0.40:4444 出现 4 次周期为 60.0s 的规律回连
     证据: {"mean_interval_s": 60.0, "jitter_ratio": 0.0, "intervals_s": [60.0, 60.0, 60.0]}
  6. 🟡 [MEDIUM] port_scan — 10.0.0.66 → 10.0.0.20 在 8 个端口上发纯 SYN 且未完成任何握手
     证据: {"distinct_ports": 8, "ports": [21, 22, 23, 25, 80, 443, 3306, 8080]}
  7. 🔵 [LOW] bad_checksum — 检测到 1 个 IPv4 头校验和错误的包

提醒：检测结果是**复核线索**，不是结论。
      ARP 冲突可能是双机热备；心跳可能是监控探针；高熵域名可能是 CDN。
```

### 6.4 处理你自己抓的包（离线解析，不碰网卡）

```bash
# 用 tcpdump 抓一小段自己的流量（需要权限；-s 0 抓完整包，-c 限制数量）
# ⚠️ 只抓自己的资产/自己的流量，并先确认合规
sudo tcpdump -i lo -c 200 -w /tmp/my.pcap

# 用本日工具分析
python3 -B days/day-157-pyshark-traffic-analysis/code/01-basic-usage.py --pcap /tmp/my.pcap --limit 20
python3 -B days/day-157-pyshark-traffic-analysis/code/02-advanced-filtering.py --pcap /tmp/my.pcap \
        --expr 'tcp.flags.syn == 1 and tcp.flags.ack == 0'
python3 -B days/day-157-pyshark-traffic-analysis/code/03-traffic-analysis.py --pcap /tmp/my.pcap --json

# CI 门禁：命中 high/critical 时退出码 3
python3 -B days/day-157-pyshark-traffic-analysis/code/03-traffic-analysis.py --pcap /tmp/my.pcap --fail-on high
echo $?    # 0 = 通过，3 = 命中门禁阈值
```

### 6.5 pyshark 联机路径（装了 tshark 之后）

```bash
pip install pyshark && sudo apt install tshark

# 两条后端对比同一文件
python3 -B days/day-157-pyshark-traffic-analysis/code/01-basic-usage.py --demo --compare

# 强制走 pyshark（没装时**明确报错**，不会静默降级）
python3 -B days/day-157-pyshark-traffic-analysis/code/01-basic-usage.py --pcap /tmp/my.pcap --backend pyshark
```

**pyshark API 速查**（原内容保留并修正字段名）：

| 对象 | 关键属性 | 说明 |
|---|---|---|
| `FileCapture` | `display_filter=` / `only_summaries=` / `bpf_filter=` | 迭代器；用完必须 `close()` |
| `Packet` | `number` / `length` / `sniff_time` | 包级元数据 |
| `pkt.ip` | `src` / `dst` / `ttl` / `proto` | **注意是 `src` 不是 `src_ip`** |
| `pkt.tcp` | `srcport` / `dstport` / `seq` / `ack` / `flags` / `flags_str` / `window_size_value` | `flags` 是 `0x00xx`，可读形式看 `flags_str` |
| `pkt.udp` | `srcport` / `dstport` / `length` | — |
| `pkt.http` | `request.method` / `request.uri` / `host` / `user_agent` / `response.code` | 请求与响应字段名不同 |
| `pkt.dns` | `qry_name` / `flags_response` / `a` | — |
| Summary 对象 | `number/time/source/destination/protocol/length/info` | **只有这 7 个**（`only_summaries=True`） |

```python
import pyshark

# 推荐写法：显式 allow 列表 + 明确的 display_filter
cap = pyshark.FileCapture('/tmp/my.pcap',
                          display_filter='tcp.flags.syn == 1',
                          keep_packets=False)     # 不把包留在内存（长时间分析必备）
try:
    for pkt in cap:
        if hasattr(pkt, 'ip'):
            print(pkt.number, pkt.ip.src, '→', pkt.ip.dst)
finally:
    cap.close()                                   # ← 不写这句会残留 tshark 子进程
```

### 6.6 pyshark 的工作流（原图解保留）

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  PCAP文件    │────▶│   tshark命令行    │────▶│   XML/JSON输出       │
│ (捕获的流量) │     │ (协议解析引擎)    │     │ (结构化数据)         │
└─────────────┘     └──────────────────┘     └─────────────────────┘
                                                            │
                                                            ▼
                                              ┌─────────────────────────┐
                                              │  pyshark 解析成 Python 对象│
                                              └─────────────────────────┘
                                                            │
                                                            ▼
                                              ┌─────────────────────────┐
                                              │  统计 / 检测 / 报告      │
                                              └─────────────────────────┘

本日的第二条路径（不经过 tshark）：
   PCAP ──► pcap_lib（纯标准库）──► 同样的字典结构 ──► 同一套统计/检测代码
```

```mermaid
flowchart TD
    classDef pcap fill:#f9f,stroke:#333,stroke-width:2px;
    classDef tshark fill:#bbf,stroke:#333,stroke-width:2px;
    classDef lib fill:#bfb,stroke:#333,stroke-width:2px;
    classDef user fill:#ffb,stroke:#333,stroke-width:2px;

    PCAP[PCAP / PCAPNG 文件]:::pcap
    TSHARK[tshark（C 解析引擎）]:::tshark
    PYSHARK[pyshark 包装]:::tshark
    LIB[pcap_lib（纯标准库）]:::lib
    IR[统一数据结构<br/>ip.src / tcp.dstport / http.request.uri]:::lib
    USER[统计 / 过滤 / 检测 / 报告]:::user

    PCAP -->|"tshark -r（子进程）"| TSHARK
    TSHARK -->|"XML/JSON"| PYSHARK
    PCAP -->|"直接读字节"| LIB
    PYSHARK --> IR
    LIB --> IR
    IR --> USER
```

---

## 七、常见陷阱速查表

> 左列是现象，右列是根因与解法。这张表基本覆盖了本日代码里踩过的每一个坑。

| 现象 | 根因 | 解法 |
|---|---|---|
| `import pyshark` 直接 ModuleNotFoundError | 没装 pyshark，或装了但没有 tshark 二进制 | 延迟导入 + 降级到标准库路径（`probe_pyshark()`） |
| `AttributeError: src_ip` | pyshark 的字段名是 `ip.src` | 用 `pkt.ip.src` / `pkt.ip.dst` / `pkt.ip.proto` |
| `only_summaries=True` 后读 `.http`/`.tcp` 报错 | Summary 对象只有 7 个字段 | 去掉摘要模式，或只读 `pkt.info` |
| 脚本跑完进程里堆了一堆 tshark | `FileCapture` 没 `close()` | `try/finally` 里 `cap.close()` |
| 时间戳差 1000 倍 | 文件是纳秒魔数（0xa1b23c4d），按微秒读了 | 由魔数决定除数（1e6 / 1e9） |
| 时间戳"差不多但总对不齐"（差 15.625ms） | pcapng 的 `if_tsresol` 被当成 2ⁿ 解释 | 按规范：最高位 0 → 10ⁿ，1 → 2ⁿ |
| `f.read()` 一次吃掉半个文件 | 字节序判错 → `incl_len` 变成天文数字 | 先判魔数；对超长单包直接报错 |
| 大端 pcap 读出来全是乱码 | 只实现了小端分支 | 魔数 `0xd4c3b2a1` 时切 `>` 前缀 |
| 最后一个包解析报错 | 抓包进程被 kill，尾部记录残缺 | 长度不足时**丢弃残包正常结束**，不要抛异常 |
| VLAN 环境字段全错位 | EtherType 0x8100 后面还有 4 字节标签 | 循环剥 VLAN（QinQ 有两层） |
| `tcp.len` 明明没数据却是 2 | TCP 选项长度不是 4 的倍数 → data offset 偏小 | 选项末尾补 NOP 凑齐 4 字节（本库会直接报错） |
| 小包（DNS/ARP）后面多出垃圾字节 | 拿 `len(以太网载荷)` 当 IP 总长，没考虑最小帧填充 | 以 IP 头 `total_len` 为准 |
| 分片包解析成垃圾 TCP | 非首片没有传输层头 | `frag_offset != 0` 时不按 TCP 解析 |
| "TCP checksum incorrect" | 改了载荷没重算校验和 | 用对象赋值改载荷后重新序列化；校验和含**伪首部** |
| "UDP checksum incorrect" 但其实是正常的 | UDP 校验和为 0 表示"未提供校验和" | 值为 0 时判定为"未提供"，不算错 |
| 分析自己的抓包发现大量校验和错误 | 网卡 checksum offload（TSO/LRO） | 先在抓包点排除 offload，再谈篡改 |
| display filter 写对了却过滤不掉噪声/丢包 | 拿 display filter 当性能手段用了 | 该用 BPF（内核态）；display filter 是事后精挑 |
| 复杂 BPF 手写不出来 | BPF 只能表达"字节偏移"，没有协议字段概念 | 用 tcpdump 语法文档，或先用 tshark 的 display filter 验证思路 |
| 长时间抓包内存暴涨 | 把包全存列表里 | 流式迭代 + `keep_packets=False` + 只保留需要的字段 |
| 100k 包分析慢到不可用 | 纯 Python 逐包全量 dissect | BPF 预过滤 + 只取必要字段 + 考虑 tshark/dpkt/Zeek |
| 检测器误报一堆 | 只有阈值没有基线，或没排除正常行为 | 加基线、加白名单、先跑一段正常流量看误报 |

---

## 八、局限（必须知道）

**本日代码是教学实现，不是生产 IDS。** 以下局限写清楚，避免误用：

1. **不做流重组**：TCP 分段/乱序/重传不会拼成完整应用层消息。
   所以"跨段的 HTTP 请求""被分片逃避的载荷"会漏检。
   生产用 Suricata/Zeek（它们有完整流重组与协议状态机）。
2. **不做解密**：TLS/SSH 之后的内容看不到（只能看 SNI、证书、包长时序）。
3. **协议覆盖有限**：只解 Ethernet/VLAN/ARP/IPv4/IPv6/TCP/UDP/ICMP/DNS/HTTP。
   加密协议、工业协议、私有协议都不认（pyshark/tshark 能认 3000+，这是它的价值）。
4. **没有 IPv6 扩展头全支持**：只跳过 Hop-by-Hop/Routing/Fragment 的基础情形。
5. **BPF 只做子集翻译**：不支持 `portrange`、`ether proto`、`vlan`、`less/greater` 等；
   真正的 BPF 必须交给 libpcap 编译（内核字节码不是用 Python 写的）。
6. **阈值写死**：`min_ports=5`、`min_syns=20`、`min_label_len=40` 等只适用于
   本演示的小数据集；生产要按业务基线调，并考虑时间窗口内速率（pps）。
7. **连接跟踪是简化状态机**：不处理同时打开、半关闭、超时重传、
   RST 的合法性等边角情况。
8. **没有 pyshark 联机验证**：本环境没装 pyshark/tshark，
   因此 `iter_pyshark()` 这条路径**没有被实际执行过**（只做了代码层面的梳理与
   防御性写法）。装了 tshark 之后请用 `--compare` 自行验证两条路径结果一致。
9. **合成流量的时间戳是固定的（1_700_000_000 起）**：
   这是为了自检可复现，不代表真实时间分布。

---

## 九、思考题

> 前 5 题保留自原版（表述已理顺），后 4 题为本次补强新增，都是能"写代码验证"的题。

1. **协议识别**：一个 PCAP 里混有 IPv4/IPv6/TCP/UDP/ICMP，
   怎么只提取 TCP？`display_filter` 和 `bpf_filter` 的本质区别是什么？
   （提示：想一想到底是谁在过滤，以及"没命中的包去哪了"）
2. **性能权衡**：要分析 100,000 个包的 pcap，你会怎么优化内存与时间？
   什么时候该从 pyshark 换到 scapy/dpkt/tshark？
   （提示：`keep_packets=False`、流式、只取必要字段、BPF 预过滤）
3. **隐私与合规**：企业里分析抓包文件有哪些合规考量？
   如何保证分析过程不泄露敏感信息？
   （提示：参考本日 `mask_secret`/`fingerprint` 的设计，以及第四章 4.7）
4. **解析的局限**：你遇到过 pyshark 解不了的协议/字段吗？
   解析失败时怎么回退到原始字节或 scapy？
   （提示：本库的"返回 None 不抛异常"+ `hexdump` 就是最小的回退机制）
5. **扩展性设计**：设计一个以 pyshark 为核心的流量分析平台，
   如何做插件架构（自定义解析、可视化、报告）？
   （提示：本日"统一 IR + 后端可替换"就是插件化的第一层）
6. **校验和**：为什么 TCP/UDP 校验和要带伪首部，而 ICMP 不带？
   如果 NAT 改了源 IP 却不改 TCP 校验和，会发生什么？
   （可以自己改 `pcap_lib.build_ipv4` 造一个，再用 `dissect_packet` 验）
7. **纸面推演 → 代码验证**：本日 `detect_beaconing` 用"抖动系数 ≤ 0.10"判定心跳。
   如果攻击者把周期改成"60 秒 ± 5 秒随机"，这个检测器还能抓到吗？
   你会怎么改进？（提示：思考"规律性"的其它度量：自相关、直方图、
   与"人类活动曲线"的对比）
8. **pcapng**：为什么 pcapng 的每块长度字段要写**两次**？
   这个设计换来了什么能力？（提示：想想从文件尾部往前遍历、
   以及文件被截断时如何校验完整性）
9. **检测工程**：本日自检里专门有一条断言"正常 Web 会话不被误报"。
   如果让你给 `detect_port_scan` 增加一条基线规则来进一步降误报，
   你会用哪个统计量？（提示：全局"每个源的平均目的端口数"）

---

## 附：本日文件清单

```
days/day-157-pyshark-traffic-analysis/
├── README.md                    ← 本文
├── code/
│   ├── pcap_lib.py              ← 核心引擎：pcap/pcapng 读写 + 解析 + 过滤器 + 合成流量
│   ├── 01-basic-usage.py        ← 读取与列出数据包（pyshark 主路径 + 标准库兜底）
│   ├── 02-advanced-filtering.py ← BPF vs display filter + HTTP 提取 + Summary 坑
│   └── 03-traffic-analysis.py   ← 统计 + 连接跟踪 + 7 类异常检测 + 报告 + CI 门禁
├── diagrams/
│   └── README.md                ← 机制图（ASCII + Mermaid）
└── exercises/
    └── checklist.md             ← 完成清单 + 练习
```

**与旧版内容的对应关系**（旧版是 47/48/96 行的清单式脚本，本次改造后）：

| 旧版 | 现在 | 变化 |
|---|---|---|
| 案例 1（47 行，硬编码 `example_traffic.pcap`） | `01-basic-usage.py` | 加 CLI、加标准库兜底、加 HTTP/统计、加自检；删掉硬编码文件名 |
| 案例 2（48 行，`only_summaries=True` + 读 `http` 字段） | `02-advanced-filtering.py` | **修掉 AttributeError 级 bug**；加 BPF/display 对照与等价性验证 |
| 案例 3（96 行，含 `x[1] if False else count` 死代码） | `03-traffic-analysis.py` | 清掉死代码；加连接跟踪与 7 个检测器；加误报控制与 CI 门禁 |
| — | `pcap_lib.py`（新增） | 纯标准库引擎：让全部自检不依赖 pyshark/tshark |
