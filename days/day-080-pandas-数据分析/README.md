# Day 080 — Pandas 数据分析

> **数据分析仪表盘项目 Day 2/3：Pandas — 数据处理的瑞士军刀**

---

## 📋 今日学习目标

- 理解 Pandas 的设计理念与核心价值
- 掌握 Series 与 DataFrame 的创建、属性与基本操作
- 学会数据读取（CSV/Excel/JSON）、筛选与清洗
- 掌握 GroupBy 分组聚合与透视表
- 理解缺失值处理与数据类型转换
- 掌握数据合并（merge/concat/join）操作

---

## 1. 为什么需要 Pandas？

### 1.1 数据分析的痛点

实际数据分析中，数据往往来自多个来源（CSV、数据库、API），格式不统一，有缺失值、重复行、异常值等问题。如果用 Python 原生数据结构处理，代码会非常繁琐且容易出错。

```python
# 用原生 Python 读取 CSV 并统计
import csv

with open('sales.csv') as f:
    reader = csv.DictReader(f)
    data = list(reader)

# 统计每个地区的销售额 — 写起来很痛苦
regions = {}
for row in data:
    region = row['region']
    amount = float(row['amount'])
    regions[region] = regions.get(region, 0) + amount
```

### 1.2 Pandas 的核心优势

| 特性 | Python 原生 | Pandas |
|------|-----------|--------|
| 数据读取 | csv 手动解析 | `read_csv()` 一行搞定 |
| 数据筛选 | 循环 + if | 布尔索引，简洁直观 |
| 缺失值处理 | 到处写 `if x is not None` | `dropna()` / `fillna()` |
| 分组聚合 | 手动分组 + 字典累加 | `groupby().agg()` |
| 数据合并 | 循环 + 匹配 | `merge()` 一行搞定 |
| 统计分析 | 手写公式 | `.describe()` 一键统计 |

**Pandas 之于数据分析，就像 NumPy 之于科学计算。**

---

## 2. Series — 一维数据

### 2.1 什么是 Series？

Series 是 Pandas 的一维数据结构，类似于带标签的数组。它由两部分组成：
- **values**：NumPy 数组，存储实际数据
- **index**：索引标签，可以是数字、字符串、日期等

```python
import pandas as pd
import numpy as np

# 创建 Series
s = pd.Series([10, 20, 30, 40], index=['a', 'b', 'c', 'd'])
print(s)
# a    10
# b    20
# c    30
# d    40

# 带名称的 Series
prices = pd.Series(
    [29.99, 49.99, 19.99],
    index=['iPhone', 'iPad', 'AirPods'],
    name='价格'
)
print(prices['iPhone'])  # 29.99
```

### 2.2 Series 操作

```python
# 索引与切片
print(prices['iPad'])           # 49.99
print(prices[prices > 25])     # 过滤价格 > 25 的产品

# 向量化运算（与 NumPy 一致）
prices_with_tax = prices * 1.13
print(prices_with_tax)

# 常用统计方法
print(f"平均价格: {prices.mean():.2f}")
print(f"最高价格: {prices.max():.2f}")
print(f"价格中位数: {prices.median():.2f}")

# Series 与字典的转换
prices_dict = prices.to_dict()
new_series = pd.Series(prices_dict)
```

---

## 3. DataFrame — 二维数据（核心！）

### 3.1 什么是 DataFrame？

DataFrame 是 Pandas 最核心的数据结构，可以理解为一个**带行标签和列标签的二维表格**。它相当于 Excel 中的一个工作表或 SQL 中的一张表。

**核心特性：**
- 每列可以有不同的数据类型
- 行和列都有标签（index 和 columns）
- 支持向量化运算
- 内存效率高（NumPy 底层实现）

### 3.2 创建 DataFrame

