# Day 063 — CSV 与 Excel

## 概述

CSV（Comma-Separated Values，逗号分隔值）和 Excel（.xlsx/.xls）是最常见的数据表格格式。Python 的标准库和第三方库提供了强大的读写能力，是数据分析、报表生成、数据迁移的必备技能。

---

## 1. CSV 格式基础

### 1.1 概念

CSV 是一种简单的表格数据格式，每行代表一条记录，字段用逗号分隔。本质上是一个纯文本文件。

```
name,age,city
Alice,30,Beijing
Bob,25,Shanghai
Charlie,35,Shenzhen
```

**为什么需要掌握 CSV？**
- 几乎所有数据库和数据分析工具都支持 CSV 导入/导出
- 文件体积小，人类可读
- 跨平台、跨语言兼容性最好
- 是数据交换的"最低公共标准"

### 1.2 CSV 的"坑"（为什么不能直接用 split(",")？）

| 问题 | 示例 | 说明 |
|------|------|------|
| **字段内含逗号** | `"Alice, Inc.",30` | 需要引号包围 |
| **字段内含换行** | `"line1\nline2",30` | 跨行字段 |
| **字段内含引号** | `"He said ""Hi"""` | 引号转义 |
| **不同分隔符** | 制表符分隔的 TSV | 不一定是逗号 |
| **编码问题** | 中文 CSV vs Excel | UTF-8 BOM 问题 |
| **空值处理** | `,30` vs `"",30` | 空字符串 vs 缺失 |

```python
# ❌ 错误的做法：用 split(",")
line = 'Alice, "Bob, Inc.", 30'
fields = line.split(",")
# 结果: ['Alice', ' "Bob', ' Inc."', ' 30']  ← 错误！

# ✅ 正确的做法：使用 csv 模块
import csv
import io
reader = csv.reader(io.StringIO(line))
fields = next(reader)
# 结果: ['Alice', 'Bob, Inc.', ' 30']  ← 正确！
```

---

## 2. csv 模块详解

### 2.1 核心类

| 类/函数 | 说明 | 示例 |
|---------|------|------|
| `csv.reader` | 逐行读取 CSV | `reader = csv.reader(f)` |
| `csv.writer` | 逐行写入 CSV | `writer = csv.writer(f)` |
| `csv.DictReader` | 读取为字典列表（第一行做表头） | `reader = csv.DictReader(f)` |
| `csv.DictWriter` | 将字典写入 CSV | `writer = csv.DictWriter(f, fieldnames=...)` |
| `csv.Sniffer` | 自动检测 CSV 格式（分隔符、引号等） | `dialect = csv.Sniffer().sniff(sample)` |

### 2.2 方言（Dialect）系统

CSV 没有统一标准，不同系统使用不同的分隔符、引号规则。Python 用 Dialect 抽象这些差异：

```python
import csv

# 预定义方言
csv.excel          # Excel 风格（逗号分隔，双引号转义）
csv.excel_tab      # Excel 制表符分隔
csv.unix_dialect   # Unix 风格（换行符 \n）

# 自定义方言
csv.register_dialect('mydialect',
    delimiter='|',          # 分隔符
    quotechar='"',          # 引号字符
    quoting=csv.QUOTE_MINIMAL,  # 引用策略
    lineterminator='\n',    # 行终止符
    skipinitialspace=True,  # 跳过字段前导空格
    doublequote=True,       # 引号内双写转义
    escapechar=None         # 转义字符
)
```

**引用策略（quoting）：**

| 常量 | 值 | 行为 |
|------|-----|------|
| `csv.QUOTE_MINIMAL` | 0 | 仅在需要时加引号（默认） |
| `csv.QUOTE_ALL` | 1 | 所有字段加引号 |
| `csv.QUOTE_NONNUMERIC` | 2 | 非数字字段加引号 |
| `csv.QUOTE_NONE` | 3 | 不加引号，特殊字符用 escapechar |

### 2.3 API 速查

