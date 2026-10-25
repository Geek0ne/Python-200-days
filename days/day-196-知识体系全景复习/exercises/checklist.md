# Day 196 练习与检查清单

> 所有命令都可直接复制执行。工作目录：
> `cd ~/code/Learn-Python/days/day-196-知识体系全景复习/code`

## 一、今日完成清单

- [ ] 能说清「存储强度」与「提取强度」的区别，并各举一个自己的例子
- [ ] 能手算 SM-2 的间隔序列（q=5 连续 4 次：1 → 6 → 16 → 45）
- [ ] 能解释 EF 为什么要有 1.3 的下限（写出 EF 无限下降时的后果）
- [ ] 能解释为什么间隔要乘法增长而不是加法
- [ ] 跑通 `01-knowledge-map.py --self-test` 与真实扫描
- [ ] 跑通 `02-spaced-repetition.py --self-test` 与 `--demo`
- [ ] 跑通 `03-review-planner.py --dry-run`，并看懂 Day14 为什么是空的
- [ ] 跑通 `04-scan-benchmark.py --repeat 5`，能解释四个数字的差异
- [ ] 能解释「bytes.count 少算 19 行」的原因
- [ ] 复述两个翻车实验的根因（计时器边界 / 写死的日期）

## 二、基础练习

### 练习 1：手算 SM-2

一张卡初始 EF=2.5，连续 5 次 q=4。写出每次的 interval、EF、due（从 2026-11-01 起）。

要求：先手算，再用下面的代码验证。

```python
import importlib.util, sys
from datetime import date

# 文件名带连字符，不能直接 import；用 spec 加载并注册到 sys.modules
spec = importlib.util.spec_from_file_location("sr", "02-spaced-repetition.py")
sr = importlib.util.module_from_spec(spec)
sys.modules["sr"] = sr          # 不注册的话 @dataclass 会崩
spec.loader.exec_module(sr)

card = sr.Card(topic="demo")
day = date(2026, 11, 1)
for i in range(5):
    card.review(4, day)
    print(i + 1, card.interval, round(card.ease, 2), card.due)
    day = card.due
```

> 提示：q=4 时 ΔEF = 0，所以 EF 一直是 2.5；间隔序列是 1, 6, 15, 38, 95。

> 实测踩坑：漏掉 `sys.modules["sr"] = sr` 时，Python 3.12 会在 `@dataclass` 处抛
> `AttributeError: 'NoneType' object has no attribute '__dict__'`。
> 原因是 dataclass 需要回查 `sys.modules[cls.__module__]`，而手工加载的模块默认不在里面。

### 练习 2：统计口径

用三种写法统计本课程目录（`days/day-196-*`，不含子目录以外的文件）的行数，
解释为什么可能不同。

```bash
find ../../../day-196-* -name '*.py' | xargs wc -l | tail -1
python3 -c "
from pathlib import Path
root = next(Path('../../..').glob('day-196-*'))
files = list(root.rglob('*.py'))
print('bytes:', sum(p.read_bytes().count(b'\n') for p in files))
print('split:', sum(len(p.read_text(encoding='utf-8').splitlines()) for p in files))
"
```

问题：两个数字差多少？差在哪个文件？为什么？

### 练习 3：把地图导出成 JSON

```bash
python3 01-knowledge-map.py --json /tmp/map.json
python3 - <<'PY'
import json
data = json.load(open('/tmp/map.json'))
print(data['total_days'], data['total_py_files'], data['total_py_lines'])
top = sorted(data['days'], key=lambda d: d['py_lines'], reverse=True)[:3]
for d in top:
    print(d['day'], d['title'], d['py_lines'])
PY
```

要求：说出代码行数最多的 3 课，以及它们属于哪个阶段。

## 三、进阶挑战

### 练习 4：给 SM-2 加「提前复习」惩罚

真实场景：用户在到期前就点了复习。当前实现会直接按 q 评分并延长间隔，
这会让「手贱多点几次」的人把间隔刷到几百天。

任务：修改 `Card.review`，当 `today < self.due` 时，把 interval 增长改为
`max(1, round(interval * 0.5))`（提前复习不增加间隔），并补一条 self-test。

验收：

```python
c = sr.Card(topic="x", interval=10, reps=3, due=date(2026, 1, 11), last_review=date(2026, 1, 1))
c.review(5, date(2026, 1, 5))   # 提前 6 天
assert c.interval <= 5, c.interval
```

### 练习 5：让计划填满 14 天（并说明代价）

当前 `03-review-planner.py` 的 Day14 为空。实现任意一种填充策略：

1. 缩短最大间隔（8 → 4 天）；
2. 提高每日槽位（4 → 6）；
3. 增加「整章自测」虚拟单元。

要求：
- 三种方案各跑一次，记录总槽位与每单元次数；
- 用一张表对比「覆盖率 vs 单日负担」；
- 明确写出你选了哪个、牺牲了什么。

### 练习 6（选做）：用真实自测替换模拟评分

把 `02-spaced-repetition.py` 的模拟评分换成终端交互：

```text
[P10 网络安全开发] Day 146 内容，能不看资料说出 SQLi 三种判定吗？(0-5):
```

要求：
- 输入直接落库（sqlite 文件而非 `:memory:`）；
- Ctrl-C 退出时保存进度；
- 第二天运行只出到期的卡。

## 四、验收命令（全部应通过）

```bash
cd ~/code/Learn-Python/days/day-196-知识体系全景复习/code
python3 01-knowledge-map.py --self-test
python3 02-spaced-repetition.py --self-test
python3 03-review-planner.py --self-test
python3 04-scan-benchmark.py --self-test
python3 01-knowledge-map.py --json /tmp/map.json >/dev/null && test -s /tmp/map.json && echo "JSON OK"
python3 -m py_compile 01-knowledge-map.py 02-spaced-repetition.py 03-review-planner.py 04-scan-benchmark.py && echo "compile OK"
```

## 五、自评表

| 项 | 会 | 模糊 | 不会 |
|---|---|---|---|
| 解释 R=exp(-t/S) 的三个变量 | ☐ | ☐ | ☐ |
| 手算 SM-2 间隔 | ☐ | ☐ | ☐ |
| 解释 EF 下限 1.3 | ☐ | ☐ | ☐ |
| 解释为什么用乘法 | ☐ | ☐ | ☐ |
| 说出 rglob 与 scandir 的实测差距 | ☐ | ☐ | ☐ |
| 解释 19 行差异 | ☐ | ☐ | ☐ |
| 复述两个翻车根因 | ☐ | ☐ | ☐ |

「模糊」超过 3 项：明天开始前先重跑一遍本课实验，不要直接进 Day 197。
