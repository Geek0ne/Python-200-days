# Day 080 — Pandas 数据分析 · 图解

---

## 1. Pandas 数据结构关系图

```mermaid
classDiagram
    class Series {
        +values: ndarray
        +index: Index
        +name: str
        +mean()
        +max()
        +min()
        +to_dict()
    }
    
    class DataFrame {
        +columns: Index
        +index: Index
        +dtypes: Series
        +shape: tuple
        +describe()
        +info()
        +head()
    }
    
    class ndarray {
        +dtype: dtype
        +shape: tuple
    }
    
    DataFrame "1" --> "*" Series : 每列是一个 Series
    Series "1" --> "1" ndarray : 底层数据
    DataFrame "1" --> "1" ndarray : 内部存储
```

---

## 2. loc vs iloc 索引对比

```
原始 DataFrame:
┌─────┬──────┬──────┬──────┐
│ idx │  A   │  B   │  C   │  ← columns（列标签）
├─────┼──────┼──────┼──────┤
│  0  │ 10   │ 20   │ 30   │
│  1  │ 15   │ 25   │ 35   │  ← index（行标签）
│  2  │ 20   │ 30   │ 40   │
│  3  │ 25   │ 35   │ 45   │
└─────┴──────┴──────┴──────┘

loc[0:2, 'A':'B']     iloc[0:2, 0:2]
┌─────┬──────┬──────┐  ┌─────┬──────┬──────┐
│ idx │  A   │  B   │  │ idx │  A   │  B   │
├─────┼──────┼──────┤  ├─────┼──────┼──────┤
│  0  │ 10   │ 20   │  │  0  │ 10   │ 20   │
│  1  │ 15   │ 25   │  │  1  │ 15   │ 25   │
│  2  │ 20   │ 30   │  │  2  │ 20   │ 30   │
└─────┴──────┴──────┘  └─────┴──────┴──────┘
  ↑ 包含末尾标签 2        ↑ 不包含末尾位置 2

关键区别：loc 切片包含末尾，iloc 切片不包含末尾（与 Python 一致）
```

---

## 3. GroupBy 分组聚合流程

```mermaid
flowchart TD
    A[原始数据 DataFrame] --> B{按某列分组}
    B --> C1[组1: 销售部]
    B --> C2[组2: 技术部]
    B --> C3[组3: 人事部]
    
    C1 --> D1[apply 聚合函数]
    C2 --> D2[apply 聚合函数]
    C3 --> D3[apply 聚合函数]
    
    D1 --> E[合并结果 DataFrame]
    D2 --> E
    D3 --> E
    
    E --> F[输出统计结果]
```

---

## 4. 数据合并类型对比

```mermaid
flowchart LR
    subgraph 数据源
        A[employees 表]
        B[departments 表]
    end
    
    A --> C{合并方式}
    B --> C
    
    C -->|inner| D[内连接: 只保留两边都有的]
    C -->|left| E[左连接: 保留左表所有行]
    C -->|right| F[右连接: 保留右表所有行]
    C -->|outer| G[外连接: 保留所有行]
    
    style D fill:#90EE90
    style E fill:#ADD8E6
    style F fill:#FFB6C1
    style G fill:#FFD700
```

---

## 5. 数据分析工作流

```mermaid
flowchart TD
    A[数据源] -->|读取| B[DataFrame]
    B --> C{数据质量检查}
    C -->|缺失值| D[填充/删除]
    C -->|重复值| E[去重]
    C -->|异常值| F[过滤/截断]
    D --> G[清洗后数据]
    E --> G
    F --> G
    G --> H[探索性分析]
    H --> I[统计摘要]
    H --> J[分组聚合]
    H --> K[透视表]
    I --> L[可视化]
    J --> L
    K --> L
    L --> M[分析报告]
```

---

## 6. Pandas 常用操作速查

| 操作 | 语法 | 说明 |
|------|------|------|
| 创建 | `pd.DataFrame(dict)` | 从字典创建 |
| 读取 CSV | `pd.read_csv('file.csv')` | 读取 CSV 文件 |
| 写入 CSV | `df.to_csv('file.csv')` | 写入 CSV 文件 |
| 查看形状 | `df.shape` | (行数, 列数) |
| 查看列名 | `df.columns` | 列标签 |
| 列选择 | `df['col']` 或 `df[['col1','col2']]` | 单列或多列 |
| 行筛选 | `df[df['col'] > value]` | 布尔索引 |
| loc 索引 | `df.loc[行标签, 列标签]` | 基于标签 |
| iloc 索引 | `df.iloc[行位置, 列位置]` | 基于位置 |
| 缺失值 | `df.isnull().sum()` | 统计缺失值 |
| 填充 | `df.fillna(value)` | 填充缺失值 |
| 去重 | `df.drop_duplicates()` | 删除重复行 |
| 分组 | `df.groupby('col').agg(...)` | 分组聚合 |
| 透视表 | `df.pivot_table(...)` | 交叉分析 |
| 排序 | `df.sort_values('col')` | 按值排序 |
| 合并 | `pd.merge(df1, df2, on='key')` | 表连接 |
| 拼接 | `pd.concat([df1, df2])` | 简单拼接 |
