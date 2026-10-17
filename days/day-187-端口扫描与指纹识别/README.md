# Day 187 — 综合项目 I（二）：端口扫描与指纹识别

> **阶段**：Phase 12 — 综合实战
> **项目**：企业资产监控系统 · 第 2/5 天
> **子主题**：TCP connect 扫描 · errno 判定 · 超时设计 · banner/HTTP 指纹 · nmap 对账
> **代码**：4 个标准库脚本，全部带 `--self-test`
> **实测环境**：Linux 7.0.0-34-generic / Python 3.12.3 / nmap 7.94SVN / 2026-10-18

---

## 今天在项目里的位置

Day 186 得到了"名字 → IP"。今天回答第二个问题：**这些 IP 上开了什么服务？**

```text
Day 186  资产发现        →  python.org / 8 个可解析主机
Day 187  端口 + 指纹     →  127.0.0.1:18080 open, Python http.server
Day 188  Web 漏洞检测    →  这个 HTTP 服务有没有 SQLi/XSS
```

只有确认了"这是 HTTP 服务"，Day 188 的 Web 扫描才有意义。
对 SSH 端口发 `?id=1'` 只会浪费时间，还会制造噪音。

---

## 概念速览

完整原理（errno 表、三种扫描方式、指纹置信度）见 **`concepts.md`**。

| 概念 | 一句话 | 为什么重要 |
|---|---|---|
| TCP connect 扫描 | 完整握手判断端口 | 无需 root，日志可审计 |
| errno 判定 | 0/111/11/110 决定状态 | 判错会把 filtered 当 error |
| filtered | 防火墙 DROP，等到超时 | 决定扫描总耗时 |
| banner | 服务主动吐出的版本串 | SSH/FTP/SMTP 最有效 |
| 指纹置信度 | high/medium/low | 避免把猜测当事实 |
| nmap 对账 | 用成熟工具验证自研结果 | 发现实现差异 |

---

## 原理解释：本日三个真实 bug

### 1. 只读到 `\r\n\r\n`，永远拿不到 `<title>`

第一版 `read_some()` 一看到响应头结束就 `break`。HEAD 请求没问题，
但 GET 的 HTML body 在头后面，于是 `title` 永远是空字符串。

自测直接抓到了：

```text
AssertionError: {'status_line': 'HTTP/1.0 200 OK', 'title': '', ...}
```

修复：解析 `Content-Length`，继续读到 body 满足长度为止。
**教训**：HTTP 不是"读到空行就结束"，头和 body 是两个阶段。

### 2. HEAD 与 GET 的指纹证据不同

`02-banner-fingerprint.py` 默认发 HEAD，实测本地服务输出：

```text
状态行: HTTP/1.0 200 OK
Server: SimpleHTTP/0.6 Python/3.12.3
Title : (无)
指纹  : Python http.server (置信度 high)
```

而 `03-asset-scan-case.py` 显式发 GET，同一服务得到：

```text
Title=Directory listing for /
```

**结论**：HEAD 省流量，但没有 body；需要页面内容做指纹时必须 GET。

### 3. errno 11 被误判成 error

对黑洞地址 `198.51.100.1:81` 扫描，Linux 返回 `errno 11 (EAGAIN)`，
耗时正好等于 timeout。第一版只把 `110` 当 filtered，输出变成：

```text
198.51.100.1:81   0.2   error(11)   200.36ms
```

修复：把 `11/115` 也归入 filtered。复测：

```text
198.51.100.1:81   0.2   filtered   200.37ms
198.51.100.1:81   1.0   filtered  1001.18ms
```

**教训**：errno 归类必须用真实环境验证；"耗时 ≈ timeout"是强辅助信号。

---

## API 速查

| 需求 | 写法 | 注意 |
|---|---|---|
| 解析端口段 | `parse_ports("80,8000-8010")` | 去重、排序、边界检查 |
| 连接并取错误码 | `sock.connect_ex((host, port))` | 0 成功，其余是 errno |
| 超时 | `sock.settimeout(0.5)` | 单 socket 生效 |
| 并发 | `ThreadPoolExecutor(max_workers=100)` | I/O 密集 |
| 读 HTTP | 头 + 按 Content-Length 读 body | 别在空行处停 |
| 取 header | 按 `:` 切分，key 小写 | 重复 header 保留最后一个 |
| 取 title | 正则 `<title>(.*?)</title>` | 加 `re.S` |
| SQLite upsert | `ON CONFLICT(host,port) DO UPDATE` | 重复扫描不膨胀 |

---

## 代码导览

| 文件 | 内容 |
|---|---|
| `01-port-scan-basic.py` | connect 扫描、端口段解析、状态统计、自测绑定真实端口 |
| `02-banner-fingerprint.py` | banner/HTTP 头/title 指纹、置信度、自测本地 HTTP 服务 |
| `03-asset-scan-case.py` | 扫描→指纹→JSON/SQLite 全链路 |
| `04-timeout-benchmark.py` | open/closed/filtered 真实耗时中位数 |

---

## 实战实验手册

