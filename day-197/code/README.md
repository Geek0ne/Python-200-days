# Day 197 代码运行说明

## 运行顺序

| 顺序 | 文件 | 作用 | 耗时 | 离线 |
|---|---|---|---|---|
| 1 | `01-algorithm-templates.py` | 9 类算法模板 + 25 条断言 | <1s | 是 |
| 2 | `02-python-interview-facts.py` | 12 条八股实测 + 25 条断言 | <1s | 是 |
| 3 | `03-mock-interview-scorer.py` | 12 题题库 + 四维评分 + 8 条校准 | <1s | 是 |
| 4 | `04-concurrency-and-memory.py` | GIL / IO / 内存基准 + 12 条断言 | self-test <1s，bench 约 5s | 是 |

依赖：**零第三方包**，仅标准库。Python 3.10+（实测 3.12.3）。
题库 `interview_bank.json` 必须与 `03` 放在同一目录。

## 常用命令

```bash
# 全部自检（推荐先跑这个）
for f in code/0*.py; do python3 "$f" --self-test || exit 1; done

# 算法模板速查 / 单题演示
python3 code/01-algorithm-templates.py
python3 code/01-algorithm-templates.py --demo n_queens

# 八股文实测
python3 code/02-python-interview-facts.py
python3 code/02-python-interview-facts.py --json

# 评分器
python3 code/03-mock-interview-scorer.py --list
python3 code/03-mock-interview-scorer.py --demo
python3 code/03-mock-interview-scorer.py --calibrate
python3 code/03-mock-interview-scorer.py --question py-gil --answer-file answer.txt

# 基准（数值随机器负载变化）
python3 code/04-concurrency-and-memory.py --bench
python3 code/04-concurrency-and-memory.py --bench --json
```

## 实测参数与结果（2026-10-27，4 vCPU / loadavg 5.31）

- 算法断言：25 项通过。
- 八股断言：25 项通过；dict vs list 查找 1220.6x；生成器峰值内存 0.5KB vs list 7835.5KB。
- 评分器：35 项断言通过；校准 8 条，及格线 60，准确率 100%，通过/未通过间隔 22.2。
- 并发：CPU 密集线程 0.57–0.77x（更慢），进程 1.46–2.09x；IO 密集线程 3.98x。
- 内存：`list(range(100000))` 容器口径 800,056B，真实峰值 3,991,952B，相差 4.99x。

> 基准只用于量级对比，不是性能承诺。宿主负载、CPU 配额、Python 版本都会改变绝对值。
