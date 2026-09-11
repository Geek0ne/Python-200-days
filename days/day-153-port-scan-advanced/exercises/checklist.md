# Day 153 — 端口扫描进阶 · 练习与完成清单

> 主题：Nmap 基础与扫描类型 / python-nmap / banner 抓取与服务识别
> 实战：多线程自动化端口扫描器（结果导出）
> 预计用时：100~160 分钟（不含思考题）
>
> ⚠️ 所有练习**只允许在本机 `127.0.0.1` 或你已获得书面授权的目标上完成**。
> 拿不准的时候，答案永远是"不扫描"。

---

## ✅ 今日完成清单

### 概念理解（能用自己的话讲清楚）

- [ ] 说清"IP 标识主机、端口标识服务"的分层，以及内核靠**四元组**做多路复用
- [ ] 说出端口的三段划分（0-1023 / 1024-49151 / 49152-65535）及各自权限要求
- [ ] 说出 4 种常用扫描类型（`-sT` / `-sS` / `-sU` / `-sV`），
      并说清 **`-sS` 为什么需要 root**、为什么它对应用层"隐蔽"
- [ ] 解释 `-T0 ~ -T5` 六个时序模板的取舍，并说出**为什么默认是 T3 而不是 T5**
- [ ] 解释 UDP 扫描为什么不可靠（至少说出"合法沉默"和"ICMP 限速"两个原因）
- [ ] 说清端口 **三态**（open / closed / filtered）的判定依据与各自含义
- [ ] 能解释"扫本机开放 ≠ 对外开放"（服务只绑 `127.0.0.1` 的情况）

### 原理掌握（能画出流程图）

- [ ] 能画出 **TCP 三次握手**图，并在图上标出 connect 扫描与 SYN 扫描的**分歧点**
- [ ] 能解释"收到 RST"和"超时"这两种证据的**强度差异**
- [ ] 能说出 banner 抓取的**四种服务性格**（话痨 / 握手 / 请求-响应 / 冰柜）
- [ ] 能解释 `recv` 一次为什么可能拿到被切碎的 banner（TCP 是字节流）
- [ ] 能解释：为什么并发扫描的耗时约等于 `max(单端口耗时)` 而不是求和
- [ ] 能说出 `python-nmap` 的**真实工作原理**（subprocess 调 nmap + 解析 XML）
- [ ] 能说出扫描器**必须限流**的三条理由（自己的 fd / 目标的 conntrack / 授权条款）

### 动手实践（跑代码 + 改代码）

- [ ] 运行 `code/01-nmap-basics.py`，观察三种调用方式的输出差异
- [ ] 检查本机有没有 nmap（`which nmap`）和 python-nmap（`pip show python-nmap`），
      分别制造"有/无"两种组合，确认脚本**都不会崩**
- [ ] 把 `01` 里的 `COMMON_PORTS` 加上几个端口（如 1080、2375、5984），重新运行
- [ ] 运行 `code/02-banner-grab-pitfalls.py`，把 8 个坑的"错误 / 正确"输出都看懂
- [ ] 把 `02` 里 `grab_banner()` 的 `max_bytes` 改成 `64`，观察 HTTP banner 被截断
- [ ] 把 `02` 的 `pitfall_6` 中 `max_workers` 从 8 改成 1，观察耗时的变化并解释
- [ ] 运行 `code/03-auto-port-scanner.py`，打开导出的三种格式文件，逐个看懂字段
- [ ] 运行 `python3 code/03-auto-port-scanner.py --ports 1-1024 --workers 128 --timeout 0.5`，
      记录耗时并与 `--ports top` 对比，算一下加速比
- [ ] 运行 `python3 code/03-auto-port-scanner.py --target 192.168.1.1`，
      确认**护栏生效并拒绝执行**（这是今天最重要的一个观察）
- [ ] 修改 `03` 的 `FINGERPRINTS`，为 `memcached`（响应含 `VERSION`）增加一条规则

### 输出物

- [ ] `days/day-153-port-scan-advanced/` 目录下 4 类文件齐全（README / code / diagrams / exercises）
- [ ] 3 个 `.py` 全部能 `python3` 直接跑通，**只依赖标准库**
- [ ] 能对着 `diagrams/README.md` 给别人讲一遍"扫描类型分歧点 + banner 决策流程"
- [ ] 能说出本日代码里**所有**"只扫本机"的保护措施在哪几行、分别防什么

---

## 📝 练习题

### 基础题（巩固机制）

