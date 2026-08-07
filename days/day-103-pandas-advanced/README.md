# Day 103 — Pandas 进阶

> 掌握数据清洗、分组聚合、合并连接和时间序列处理，成为数据分析实战高手。

---

## 目录

1. [数据清洗](#1-数据清洗)
2. [分组聚合：groupby / agg / transform](#2-分组聚合groupby--agg--transform)
3. [合并连接：merge / concat / join](#3-合并连接merge--concat--join)
4. [时间序列处理](#4-时间序列处理)
5. [实战：电商销售数据分析](#5-实战电商销售数据分析)
6. [思考题](#6-思考题)

---

## 1. 数据清洗

### 1.1 缺失值处理

```python
import pandas as pd
import numpy as np

df = pd.DataFrame({
    '姓名': ['张三', '李四', '王五', '赵六', None],
    '年龄': [25, np.nan, 35, 28, 30],
    '薪资': [15000, 25000, np.nan, 22000, 18000],
    '部门': ['技术', '产品', '技术', np.nan, '运营']
})

# 检测缺失值
print(df.isnull())           # 布尔矩阵
print(df.isnull().sum())     # 每列缺失数
print(df.isnull().sum().sum())  # 总缺失数

# 删除缺失值
print(df.dropna())                    # 删除任何含 NaN 的行
print(df.dropna(subset=['年龄']))     # 只看特定列
print(df.dropna(thresh=3))            # 至少 3 个非空值才保留

# 填充缺失值
print(df.fillna(0))                          # 用 0 填充
print(df.fillna({'年龄': df['年龄'].mean(),  # 按列用不同值填充
                 '部门': '未知'}))
print(df.fillna(method='ffill'))             # 前向填充
print(df.fillna(method='bfill'))             # 后向填充
print(df.interpolate())                      # 插值法

# 替换值
df['部门'] = df['部门'].replace({np.nan: '未知'})
```

### 1.2 重复值处理

```python
df = pd.DataFrame({
    '姓名': ['张三', '李四', '张三', '王五', '李四'],
    '部门': ['技术', '产品', '技术', '设计', '产品']
})

# 检测重复
print(df.duplicated())                   # 布尔标记
print(df.duplicated().sum())             # 重复行数

# 删除重复
print(df.drop_duplicates())              # 保留第一次出现
print(df.drop_duplicates(keep='last'))   # 保留最后出现
print(df.drop_duplicates(subset=['姓名']))  # 按指定列判断
```

### 1.3 数据类型转换

```python
df = pd.DataFrame({
    '价格': ['1999', '2999', '3999'],
    '日期': ['2024-01-01', '2024-02-15', '2024-03-20'],
    '是否促销': ['是', '否', '是']
})

# 类型转换
df['价格'] = df['价格'].astype(int)
df['日期'] = pd.to_datetime(df['日期'])
df['是否促销'] = df['是否促销'].map({'是': True, '否': False})

print(df.dtypes)
# 价格              int64
# 日期     datetime64[ns]
# 是否促销            bool
```

### 1.4 异常值处理

```python
# IQR 方法检测异常值
Q1 = df['价格'].quantile(0.25)
Q3 = df['价格'].quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR

# 筛选正常范围
normal = df[(df['价格'] >= lower) & (df['价格'] <= upper)]

# 截断异常值
df['价格'] = df['价格'].clip(lower, upper)
```

---

## 2. 分组聚合：groupby / agg / transform

### 2.1 基础 groupby

```python
df = pd.DataFrame({
    '部门': ['技术', '产品', '技术', '设计', '产品', '技术'],
    '员工': ['张三', '李四', '王五', '赵六', '钱七', '孙八'],
    '薪资': [18000, 22000, 35000, 16000, 20000, 25000]
})

# 分组统计
dept_group = df.groupby('部门')
print(dept_group['薪资'].mean())       # 各部门平均薪资
print(dept_group['薪资'].sum())        # 各部门薪资总额
print(dept_group['薪资'].count())      # 各部门人数
print(dept_group['员工'].first())      # 各部门第一个员工
```

### 2.2 多函数聚合 agg

```python
# 单列多函数
print(df.groupby('部门')['薪资'].agg(['mean', 'std', 'min', 'max']))

# 多列多函数
print(df.groupby('部门').agg(
    人数=('员工', 'count'),
    平均薪资=('薪资', 'mean'),
    最高薪资=('薪资', 'max'),
    薪资标准差=('薪资', 'std')
))

# 自定义聚合函数
salary_range = lambda x: x.max() - x.min()
print(df.groupby('部门')['薪资'].agg(salary_range))
```

### 2.3 transform — 保持原始行数

```python
# transform 返回与原 DataFrame 等长的结果
df['部门平均薪资'] = df.groupby('部门')['薪资'].transform('mean')
df['薪资偏差'] = df['薪资'] - df['部门平均薪资']

print(df)
#    部门  员工    薪资  部门平均薪资  薪资偏差
# 0  技术  张三  18000     26000    -8000
# 1  产品  李四  22000     21000     1000
# 2  技术  王五  35000     26000     9000
# 3  设计  赵六  16000     16000        0
# 4  产品  钱七  20000     21000    -1000
# 5  技术  孙八  25000     26000    -1000
```

### 2.4 分组后筛选

```python
# 过滤组：只保留平均薪资 > 20000 的部门
high_salary = df.groupby('部门').filter(lambda x: x['薪资'].mean() > 20000)
print(high_salary)

# apply：更灵活的分组操作
def top_n(group, n=2):
    return group.nlargest(n, '薪资')

print(df.groupby('部门').apply(top_n, n=2))
```

---

## 3. 合并连接：merge / concat / join

### 3.1 merge — 类似 SQL JOIN

```python
# 员工表
employees = pd.DataFrame({
    '工号': ['E001', 'E002', 'E003', 'E004', 'E005'],
    '姓名': ['张三', '李四', '王五', '赵六', '钱七'],
    '部门': ['技术', '产品', '技术', '设计', '运营']
})

# 薪资表
salaries = pd.DataFrame({
    '工号': ['E001', 'E002', 'E003', 'E006'],
    '薪资': [18000, 22000, 35000, 20000]
})

# 内连接（交集）
inner = pd.merge(employees, salaries, on='工号', how='inner')
print("内连接:")
print(inner)

# 左连接（保留左表所有行）
left = pd.merge(employees, salaries, on='工号', how='left')
print("\n左连接:")
print(left)

# 右连接（保留右表所有行）
right = pd.merge(employees, salaries, on='工号', how='right')
print("\n右连接:")
print(right)

# 外连接（并集）
outer = pd.merge(employees, salaries, on='工号', how='outer')
print("\n外连接:")
print(outer)
```

```
内连接 (inner):       左连接 (left):        右连接 (right):       外连接 (outer):
A  B                 A  B                 A  B                 A  B
├──┤                 ├──┤                 ├──┤                 ├──┤
│a1├──b1             │a1├──b1             │a1├──b1             │a1├──b1
│a2├──b2             │a2├──b2             │a2├──b2             │a2├──b2
│a3├──b3             │a3├──b3             │a3├──b3             │a3├──b3
                     │a4│  (NaN)          │  │──b4             │a4│  (NaN)
                                          │  │                 │  │──b4
```

### 3.2 concat — 纵向/横向拼接

```python
df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
df2 = pd.DataFrame({'A': [5, 6], 'B': [7, 8]})
df3 = pd.DataFrame({'C': [9, 10]})

# 纵向拼接（行增加）
vertical = pd.concat([df1, df2], ignore_index=True)
print("纵向拼接:")
print(vertical)

# 横向拼接（列增加）
horizontal = pd.concat([df1, df3], axis=1)
print("\n横向拼接:")
print(horizontal)
```

### 3.3 join — 按索引合并

```python
df1 = pd.DataFrame({'A': [1, 2, 3]}, index=['a', 'b', 'c'])
df2 = pd.DataFrame({'B': [4, 5, 6]}, index=['b', 'c', 'd'])

# 按索引连接
joined = df1.join(df2, how='outer')
print(joined)
```

---

## 4. 时间序列处理

### 4.1 日期时间基础

```python
import pandas as pd

# 创建日期时间
dates = pd.date_range('2024-01-01', periods=12, freq='M')
print(dates)

# 提取日期组件
df = pd.DataFrame({'日期': dates})
df['年'] = df['日期'].dt.year
df['月'] = df['日期'].dt.month
df['季度'] = df['日期'].dt.quarter
df['星期'] = df['日期'].dt.dayofweek  # 0=周一
df['是否周末'] = df['星期'] >= 5
print(df)
```

### 4.2 时间序列聚合

```python
# 模拟每日销售数据
np.random.seed(42)
dates = pd.date_range('2024-01-01', periods=365, freq='D')
sales = pd.DataFrame({
    '日期': dates,
    '销售额': np.random.lognormal(10, 0.5, 365).round(2),
    '订单数': np.random.randint(50, 200, 365)
})

# 按月汇总
monthly = sales.set_index('日期').resample('M').agg({
    '销售额': 'sum',
    '订单数': 'sum'
})
print("月度汇总:")
print(monthly.head())

# 按周汇总
weekly = sales.set_index('日期').resample('W').sum()
print("\n周度汇总:")
print(weekly.head())

# 按季度汇总
quarterly = sales.set_index('日期').resample('Q').sum()
print("\n季度汇总:")
print(quarterly)
```

### 4.3 滚动窗口

```python
# 7 天移动平均
sales['7日均值'] = sales.set_index('日期')['销售额'].rolling(7).mean().values

# 30 天移动标准差
sales['30日波动'] = sales.set_index('日期')['销售额'].rolling(30).std().values

# 指数移动平均
sales['EMA_7'] = sales.set_index('日期')['销售额'].ewm(span=7).mean().values

print(sales[['日期', '销售额', '7日均值', '30日波动', 'EMA_7']].tail(10))
```

### 4.4 时间差与偏移

```python
# 日期偏移
sales['下月同日'] = sales['日期'] + pd.DateOffset(months=1)
sales['3天后'] = sales['日期'] + pd.Timedelta(days=3)

# 时间差
start = pd.Timestamp('2024-01-01')
end = pd.Timestamp('2024-12-31')
diff = end - start
print(f"2024年共 {diff.days} 天")
```

---

## 5. 实战：电商销售数据分析

### 完整分析流程

```python
import pandas as pd
import numpy as np
import os

np.random.seed(42)

# ══════════════════════════════════════════════════════
# 第一步：生成并加载数据
# ══════════════════════════════════════════════════════
n = 5000
dates = pd.date_range('2023-01-01', periods=n, freq='6H')

df = pd.DataFrame({
    '日期': np.random.choice(dates, n),
    '产品': np.random.choice(['iPhone', 'MacBook', 'iPad', 'AirPods', 'Apple Watch'], n,
                            p=[0.3, 0.15, 0.2, 0.25, 0.1]),
    '渠道': np.random.choice(['线上', '线下', '直播', '社群'], n, p=[0.4, 0.3, 0.2, 0.1]),
    '城市': np.random.choice(['北京', '上海', '广州', '深圳', '杭州', '成都'], n),
    '数量': np.random.choice([1, 1, 1, 2, 2, 3], n),
    '折扣': np.random.choice([0, 0, 5, 10, 15, 20], n, p=[0.4, 0.2, 0.15, 0.1, 0.1, 0.05]),
    '评分': np.random.choice([np.nan, 3, 4, 4, 4, 5, 5, 5], n)
})

base_prices = {'iPhone': 6999, 'MacBook': 12999, 'iPad': 4999, 'AirPods': 1299, 'Apple Watch': 3299}
df['单价'] = df['产品'].map(base_prices) * np.random.uniform(0.85, 1.15, n)
df['实付金额'] = (df['单价'] * df['数量'] * (1 - df['折扣'] / 100)).round(2)

os.makedirs('days/day-103-pandas-advanced/data', exist_ok=True)
df.to_csv('days/day-103-pandas-advanced/data/sales.csv', index=False)
print(f"生成 {n} 条销售记录")

# ══════════════════════════════════════════════════════
# 第二步：数据清洗
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("第二步：数据清洗")
print("=" * 60)

df = pd.read_csv('days/day-103-pandas-advanced/data/sales.csv', parse_dates=['日期'])

print(f"缺失值:\n{df.isnull().sum()}")
df['评分'] = df['评分'].fillna(df['评分'].median())
df['日期'] = pd.to_datetime(df['日期'])

# 添加时间特征
df['年'] = df['日期'].dt.year
df['月'] = df['日期'].dt.month
df['季度'] = df['日期'].dt.quarter
df['星期'] = df['日期'].dt.dayofweek

# ══════════════════════════════════════════════════════
# 第三步：分组分析
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("第三步：分组分析")
print("=" * 60)

# 产品维度
print("\n📊 产品销售统计:")
product_stats = df.groupby('产品').agg(
    订单数=('实付金额', 'count'),
    总销售额=('实付金额', 'sum'),
    平均客单价=('实付金额', 'mean'),
    平均评分=('评分', 'mean'),
    平均折扣=('折扣', 'mean')
).round(2).sort_values('总销售额', ascending=False)
print(product_stats)

# 渠道维度
print("\n📊 渠道对比:")
channel_stats = df.groupby('渠道').agg(
    订单数=('实付金额', 'count'),
    总销售额=('实付金额', 'sum'),
    平均评分=('评分', 'mean'),
    平均折扣=('折扣', 'mean')
).round(2)
print(channel_stats)

# 城市维度
print("\n📊 城市销售排名:")
city_stats = df.groupby('城市').agg(
    订单数=('实付金额', 'count'),
    总销售额=('实付金额', 'sum')
).round(2).sort_values('总销售额', ascending=False)
print(city_stats)

# ══════════════════════════════════════════════════════
# 第四步：时间序列分析
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("第四步：时间序列分析")
print("=" * 60)

# 月度趋势
df.set_index('日期', inplace=True)
monthly = df.resample('M').agg({
    '实付金额': 'sum',
    '订单数': 'count',
    '评分': 'mean'
})
print("\n📊 月度销售趋势:")
print(monthly.round(2).head(12))

# 移动平均
monthly['销售MA3'] = monthly['实付金额'].rolling(3).mean()
print("\n📊 3 月移动平均:")
print(monthly[['实付金额', '销售MA3']].head(6))

# 季度对比
quarterly = df.resample('Q').agg({
    '实付金额': 'sum',
    '订单数': 'count'
})
print("\n📊 季度对比:")
print(quarterly)

# ══════════════════════════════════════════════════════
# 第五步：交叉分析
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("第五步：交叉分析")
print("=" * 60)

# 产品 × 渠道
print("\n📊 产品 × 渠道 销售额:")
cross = pd.pivot_table(df, values='实付金额', index='产品', columns='渠道',
                       aggfunc='sum', fill_value=0).round(2)
print(cross)

# 城市 × 产品
print("\n📊 城市 × 产品 订单数:")
cross2 = pd.crosstab(df['城市'], df['产品'])
print(cross2)

print("\n✅ Pandas 进阶实战完成！")
```

---

## 6. 思考题

1. **`groupby().transform()` 和 `groupby().agg()` 的本质区别是什么？什么场景下必须用 `transform`？**

2. **`merge` 的 `how` 参数有哪几种？外连接 (outer) 结果中 NaN 是怎么产生的？**

3. **`resample('M')` 和 `groupby(df['日期'].dt.month)` 有什么区别？在处理跨年数据时哪个更好？**

4. **处理一个有 100 万行、包含大量缺失值和异常值的数据集，你会按什么顺序进行清洗？为什么？**

5. **`rolling(7).mean()` 计算的是包含当天的 7 天还是不包含？如果要计算"过去 7 天"的均值，该怎么设置？**
