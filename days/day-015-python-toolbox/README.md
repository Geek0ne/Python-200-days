# Day 015 - 阶段项目：Python 工具箱 🧰

## 项目概述

**Python 工具箱** 是 Learn-Python 系列 Phase 1（Day 001-014）的综合实战项目。

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
days/day-015-python-toolbox/
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
cd days/day-015-python-toolbox/code

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
2. `word_frequency()` 如果处理非常大的文件（GB 级别），该如何优化？
3. 对于 `analyze_csv()`，如何处理包含缺失值的 CSV 文件？
4. `classify_files()` 中如果目标文件夹已经存在同名文件，如何避免数据覆盖？
5. 比较模块中的函数使用 `sample=True` 和 `sample=False` 有什么区别？何时使用哪种？
6. 如果要将 `pytools` 发布到 PyPI，需要做哪些准备工作？
7. 如何在交互式菜单中支持 Tab 补全和历史记录？

---

> **提示：** 每个模块的代码都包含详细的类型注解、文档字符串和错误处理。建议先尝试自己实现，再对比参考实现。
