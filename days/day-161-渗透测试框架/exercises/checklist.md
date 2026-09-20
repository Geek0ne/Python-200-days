# Day 161 — 完成清单与练习题（渗透测试框架）

> **全部操作只在授权环境进行**：本课所有实验都在 `127.0.0.1` 的回环实验服务上完成。
> 框架**只读**探测（TCP connect + 读取服务主动发来的 banner），
> **不发送任何数据**、不做爆破、不做利用、不改动目标任何内容。
> 练习里出现的地址一律是回环地址或文档网段（RFC 5737：203.0.113.0/24、
> 198.51.100.0/24、192.0.2.0/24）。

## 一、完成清单（先跑通，再做题）

- [ ] `python3 code/pentest_core.py --self-test` → `SELF-TEST OK`
- [ ] `python3 code/01-scan-engine.py --self-test` → `SELF-TEST OK`
- [ ] `python3 code/02-framework-advanced.py --self-test` → `SELF-TEST OK`
- [ ] `python3 code/03-pitfalls.py --self-test` → `SELF-TEST OK`
- [ ] `python3 code/04-pentest-framework.py --self-test` → `SELF-TEST OK`
- [ ] `python3 code/04-pentest-framework.py plugins` → 看到 4 个插件与 priority 分层
- [ ] `python3 code/04-pentest-framework.py lab --ports 8000-8080 --rate 500` →
      报告里 `open 2 / closed 79`、`findings 9`、退出码 3
- [ ] `python3 code/04-pentest-framework.py authorize --hosts 127.0.0.1 --ports 8000-8002`
      → 通过，且**没有产生任何 probe 记录**（只做校验）
- [ ] `python3 code/04-pentest-framework.py scan --hosts 10.0.0.5 --ports 8000`
      → `AuthorizationError`、退出码 2
- [ ] 打开 `out/day161-lab-audit.jsonl`，能指出 `scope_check / probe / finding` 三类记录
- [ ] 能口述：`filtered` 为什么不能写成 `closed`
- [ ] 能口述：为什么范围校验必须在 `socket()` **之前**
- [ ] 能口述：为什么"上游无资产"时检测阶段必须 `skipped`，而不是"0 个问题"

## 二、基础练习

### 练习 1：给范围加上"授权时间窗"

当前 `Scope` 有 `expires` 字段，但没有"生效时间"（not_before）。
请增加 `not_before` 字段并让 `Scope.check` 在"尚未生效"时也抛
`AuthorizationError`。要求：

- `Scope.from_dict` 能解析该字段（ISO8601，允许带时区）
- 写两条自检：窗口外拒绝、窗口内通过
- 在 `README` 的 API 表里补一行说明

**提示**：`datetime.fromisoformat()` 对无时区字符串会给出 naive datetime，
要像 `expired()` 那样显式补时区，否则比较会抛 `TypeError`。

### 练习 2：让报告显示"每个端口的状态"

当前报告只列 open 的资产，closed/filtered 只在统计里出现数量。
请给 `render_markdown` 增加一节"全部目标明细"，按 `host` 分组输出：

```text
127.0.0.1
  8000  open     ssh     SSH-2.0-OpenSSH_8.9p1…
  8001  closed   -       -
  8002  filtered -       -
```

要求：`filtered` 行必须在末尾加 `（不可判定）` 标记。写完后跑 `lab` 验证。

### 练习 3：实现"服务指纹"插件

新增插件 `tls_hint`（priority=35）：对 443/8443/9443 这类端口，
若 connect 成功但 **没有** 返回明文 banner，则产出一条
`severity="info", confidence="low"` 的 Finding，说明"疑似 TLS 服务（需握手确认）"。

**关键要求**：**不要真的发起 TLS 握手**（那会发送数据，超出本课"只读"边界）。
只在报告里标注"需要人工验证"。这正是框架中"推断层"与"结论层"的边界示例。

### 练习 4：黑名单优先的边界测试

构造一个范围：`networks=["127.0.0.0/29"]`、`excluded=["127.0.0.1/32", "127.0.0.4/31"]`。
列出 `127.0.0.0/29` 里**被允许**的主机，并解释为什么 `127.0.0.1`
即使同时出现在白名单里也必须被拒绝。写一句给"非技术同事"的解释。

### 练习 5：把三态统计做成"结论可信度"评分

定义一个 0–100 的可信度分数：

```text
可信度 = 100 × 可判定目标数 / 总目标数
```

在报告顶部输出该分数，并在 `filtered` 占比 > 30% 时强制加一行警告：
"本次结论可信度不足，建议更换网络路径复测"。写自检覆盖两种情况。

