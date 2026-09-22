# Day 164 完成清单 · 安全审计工具箱（三）：代理中间人 + 流量分析

> 用法：**先自己跑，再对照打勾**。打不上的勾就是今天没掌握的部分。
> 所有命令都在 `days/day-164-安全审计工具箱-part3/code/` 下执行。

---

## ✅ 一、完成清单（照着打勾）

### 概念与原理（读 `README.md`）

- [ ] 能说清"资产面 / 漏洞面 / 流量面"三者的区别，
      并各举一个"只有它才能回答"的问题
- [ ] 能说清**正向代理**与**反向代理**的立场差异，
      以及为什么审计要用正向代理
- [ ] 能说清"绝对 URI 形式"与"源站形式"两种请求行，
      以及为什么门禁要校验 **request-target 的主机**而不是 `Host` 头
- [ ] 能说清 `CONNECT` 之后代理"能看见什么 / 看不见什么"（各三项）
- [ ] 能解释**为什么不去解密**（两条路各是什么性质）
- [ ] 能说清**逐跳头**与端到端头的区别，并说出不剔除的三个后果
- [ ] 能解释代理为什么主动去掉 `Accept-Encoding`，以及它的**两项代价**
- [ ] 能说清"**先脱敏，再检测**"的原理：检测靠哪两个**结构信号**工作
- [ ] 能解释值指纹为什么保留（`sha256 前 8 位` 的两个用途）
- [ ] 能说清 **PII 擦除**与 **PII 检测**为什么必须分开
- [ ] 能说清**两层覆盖率**（流量层 / 业务层）各抓什么盲区
- [ ] 能解释为什么退出码 `4` 的优先级高于 `3`
- [ ] 能说清"优先级 = 严重度 × 置信度"为什么比"只看严重度"更诚实

### 代码与实测（在 `code/` 下跑）

- [ ] `python3 mitm_core.py --self-test` 输出 `SELF-TEST OK`
- [ ] `python3 01-flow-capture.py` 跑通，档案里出现 14 条 flow
- [ ] 亲眼确认档案里的 `request_body` **不含明文口令**，但 `note` 记着
      "命中过 password"（这是今天的核心设计）
- [ ] `python3 02-flow-analyze.py` 看到 34 条发现，且退出码打印为 `4`
- [ ] `python3 02-flow-analyze.py` 的**四个踩坑演示**全部看懂，
      能不看注释复述每个坑的现象 → 根因 → 教训
- [ ] `python3 03-traffic-audit-cli.py --tag demo` 产出 JSON + Markdown 两个报告
- [ ] `python3 03-traffic-audit-cli.py --capture flows.example.jsonl --quiet`
      退出码为 `4`，并能解释"流量层 100% 为什么还是 4"
- [ ] 手工构造一份含越界主机的档案，确认 CLI 给出退出码 `2` 并拒绝出结论
- [ ] 跑一遍 README §7 的"防泄密验证"脚本，全部输出 `✅ 无明文`

### 工程习惯

- [ ] 能说清"改完脱敏逻辑要跑什么来防回归"（答案：自检第 ② 组断言 + 全文扫描）
- [ ] 能说清"为什么 `AuditProxy` 对 `0.0.0.0` 是硬拒绝而不是警告"
- [ ] 主动**没有**对任何非本人拥有/非授权的目标发起过请求

---

## 📝 二、基础练习题（3 道）

### 练习 1：读档案，找出"看得见"与"看不见"的边界（观察题）

```bash
cd days/day-164-安全审计工具箱-part3/code
python3 01-flow-capture.py > /dev/null
python3 - <<'EOF'
import json
rows = [json.loads(l) for l in open("out/day164-basic-flows.jsonl", encoding="utf-8")]
for r in rows:
    print(f"{r['fid']}  {r['method']:<7} inspected={str(r['inspected']):<5} "
          f"status={r['response_status']:<4} url={r['url']}")
EOF
```

**问题**：

1. 哪一条 flow 的 `inspected` 是 `False`？它的 `method` 是什么？
2. 它的 `response_body` 和 `request_body` 分别是什么？为什么？
3. `coverage_percent` 算出多少？如果这条 flow 不存在，覆盖率会变成多少？

**验收标准**：能用一句话说清"`inspected=False` 意味着**没有结论**，
而不是**没有问题**"，并说出它会把退出码推到哪个值。

---

### 练习 2：只加一条规则，并解释它的代价

给 `FlowAnalyzer` 加一条 **`R16 http-method-over-plaintext-header`**：
当 `scheme == "http"` 且请求头里出现 `X-API-Key` 时报告一条 `high` 发现。