```python
import csv

# ─── 写 CSV ───

# 方式 1: csv.writer (逐行写入)
with open('data.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['name', 'age', 'city'])      # 写表头
    writer.writerows([                             # 批量写内容
        ['Alice', 30, 'Beijing'],
        ['Bob', 25, 'Shanghai'],
    ])

# 方式 2: DictWriter (写字典)
with open('data.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['name', 'age', 'city'])
    writer.writeheader()                          # 写表头
    writer.writerows([
        {'name': 'Alice', 'age': 30, 'city': 'Beijing'},
        {'name': 'Bob', 'age': 25, 'city': 'Shanghai'},
    ])

# ─── 读 CSV ───

# 方式 1: csv.reader (列表)
with open('data.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        print(row)  # ['name', 'age', 'city'] → ['Alice', '30', 'Beijing']

# 方式 2: DictReader (字典)
with open('data.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row['name'], row['age'])  # Alice 30

# ─── 自动检测 ───
with open('unknown.csv', 'r') as f:
    sample = f.read(1024)
    dialect = csv.Sniffer().sniff(sample)
    has_header = csv.Sniffer().has_header(sample)
    f.seek(0)
    reader = csv.reader(f, dialect)
```

---

## 3. Excel 文件处理（openpyxl）

### 3.1 概念

Excel 文件（.xlsx）是基于 Office Open XML 标准的二进制文件，本质上是一个 ZIP 包内含 XML 文件。

```
demo.xlsx (ZIP 包)
├── xl/
│   ├── workbook.xml       → 工作簿定义
│   ├── worksheets/
│   │   ├── sheet1.xml     → 工作表 1
│   │   └── sheet2.xml     → 工作表 2
│   ├── sharedStrings.xml  → 共享字符串表
│   └── styles.xml         → 样式定义
├── [Content_Types].xml
└── _rels/.rels
```

**安装：** `pip install openpyxl`

### 3.2 openpyxl 核心 API

```python
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference
from openpyxl.utils import get_column_letter

# ─── 创建工作簿 ───
wb = Workbook()
ws = wb.active
ws.title = "销售数据"

# ─── 写入数据 ───
ws['A1'] = '产品名称'
ws['B1'] = '销量'
ws['C1'] = '金额'

# 追加数据
ws.append(['iPhone', 100, 899900])
ws.append(['MacBook', 50, 999800])

# ─── 单元格样式 ───
header_font = Font(name='微软雅黑', bold=True, size=12, color='FFFFFF')
header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
thin_border = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

for cell in ws[1]:  # 第一行 (表头)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal='center')

# ─── 合并单元格 ───
ws.merge_cells('A1:C1')
ws['A1'].alignment = Alignment(horizontal='center')

# ─── 列宽自动调整 ───
for col in ws.columns:
    max_length = max(len(str(cell.value or '')) for cell in col)
    ws.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2

# ─── 图表 ───
chart = BarChart()
chart.title = "产品销售统计"
chart.y_axis.title = "金额 (元)"
data = Reference(ws, min_col=3, min_row=1, max_row=3)
cats = Reference(ws, min_col=1, min_row=2, max_row=3)
chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)
ws.add_chart(chart, "E2")

# ─── 保存 ───
wb.save('report.xlsx')

# ─── 读取 ───
wb = load_workbook('report.xlsx', data_only=True)  # data_only=True 获取计算结果而非公式
ws = wb.active
for row in ws.iter_rows(min_row=1, values_only=True):
    print(row)  # 元组形式输出
```

### 3.3 openpyxl vs xlrd/xlwt

| 特性 | openpyxl | xlrd / xlwt |
|------|----------|-------------|
| 支持 .xlsx | ✅ | xlrd 2.x 不支持（仅 .xls） |
| 支持 .xls | ❌ | ✅ |
| 写入 | ✅ | xlwt（仅 .xls） |
| 公式 | ✅ 读取+写入 | ❌ |
| 图表 | ✅ | ❌ |
| 样式 | ✅ 丰富 | 有限 |
| 大文件 | ❌ 内存占用大 | ❌ |
| 推荐度 | ⭐⭐⭐⭐⭐（现代 .xlsx） | ⭐⭐（兼容旧 .xls） |

