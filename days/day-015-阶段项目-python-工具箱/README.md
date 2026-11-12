# Day 015 — 阶段项目：Python 工具箱

## 项目概述

**Python 工具箱** 是 Python-200-days 系列 Phase 1（Day 001-014）的综合实战项目。

本项目的核心理念是：**用 Python 解决日常工作中的真实问题**。我们构建了一个模块化的工具包 `pytools`，包含文件管理、文本处理、数据统计三大功能模块，并提供了友好的命令行和交互式操作界面。

通过这个项目，你将综合运用以下知识：
- ✅ 变量与数据类型
- ✅ 字符串处理与正则表达式
- ✅ 数字运算与布尔逻辑
- ✅ 条件判断与分支控制
- ✅ 列表、元组、字典、集合
- ✅ 循环与控制流
- ✅ 函数定义、参数传递、Lambda
- ✅ 作用域与命名空间
- ✅ 模块化设计与包结构
- ✅ argparse 命令行解析

## 🏗️ 包结构

```
days/day-015-阶段项目-python-工具箱/
├── README.md                 # 本文件 — 项目说明
├── code/
│   └── pytools/              # Python 工具包
│       ├── __init__.py       # 包入口，统一暴露 API
│       ├── file_tools.py     # 文件管理工具
│       ├── text_tools.py     # 文本处理工具
│       ├── stats_tools.py    # 数据统计工具
│       └── main.py           # 命令行入口与交互菜单
├── diagrams/
│   └── README.md             # 架构示意图（Mermaid/ASCII）
└── exercises/
    └── checklist.md          # 完成清单与练习题
```

## 📦 模块说明

### 1️⃣ 文件管理工具 (`file_tools.py`)

提供日常文件操作的便捷函数：

| 功能 | 函数 | 说明 |
|------|------|------|
| 批量重命名 | `batch_rename()` | 支持添加前缀/后缀、替换文本、序号编号 |
| 文件查找 | `find_files()` | 按扩展名、最小/最大大小、日期范围过滤 |
| 目录大小统计 | `dir_size_stats()` | 统计目录总大小、子目录大小分布 |
| 文件分类整理 | `classify_files()` | 自动按扩展名将文件移至对应类型文件夹 |

**用法示例：**
```python
from pytools.file_tools import batch_rename, find_files, classify_files

# 给所有 .txt 文件添加前缀
batch_rename("/path/to/files", prefix="backup_", ext=".txt")

# 查找大于 1MB 的图片文件
images = find_files("/path/to/files", ext=(".jpg", ".png"), min_size=1024*1024)

# 按扩展名分类整理文件
classify_files("/path/to/files")
```

### 2️⃣ 文本处理工具 (`text_tools.py`)

提供文本分析与处理功能：

| 功能 | 函数 | 说明 |
|------|------|------|
| 词频统计 | `word_frequency()` | 统计文本词频，支持排除停用词 |
| CSV 分析 | `analyze_csv()` | 读取 CSV 并返回基本统计信息 |
| 文本搜索 | `search_text()` | 支持正则匹配和普通字符串匹配 |
| 文本格式转换 | `convert_text()` | 大小写转换、换行符转换、编码转换 |

**用法示例：**
```python
from pytools.text_tools import word_frequency, analyze_csv, search_text

# 词频统计（排除常见停用词）
wf = word_frequency("sample.txt", ignore_stopwords=True)

# CSV 分析
stats = analyze_csv("data.csv", column="score")

# 文本搜索（正则）
results = search_text("document.txt", r"\bPython\b", use_regex=True)
```

### 3️⃣ 数据统计工具 (`stats_tools.py`)

提供基础统计分析功能：

| 功能 | 函数 | 说明 |
|------|------|------|
| 集中趋势 | `mean()`, `median()`, `mode()` | 均值、中位数、众数 |
| 离散程度 | `variance()`, `std_dev()` | 方差、标准差（支持样本/总体） |
| 分布统计 | `frequency_distribution()` | 直方图分箱与频数统计 |
| 排序统计 | `sort_and_dedup()` | 排序并去重，返回统计信息 |
| 百分比 | `percentiles()` | 计算任意分位数 |
| 综合报告 | `summary_report()` | 一键生成统计分析报告 |

**用法示例：**
```python
from pytools.stats_tools import *

data = [12, 15, 18, 22, 22, 25, 30, 35, 42, 55]
print(f"均值: {mean(data):.2f}")
print(f"中位数: {median(data)}")
print(f"众数: {mode(data)}")
print(f"标准差: {std_dev(data, sample=True):.2f}")
print(summary_report(data))
```

### 4️⃣ 主程序 (`main.py`)

提供两种使用模式：

