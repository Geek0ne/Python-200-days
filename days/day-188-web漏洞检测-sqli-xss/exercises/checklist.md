# Day 188 · 练习与验收清单

## ✅ 完成清单

- [ ] 能解释 SQLi 的根因是"数据被当成代码"
- [ ] 能写出参数化查询修复
- [ ] 能区分报错型、布尔型、UNION、时间盲注
- [ ] 能解释 baseline 在扫描器中的作用
- [ ] 能实现报错型 + 布尔型检测
- [ ] 能解释转义与过滤的区别
- [ ] 能写出反射型 XSS 的上下文判定
- [ ] 能用对照组量化假阳性
- [ ] 跑通 5 个脚本的 `--self-test`

---

## 基础练习

### 练习 1：手工复现

启动靶场后，用 curl 完成：
1. `/product?id=1` 正常返回
2. `/product?id=1'` 返回 SQL 错误
3. `/product?id=1 AND 1=1` 正常
4. `/product?id=1 AND 1=2` 无结果

**验收**：能解释第 3、4 步的状态码差异。

### 练习 2：补一个 payload

在 `01-sqli-detect.py` 的 `ERROR_PAYLOADS` 中加入 `1 OR 1=1`，
观察它返回什么，并判断它属于报错型还是布尔型。

### 练习 3：修复靶场

把 `00-vuln-lab.py` 的 `/product` 改成参数化查询：
`conn.execute("SELECT ... WHERE id = ?", (pid,))`。
**验收**：`01-sqli-detect.py` 不再报告任何 SQLi。

### 练习 4：XSS 上下文

对 `/safe-search` 的响应打印原始 body，标出：
- `alert` 出现的位置
- `<` 被转义成什么
- 为什么浏览器不会执行

---

## 进阶挑战

### 挑战 1：加入 UNION 检测（只做判定，不拖库）

构造 `1 UNION SELECT 1,2,3`，观察响应是否出现额外列。
要求：
- 不读取真实数据；
- 只在本地靶场测试；
- 输出"可能存在 UNION 注入"而非具体数据。

### 挑战 2：合并同类 finding

给 `03-security-scan-report.py` 增加去重：
- 同一 `category + endpoint` 的多个 payload 合并为 1 个漏洞；
- 保留全部证据；
- 报告同时输出 `raw_finding_count` 与 `vuln_count`。

**目标**：本日结果从 6 条 finding 合并为 2 个漏洞。

### 挑战 3：假阳性率基准

写一个 `bench_fp.py`：
- 对 `/safe-search` 发 50 个不同 payload；
- 统计 naive 与 precise 的报警次数；
- 输出假阳性率。

**验收**：naive > 0，precise = 0。

### 挑战 4：CI 阈值

设计 GitHub Actions 步骤：
- 启动靶场；
- 运行 `03-security-scan-report.py`；
- 若 `severity == critical` 则 job 失败。

写出 YAML 片段并解释为什么"发现漏洞就让 CI 失败"在某些场景下不合适。

---

## 验收命令

```bash
cd days/day-188-web漏洞检测-sqli-xss/code
python3 00-vuln-lab.py --help
python3 01-sqli-detect.py --self-test
python3 02-xss-detect.py --self-test
python3 03-security-scan-report.py --self-test
python3 04-false-positive-drill.py --self-test
```

## 提交前自检

- [ ] 靶场进程已 kill，18081 无监听
- [ ] 没有对公网目标发起任何请求
- [ ] 报告里没有真实敏感数据
- [ ] README 的数字与本次运行一致
- [ ] /tmp 产物已删除