```python
import pandas as pd
import numpy as np

# 从字典创建
df = pd.DataFrame({
    '姓名': ['张三', '李四', '王五', '赵六', '钱七'],
    '部门': ['销售', '技术', '销售', '技术', '人事'],
    '薪资': [8000, 15000, 9000, 18000, 12000],
    '入职年份': [2020, 2019, 2021, 2018, 2022]
})
print(df)
#    姓名  部门    薪资  入职年份
# 0  张三  销售   8000    2020
# 1  李四  技术  15000    2019
# 2  王五  销售   9000    2021
# 3  赵六  技术  18000    2018
# 4  钱七  人事  12000    2022

# 从 NumPy 数组创建
df2 = pd.DataFrame(
    np.random.randn(5, 3),
    columns=['A', 'B', 'C'],
    index=pd.date_range('2024-01-01', periods=5)
)
```

### 3.3 查看数据

```python
# 基本信息
print(f"形状: {df.shape}")         # (5, 4)
print(f"列名: {df.columns.tolist()}")
print(f"数据类型:\n{df.dtypes}")
print(f"前 3 行:\n{df.head(3)}")
print(f"后 2 行:\n{df.tail(2)}")

# 统计摘要 — 一键查看所有数值列的统计信息
print(df.describe())

# 信息概览
print(df.info())
```

### 3.4 索引与选择数据（重点！）

Pandas 提供多种索引方式，理解它们的区别是高效使用 Pandas 的关键：

```python
# === 1. 列选择 ===
print(df['姓名'])        # 返回 Series
print(df[['姓名', '薪资']])  # 返回 DataFrame

# === 2. loc — 基于标签的索引（推荐！） ===
print(df.loc[0])                    # 第 0 行（标签为 0）
print(df.loc[0:2, '姓名':'薪资'])    # 行 0-2，列 '姓名' 到 '薪资'
print(df.loc[df['薪资'] > 10000])    # 条件筛选

# === 3. iloc — 基于位置的索引（纯数字位置） ===
print(df.iloc[0])          # 第 0 行（无论标签是什么）
print(df.iloc[0:3, 0:2])   # 前 3 行，前 2 列
print(df.iloc[-1])         # 最后一行

# === 4. 条件筛选（最常用！） ===
tech_staff = df[df['部门'] == '技术']
print(tech_staff)

# 多条件筛选（注意 & | ~ 运算符）
senior_tech = df[(df['部门'] == '技术') & (df['入职年份'] < 2020)]
print(senior_tech)

# === 5. query 方法（更直观的语法） ===
result = df.query('部门 == "技术" and 薪资 > 10000')
print(result)
```

**`loc` vs `iloc` 记忆口诀：**
- `loc` = **label**（标签）→ 用行标签和列名
- `iloc` = **integer location**（整数位置）→ 用纯数字索引

### 3.5 赋值与修改

```python
# 新增列
df['年薪'] = df['薪资'] * 12

# 条件赋值
df['级别'] = df['薪资'].apply(lambda x: '高级' if x > 12000 else '初级')

# 修改特定值
df.loc[df['姓名'] == '张三', '薪资'] = 8500

# 删除列
df = df.drop(columns=['年薪'])

# 重命名列
df = df.rename(columns={'入职年份': 'year'})
```

---

## 4. 数据读取与写入

### 4.1 读取 CSV

```python
# 基本读取
df = pd.read_csv('data/sales.csv')

# 高级选项
df = pd.read_csv(
    'data/sales.csv',
    encoding='utf-8',
    sep=',',
    index_col='id',
    usecols=['name', 'price'],
    dtype={'id': str},
    parse_dates=['date'],
    na_values=['N/A', '-'],
    nrows=1000,
    skiprows=2,
)

# 大文件分块读取（避免内存溢出）
chunks = pd.read_csv('big_data.csv', chunksize=10000)
result = pd.concat([chunk.groupby('category')['amount'].sum() for chunk in chunks])
```

### 4.2 读取 Excel

```python
# 读取第一个 sheet
df = pd.read_excel('report.xlsx')

# 读取指定 sheet
df = pd.read_excel('report.xlsx', sheet_name='销售数据')

# 读取多个 sheet
all_sheets = pd.read_excel('report.xlsx', sheet_name=None)
for name, sheet_df in all_sheets.items():
    print(f"{name}: {sheet_df.shape}")
```

### 4.3 读取 JSON

```python
# JSON 文件
df = pd.read_json('data.json')

# 嵌套 JSON（展平）
df = pd.json_normalize(
    json_data,
    record_path='items',
    meta=['order_id', 'date']
)
```