**命令行模式：** 通过 `argparse` 解析参数，直接调用各模块功能：
```bash
# 文件管理
python -m pytools.main file find /path --ext .py
python -m pytools.main file rename /path --prefix "new_"

# 文本处理
python -m pytools.main text freq sample.txt --top 10

# 数据统计
python -m pytools.main stats analyze data.json
```

**交互式菜单模式：** 提供友好的 TUI 菜单界面：
```bash
python -m pytools.main
# 或
python -m pytools.main interactive
```

## 🚀 快速开始

```bash
# 进入项目目录
cd days/day-015-阶段项目-python-工具箱/code

# 以交互模式启动
python -m pytools.main

# 或直接运行
python -m pytools.main interactive
```

### 测试数据

也可以使用 `exercises/` 下的测试文件来验证各模块功能。

## 💡 扩展思路

完成本项目后，你可以尝试以下扩展方向：

1. **撤销功能** — 为 `file_tools.py` 添加操作日志和回滚功能
2. **GUI 界面** — 使用 `tkinter` 或 `PyQt` 添加图形界面
3. **配置文件** — 支持通过 YAML/JSON 配置文件自定义工具行为
4. **插件系统** — 设计插件接口，允许第三方扩展工具模块
5. **异步支持** — 使用 `asyncio` 实现异步文件处理
6. **日志系统** — 集成 `logging` 模块，记录操作历史

## 🤔 思考题

1. 在 `batch_rename()` 中，如何处理文件名冲突（目标文件名已存在）？

**参考答案**

现有代码已有一道防线：内部 `_safe_rename(src, dst, overwrite=False)` 在重命名前检查目标是否存在——默认（`overwrite=False`）遇到目标已存在就抛 `FileExistsError_`，`batch_rename` 捕获后把该文件记进 `errors` 并计入 `skipped`，**绝不会静默覆盖**；只有显式传 `overwrite=True` 才允许覆盖。配合 `dry_run=True` 可以先预览全部改名、确认无冲突再真正执行。

如果希望"冲突时自动避开"而不是"跳过"，可以借鉴 `classify_files` 的思路：给目标名追加序号。核心逻辑如下（可运行）：

```python
import os
import tempfile

def unique_path(dst):
    """若目标已存在，自动追加 _1、_2… 直到不冲突"""
    if not os.path.exists(dst):
        return dst
    base, ext = os.path.splitext(dst)
    i = 1
    while os.path.exists(f"{base}_{i}{ext}"):
        i += 1
    return f"{base}_{i}{ext}"

# 演示：目录里已有 report.txt，再把 data.txt 重命名为 report.txt
d = tempfile.mkdtemp()
open(os.path.join(d, "report.txt"), "w").close()      # 已存在的目标
src = os.path.join(d, "data.txt")
open(src, "w").close()
target = unique_path(os.path.join(d, "report.txt"))
os.rename(src, target)
print(sorted(os.listdir(d)))   # ['report.txt', 'report_1.txt']
```

预期输出：`['report.txt', 'report_1.txt']`——原有 report.txt 保留，新文件自动变成 report_1.txt。

⚠️ 注意："覆盖"这条路径有平台差异——Windows 上 `os.rename` 在目标已存在时会抛 `FileExistsError`（已实测），Unix 才会静默覆盖。要跨平台真正覆盖，应改用 `os.replace(src, dst)`。

2. `word_frequency()` 如果处理非常大的文件（GB 级别），该如何优化？

**参考答案**

瓶颈在于现有实现 `text = f.read()` **一次性把整个文件读进内存**，随后 `text.lower()`、`re.findall` 又生成同样巨大的词列表——GB 级文件会直接撑爆内存。优化核心是**流式处理**：逐行读、边读边统计，内存里只留"一行 + 词频表"。

- 用 `for line in f` 逐行迭代，不要 `f.read()`。
- 用 `re.finditer` 代替 `re.findall`，避免一次性生成完整词列表。
- 用 `Counter` 增量更新（`counter[word] += 1`），内存只取决于**不同词的数量**，与文件大小无关。
- 若只要 top_n 且不同词也极多，可考虑近似算法（Count-Min Sketch、Space-Saving）或多进程分片 map-reduce。

流式实现（可运行）：

```python
import os
import re
import tempfile
from collections import Counter

def word_frequency_stream(filepath, top_n=10):
    counter = Counter()
    pattern = re.compile(r"[a-z]+|[\u4e00-\u9fff]+")
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:                      # 逐行读取，内存只占一行
            for m in pattern.finditer(line.lower()):
                counter[m.group()] += 1     # 增量更新计数
    return counter.most_common(top_n)

# 造一个小文件演示
d = tempfile.mkdtemp()
p = os.path.join(d, "big.txt")
with open(p, "w", encoding="utf-8") as f:
    f.write("hello world hello\npython world hello\n")
print(word_frequency_stream(p, top_n=2))
```

