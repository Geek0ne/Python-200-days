# Day 102 — Pandas 核心

> Pandas 是 Python 数据分析的核心库，提供了类似 Excel 的数据操作能力，底层基于 NumPy。

---

## 目录

1. [为什么需要 Pandas](#1-为什么需要-pandas)
2. [Series 基础](#2-series-基础)
3. [DataFrame 基础](#3-dataframe-基础)
4. [数据查看与信息获取](#4-数据查看与信息获取)
5. [数据选择：loc / iloc / 布尔索引](#5-数据选择loc--iloc--布尔索引)
6. [数据筛选与查询](#6-数据筛选与查询)
7. [文件读写](#7-文件读写)
8. [实战：加载 CSV 数据探索](#8-实战加载-csv-数据探索)
9. [思考题](#9-思考题)

---

## 1. 为什么需要 Pandas

### 从 NumPy 到 Pandas

NumPy 擅长数值计算，但数据分析还需要：
- **列名/行标签**：NumPy 数组没有语义标签
- **混合类型**：一列可以是字符串，另一列是数字
- **缺失值处理**：真实数据总有 NaN
- **便捷的数据操作**：筛选、分组、合并

```
NumPy ndarray:           Pandas DataFrame:
┌──────────────┐         ┌──────────┬────────┬──────┐
│ 1    2    3  │         │ 姓名     │ 年龄   │ 城市 │
│ 4    5    6  │   →     ├──────────┼────────┼──────┤
│ 7    8    9  │         │ 张三     │ 25     │ 北京 │
└──────────────┘         │ 李四     │ 30     │ 上海 │
(纯数值，无标签)          └──────────┴────────┴──────┘
                         (有列名，有行索引)
```

### Pandas 的两大核心结构

```
Series   → 一维带标签数组（类比 Excel 的一列）
DataFrame → 二维带标签表格（类比 Excel 的一个 sheet）
```

---

## 2. Series 基础

### 创建 Series

```python
import pandas as pd

# 从列表创建（自动索引 0,1,2...）
s = pd.Series([10, 20, 30, 40])
print(s)
# 0    10
# 1    20
# 2    30
# 3    40
# dtype: int64

# 指定索引
s = pd.Series([10, 20, 30], index=['a', 'b', 'c'])
print(s)
# a    10
# b    20
# c    30

# 从字典创建
s = pd.Series({'数学': 95, '英语': 88, '物理': 92})
```

### Series 核心操作

```python
s = pd.Series([10, 20, 30, 40, 50], index=['a', 'b', 'c', 'd', 'e'])

# 索引
print(s['b'])         # 20
print(s[['a', 'c']])  # a=10, c=30
print(s[1:3])         # b=20, c=30

# 属性
print(s.index)        # Index(['a', 'b', 'c', 'd', 'e'])
print(s.values)       # [10 20 30 40 50]
print(s.dtype)        # int64
print(s.shape)        # (5,)

# 统计方法
print(s.mean())       # 30.0
print(s.std())        # 15.81...
print(s.describe())   # 完整统计摘要

# 条件筛选
print(s[s > 25])      # c=30, d=40, e=50
```

---

## 3. DataFrame 基础

### 创建 DataFrame

```python
import pandas as pd
import numpy as np

# 从字典创建（最常用）
df = pd.DataFrame({
    '姓名': ['张三', '李四', '王五', '赵六'],
    '年龄': [25, 30, 35, 28],
    '城市': ['北京', '上海', '广州', '深圳'],
    '薪资': [15000, 25000, 18000, 22000]
})
print(df)
#    姓名  年龄  城市    薪资
# 0  张三   25  北京  15000
# 1  李四   30  上海  25000
# 2  王五   35  广州  18000
# 3  赵六   28  深圳  22000

# 从 NumPy 数组创建
arr = np.random.randint(0, 100, (4, 3))
df = pd.DataFrame(arr, columns=['数学', '英语', '物理'],
                        index=['张三', '李四', '王五', '赵六'])

# 从列表的字典创建
data = [
    {'产品': '手机', '数量': 100, '单价': 4999},
    {'产品': '电脑', '数量': 50, '单价': 7999},
    {'产品': '耳机', '数量': 200, '单价': 299},
]
df = pd.DataFrame(data)
```

### DataFrame 核心属性

```python
df = pd.DataFrame({
    '姓名': ['张三', '李四', '王五'],
    '年龄': [25, 30, 35],
    '薪资': [15000.0, np.nan, 18000.0]
})

print(df.shape)       # (3, 3)  → (行数, 列数)
print(df.columns)     # Index(['姓名', '年龄', '薪资'])
print(df.index)       # RangeIndex(start=0, stop=3, step=1)
print(df.dtypes)      # 各列的数据类型
print(df.values)      # 底层数组
print(df.T)           # 转置
```

---

## 4. 数据查看与信息获取

### 快速浏览

```python
df = pd.DataFrame({
    '产品': [f'产品{i}' for i in range(100)],
    '销量': np.random.randint(10, 1000, 100),
    '单价': np.random.uniform(10, 1000, 100).round(2),
    '类别': np.random.choice(['电子', '服装', '食品'], 100)
})

# 查看前/后几行
print(df.head(3))     # 前 3 行
print(df.tail(3))     # 后 3 行
print(df.sample(5))   # 随机 5 行

# 数据概览
print(df.info())
# <class 'pandas.core.frame.DataFrame'>
# RangeIndex: 100 entries, 0 to 99
# Data columns (total 4 columns):
#  #   Column  Non-Null Count  Dtype
# ---  ------  --------------  -----
#  0   产品     100 non-null    object
#  1   销量     100 non-null    int64
#  2   单价     100 non-null    float64
#  3   类别     100 non-null    object

# 数值统计摘要
print(df.describe())
#               销量         单价
# count  100.000000  100.000000
# mean   503.420000  502.310000
# std    281.234567  281.123456
# min     12.000000   12.340000
# 25%    250.000000  250.000000
# 50%    500.000000  500.000000
# 75%    750.000000  750.000000
# max    999.000000  999.000000

# 非数值列的统计
print(df.describe(include='object'))
#         产品   类别
# count    100   100
# unique   100     3
# top     产品0   电子
# freq       1    35
```

### 缺失值检测

```python
df = pd.DataFrame({
    'A': [1, 2, np.nan, 4],
    'B': [np.nan, 2, 3, np.nan],
    'C': [1, 2, 3, 4]
})

print(df.isnull())        # 布尔矩阵
print(df.isnull().sum())  # 每列缺失值计数
# A    1
# B    2
# C    0

print(df.isnull().sum().sum())  # 总缺失值数: 3
print(df.notna())         # 与 isnull 相反
```

---

## 5. 数据选择：loc / iloc / 布尔索引

### 三种选择方式对比

```
┌─────────────────────────────────────────────────┐
│              DataFrame 数据选择                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  loc  → 按标签选择（label-based）               │
│  iloc → 按位置选择（integer-based）              │
│  []   → 列选择 + 布尔索引                       │
│                                                 │
└─────────────────────────────────────────────────┘
```

### loc — 按标签选择

```python
df = pd.DataFrame({
    '姓名': ['张三', '李四', '王五'],
    '年龄': [25, 30, 35],
    '城市': ['北京', '上海', '广州']
}, index=['a', 'b', 'c'])

# 选择单行
print(df.loc['a'])
# 姓名    张三
# 年龄     25
# 城市    北京

# 选择多行
print(df.loc[['a', 'c']])

# 选择行和列
print(df.loc['a', '年龄'])           # 25
print(df.loc['a':'b', ['姓名', '城市']])  # a 到 b 行的指定列

# 条件选择
print(df.loc[df['年龄'] > 25])
```

### iloc — 按位置选择

```python
df = pd.DataFrame({
    '姓名': ['张三', '李四', '王五'],
    '年龄': [25, 30, 35],
    '城市': ['北京', '上海', '广州']
})

# 选择第 0 行
print(df.iloc[0])

# 选择第 0-1 行，第 1-2 列
print(df.iloc[0:2, 1:3])

# 选择指定行和列
print(df.iloc[[0, 2], [0, 2]])

# 条件选择（注意：iloc 不支持布尔索引，需要先用 loc）
print(df.iloc[df.index[df['年龄'] > 25].tolist()])
```

### 列选择与布尔索引

```python
# 直接选择列
print(df['姓名'])           # Series
print(df[['姓名', '年龄']])  # DataFrame

# 布尔索引
mask = df['年龄'] > 25
print(df[mask])              # 等价于 df[df['年龄'] > 25]

# 多条件（用 & | ~，不是 and or not）
print(df[(df['年龄'] > 25) & (df['城市'] == '上海')])
print(df[(df['年龄'] < 28) | (df['城市'] == '广州')])
print(df[~(df['年龄'] > 30)])  # 取反
```

### 选择方式总结

| 场景 | 推荐方式 | 示例 |
|------|---------|------|
| 按行标签 | `loc` | `df.loc['row_name']` |
| 按行位置 | `iloc` | `df.iloc[0]` |
| 选择列 | `[]` | `df['col_name']` |
| 条件筛选 | `布尔索引` | `df[df['col'] > value]` |
| 行+列组合 | `loc` | `df.loc['a':'c', ['col1']]` |
| 位置+列组合 | `iloc` | `df.iloc[0:3, 0:2]` |

---

## 6. 数据筛选与查询

### 复杂条件筛选

```python
df = pd.DataFrame({
    '产品': ['手机', '电脑', '耳机', '手机', '电脑', '耳机'],
    '品牌': ['华为', '联想', '苹果', '小米', '戴尔', '索尼'],
    '价格': [4999, 5999, 1299, 3999, 6999, 899],
    '销量': [100, 50, 200, 150, 30, 80]
})

# query 方法（字符串表达式）
print(df.query('价格 > 2000 & 销量 > 100'))
print(df.query('产品 == "手机"'))

# isin 筛选
print(df[df['产品'].isin(['手机', '电脑'])])

# between 范围筛选
print(df[df['价格'].between(1000, 5000)])

# str 方法（字符串筛选）
print(df[df['品牌'].str.startswith('华')])
print(df[df['品牌'].str.contains('尔')])
```

### 排序

```python
# 按列排序
print(df.sort_values('价格', ascending=False))      # 降序
print(df.sort_values(['产品', '价格'], ascending=[True, False]))  # 多列

# 按索引排序
print(df.sort_index())

# 按值排名
df['价格排名'] = df['价格'].rank(ascending=False)
print(df)
```

---

## 7. 文件读写

### CSV 读写

```python
# 读取 CSV
df = pd.read_csv('data.csv')
df = pd.read_csv('data.csv', encoding='gbk')          # 中文编码
df = pd.read_csv('data.csv', index_col=0)              # 指定索引列
df = pd.read_csv('data.csv', parse_dates=['日期'])      # 解析日期列
df = pd.read_csv('data.csv', na_values=['N/A', '-'])    # 自定义缺失值

# 保存 CSV
df.to_csv('output.csv', index=False)
df.to_csv('output.csv', encoding='utf-8-sig')           # 中文 Excel 友好
```

### 其他格式

```python
# Excel
df = pd.read_excel('data.xlsx', sheet_name='Sheet1')
df.to_excel('output.xlsx', index=False)

# JSON
df = pd.read_json('data.json')
df.to_json('output.json', orient='records', force_ascii=False)

# SQL（需要 sqlalchemy）
from sqlalchemy import create_engine
engine = create_engine('sqlite:///data.db')
df = pd.read_sql('SELECT * FROM table_name', engine)
df.to_sql('table_name', engine, if_exists='replace', index=False)

# Parquet（大数据常用，压缩高效）
df.to_parquet('data.parquet')
df = pd.read_parquet('data.parquet')
```

---

## 8. 实战：加载 CSV 数据探索

### 模拟电商数据

```python
import pandas as pd
import numpy as np
import os

# 生成模拟数据
np.random.seed(42)
n = 1000

products = np.random.choice(['手机', '电脑', '耳机', '平板', '手表'], n)
categories = np.where(np.isin(products, ['手机', '电脑', '平板']), '电子',
              np.where(np.isin(products, ['耳机']), '配件', '穿戴'))
prices = np.where(products == '手机', np.random.uniform(2000, 6000, n),
         np.where(products == '电脑', np.random.uniform(4000, 12000, n),
         np.where(products == '耳机', np.random.uniform(100, 2000, n),
         np.where(products == '平板', np.random.uniform(1500, 5000, n),
                  np.random.uniform(500, 3000, n)))))
quantities = np.random.randint(1, 10, n)
discounts = np.random.choice([0, 5, 10, 15, 20], n, p=[0.3, 0.3, 0.2, 0.15, 0.05])
cities = np.random.choice(['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉'], n)
dates = pd.date_range('2024-01-01', periods=n, freq='D')

df = pd.DataFrame({
    '日期': dates,
    '产品': products,
    '类别': categories,
    '单价': np.round(prices, 2),
    '数量': quantities,
    '折扣%': discounts,
    '城市': cities,
    '总金额': np.round(prices * quantities * (1 - discounts / 100), 2)
})

# 保存为 CSV
os.makedirs('days/day-102-pandas-core/data', exist_ok=True)
df.to_csv('days/day-102-pandas-core/data/ecommerce.csv', index=False)
print(f"数据已保存，共 {len(df)} 条记录")
```

### 数据探索流程

```python
# 1. 加载数据
df = pd.read_csv('days/day-102-pandas-core/data/ecommerce.csv')
df['日期'] = pd.to_datetime(df['日期'])

# 2. 快速概览
print("=== 数据形状 ===")
print(f"行数: {df.shape[0]}, 列数: {df.shape[1]}")

print("\n=== 数据类型 ===")
print(df.dtypes)

print("\n=== 前5行 ===")
print(df.head())

print("\n=== 缺失值 ===")
print(df.isnull().sum())

print("\n=== 数值统计 ===")
print(df[['单价', '数量', '总金额']].describe())

# 3. 基础分析
print("\n=== 各产品总销售额 ===")
print(df.groupby('产品')['总金额'].sum().sort_values(ascending=False))

print("\n=== 各城市订单数 ===")
print(df['城市'].value_counts())

print("\n=== 各类别平均单价 ===")
print(df.groupby('类别')['单价'].mean())

# 4. 条件筛选
print("\n=== 高额订单 (>5000元) ===")
high_value = df[df['总金额'] > 5000]
print(f"数量: {len(high_value)}, 占比: {len(high_value)/len(df)*100:.1f}%")

print("\n=== 北京的手机订单 ===")
bj_phone = df[(df['城市'] == '北京') & (df['产品'] == '手机')]
print(bj_phone[['日期', '单价', '数量', '总金额']].head())
```

---

## 9. 思考题

1. **`loc` 和 `iloc` 的本质区别是什么？在什么场景下必须用 `loc` 而不能用 `iloc`？**

2. **DataFrame 的 `[]` 操作符在选择单列和多列时，行为有什么不同？为什么？**

3. **为什么 `df[df['A'] > 1 & df['B'] > 2]` 会报错？正确的写法是什么？运算符优先级的原理是什么？**

4. **`query` 方法和布尔索引在性能上有什么区别？大数据量下推荐用哪个？**

5. **读取一个 10GB 的 CSV 文件，`pd.read_csv()` 一次性加载可能内存不够，有什么解决方案？**（提示：chunksize 参数）