## 三、进阶挑战

### 练习 6：插件依赖的显式声明（替代隐式 priority）

当前插件顺序靠 `priority` 数字约定，属于隐式依赖。请改造成**声明式依赖**：

```python
@fw.plugin("version_disclosure", priority=30, requires=["banner_evidence"])
```

要求：

- 注册时校验 `requires` 里引用的插件存在（否则报错）
- 执行时按拓扑排序（若有环则报错并列出环）
- 保持向后兼容：不写 `requires` 时退回 priority 排序
- 写自检：`A requires B` 时 B 一定先执行；构造环 `A→B→A` 必须报错

**讨论**：为什么"声明式依赖"比"数字优先级"更难写错？它又引入了什么新成本？

### 练习 7：把 `authorize` 做成签发前的"边界报告"

`authorize` 目前只在通过时打印前 20 条目标。请改造为输出一份**边界报告**：

- 允许的目标数（按 host 聚合）
- 被拒绝的目标及原因（分主机越界 / 端口越界 / 命中黑名单 / 授权过期）
- 授权单号、生效时间、到期时间、总端口数
- 输出为 JSON，供后续 `scan --scope` 复用

**思考**：为什么这份边界报告应该在**扫描之前**发给客户确认？

### 练习 8：并发下的"礼貌退避"（backoff）

当连续出现多个 `filtered` 时，说明链路在丢包。请实现**自适应退避**：

- 连续 N 个 `filtered` → 把 `rate` 减半（下限 1/s）
- 连续 M 个成功判定（open 或 closed）→ 逐步恢复 `rate`
- 把每次调整写进审计日志（`event="rate_adjust"`）

写自检：构造一个全部 filtered 的场景，断言 rate 至少被调整过一次。

### 练习 9：给框架加"离线重放"能力

扫描结果已存进 `out/*-report.json`，但审计日志是独立文件。
请实现 `replay` 子命令：读审计日志，**不发起任何连接**，
重建"阶段 → 资产 → 发现"的全过程并打印时间线。

**为什么值得做**：复核、教学、事故复盘都需要"重放"；
而重放必须是**离线**的，否则"复核一次"就等于"再扫一次"（可能超出授权窗口）。

### 练习 10：写一份"能力与局限"声明模板

为框架写一份给客户看的声明（一页以内），必须包含：

- 本工具**能做**的三件事（资产盘点、服务识别、配置类风险提示）
- 本工具**不做**的五件事（利用、提权、处置、规避检测、扩大范围）
- 结论可信度受什么影响（filtered 比例、超时值、限速参数）
- 出报告后客户需要做什么（人工复核清单、授权窗口内验证）

**要求**：不出现"确保安全""彻底扫描"这类无法兑现的措辞。

## 四、验收命令

```bash
cd ~/code/Learn-Python
D="days/day-161-渗透测试框架/code"
python3 "$D/pentest_core.py" --self-test
python3 "$D/01-scan-engine.py" --self-test
python3 "$D/02-framework-advanced.py" --self-test
python3 "$D/03-pitfalls.py" --self-test
python3 "$D/04-pentest-framework.py" --self-test
python3 "$D/04-pentest-framework.py" lab --ports 8000-8080 --rate 500
python3 "$D/04-pentest-framework.py" authorize --hosts 127.0.0.1 --ports 8000-8002
python3 "$D/04-pentest-framework.py" scan --hosts 10.0.0.5 --ports 8000   # 期望退出码 2
```

前五条必须输出 `SELF-TEST OK`；`lab` 退出码 3；越界 `scan` 退出码 2。

## 五、思考题（写在笔记里）

- 框架把"越界"做成了**异常**而不是"警告 + 跳过"。如果改成后者，
  谁会因此承受风险？为什么"少扫几台"的代价小于"多扫一台"？
- `filtered` 意味着"不可判定"。如果客户坚持要一个"通过/不通过"的结论，
  你会怎么设计这份报告，才能既不撒谎、又能被业务方使用？
- 审计日志本身也是敏感数据（谁在什么时候扫了谁）。它的留存期限、
  访问权限、脱敏粒度应该怎么定？和"报告"相比，为什么日志的限制更严？
- 本课刻意不做利用能力与规避检测。请说明：如果一个团队只做"扫描 + 报告"，
  它在真实安全工作中能覆盖多少比例的价值？剩下的部分必须由谁来补？
- 假设你要把这份框架接入 CI（每次发布前对测试环境跑一次），
  你会怎么处理"退出码 4（无结论）"？直接失败会让流水线卡住，
  直接放行又等于放弃门禁——你的取舍是什么？