预期输出：`[('hello', 3), ('world', 2)]`。无论文件多大，内存占用都约等于"一行文本 + 词频字典"。

💡 提示：原版"整体小写化再分词"可改成"每行小写化"，效果等价；超大文件还可在 open 时指定 `errors="ignore"`，避免个别坏字节中断整个统计。

3. 对于 `analyze_csv()`，如何处理包含缺失值的 CSV 文件？

**参考答案**

现有代码已经处理了"空缺失值"：`_analyze_column` 用 `v.strip()` 过滤掉空字符串和纯空白，把它们计入 `missing`，数值统计（mean/min/max）只在非空值上计算——所以空单元格不会报错，也不会污染均值。

但它只认"空字符串"。真实 CSV 常用 `NA`、`N/A`、`null`、`-`、`?` 等哨兵标记表示缺失，现有实现会把这些当文本（导致整列被判为 text 而非 numeric）。扩展办法是统一把这些标记识别为缺失：

```python
MISSING_TOKENS = {"", "na", "n/a", "null", "none", "-", "?"}

def clean_values(values):
    """把各种缺失标记统一识别为缺失，返回 (有效值, 缺失数)"""
    valid = [v for v in values if v.strip().lower() not in MISSING_TOKENS]
    return valid, len(values) - len(valid)

vals = ["10", "", "20", "NA", "30", "null", " "]
valid, missing = clean_values(vals)
print(valid)    # ['10', '20', '30']
print(missing)  # 4
```

预期输出：`['10', '20', '30']` 和 `4`。这样该列仍能被正确识别为数值并参与统计。

识别出缺失后，常见处理策略（按业务选择）：

- **删除**：丢弃含缺失的行（适合缺失很少且随机时）。
- **填补**：数值列用均值/中位数、分类列用众数填充，时间序列可用前向/后向填充。
- **标记**：额外加一列"是否缺失"，保留"这里曾经缺失"的信息。

⚠️ 注意：填补会改变数据分布，均值对异常值敏感，偏态数据用中位数更稳妥；删除前要确认缺失不是"系统性"的（如某类群体全缺失），否则会引入偏差。

4. `classify_files()` 中如果目标文件夹已经存在同名文件，如何避免数据覆盖？

**参考答案**

现有代码**已经避免了覆盖**：移动前检查 `os.path.exists(dst)`，若目标已存在，就用 `while` 循环依次追加 `_1`、`_2`… 直到找到不冲突的名字，再 `shutil.move`。因此同名文件会被并列保存，不会丢数据。核心逻辑如下（可运行）：

```python
import os
import tempfile

def resolve_collision(category_dir, filename):
    """目标已存在时追加序号，绝不覆盖"""
    dst = os.path.join(category_dir, filename)
    if not os.path.exists(dst):
        return dst
    name, ext = os.path.splitext(filename)
    i = 1
    while os.path.exists(dst):
        dst = os.path.join(category_dir, f"{name}_{i}{ext}")
        i += 1
    return dst

# 演示：images 目录里已有 photo.png
d = tempfile.mkdtemp()
cat = os.path.join(d, "images")
os.makedirs(cat)
open(os.path.join(cat, "photo.png"), "w").close()
print(os.path.basename(resolve_collision(cat, "photo.png")))  # photo_1.png
open(os.path.join(cat, "photo_1.png"), "w").close()
print(os.path.basename(resolve_collision(cat, "photo.png")))  # photo_2.png
```

预期输出：`photo_1.png` 和 `photo_2.png`——每冲突一次序号自动加一。

若想更智能，可做**内容去重**：用 `hashlib` 计算两个文件的 SHA-256，内容完全相同就跳过移动（或删除重复项），避免同一文件留多份。对"既要绝不丢、又不要重复"的场景，还可先移到隔离目录交由人工确认。

💡 提示：与第 1 题的区别——`batch_rename` 默认冲突时"跳过并报告"，`classify_files` 则"自动追加序号"；前者更保守、后者更自动化，可按场景选择。

5. 比较模块中的函数使用 `sample=True` 和 `sample=False` 有什么区别？何时使用哪种？

**参考答案**

区别在**分母**：`sample=True` 算样本方差，除以 `n-1`；`sample=False` 算总体方差，除以 `n`。标准差是方差的平方根，随之同理。

为什么样本要除以 `n-1`？因为你只有样本时，是用样本均值去估计均值的，数据"围绕自己的均值"波动，离差平方和会系统性地小于围绕真实总体均值的波动；除以 `n` 会**低估**总体方差。除以 `n-1`（称贝塞尔校正）能让估计无偏——少的那个"自由度"是因为估计均值用掉了一个约束。

何时用哪种：