**Q1. 状态判定连线**
把左边的现象与右边的状态、以及"你的解读"正确配对：

| 现象 | 状态候选项 | 解读候选项 |
|---|---|---|
| A. `connect_ex` 返回 `0` | ① open | ⅰ. 报文被中间设备丢弃，可能有防火墙 |
| B. `connect_ex` 返回 `111` | ② closed | ⅱ. 有进程在监听，可以继续抓 banner |
| C. `connect_ex` 返回 `110` | ③ filtered | ⅲ. 主机在线但该端口无监听，主机存活性暴露 |
| D. 目标主机整体不可达 | ④ filtered | ⅳ. 路由或网络问题，先检查自己的网络 |

**Q2. 命令纠错**
下面几条 nmap 命令各有什么问题？请写出修正后的命令与理由：

```bash
# ① 想扫全端口但只花几秒
nmap -p- -sV -T5 127.0.0.1

# ② 想抓服务版本，但目标在防火墙后面，每次都显示 "Host seems down"
nmap -sV 127.0.0.1

# ③ 想看 UDP 的 DNS 服务，但用了默认时序
nmap -sU 127.0.0.1

# ④ 想在非 root 用户下做 SYN 扫描
nmap -sS 127.0.0.1
```

**Q3. banner 抓取纠错**
下面这段代码有 **4 个**问题，请找出来并给出修正版：

```python
import socket

def get_banner(host, port):
    s = socket.socket()
    s.connect((host, port))
    data = s.recv(1024)
    return data.decode("utf-8")
```

> 提示：超时、协议行为、TCP 分段、二进制解码、资源释放。

**Q4. 探针配对**
为下列服务选择正确的抓取方式（只读 / 发 HTTP 探针 / 发 PING 探针 / 必须先 TLS 握手）：

| 服务 | 端口 | 抓取方式 |
|---|---|---|
| 1. OpenSSH | 22 | ？ |
| 2. nginx HTTP | 80 | ？ |
| 3. nginx HTTPS | 443 | ？ |
| 4. Redis | 6379 | ？ |
| 5. Postfix SMTP | 25 | ？ |

---

### 进阶题（设计 + 代码）

**Q5. 给扫描器加一个"服务指纹报告"模块**
在 `code/03-auto-port-scanner.py` 的基础上，新增一个导出函数
`export_fingerprint_summary(results, path)`，输出一份按"服务名"聚合的统计报告：

要求：
1. 统计每个服务（ssh / http / smtp / unknown…）出现的端口数量；
2. 对 `unknown` 服务额外标注"需要人工确认"，因为无法做漏洞评估；
3. 输出为 Markdown，格式自拟，但必须包含"服务 | 端口列表 | 数量 | 备注"四列；
4. 对以下**高危服务**加醒目标记（🔴）：`redis`、`mongodb`、`elasticsearch`、
   `memcached`、`ms-wbt-server`（RDP）、`docker`、`vnc`。

**验收标准**：
- 运行 `python3 code/03-auto-port-scanner.py --out-dir ./out` 后，
  `./out/fingerprint-summary.md` 存在且内容符合上述四列要求；
- 用 `--no-demo` 跑一次（没有演示服务）时，函数不能因为空结果崩溃。

**Q6. 实现"扫描结果差异对比"（配置漂移检测）**
写一个独立脚本 `code/04-scan-diff.py`（或直接加为 `03` 的子命令）：

1. 读取两份 `scan-result.json`（昨天 / 今天）；
2. 输出四类差异：**新增开放端口**、**消失的开放端口**、
   **服务/版本发生变化的端口**、**状态从 closed 变成 filtered 的端口**；
3. 用 Markdown 表格输出，并对"新增开放端口"用 ⚠️ 高亮
   —— 因为**配置漂移里最危险的就是"莫名其妙多出来一个开放端口"**；
4. 退出码：有新增开放端口 → 返回 `1`（便于接 cron/CI 做告警）。

**提示**：`scan-result.json` 的 `results` 是一个列表，每项含
`host / port / state / service / banner / latency_ms / error`。

**Q7. 让扫描器"礼貌"起来（限流与退避）**
真实项目里，扫描器必须对目标友好。请给 `03` 增加以下能力：

1. `--max-rate N`：全局每秒最多发起 N 个连接（提示：用
   `threading.Semaphore` + 定时补充令牌，或简单地用
   `time.sleep(1/N)` 在提交任务前限速）；
