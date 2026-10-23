# Day 194 练习与验收清单

## 今日完成清单

- [ ] 读完 README 的"概念解释"与"原理深入"
- [ ] 跑通 `pipeline_lib.py --self-test`（应全部 ✅）
- [ ] 跑通 `01-risk-classifier.py --self-test` 与主程序，能解释规则基线为什么漏 57 条软封
- [ ] 跑通 `02-simhash-dedup.py`，能说出 bands=4 与 bands=8 的取舍
- [ ] 跑通 `03-pitfall-canonicalize.py`，能复述 419 个页面是怎么消失的
- [ ] 跑通 `04-pipeline-e2e.py`，确认两次入库行数一致
- [ ] 至少手改一处阈值（如 k、Jaccard、质量规则）并观察指标变化
- [ ] 记录一条自己跑出来的数字（不要抄 README）

## 实验复现（逐条可复制）

```bash
cd ~/code/Learn-Python/days/day-194-ai-data-pipeline/code

# 0. 公共库
python3 pipeline_lib.py --self-test

# 1. 风险分类器：规则 vs 模型 vs 泄漏
python3 01-risk-classifier.py --self-test
python3 01-risk-classifier.py

# 2. 去重：精确哈希 / SimHash 阈值 / 分桶 / 两阶段
python3 02-simhash-dedup.py --self-test
python3 02-simhash-dedup.py

# 3. 翻车复现：URL 规范化导致的数据丢失
python3 03-pitfall-canonicalize.py

# 4. 端到端管道
python3 04-pipeline-e2e.py --self-test
python3 04-pipeline-e2e.py --report /tmp/day194-report.json

# 5. 清理
rm -f /tmp/day194*.db /tmp/day194-report.json
find . -name __pycache__ -type d -exec rm -rf {} +
```

**验收标准（本机对照）**

| 脚本 | 应看到 | 允许偏差 |
|---|---|---|
| `01` | 规则 F1 0.551 / 模型 AUC 0.9299 / 阈值 0.34 | AUC ±0.02（切分随机性） |
| `02` | 精确召回 0.164 / 两阶段 P 1.000 R 0.853 | 候选对数量随语料版本变化 |
| `03` | 旧规则丢 419 页 / 新规则丢 0 页 | 应完全一致 |
| `04` | 两次入库行数相同；去重约 11.6% | ±2% |

注意：`01` 依赖 numpy，`01` 的交叉验证对照依赖 scikit-learn；
其余脚本纯标准库。没有 sklearn 时 `01` 会打印跳过提示，不影响主结论。

---

## 基础题

### 练习 1：把规则基线补强，看能不能追上模型

现在的规则是 `status in (403,429,503) or captcha or js_challenge`。
试着加入 `body_len < 8000` 和 `header_count < 5` 两条，然后跑 `01` 看 F1 变化。

要求：
1. 记录加规则前后的 precision / recall / F1（贴真实输出）
2. 解释为什么"规则越加越多"最终会撞上天花板

### 练习 2：换一个 k，画出你自己的阈值曲线

在 `02` 里把扫描区间改成 `k = 1..20`，把结果写成 CSV，
然后用任意工具画出 precision/recall 曲线（哪怕用 ASCII 柱状图）。

要求：
1. 找到你这台机器上 F1 最高的 k
2. 解释 k 从 12 涨到 15 时 precision 为什么断崖式下跌

### 练习 3：给质量门禁加一条规则

新增 `PRICE_SUSPICIOUS`：价格低于同类中位数的 1/10 时告警（不是拦截）。
要求：
1. 规则要能拿到"同类中位数"，说明数据从哪来
2. 写一个自检用例，证明它不会把正常促销价当异常

---

## 进阶题

### 练习 4：把去重改成"按长度分层阈值"

当前全语料统一 k=7。请实现：
- 长度 < 50 token → k=10
- 50–150 token → k=7
- > 150 token → k=5

要求：
1. 在 `02` 的语料上测 P/R/F1，与统一 k=7 对比
2. 说明为什么短文本要更大的 k（从"单 token 影响位数"角度解释）
3. 注意：`SimHashIndex.query` 会拒绝超过 `bands-1` 的 k，你需要调整 bands

### 练习 5：构造一个"幂等但错"的管道，并让 CI 抓住它

参考 `03` 的事故，自己设计一个类似的坑（例如：把商品名当唯一键、
把时间戳截断到天、把金额四舍五入到元），然后：
1. 证明重跑两次结果一致
2. 写一条断言（pytest 或 纯 Python `assert`）能在 CI 里失败
3. 说明这条断言依赖什么"黄金数据"，黄金数据怎么维护

### 练习 6（挑战）：给管道加一个 `--resume`

需求：管道中途崩溃后，重跑只处理未完成的批次。

要求：
1. 用 SQLite 记录 batch_id 与阶段状态
2. 保证 resume 后不重复入库、不重复写隔离区
3. 写自检：模拟在 S5 之后 kill，resume 后行数与一次性跑完一致