> 命令均在 `days/day-187-端口扫描与指纹识别/code` 下执行。
> 实验只针对 `127.0.0.1` 和自己启动的临时 HTTP 服务。

### 实验 1：本地 HTTP 服务扫描 + 指纹 + nmap 对账

**目的**：验证 open/closed 判定、HTTP 指纹、SQLite 落库，并与 nmap 对账。

**准备**：Python 标准库即可；nmap 已安装（7.94SVN）。

**执行**：

```bash
python3 -m http.server 18080 --bind 127.0.0.1 >/tmp/day187-http.log 2>&1 &
HTTP_PID=$!
sleep 1
python3 03-asset-scan-case.py --host 127.0.0.1 --ports 18080,18022 \
  --timeout 0.5 --json /tmp/day187-assets.json --db /tmp/day187-assets.db
python3 02-banner-fingerprint.py --host 127.0.0.1 --port 18080
nmap -sT -Pn -p 18080,18022 127.0.0.1
kill $HTTP_PID
```

**实际结果**（2026-10-18 真机）：

```text
[*] 目标 127.0.0.1，2 个端口
  [+] 127.0.0.1:18080  Python http.server (high)  Server=SimpleHTTP/0.6 Python/3.12.3  Title=Directory listing for /
[*] JSON 已写入 /tmp/day187-assets.json
[*] SQLite 已写入 /tmp/day187-assets.db（表 service_assets）

[*] 127.0.0.1:18080
    状态行: HTTP/1.0 200 OK
    Server: SimpleHTTP/0.6 Python/3.12.3
    Title : (无)
    指纹  : Python http.server (置信度 high, 证据 simplehttp)

PORT      STATE  SERVICE
18022/tcp closed unknown
18080/tcp open   unknown
Nmap done: 1 IP address (1 host up) scanned in 0.07 seconds

[('127.0.0.1', 18080, 'Python http.server', 'Directory listing for /')]
```

**结论**：
- 自研扫描器与 nmap 对 18080/18022 的判定**完全一致**；
- 自研脚本多给出产品与 title，nmap 只给 open/closed；
- 02 的 HEAD 探测拿不到 title（`Title : (无)`），03 的 GET 能拿到 —— 方法选择会影响证据；
- SQLite 里 `host/port` 主键保证重复扫描只更新，不产生重复行。

**清理**：
```bash
kill $HTTP_PID 2>/dev/null
rm -f /tmp/day187-http.log /tmp/day187-assets.json /tmp/day187-assets.db
```

---

### 实验 2：open / closed / filtered 的真实耗时

**目的**：用数据说明 timeout 对扫描总耗时的影响。

**执行**：

```bash
python3 04-timeout-benchmark.py
```

**实际结果**（2026-10-18，每类 5 次取中位数）：

```text
目标                        timeout          状态     中位数ms            范围ms
127.0.0.1:34015               0.5        open       0.22    0.05~0.68
127.0.0.1:33097               0.5      closed       0.02    0.02~0.03
198.51.100.1:81               0.2    filtered    200.37   200.3~200.39
198.51.100.1:81               1.0    filtered   1001.18  1000.96~1002.97
```

**结论**：
- 本机 open 约 0.22ms，closed 约 0.02ms，**filtered 严格等于 timeout**；
- timeout 从 0.2s 提到 1.0s，单个 filtered 端口耗时增加 5 倍；
- 扫 1000 个端口时，哪怕只有 10% filtered，串行也要多等 100 秒（0.2s 超时）。
- 并发能重叠等待，但不能低于"单端口 timeout"这个下限。

**清理**：无残留（只连接，不监听）。

---

### 实验 3：翻车复盘 —— 自测抓出的两个 bug

| 现象 | 假设 | 验证 | 根因 | 修复 | 复测 |
|---|---|---|---|---|---|
| title 永远为空 | 正则写错 | 打印完整响应 | 只读到 `\r\n\r\n`，body 没读 | 按 Content-Length 续读 | title 正确 |
| filtered 显示 error(11) | errno 表漏项 | 真机打印 connect_ex 返回值 | 黑洞地址返回 EAGAIN | 把 11/115 归入 filtered | 状态 filtered |

这两个 bug 都不是"想"出来的，是 `--self-test` 和真机实验暴露的。
教材里只写"正确代码"会掩盖这部分，而它恰恰是最值得学的。

---

## 收尾卫生

```bash
rm -f /tmp/day187-http.log /tmp/day187-assets.json /tmp/day187-assets.db
pgrep -f "http.server 18080" || echo "no leftover server"
```

已确认：临时 HTTP 服务已 kill，端口 18080 无残留监听，临时文件已删除。

---

## 思考题

1. 为什么 `connect_ex` 对黑洞地址返回 11 而不是 110？归类时如何避免类似漏项？
2. HEAD 和 GET 对指纹各有什么利弊？什么时候必须用 GET？
3. 如果目标把 `Server` 头改成随机值，你还能用哪些证据识别服务？
4. 500 个端口、100 并发、timeout=0.5s，最坏耗时多少？要压到 3 秒内怎么调？
5. 为什么"端口 open"不等于"服务可用"？举两个真实例子。