### 4.4 写入文件

```python
# CSV
df.to_csv('output.csv', index=False, encoding='utf-8-sig')

# Excel（需要 openpyxl）
df.to_excel('output.xlsx', index=False, sheet_name='结果')

# JSON
df.to_json('output.json', orient='records', force_ascii=False)

# 追加写入 CSV（注意 mode）
df.to_csv('log.csv', mode='a', header=False, index=False)
```

---

## 5. 数据清洗

真实数据几乎总是"脏"的。Pandas 提供了强大的数据清洗工具。

### 5.1 缺失值处理

```python
import pandas as pd
import numpy as np

# 创建含缺失值的 DataFrame
df = pd.DataFrame({
    'A': [1, 2, np.nan, 4, 5],
    'B': [np.nan, 2, 3, np.nan, 5],
    'C': ['a', None, 'c', 'd', 'e']
})

# 查看缺失值
print(df.isnull().sum())

# 缺失值比例
print(df.isnull().mean() * 100)

# 删除缺失值
df_dropped = df.dropna()
df_dropped = df.dropna(subset=['A'])
df_dropped = df.dropna(thresh=3)

# 填充缺失值
df_filled = df.fillna(0)
df_filled = df.fillna(df.mean())
df_filled = df.fillna(method='ffill')
df_filled = df.fillna(method='bfill')
df['A'] = df['A'].interpolate()

# 替换特定值
df['C'] = df['C'].replace({None: '未知'})
```

**缺失值处理决策树：**
```
缺失值 < 5% → 直接删除（dropna）
缺失值 5%-30% → 填充（fillna）
  - 数值列：均值/中位数/插值
  - 分类列：众数/新类别"未知"
缺失值 > 30% → 考虑删除该列
```

### 5.2 重复值处理

```python
# 查看重复行
print(df.duplicated().sum())

# 删除完全重复的行
df = df.drop_duplicates()

# 按指定列去重（保留第一条）
df = df.drop_duplicates(subset=['姓名'], keep='first')

# 查看重复详情
duplicates = df[df.duplicated(subset=['姓名'], keep=False)]
print(duplicates)
```

### 5.3 数据类型转换

```python
# 查看当前类型
print(df.dtypes)

# 转换类型
df['日期'] = pd.to_datetime(df['日期'])
df['价格'] = df['价格'].astype(float)
df['类别'] = df['类别'].astype('category')

# 智能类型转换（自动推断）
df = df.convert_dtypes()

# 处理字符串列
df['电话'] = df['电话'].str.replace('-', '')
df['邮箱'] = df['邮箱'].str.lower()
df['姓名'] = df['姓名'].str.strip()
```

### 5.4 异常值处理

```python
# 方法 1：IQR（四分位距）法
Q1 = df['薪资'].quantile(0.25)
Q3 = df['薪资'].quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR

# 筛选正常范围内的数据
df_clean = df[(df['薪资'] >= lower) & (df['薪资'] <= upper)]

# 方法 2：Z-Score 法
from scipy import stats
z_scores = np.abs(stats.zscore(df['薪资']))
df_clean = df[z_scores < 3]

# 方法 3：截断（Winsorize）
df['薪资'] = df['薪资'].clip(lower=lower, upper=upper)
```

---

## 6. 数据转换与增强

### 6.1 apply — 逐行/逐列应用函数

```python
# 逐行应用（axis=1）
df['税后薪资'] = df.apply(lambda row: row['薪资'] * 0.85, axis=1)

# 逐列应用（axis=0，默认）
df['薪资_万'] = df['薪资'].apply(lambda x: round(x / 10000, 2))

# 使用命名函数（更高效）
def classify_salary(salary):
    if salary < 10000:
        return '初级'
    elif salary < 15000:
        return '中级'
    else:
        return '高级'

df['级别'] = df['薪资'].apply(classify_salary)
```

### 6.2 map 与 replace

```python
# map — 用于 Series，逐元素映射
level_map = {'初级': 1, '中级': 2, '高级': 3}
df['级别码'] = df['级别'].map(level_map)

# replace — 用于 DataFrame 或 Series
df['部门'] = df['部门'].replace({
    '技术': 'Engineering',
    '销售': 'Sales',
    '人事': 'HR'
})

# 条件映射
df['部门'] = df['部门'].map(
    lambda x: '技术中心' if x == '技术' else '业务部门'
)
```

