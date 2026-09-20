# Day 162 — 完成清单与练习题（安全审计工具箱 · 资产面）

> **全部操作只在授权环境进行**：所有实验都跑在 `127.0.0.1` 的**自建实验服务**上
> （`audit_core.LabHTTP`，端口 8000-8099）。
> 工具箱只做**匿名视角的只读 GET**：不登录、不带 Cookie、不爆破凭据、
> 不上传、不修改任何数据、不下载备份文件。
> 词表是内置的 30 条公开文档化路径，默认 5 请求/秒。
> 练习中的地址一律为回环或文档网段（RFC 5737：192.0.2.0/24 等）。

## 一、完成清单（先跑通，再做题）

- [ ] `python3 code/audit_core.py --self-test` → `SELF-TEST OK`
- [ ] `python3 code/01-port-scan.py --self-test` → `SELF-TEST OK`
- [ ] `python3 code/02-dir-brute.py --self-test` → `SELF-TEST OK`
- [ ] `python3 code/03-audit-toolkit.py --self-test` → `SELF-TEST OK`
- [ ] `python3 code/03-audit-toolkit.py lab` → 基线 `status=200 len=77`、`findings 33`、退出码 3
- [ ] `python3 code/03-audit-toolkit.py lab --http-port 8085 --throttle-after 8`
      → `限速 25`、`coverage_gap`、退出码 4
- [ ] `python3 code/03-audit-toolkit.py dirs --base http://192.0.2.1:8080`
      → `AuthorizationError`、退出码 2
- [ ] `python3 code/03-audit-toolkit.py fingerprint --base http://127.0.0.1:8080`
      → `lab-cms 0.5 medium`、`lab-nginx 0.4 low`
- [ ] 打开 `out/day162-lab-report.json`，能找到 `baseline` / `dirs` / `fingerprint` / `findings`
- [ ] 能口述：为什么"只认 200"会漏掉最有价值的发现
- [ ] 能口述：429 为什么必须把退出码抬到 4
- [ ] 能口述：为什么 `Server` 头只能算"低置信"信号

## 二、基础练习

### 练习 1：给实验服务加一个"真 404"目录

`LabHTTP` 目前对所有未匹配路径都返回 200（软 404 配置）。
请增加规则：`/static/` 下的未匹配路径返回**真 404**（`NOT_FOUND_BODY`），
其余路径保持软 404。然后：

- 用 `dir_brute` 扫 `["static/a.css", "robots.txt"]`，确认前者是 `missing`、后者是 `soft_404`；
- 写一句结论：**同一台服务器上可以同时存在软 404 与真 404**，
  因此判定必须逐目录/逐前缀地看，而不能全局套一个规则。

### 练习 2：把软 404 判定改成"双请求同路径"

`build_baseline` 目前用**随机路径**取基线。请实现 `build_baseline_stable`：
对**同一条**不存在的路径连发 2 次，比较两次的长度差；
若长度抖动 > 8 字节，说明页面里有动态内容，此时把容差按实测抖动放大。

要求：打印两次的长度与最终采用的容差，并说明为什么"同路径双请求"比
"两次随机路径"更贴近真实噪声。

### 练习 3：补一类分类 `auth_redirect`

很多站点对未登录用户返回 `302 → /login`。请新增分类 `auth_redirect`：

- 条件：`status in (301,302)` 且 `Location` 指向包含 `login`/`signin`/`auth` 的路径；
- 在报告里单独统计，并输出一句提示"疑似需登录后可见（本次未尝试登录）"；
- 写自检。

**思考**：把这个分类和 `protected`（401/403）放在一起看，
哪一类更值得优先人工跟进？为什么？

### 练习 4：把端口扫描的"服务来源"写进报告标题

当前报告只在 JSON 里保留 `service_source`。请修改 `render_markdown`，
在端口表里增加一列 `来源`（`banner` / `port_map`），并加一句脚注：

> `banner` = 服务自报家门（高置信）；`port_map` = 端口号约定（低置信，端口可被改写）。

### 练习 5：给词表加"业务前缀"支持

真实审计里经常需要扫 `/api/v1/`、`/admin/` 这类前缀下的路径。
请实现 `expand_words(prefixes, words)`：把词表与前缀做笛卡尔积，
并**去重**、**限制总数上限**（例如 200 条），超出时打印警告并截断。

要求：说明为什么"上限 + 警告"是必须的（提示：请求量与授权边界的关系）。

