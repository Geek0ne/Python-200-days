# Day 187 · 练习与验收清单

## ✅ 完成清单

- [ ] 能解释 open / closed / filtered 的内核行为
- [ ] 能背出 0 / 111 / 11 / 115 / 110 / 101 的含义
- [ ] 能实现端口段解析（逗号 + 区间 + 去重 + 边界）
- [ ] 能用 ThreadPoolExecutor 并发扫描并统计状态
- [ ] 能发 HTTP GET，按 Content-Length 读完整 body
- [ ] 能从 Server 头 + title + banner 做指纹并给出置信度
- [ ] 能用 nmap -sT 对账，解释差异
- [ ] 跑通 4 个脚本的 --self-test
- [ ] 完成至少 3 道练习

---

## 基础练习

### 练习 1：补全 errno 表

写一个小脚本，对以下目标各调用 5 次 connect_ex，打印返回值与耗时：
- 127.0.0.1 上一个监听端口
- 127.0.0.1 上一个刚释放的端口
- 198.51.100.1:81（TEST-NET-2，通常黑洞）

**验收**：能解释为什么第三个返回 11 而不是 110/111。

### 练习 2：端口段解析边界

为 parse_ports 补测试：
- "80,80,80" → [80]
- "100-99" → [99,100]
- "0" / "65536" → 抛 ValueError
- "1-3,2-4" → [1,2,3,4]

### 练习 3：HEAD vs GET

对同一个 HTTP 服务分别发 HEAD 和 GET，记录：
- 状态行
- Server 头
- Content-Length
- 是否能拿到 title

**验收**：能说明为什么指纹流程通常先 HEAD、需要内容时再 GET。

### 练习 4：SQLite 幂等

连续跑两次 `03-asset-scan-case.py --db assets.db`，查询行数。
**验收**：行数不变，scanned_at 更新。

---

## 进阶挑战

### 挑战 1：加入 UDP 探测

用 SOCK_DGRAM 向 127.0.0.1 的某端口发一个字节：
- 若收到 ICMP port unreachable（connect_ex 返回 111）→ closed
- 若超时 → open|filtered

写清"UDP 无法区分 open 与 filtered"的原因。

### 挑战 2：指纹插件化

把 SIGNATURES 列表改成"规则函数"：每个函数接收 info，返回 (product, confidence, evidence) 或 None。
要求新增一条规则不需要改主流程。

### 挑战 3：扫描限速

给 scan_host 加 `--rate`（每秒最多发起 N 个连接），用令牌桶实现。
验证：N=20 时，200 个端口的扫描耗时 ≥ 10 秒。

### 挑战 4：与 nmap 的差异报告

对 127.0.0.1 的 1-1024 端口分别用自研脚本与 nmap -sT -Pn 扫描：
- 统计两者判定不一致的端口
- 对每个不一致，抓包或打印 errno 解释原因

---

## 验收命令

```bash
cd days/day-187-端口扫描与指纹识别/code
python3 01-port-scan-basic.py --self-test
python3 02-banner-fingerprint.py --self-test
python3 03-asset-scan-case.py --self-test
python3 04-timeout-benchmark.py --self-test
```

## 提交前自检

- [ ] 没有扫描任何未授权公网地址
- [ ] 临时 HTTP 服务已 kill，端口无残留
- [ ] README 的数字与本次运行一致
- [ ] 没有把 /tmp 产物提交进仓库