### 6.3 排序

```python
# 单列排序
df_sorted = df.sort_values('薪资', ascending=False)

# 多列排序（先按薪资降序，再按入职年份升序）
df_sorted = df.sort_values(['薪资', '入职年份'], ascending=[False, True])

# 按索引排序
df_sorted = df.sort_index()
```

---

## 7. GroupBy 分组聚合

### 7.1 基本分组

```python
# 按部门分组统计
dept_stats = df.groupby('部门').agg({
    '薪资': ['mean', 'max', 'min', 'count'],
    '入职年份': 'min'
})
print(dept_stats)
```

### 7.2 多种聚合方式

```python
# 对不同列使用不同聚合函数
result = df.groupby('部门').agg(
    平均薪资=('薪资', 'mean'),
    最高薪资=('薪资', 'max'),
    人数=('姓名', 'count'),
    入职最早=('入职年份', 'min')
)
print(result)

# 自定义聚合函数
def salary_range(group):
    return group.max() - group.min()

salary_ranges = df.groupby('部门')['薪资'].agg(salary_range)
print(salary_ranges)
```

### 7.3 transform — 保持原始形状的聚合

```python
# 计算每个部门的平均薪资
df['部门平均薪资'] = df.groupby('部门')['薪资'].transform('mean')

# 计算每个人薪资与部门平均的差距
df['薪资差距'] = df['薪资'] - df['部门平均薪资']

# 标准化（Z-score）
df['薪资_zscore'] = df.groupby('部门')['薪资'].transform(
    lambda x: (x - x.mean()) / x.std()
)
print(df[['姓名', '部门', '薪资', '部门平均薪资', '薪资差距']])
```

### 7.4 透视表（Pivot Table）

```python
# 创建示例数据
sales = pd.DataFrame({
    '月份': ['1月', '1月', '2月', '2月', '3月', '3月'],
    '产品': ['A', 'B', 'A', 'B', 'A', 'B'],
    '销售额': [1000, 1500, 1200, 1800, 1400, 2000],
    '地区': ['北京', '北京', '上海', '上海', '北京', '上海']
})

# 基本透视表
pivot = sales.pivot_table(
    values='销售额',
    index='月份',
    columns='产品',
    aggfunc='sum'
)
print(pivot)

# 多级分组透视
pivot2 = sales.pivot_table(
    values='销售额',
    index=['月份', '地区'],
    columns='产品',
    aggfunc='sum',
    margins=True,
    margins_name='合计'
)
print(pivot2)
```

---

## 8. 数据合并

### 8.1 merge — 类似 SQL JOIN

```python
# 两个相关表
employees = pd.DataFrame({
    '员工ID': [1, 2, 3, 4],
    '姓名': ['张三', '李四', '王五', '赵六'],
    '部门ID': [101, 102, 101, 103]
})

departments = pd.DataFrame({
    '部门ID': [101, 102, 103],
    '部门名称': ['销售部', '技术部', '人事部']
})

# 内连接（只保留匹配的行）
merged = pd.merge(employees, departments, on='部门ID', how='inner')

# 左连接（保留左表所有行）
merged = pd.merge(employees, departments, on='部门ID', how='left')

# 右连接（保留右表所有行）
merged = pd.merge(employees, departments, on='部门ID', how='right')

# 外连接（保留所有行）
merged = pd.merge(employees, departments, on='部门ID', how='outer')
```

### 8.2 concat — 简单拼接

```python
# 纵向拼接（行增加）
df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
df2 = pd.DataFrame({'A': [5, 6], 'B': [7, 8]})
result = pd.concat([df1, df2], ignore_index=True)

# 横向拼接（列增加）
result = pd.concat([df1, df2], axis=1)
```

### 8.3 join — 基于索引的合并

```python
# 当两个表需要按索引合并时
df1 = pd.DataFrame({'A': [1, 2, 3]}, index=['a', 'b', 'c'])
df2 = pd.DataFrame({'B': [4, 5, 6]}, index=['a', 'b', 'd'])
result = df1.join(df2, how='outer')
```