## 三、进阶挑战

### 练习 6：并发限速（保持礼貌的同时提速）

当前目录爆破是**串行**的（并发 1）。请改成"**有并发但严格限速**"：

- 用 `ThreadPoolExecutor(max_workers=4)`；
- 用同一个 `TokenBucket(rate=5)` 控制**每秒请求数**；
- 保持结果顺序与词表顺序一致（便于 diff 两次扫描）。

要求：实测"串行 5/s"与"并发 4 + 5/s"的耗时差异，并证明**总请求速率没有被放大**
（打印每秒实际请求数）。讨论：并发在这里的意义是什么？

### 练习 7：429 的"自适应恢复"

当前出现 429 只会退避，不会恢复。请实现：

- 连续 N 次成功（非 429）后，把退避基数**折半**（下限 0.25s）；
- 再把每次退避与恢复写进日志（`event="backoff"` / `event="recover"`）；
- 让 `coverage` 增加 `recovered` 计数。

**思考**：为什么"恢复"逻辑比"退避"逻辑更容易写出问题（提示：抖动、假恢复）？

### 练习 8：指纹置信度的"证据权重表"可配置化

把 `collect_signals` 里的权重硬编码改成从 JSON 加载：

```json
{"header:Server": 0.4, "cookie": 0.2, "html:meta": 0.3, "path:": 0.6}
```

要求：缺省值兜底、非法权重（<0 / >1）报错、支持按 site 覆盖。
写自检：覆盖后 `lab-cms` 的分档从 `medium` 变为其它档。

### 练习 9：把三模块结果做成"资产清单"导出

新增 `assets` 子命令：把端口 + 目录 + 指纹合并成一份**资产清单**：

```json
{
  "hosts": [{"host": "127.0.0.1", "open_ports": [{"port": 8080, "service": "http-proxy", "source": "port_map"}],
             "paths": {"accessible": ["healthz"], "protected": ["admin/"], "soft_404": 19},
             "tech": [{"tech": "lab-cms", "score": 0.5, "confidence": "medium"}]}]
}
```

要求：这份清单可以直接作为 Day 163 漏洞检测的输入（说明如何衔接）。

### 练习 10：写一份"覆盖边界声明"

为本工具箱写一份给客户看的覆盖声明（半页以内），必须包含：

- **测了什么**：端口扫描 / 目录爆破（匿名视角）/ 指纹识别；
- **没测什么**：认证后区域、参数注入、文件上传、业务逻辑、任何绕过；
- **结论受什么限制**：429 次数、filtered 端口数、软 404 容差、词表规模；
- **客户需要做什么**：复核 403/401 清单、确认 `/backup.zip` 是否需要下线。

**要求**：不出现"确保安全""全面覆盖"这类无法兑现的措辞。

## 四、验收命令

```bash
cd ~/code/Learn-Python
D="days/day-162-安全审计工具箱-part1/code"
python3 "$D/audit_core.py" --self-test
python3 "$D/01-port-scan.py" --self-test
python3 "$D/02-dir-brute.py" --self-test
python3 "$D/03-audit-toolkit.py" --self-test
python3 "$D/03-audit-toolkit.py" lab
python3 "$D/03-audit-toolkit.py" lab --http-port 8085 --throttle-after 8   # 期望退出码 4
python3 "$D/03-audit-toolkit.py" dirs --base http://192.0.2.1:8080         # 期望退出码 2
```

前四条必须输出 `SELF-TEST OK`。

## 五、思考题（写在笔记里）

- 软 404 基线与容差是一对"误报/漏报滑块"。如果客户只给你 10 分钟窗口，
  你会把滑块往哪边调？为什么必须在报告里写明你调到了哪一档？
- 429 意味着"目标认为我在压它"。如果目标是一家**已授权的客户网站**，
  你会先联系谁、说什么？如果目标是你自己的测试环境呢，处理方式有什么不同？
- 指纹全部可被伪造。既然如此，"指纹识别"这项工作的价值到底是什么？
  （提示：想想它对**后续检测的选择**和**与客户沟通**的作用）
- 本课只做匿名视角。假设业务方要求覆盖认证后区域，
  列出你需要的**前置条件**（至少 4 条），并说明每条对应什么风险。
- 如果把这份工具箱接入 CI 对测试环境每日跑一次，
  `soft_404`（19 条）与 `429` 会产生多少噪声？你会用什么办法让流水线**稳定但不失效**？