```python
# 在 FlowAnalyzer._analyze_one 里找位置插入（参考 R3 的写法）
```

**问题**：

1. 为什么这条规则要单独加，而不是直接放进 `SENSITIVE_KEYS`？
   *提示：`SENSITIVE_KEYS` 管的是"值是否脱敏"，规则管的是"这件事是不是问题"。*
2. 加完之后 `--self-test` 会不会失败？为什么？
   *提示：靶场里有没有端点在明文连接上发 `X-API-Key`？*
3. 如果要让自检通过，你会改靶场还是改断言？两个选择各自的含义是什么？

**验收标准**：能说清"**新增检测规则**"与"**新增脱敏字段**"是两件不同的事，
且能说出为什么改动规则时**必须**同步考虑靶场/断言。

---

### 练习 3：手算一次优先级（算术题）

现有三条发现：

| 规则 | 严重度 | 置信度 |
|---|---|---|
| A `cleartext-credential` | high | 0.95 |
| B `tls-tunnel-uninspected` | medium | 1.00 |
| C `suspected-time-based-sqli`（流量层推测） | high | 0.30 |

**问题**：

1. 分别算出三条的 `priority` 与 `level`
2. 按优先级排序，并说明 **C 为什么排在 A 之后**——尽管它俩严重度相同
3. 如果 C 的置信度被提到 0.80，排序会怎么变？这次变化说明了什么？

**验收标准**：能说清"**严重但很可能假阳性**的发现必须排在
**不严重但确定**的发现之后"，并说出理由（否则运维会不再读报告）。

---

## 🔍 三、自检命令（一键跑完）

```bash
cd days/day-164-安全审计工具箱-part3/code

# 1) 引擎自检（7 组断言，含"档案不得含明文"这条硬线）
python3 mitm_core.py --self-test                        # 期望 SELF-TEST OK

# 2) 基础闭环
python3 01-flow-capture.py | tail -15

# 3) 规则引擎 + 四个踩坑复现
python3 02-flow-analyze.py --no-pitfalls | tail -15

# 4) CLI 三种模式的退出码
python3 03-traffic-audit-cli.py --tag verify           > /dev/null; echo "auto      exit=$?"   # 4
python3 03-traffic-audit-cli.py --capture flows.example.jsonl --quiet >/dev/null; echo "fixture   exit=$?"  # 4

# 5) 防泄密全文扫描（应全部 ✅）
python3 - <<'EOF'
import json, pathlib
BAD = ["Sup3rSecret!", "tk_live_164_fake", "sk_live_164_FAKE_NOT_REAL", "13800138000"]
for p in sorted(pathlib.Path("out").glob("*.jsonl")):
    blob = p.read_text(encoding="utf-8")
    hits = [b for b in BAD if b in blob]
    print(f"{p.name}: {'❌ ' + str(hits) if hits else '✅ 无明文'}")
EOF
```

---

## 📌 四、今日关键结论（背下来）

1. **流量面给的是事实，前两面给的是推断。**
   事实不需要争论，所以它在报告里最站得住脚。

2. **`CONNECT` 之后代理是哑管子。**
   能看见 host:port、字节数、时间；看不见路径、头、体。
   不伪造证书、不降级 TLS——**"看不见"必须如实记账**。

3. **"没看" ≠ "没问题"。**
   这是整份报告诚实性的基准线，也是退出码 `4` 存在的唯一理由。

4. **逐跳头必须剔除。** 不剔除会污染两段连接的状态，
   严重时构成请求走私（request smuggling）的土壤。

5. **先脱敏，再检测。** 检测靠"字段名 + 指纹标记"两个**结构信号**工作，
   全程不需要看到明文。脱敏是唯一入口，不是事后补救。

6. **PII 擦除与 PII 检测必须分开。**
   擦掉就再也扫不到——所以必须在擦除的**同一时刻**记下类别
   （`flow.pii_labels`）。

7. **覆盖率是两层的。**
   流量层（内容看得见多少）+ 业务层（清单端点出现在流量里的比例）。
   只看第一层会得到"100% 覆盖"的假象。

8. **优先级 = 严重度 × 置信度。**
   报告的价值在"被读"，不在"条目多"。降噪是为了让人继续读。

9. **退出码的优先级顺序 = 谁该被最先通知。**
   `2` 找流程、`4` 找运维、`3` 找开发、`0` 才能自动通过。

10. **五个真实 bug 的共性：假设当成了事实。**
    ① 框架默认行为 ② 编码后字面量 ③ 同源数据漏脱敏
    ④ 破坏性操作与检测的顺序 ⑤ 端口漂移造成的假盲区。
    **对策：把假设变成断言。**

---