---

## 9. 图解 Pandas 核心概念

### 9.1 DataFrame 内部结构

```
DataFrame
┌─────────────────────────────────────────────┐
│              index (行标签)                   │
│  ┌─────┬──────┬──────┬──────┬──────┐        │
│  │     │ col1 │ col2 │ col3 │ col4 │        │
│  ├─────┼──────┼──────┼──────┼──────┤        │
│  │ idx0│  10  │  20  │  30  │  40  │        │
│  │ idx1│  15  │  25  │  35  │  45  │        │
│  │ idx2│  20  │  30  │  40  │  50  │        │
│  └─────┴──────┴──────┴──────┴──────┘        │
│           columns (列标签)                    │
└─────────────────────────────────────────────┘
```

### 9.2 数据合并类型

```
    employees                    departments
┌──────┬──────┬──────┐      ┌──────┬──────────┐
│  ID  │ 姓名 │DeptID│      │DeptID│ 部门名称  │
├──────┼──────┼──────┤      ├──────┼──────────┤
│  1   │ 张三 │ 101  │      │ 101  │  销售部   │
│  2   │ 李四 │ 102  │      │ 102  │  技术部   │
│  3   │ 王五 │ 101  │      │ 103  │  人事部   │
│  4   │ 赵六 │ 103  │      └──────┴──────────┘
└──────┴──────┴──────┘

inner join → 只保留两边都有匹配的
left join  → 保留左边所有行，右边没匹配的填 NaN
right join → 保留右边所有行，左边没匹配的填 NaN
outer join → 保留所有行，没匹配的填 NaN
```

### 9.3 GroupBy 工作流程

```
原始数据
┌──────┬──────┬──────┐
│ 姓名 │ 部门 │ 薪资 │
├──────┼──────┼──────┤
│ 张三 │ 销售 │ 8000 │
│ 李四 │ 技术 │15000 │
│ 王五 │ 销售 │ 9000 │
│ 赵六 │ 技术 │18000 │
│ 钱七 │ 人事 │12000 │
└──────┴──────┴──────┘
        │
        ▼ Split（按部门拆分）
  ┌─────┐  ┌─────┐  ┌─────┐
  │销售部│  │技术部│  │人事部│
  │张三  │  │李四  │  │钱七  │
  │王五  │  │赵六  │  │     │
  └─────┘  └─────┘  └─────┘
        │
        ▼ Apply（对每组应用函数）
  ┌─────┐  ┌─────┐  ┌─────┐
  │mean │  │mean │  │mean │
  │8500 │  │16500│  │12000│
  └─────┘  └─────┘  └─────┘
        │
        ▼ Combine（合并结果）
  ┌──────┬──────┐
  │ 部门 │ 均薪 │
  ├──────┼──────┤
  │ 销售 │ 8500 │
  │ 技术 │16500 │
  │ 人事 │12000 │
  └──────┴──────┘
```

---

## 10. 实战案例：电商销售数据分析

