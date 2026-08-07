# Pandas 进阶 API 速查表

## 数据清洗

| 操作 | 方法 | 说明 |
|------|------|------|
| 检测缺失 | `df.isnull()` | 布尔矩阵 |
| 缺失计数 | `df.isnull().sum()` | 每列计数 |
| 删除缺失 | `df.dropna()` | 删除含 NaN 行 |
| 填充缺失 | `df.fillna(value)` | 用值填充 |
| 前向填充 | `df.fillna(method='ffill')` | 用前一个值 |
| 后向填充 | `df.fillna(method='bfill')` | 用后一个值 |
| 插值 | `df.interpolate()` | 数学插值 |
| 检测重复 | `df.duplicated()` | 布尔标记 |
| 删除重复 | `df.drop_duplicates()` | 去重 |
| 替换值 | `df.replace(old, new)` | 替换特定值 |
| 截断 | `df.clip(lower, upper)` | 限制范围 |

## 分组聚合

| 操作 | 语法 | 说明 |
|------|------|------|
| 分组 | `df.groupby('col')` | 按列分组 |
| 聚合 | `.agg(func)` | 多函数聚合 |
| 转换 | `.transform(func)` | 保持原始行数 |
| 过滤 | `.filter(func)` | 筛选组 |
| 应用 | `.apply(func)` | 灵活操作 |

### agg 常用聚合函数

| 函数 | 说明 |
|------|------|
| `'mean'` | 均值 |
| `'sum'` | 求和 |
| `'count'` | 计数 |
| `'min'` / `'max'` | 最小/最大值 |
| `'std'` / `'var'` | 标准差/方差 |
| `'first'` / `'last'` | 首/末值 |
| `'nunique'` | 唯一值数 |

## 合并连接

| 方法 | 语法 | 说明 |
|------|------|------|
| merge | `pd.merge(a, b, on='key', how='inner')` | 类似 SQL JOIN |
| concat | `pd.concat([a, b], axis=0)` | 拼接 |
| join | `a.join(b, on='key')` | 按索引合并 |

### merge how 参数

| 值 | 说明 |
|------|------|
| `'inner'` | 内连接（交集） |
| `'left'` | 左连接（保留左表） |
| `'right'` | 右连接（保留右表） |
| `'outer'` | 外连接（并集） |

## 时间序列

| 操作 | 语法 | 说明 |
|------|------|------|
| 日期范围 | `pd.date_range(start, periods, freq)` | 创建日期序列 |
| 日期组件 | `df['date'].dt.year/month/day` | 提取年月日 |
| 重采样 | `df.resample('M').sum()` | 按时间汇总 |
| 滚动窗口 | `df.rolling(7).mean()` | 移动平均 |
| 指数平均 | `df.ewm(span=7).mean()` | 指数移动平均 |
| 日期偏移 | `df['date'] + pd.DateOffset(months=1)` | 日期加减 |

### resample 频率代码

| 代码 | 说明 | 代码 | 说明 |
|------|------|------|------|
| `'D'` | 日 | `'W'` | 周 |
| `'M'` | 月末 | `'Q'` | 季末 |
| `'Y'` | 年末 | `'H'` | 小时 |
| `'T'` / `'min'` | 分钟 | `'S'` | 秒 |

## 透视表与交叉表

| 方法 | 语法 | 说明 |
|------|------|------|
| pivot_table | `pd.pivot_table(df, values, index, columns, aggfunc)` | 透视表 |
| crosstab | `pd.crosstab(df['a'], df['b'])` | 频率交叉表 |

## 字符串操作

| 方法 | 说明 |
|------|------|
| `df['col'].str.contains('x')` | 包含 |
| `df['col'].str.startswith('x')` | 开头 |
| `df['col'].str.endswith('x')` | 结尾 |
| `df['col'].str.replace('a', 'b')` | 替换 |
| `df['col'].str.split('x')` | 分割 |
| `df['col'].str.upper()` / `.lower()` | 大小写 |
| `df['col'].str.strip()` | 去空白 |
| `df['col'].str.len()` | 字符长度 |
