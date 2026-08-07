# Pandas 核心 API 速查表

## Series 操作

| 操作 | 语法 | 说明 |
|------|------|------|
| 创建 | `pd.Series(data, index=idx)` | 从数据创建 |
| 索引 | `s['label']` / `s.iloc[0]` | 标签/位置索引 |
| 切片 | `s['a':'c']` / `s[0:3]` | 注意标签切片包含末端 |
| 筛选 | `s[s > value]` | 布尔筛选 |
| 统计 | `s.mean()`, `s.std()`, `s.sum()` | 聚合统计 |
| 排序 | `s.sort_values()`, `s.sort_index()` | 按值/索引排序 |
| 唯一值 | `s.unique()`, `s.nunique()` | 去重 |
| 映射 | `s.map(dict)`, `s.apply(func)` | 值转换 |

## DataFrame 创建

| 方法 | 语法 | 说明 |
|------|------|------|
| 字典 | `pd.DataFrame({'col': data})` | 最常用 |
| 列表 | `pd.DataFrame([dict1, dict2])` | 每行一个字典 |
| NumPy | `pd.DataFrame(arr, columns=[])` | 从数组创建 |
| 读文件 | `pd.read_csv('file.csv')` | 从文件加载 |

## 数据查看

| 方法 | 说明 |
|------|------|
| `df.head(n)` | 前 n 行（默认 5） |
| `df.tail(n)` | 后 n 行 |
| `df.sample(n)` | 随机 n 行 |
| `df.shape` | (行数, 列数) |
| `df.info()` | 列名、类型、非空数 |
| `df.describe()` | 数值列统计摘要 |
| `df.dtypes` | 各列数据类型 |
| `df.columns` | 列名 |
| `df.index` | 行索引 |

## 数据选择

| 方式 | 语法 | 说明 |
|------|------|------|
| 单列 | `df['col']` | 返回 Series |
| 多列 | `df[['col1', 'col2']]` | 返回 DataFrame |
| 标签 | `df.loc[row, col]` | 按标签选择 |
| 位置 | `df.iloc[row, col]` | 按位置选择 |
| 布尔 | `df[df['col'] > val]` | 条件筛选 |
| 查询 | `df.query('col > val')` | 字符串表达式 |
| 范围 | `df[df['col'].between(a, b)]` | 范围筛选 |
| 列表 | `df[df['col'].isin(list)]` | 列表匹配 |
| 字符串 | `df[df['col'].str.contains('x')]` | 字符串匹配 |

## 数据清洗

| 操作 | 方法 | 说明 |
|------|------|------|
| 缺失值检测 | `df.isnull().sum()` | 每列缺失数 |
| 填充缺失值 | `df.fillna(value)` | 用指定值填充 |
| 删除缺失值 | `df.dropna()` | 删除含 NaN 的行 |
| 删除重复 | `df.drop_duplicates()` | 去重 |
| 类型转换 | `df['col'].astype(type)` | 转换数据类型 |
| 重命名列 | `df.rename(columns={old: new})` | 重命名 |
| 删除列 | `df.drop(columns=['col'])` | 删除指定列 |

## 数据聚合

| 操作 | 语法 | 说明 |
|------|------|------|
| 分组 | `df.groupby('col')` | 按列分组 |
| 聚合 | `df.groupby('col').agg(func)` | 分组聚合 |
| 透视表 | `df.pivot_table(values, index, columns)` | 交叉分析 |
| 交叉表 | `pd.crosstab(df['a'], df['b'])` | 频率统计 |

## 数据排序

| 操作 | 语法 | 说明 |
|------|------|------|
| 按值排序 | `df.sort_values('col')` | 升序（默认） |
| 多列排序 | `df.sort_values(['a', 'b'], ascending=[T, F])` | 多列 |
| 按索引排序 | `df.sort_index()` | 按索引排序 |
| 排名 | `df['col'].rank()` | 添加排名列 |

## 文件读写

| 格式 | 读取 | 写入 |
|------|------|------|
| CSV | `pd.read_csv(path)` | `df.to_csv(path, index=False)` |
| Excel | `pd.read_excel(path)` | `df.to_excel(path, index=False)` |
| JSON | `pd.read_json(path)` | `df.to_json(path, orient='records')` |
| Parquet | `pd.read_parquet(path)` | `df.to_parquet(path)` |

## apply 与映射

| 方法 | 说明 | 示例 |
|------|------|------|
| `df.apply(func)` | 对每行/列应用函数 | `df.apply(sum, axis=0)` |
| `df.applymap(func)` | 对每个元素应用函数 | `df.applymap(lambda x: x*2)` |
| `df['col'].map(dict)` | 用字典映射 | `df['col'].map({'A': 1, 'B': 2})` |
| `df['col'].apply(func)` | 对列每个值应用函数 | `df['col'].apply(len)` |