- **sample=True（默认）**：数据只是从更大总体中抽出的样本——绝大多数实际分析（抽样调查、实验测量）都属于这种。
- **sample=False**：你手里就是总体的**全部**个体（如全班每个人的成绩），只是描述这批数据本身。

验证（与模块 `variance` 实现一致）：

```python
def variance(data, sample=True):
    n = len(data)
    avg = sum(data) / n
    denom = n - 1 if sample else n   # 样本除以 n-1，总体除以 n
    return sum((x - avg) ** 2 for x in data) / denom

data = [1, 2, 3, 4, 5]
print(variance(data, sample=True))    # 2.5
print(variance(data, sample=False))   # 2.0
```

预期输出：`2.5` 和 `2.0`。样本方差略大，正是 n-1 校正的效果。

⚠️ 注意：样本方差要求至少 2 个数据点（n=1 时 n-1 为 0），模块对此会抛 `StatsToolError`；n 越大两者差异越小，n 很大时几乎相等。

6. 如果要将 `pytools` 发布到 PyPI，需要做哪些准备工作？

**参考答案**

发布到 PyPI 大致分"准备元数据 → 构建 → 上传"三步：

1. **名称与结构**：先在 PyPI 搜索确认包名未被占用（`pytools` 很可能已被占，需改成唯一名，如 `yourname-pytools`）；项目已有 `__init__.py` 和清晰模块划分，结构达标。
2. **元数据与文档**：编写 `pyproject.toml`（现代标准，PEP 621），声明名称、版本、描述、readme、许可证、作者、`requires-python`、依赖等；再准备 `README.md`（作长描述）和 `LICENSE` 文件。最小示例：

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "yourname-pytools"
version = "0.1.0"
description = "Python 工具箱：文件管理 / 文本处理 / 数据统计"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}

[project.scripts]
pytools = "pytools.main:main"   # 安装后用户可直接用 pytools 命令
```

3. **构建**：`pip install build`，再 `python -m build`，会在 `dist/` 生成源码包（`.tar.gz`）和轮子（`.whl`）。
4. **检查与上传**：`pip install twine`，先 `twine check dist/*` 检查元数据；注册 PyPI 账号并创建 API token，再 `twine upload dist/*`。建议先用 TestPyPI 演练（`twine upload --repository testpypi dist/*`）。

⚠️ 注意：同一版本号只能上传一次，传错了只能升版本重发（不能覆盖）；`[project.scripts]` 能把现在的 `python -m pytools.main` 变成全局 `pytools` 命令，体验更好。上述构建/上传命令需联网与账号，属标准流程说明。

7. 如何在交互式菜单中支持 Tab 补全和历史记录？

**参考答案**

当前菜单用原生 `input()`，既没有 Tab 补全也没有历史。要加这两样，需借助终端行编辑库：

- **Unix/macOS**：标准库 `readline` 即可——`parse_and_bind("tab: complete")` 开启补全，`set_completer()` 注册补全器，历史由 readline 自动管理（可用 `read_history_file`/`write_history_file` 持久化）。
- **Windows**：没有 `readline`，需 `pip install pyreadline3`；想跨平台统一体验，用第三方 `prompt_toolkit` 更省心。

补全器的核心是一个可独立测试的纯函数（可运行）：

```python
COMMANDS = ["file", "text", "stats", "quit"]

def completer(text, state):
    matches = [c for c in COMMANDS if c.startswith(text)]
    return matches[state] if state < len(matches) else None

# readline 会以 state=0,1,2… 反复调用，取尽候选为止
print(completer("t", 0))    # text
print(completer("t", 1))    # None（没有更多候选）
print(completer("s", 0))    # stats

# 历史记录：每次输入后追加，↑/↓ 由 readline 管理
history = []
history.append("file find /tmp")
history.append("stats report")
print(history[-1])          # stats report（最近一条）
```

预期输出：四行依次为 `text`、`None`、`stats`、`stats report`。`completer` 返回匹配前缀的第 state 个候选，返回 `None` 表示"没有更多了"。

接线方式：Unix 下 `import readline` 后调用 `readline.parse_and_bind("tab: complete")` 与 `readline.set_completer(completer)`，之后的 `input()` 就支持 Tab 与 ↑↓ 历史；Windows 先装 `pyreadline3`。跨平台则用 `prompt_toolkit` 的 `PromptSession(history=FileHistory(...), completer=WordCompleter(COMMANDS))`，把 `input()` 换成 `session.prompt()`。这些依赖交互式终端与相应库，上面的核心补全逻辑已实跑验证。

💡 提示：本项目菜单是数字选择，补全在"输入文件路径"那一步最有价值——可换成路径补全器（prompt_toolkit 的 `PathCompleter`，或 readline 配合目录列举）。

---

> **提示：** 每个模块的代码都包含详细的类型注解、文档字符串和错误处理。建议先尝试自己实现，再对比参考实现。
