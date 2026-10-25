# Day 196 代码说明

四个脚本全部零第三方依赖、可离线自证。Python 3.10+（用了 `X | None` 注解与
`dataclass`，运行时不需要 `from __future__` 之外的东西）。

## 运行顺序

```bash
cd ~/code/Learn-Python/days/day-196-知识体系全景复习/code

# 1. 地图：先知道有什么
python3 01-knowledge-map.py --self-test
python3 01-knowledge-map.py
python3 01-knowledge-map.py --mermaid > /tmp/map.mmd
python3 01-knowledge-map.py --json /tmp/map.json

# 2. 排期算法：验证 SM-2 数值
python3 02-spaced-repetition.py --self-test
python3 02-spaced-repetition.py --demo

# 3. 计划：把权重变成日程
python3 03-review-planner.py --self-test
python3 03-review-planner.py --dry-run
python3 03-review-planner.py --write /tmp/plan.md

# 4. 基准：知道自己测的准不准
python3 04-scan-benchmark.py --self-test
python3 04-scan-benchmark.py --repeat 5
```

## 实测数字（2026-10-26 06:00–06:40 CST）

| 指标 | 值 | 来源 |
|---|---:|---|
| 扫描课程数 | 196 | 01 |
| .py 文件 | 712 | 01 / 04 一致 |
| 代码行数 | 201,558 | `bytes.count` 口径 |
| README 字符 | 2,830,754 | 01 |
| 冷缓存扫描 | 535.3 ms | 01 首次运行 |
| 热缓存扫描 | 99.6 ms | 01 第二次 |
| sqlite 写入 1 万卡 | 46.4 ms | 02 --demo |
| sqlite 查询 3,673 条 | 4.24 ms | 02 --demo |
| 最快扫描方式 | 30.3 ms（scandir） | 04 |
| 最慢扫描方式 | 51.4 ms（glob） | 04 |

## 参数约定

| 参数 | 默认 | 说明 |
|---|---|---|
| `--root` | `~/code/Learn-Python` | 可用 `LEARN_PYTHON_ROOT` 环境变量覆盖 |
| `--repeat` | 5 | 基准重复次数，取中位数 |
| 每日槽位 | 4 | 03 的模块常量 `SLOTS_PER_DAY` |
| 计划窗口 | 14 天 | 03 的 `HORIZON` |
| 读者权重系数 | 50 字符 = 1 行 | 03 的 `Unit.weight` |

## 已知边界

- 01 只认 `day-\d{3}-` 目录；改名会直接漏统计（不会报错，这是设计取舍）。
- 02 的 `--demo` 是模拟，不能当作真实留存率引用。
- 03 的 Day14 可能是空的：指数间隔推到窗口之外，属于预期行为。
- 04 的数字强依赖页缓存；跨机器比较前先固定 `--repeat` 与冷热状态。