```python
"""
电商销售数据分析完整案例
使用 Pandas 分析 3 个月的销售数据
"""
import pandas as pd
import numpy as np

# ==================== 1. 模拟数据生成 ====================
np.random.seed(42)
n = 1000

categories = ['电子产品', '服装', '食品', '家居', '运动']
regions = ['北京', '上海', '广州', '深圳', '成都']
payment_methods = ['支付宝', '微信', '银行卡']

# 创建销售数据
sales = pd.DataFrame({
    '订单ID': [f'ORD-{i:06d}' for i in range(1, n + 1)],
    '日期': pd.date_range('2024-01-01', periods=n, freq='4h'),
    '产品类别': np.random.choice(categories, n),
    '金额': np.random.lognormal(mean=5, sigma=1.5, size=n).round(2),
    '数量': np.random.randint(1, 20, n),
    '地区': np.random.choice(regions, n),
    '支付方式': np.random.choice(payment_methods, n),
})

# 添加一些缺失值（模拟真实数据）
mask = np.random.random(n) < 0.05
sales.loc[mask, '金额'] = np.nan

print(f"数据形状: {sales.shape}")
print(f"缺失值:\n{sales.isnull().sum()}")
print(f"\n前 5 行:\n{sales.head()}")

# ==================== 2. 数据清洗 ====================
# 处理缺失值：用同类别的中位数填充
for cat in categories:
    median_val = sales[sales['产品类别'] == cat]['金额'].median()
    sales.loc[(sales['产品类别'] == cat) & (sales['金额'].isna()), '金额'] = median_val

# 添加衍生列
sales['月份'] = sales['日期'].dt.month
sales['星期'] = sales['日期'].dt.day_name()
sales['单价'] = (sales['金额'] / sales['数量']).round(2)

print(f"\n清洗后缺失值: {sales['金额'].isnull().sum()}")

# ==================== 3. 分析：各类别销售情况 ====================
print("\n" + "=" * 50)
print("📊 各类别销售统计")
print("=" * 50)

cat_stats = sales.groupby('产品类别').agg(
    订单数=('订单ID', 'count'),
    总销售额=('金额', 'sum'),
    平均金额=('金额', 'mean'),
    总数量=('数量', 'sum'),
).round(2)

cat_stats['销售额占比'] = (cat_stats['总销售额'] / cat_stats['总销售额'].sum() * 100).round(2)
print(cat_stats.sort_values('总销售额', ascending=False))

# ==================== 4. 分析：各地区销售情况 ====================
print("\n" + "=" * 50)
print("📊 各地区销售统计")
print("=" * 50)

region_stats = sales.groupby('地区').agg(
    订单数=('订单ID', 'count'),
    总销售额=('金额', 'sum'),
    客单价=('金额', 'mean'),
).round(2)
print(region_stats.sort_values('总销售额', ascending=False))

# ==================== 5. 分析：每月销售趋势 ====================
print("\n" + "=" * 50)
print("📊 月度销售趋势")
print("=" * 50)

monthly = sales.groupby('月份').agg(
    订单数=('订单ID', 'count'),
    总销售额=('金额', 'sum'),
).round(2)

# 环比增长率
monthly['环比增长'] = monthly['总销售额'].pct_change() * 100
print(monthly)

# ==================== 6. 透视表分析 ====================
print("\n" + "=" * 50)
print("📊 各地区 × 各类别销售额透视表")
print("=" * 50)

pivot = sales.pivot_table(
    values='金额',
    index='地区',
    columns='产品类别',
    aggfunc='sum',
    margins=True,
    margins_name='合计'
).round(2)
print(pivot)

# ==================== 7. 找出 Top 10 大订单 ====================
print("\n" + "=" * 50)
print("📊 Top 10 大订单")
print("=" * 50)

top10 = sales.nlargest(10, '金额')[['订单ID', '日期', '产品类别', '金额', '地区']]
print(top10.to_string(index=False))

print("\n✅ 分析完成！")
```

---

## 11. 思考题

1. **Series vs DataFrame：** 什么时候应该用 Series 而不是 DataFrame？它们之间如何相互转换？

2. **loc vs iloc：** 如果一个 DataFrame 的索引是字符串（如 `['a', 'b', 'c']`），`df.loc['a':'c']` 和 `df.iloc[0:3]` 的结果有什么区别？为什么？

3. **apply vs vectorized：** `df['列'].apply(func)` 和直接向量化操作（如 `df['列'] * 2`）在性能上有什么差异？什么场景下应该用 apply？

4. **groupby vs pivot_table：** 在什么情况下用 `groupby` 更合适？什么情况下用 `pivot_table` 更方便？能否用两者实现相同的结果？

5. **缺失值策略：** 如果一列数据有 40% 的缺失值，你会选择删除该列、填充默认值、还是用其他方法处理？为什么？不同选择对分析结果会有什么影响？

---

## 📚 参考资源

- [Pandas 官方文档](https://pandas.pydata.org/docs/)
- [Pandas 10 分钟入门](https://pandas.pydata.org/docs/user_guide/10min.html)
- [Pandas 编程指南](https://pandas.pydata.org/docs/user_guide/cookbook.html)
- [Python for Data Analysis (Wes McKinney)](https://wesmckinney.com/book/)