2. `--pause-on-error K`：连续 K 个端口返回 `filtered` 时，暂停 2 秒
   —— 这通常意味着"你真的把目标惹毛了"（触发了限速或封禁）；
3. 在报告里记录实际的平均请求速率（端口数 / 耗时）。

**思考并回答**：为什么"连续 filtered 时退避"比"无脑重试"更专业？
（提示：想想你面对的可能是一台被测出限速策略的**生产**防火墙。）

---

## 🔑 参考答案要点（先自己做，再对答案）

<details>
<summary>点击展开（Q1 / Q2 要点）</summary>

**Q1**：A→①→ⅱ；B→②→ⅲ；C→③→ⅰ；D→④→ⅳ。

**Q2**：
- ① `-p- -sV -T5` 是全端口 + 版本探测 + 极限时序。这三个叠加，
  即使在局域网也可能要几十分钟，而且 T5 会大量丢包导致**结果不准**。
  修正：先 `nmap -p- -T4 --min-rate 1000`（不带 `-sV`）找出开放端口，
  再对**开放的那几十个端口**做 `-sV`。这叫"两步扫描法"。
- ② 防火墙后的主机不回 ping，nmap 默认的存活检测会判定 `Host seems down`。
  修正：`nmap -Pn -sV 127.0.0.1`。
- ③ UDP 扫描默认就很慢，但要提高可靠性应显式指定重试与超时。
  修正：`nmap -sU -p 53 --max-retries 3 --host-timeout 60s 127.0.0.1`
  —— 并且**只扫 53**，不要用 `-sU -p-`。
- ④ 非 root 用户无法创建原始套接字。修正：降级为
  `nmap -sT 127.0.0.1`（或者用 `sudo`，但要在授权范围内）。

</details>

<details>
<summary>点击展开（Q3 要点）</summary>

原代码的 4 个问题：

1. **没有超时**：`s.connect()` 和 `s.recv()` 都可能永久阻塞。
2. **没有探针**：对 HTTP 这类请求-响应协议，只 `recv` 会一直等到超时。
3. **只 `recv` 一次**：TCP 是字节流，banner 可能被分段。
4. **解码不设容错 + 不关 socket**：二进制 banner 会让 `decode` 抛异常；
   没关闭 socket 会泄漏文件描述符。

修正版（简洁版，完整版见 `code/02-banner-grab-pitfalls.py` 的 `grab_banner`）：

```python
import socket

def get_banner(host, port, probe=None, timeout=1.0, max_bytes=4096):
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            if probe:
                s.sendall(probe)
            chunks, total = [], 0
            while total < max_bytes:
                try:
                    chunk = s.recv(1024)
                except (socket.timeout, ConnectionResetError):
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
            raw = b"".join(chunks)
            return raw.decode("utf-8", errors="replace") if raw else None
    except OSError:
        return None

if __name__ == "__main__":
    print(get_banner("127.0.0.1", 80, b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n"))
```

</details>

<details>
<summary>点击展开（Q4 要点）</summary>

| 服务 | 抓取方式 | 理由 |
|---|---|---|
| OpenSSH:22 | **只读** | 服务端连上立刻发 `SSH-2.0-...` |
| nginx HTTP:80 | **发 HTTP 探针** | 请求-响应协议，不发请求它不说话 |
| nginx HTTPS:443 | **必须先 TLS 握手** | 明文探针会被当成垃圾数据；要 `ssl.wrap_socket` |
| Redis:6379 | **发 PING 探针** | 命令-应答协议；无认证时回 `+PONG` |
| Postfix SMTP:25 | **只读** | 服务端主动发 `220 ...` |

</details>

---

## 📌 今日自检的三个问题

1. 如果有人问你"端口扫描违不违法"，你**会先问哪三个问题**？
   （目标归属 / 是否有书面授权 / 授权的时间与范围）
2. `open` / `closed` / `filtered` 三个状态里，哪一个**最让运维安心**？
   为什么它不是 `closed`？
3. 今天的代码里，如果只允许你保留一个安全措施，你保留哪个？为什么？

---

## 🚫 今日红线（再强调一次）

- ❌ 不扫描任何**不属于你**、且**没有书面授权**的目标；
- ❌ 不使用 `-T5` 对生产环境扫描；
- ❌ 不把本日代码的目标参数改成公网 IP"试一试"；
- ❌ 不在扫描结果里保存任何凭据（banner 里可能含敏感信息，导出前先想清楚）；
- ✅ 拿不准时，**不扫描**。
