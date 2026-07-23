# Pandas 常见陷阱与避坑指南

## 🚫 陷阱 1：链式赋值警告

```python
# ❌ 错误：链式赋值（SettingWithCopyWarning）
df[df['A'] > 5]['B'] = 0

# ✅ 正确：使用 loc
df.loc[df['A'] > 5, 'B'] = 0
```

**原因：** 链式赋值可能返回视图或副本，Python 无法确定你要修改哪个对象。

## 🚫 陷阱 2：切片行为不一致

```python
# loc 切片包含末尾标签
df.loc[0:2]  # 包含标签 0, 1, 2

# iloc 切片不包含末尾位置（与 Python list 一致）
df.iloc[0:2]  # 只包含位置 0, 1
```

## 🚫 陷阱 3：布尔索引要用括号

```python
# ❌ 错误：运算符优先级问题
df[df['A'] > 5 and df['B'] < 10]  # 报错！

# ✅ 正确：用 & | ~ 并加括号
df[(df['A'] > 5) & (df['B'] < 10)]
```

## 🚫 陷阱 4：原地修改 vs 返回新对象

```python
# dropna 默认不修改原 DataFrame
df = df.dropna()  # 需要重新赋值

# 但有些操作会修改原 DataFrame
df.drop(columns=['A'], inplace=True)  # 直接修改

# 推荐：始终使用赋值方式，避免 inplace
df = df.dropna()
df = df.drop(columns=['A'])
```

## 🚫 陷阱 5：groupby 后的索引

```python
# groupby 默认会把分组列变成索引
df.groupby('A')['B'].mean()
# 如果不想让 A 变成索引：
df.groupby('A', as_index=False)['B'].mean()
```

## 🚫 陷阱 6：read_csv 的 dtype 陷阱

```python
# ID 列如果用数字读取，前导零会丢失
df = pd.read_csv('data.csv', dtype={'ID': str})  # 保持字符串

# 日期列需要显式解析
df = pd.read_csv('data.csv', parse_dates=['date_col'])
```

## 🚫 陷阱 7：DataFrame 合并产生重复列名

```python
# 如果两个表有同名列（非合并键），会自动加后缀
pd.merge(df1, df2, on='key')
# 结果可能有 col_x, col_y

# 解决：显式指定后缀
pd.merge(df1, df2, on='key', suffixes=('_左', '_右'))
```

## ✅ 最佳实践

1. **始终检查 `df.shape` 和 `df.info()`** — 了解数据规模和类型
2. **用 `loc`/`iloc` 代替直接索引** — 更明确、更安全
3. **先 `copy()` 再操作** — 避免修改原始数据
4. **大文件用 `chunksize`** — 避免内存溢出
5. **合并前检查键的唯一性** — 避免数据膨胀
