# Pandas 核心概念速记

## 为什么选择 Pandas？

Pandas 是 Python 数据分析的事实标准库。它构建在 NumPy 之上，提供了两个核心数据结构：
- **Series**：一维带标签数组
- **DataFrame**：二维带标签表格

核心优势：**向量化运算**（底层 C 实现）+ **声明式 API**（代码可读性高）

## 两个核心数据结构

### Series
```python
s = pd.Series([1, 2, 3], index=['a', 'b', 'c'])
# 底层是 NumPy ndarray + Index 对象
```
- 一个 Series = 一个 column
- 可以用 index 做标签索引
- 支持所有 NumPy 向量化运算

### DataFrame
```python
df = pd.DataFrame({'A': [1,2], 'B': [3,4]})
# 本质上是多个 Series 的字典（每列一个 Series）
```
- 行标签 = index，列标签 = columns
- 每列可以是不同类型
- 支持 Excel/SQL 式的数据操作

## 索引三板斧

| 方式 | 语法 | 适用场景 |
|------|------|----------|
| `df['col']` | 列名 | 选一列或多列 |
| `df.loc[]` | 标签名 | 按标签索引（含末尾） |
| `df.iloc[]` | 数字位置 | 按位置索引（不含末尾） |

## 数据清洗三步走

1. **去重** → `drop_duplicates()`
2. **异常值** → IQR / Z-Score / 条件过滤
3. **缺失值** → `dropna()` / `fillna()` / `interpolate()`

## 分组聚合三部曲

```
Split → Apply → Combine
  ↓       ↓        ↓
groupby() .agg()  结果 DataFrame
```

## 合并三兄弟

| 方法 | 适用场景 | 关键参数 |
|------|----------|----------|
| `merge()` | 按键值关联（类似 SQL JOIN） | `on`, `how` |
| `concat()` | 简单拼接（行或列） | `axis`, `ignore_index` |
| `join()` | 按索引合并 | `how` |