---

## 4. pandas 基础读取

### 4.1 概念

pandas 是 Python 数据分析的核心库，提供 `DataFrame` 数据结构。用 pandas 读取 CSV/Excel 可以自动处理表头、数据类型、缺失值等。

**安装：** `pip install pandas openpyxl`

### 4.2 核心 API

```python
import pandas as pd

# ─── 读取 CSV ───
df = pd.read_csv('data.csv')
df = pd.read_csv('data.csv', encoding='utf-8')       # 指定编码
df = pd.read_csv('data.csv', delimiter='\t')          # 制表符分隔
df = pd.read_csv('data.csv', header=None)             # 无表头
df = pd.read_csv('data.csv', names=['a','b','c'])     # 自定义列名
df = pd.read_csv('data.csv', index_col='id')          # 指定索引列
df = pd.read_csv('data.csv', parse_dates=['date'])    # 解析日期
df = pd.read_csv('data.csv', dtype={'age': int})      # 指定数据类型
df = pd.read_csv('data.csv', na_values=['', 'NA'])    # 指定缺失值标记

# ─── 读取 Excel ───
df = pd.read_excel('report.xlsx')
df = pd.read_excel('report.xlsx', sheet_name='Sheet1')     # 指定工作表
df = pd.read_excel('report.xlsx', sheet_name=None)          # 读取所有工作表
df = pd.read_excel('report.xlsx', skiprows=2)               # 跳过前 2 行
df = pd.read_excel('report.xlsx', usecols='A:C')            # 只读 A-C 列

# ─── 写入 ───
df.to_csv('output.csv', index=False, encoding='utf-8-sig')  # utf-8-sig 含 BOM，Excel 兼容
df.to_excel('output.xlsx', sheet_name='Sheet1', index=False)
```

### 4.3 pandas 优势

```
                      原始 csv.reader               pandas.read_csv
                         │                              │
                         ▼                              ▼
                 ┌──────────────┐              ┌──────────────┐
                 │ [字符串列表]  │              │  DataFrame   │
                 │ ['Alice','30']│              │  name  age   │
                 │ ['Bob','25']  │              │  Alice  30   │
                 └──────────────┘              │  Bob    25   │
                         │                     └──────────────┘
                         │                            │
                      手动转换                    自动推断类型
                 age = int(row[1])             age → int64 列
                         │                            │
                         ▼                            ▼
                ❌ 代码繁琐 + 易错           ✅ 一行代码 + 类型安全
```

---

## 5. 实战：报表生成器

详见 `code/03-report-generator.py`

实现一个报表生成器，支持：
- 从 CSV 读取销售数据
- 数据清洗与统计汇总
- 生成格式化的 Excel 报表（含样式、图表）
- 导出多种格式

---

## 6. 思考题

1. **CSV 的最大的缺点是什么？** 如果让你设计一种替代 CSV 的纯文本表格格式，你会改善哪些方面？
2. **openpyxl 在处理 10 万行 Excel 时为什么会内存溢出？** 有没有办法处理超大的 Excel 文件？
3. **为什么 Excel 打开 UTF-8 编码的 CSV 文件会乱码？** `utf-8-sig` 解决了什么问题？
4. **pandas 的 `read_csv` 和 `csv.DictReader` 在处理大型文件时哪个更高效？** 为什么？
5. **Excel 的 .xlsx 格式本质上是 ZIP 包，这带来了哪些优缺点？**

---

## 7. 最佳实践总结

| 场景 | 推荐方案 | 原因 |
|------|----------|------|
| 简单数据交换 | CSV（csv 模块） | 通用、轻量、跨平台 |
| Excel 报表生成 | openpyxl | 丰富的样式/图表支持 |
| 数据分析 | pandas | 强大的类型推断/聚合能力 |
| 老系统兼容（.xls） | xlrd/xlwt | 唯一支持旧格式的方案 |
| 超大文件处理 | 分块读取/迭代器 | 避免内存溢出 |
