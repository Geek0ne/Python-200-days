# Day 165 — 完成清单与练习（基础）

> 主题：阶段项目（四）安全审计工具箱 · 报告生成 + Docker 部署
> 使用提醒：所有练习请在 `code/` 目录下进行，目标数据用 `findings.example.json`（合成数据）。
> **不要**把任何练习指向你无授权的真实目标。

---

## ✅ 今日完成清单

### 概念层（能讲清楚，不是"看过"）

- [ ] 能说出四天阶段项目（Day 162–165）每一天负责哪一个"面"
- [ ] 能解释为什么报告层才是这个项目的**产品**，而不是附属输出
- [ ] 能说出报告的**三类消费者**及其各自要的格式
- [ ] 能解释"单一数据源"原则，以及为什么渲染器里不许做计算
- [ ] 能说出破坏确定性的三个来源，以及各自的对策
- [ ] 能解释稳定 id 为什么用内容哈希，而不是 UUID / 自增序号
- [ ] 能解释风险分里为什么要乘置信度系数
- [ ] 能说出覆盖缺口为什么必须独立建模，并单独占一个退出码
- [ ] 能说出 SARIF 的信息损失发生在哪里，以及怎么补偿
- [ ] 能解释非 root 容器 + 绑定挂载为什么 EACCES，并说出三种修法
- [ ] 能解释 exec 形式 ENTRYPOINT 与退出码门禁的因果关系

### 动手层（跑过才算）

- [ ] `python3 01-basic-report.py` 跑通，`out/` 下生成 `.md` 与 `.json`
- [ ] 打开生成的 Markdown，确认 `Authorization` 与 `password` 的值已被擦除
- [ ] `python3 02-determinism-redaction.py` 跑通，看到"两次渲染字节一致：True"
- [ ] 在 02 的输出里找到「错误顺序 → 误报凭证复用」那一段，能讲清原因
- [ ] `python3 03-toolbox-cli.py --input findings.example.json --format all` 跑通
- [ ] 实测退出码 0 / 1 / 2 / 4（`echo $?` 看结果）
- [ ] `docker build -t audit-toolbox:1.0 .` 构建成功
- [ ] `docker run --rm --entrypoint id audit-toolbox:1.0` 看到 `uid=10001`
- [ ] 实测容器里写盘失败 → 退出码 3
- [ ] 用 `chown 10001:10001 out` 修好后再跑 → 退出码 0
- [ ] `docker images` 对比基础镜像与自建镜像的体积差

### 交付层

- [ ] 能说出本工具**不做**什么（扫描 / 利用 / 解密 / 改包）
- [ ] 报告里同时包含"发现"和"覆盖缺口"两块
- [ ] 能在报告里指出至少一条"无证据的建议项"，并说明它为什么也值得保留

---

## 📝 基础练习（3 道）

### 练习 1：给报告加一个"总风险分"门槛（★☆☆）

**要求**：在 `03-toolbox-cli.py` 里新增参数 `--max-risk N`：
当报告的风险总分 `> N` 时返回退出码 1，否则正常走后续判断。

**要点**：
1. 参数加在 `argparse` 里，默认 `None`（不启用）
2. 判定用 `report.total_risk()`，不要自己再遍历累加（单一数据源）
3. 打印一行说明：`总风险分 105 > 阈值 50`
4. 保持既有优先级：**输入错误(2) > 有发现(1) > 覆盖缺口(4) > 通过(0)**
   —— 想想 `--max-risk` 应该插在链条的哪一环？

<details>
<summary>参考答案（点开）</summary>

```python
parser.add_argument("--max-risk", type=int, default=None,
                    help="风险总分超过该值即返回退出码 1")

# ……在 blocking 判定之后：
if blocking or (args.max_risk is not None and report.total_risk() > args.max_risk):
    ...
```

插入位置的选择理由：`--max-risk` 和 `--fail-on` 都是"发现类"的门禁，
应该**合并到同一个判断分支**（退出码 1），而不是新造一个码。
退出码是稀缺资源——每多一个码，消费它的 CI 就多一条要维护的分支。

</details>

### 练习 2：补一条脱敏规则（★★☆）

**要求**：为 `report_core.py` 增加一条规则，
把 JSON Web Token（`eyJ...` 开头、两段点号分隔）擦成 `<JWT>`。

**要点**：
1. 规则要**幂等**（跑两次结果一样）
2. 要能命中出现在句子中间的 JWT：`token=eyJhbGciOi...` → 全部擦掉
3. 写完用下面这段测试，全部应为 `True`：

```python
import report_core as rc
t = "token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhbGljZSJ9.abc123"
assert "eyJ" not in rc.redact_text(t)
assert rc.redact_text(rc.redact_text(t)) == rc.redact_text(t)
# 边界：不要误伤普通文本
assert rc.redact_text("see eyJx") == "see eyJx"   # 段落数不足，不该命中
```

<details>
<summary>参考答案（点开）</summary>

```python
(re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"), "<JWT>"),
```

放在 `Bearer` 规则**之前**：因为 JWT 常出现在 `Bearer eyJ...` 里，
先按结构整体擦掉，比依赖前一条规则"吃到行尾"更精确
（行尾规则会把后面的 Log-Id 之类也一起吃掉）。

</details>

### 练习 3：生成"本次新增 / 本次已修复"对比（★★☆）

**要求**：写一个脚本，读入两份 findings JSON（`old` / `new`），
输出三行：新增 N 条、已修复 M 条、未变 K 条，并列出新增的 rule_id。

**要点**：
1. 用 `Report.model()` 拿 id 集合，别自己拼哈希
2. 用集合运算：`new_ids - old_ids` / `old_ids - new_ids` / 交集
3. 输出要稳定排序（否则每次跑顺序不同，又回到了不确定性问题）

<details>
<summary>参考答案（点开）</summary>

```python
from report_core import Report, Finding
import json

def ids_of(path):
    raw = json.load(open(path, encoding="utf-8"))
    items = raw["findings"] if isinstance(raw, dict) else raw
    r = Report(title="t", scope="s", generated_at="fixed")
    for it in items:
        r.add(Finding(rule_id=it["rule_id"], title=it["title"],
                      severity=it["severity"], target=it["target"],
                      reason=it["reason"], confidence=it.get("confidence", "high")))
    return {f["id"]: f["rule_id"] for f in r.model()["findings"]}

old, new = ids_of("old.json"), ids_of("new.json")
added = sorted(new[i] for i in set(new) - set(old))
fixed = sorted(old[i] for i in set(old) - set(new))
same  = len(set(old) & set(new))
print(f"新增 {len(added)} 条：{added}")
print(f"已修复 {len(fixed)} 条：{fixed}")
print(f"未变 {same} 条")
```

注意：这一题的答案能成立，完全依赖前一天做的"稳定 id"设计。
如果 id 用 UUID，`set(new) - set(old)` 会永远等于全部条目。

</details>

---

## 🚦 自检：如果你只记住一件事

> **报告不是"打印出来的东西"，它是审计的证据链。**
> 证据链要能被复核，而复核的前提是：**结果可复现**（确定性）、
> **秘密不外流**（脱敏）、**盲区不隐藏**（覆盖缺口）。
> 这三条都比"报告好不好看"重要得多。
