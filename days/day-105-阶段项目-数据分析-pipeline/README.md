# Day 105 — 阶段项目：数据分析 Pipeline

> 📅 日期：Day 105 / 200 | 🏷️ 阶段：Phase 7 — 进阶与性能优化 | 📌 子主题：实战

---

## 目录

1. [Pipeline 概念与架构](#1-pipeline-概念与架构)
2. [数据获取：API 与 CSV](#2-数据获取api-与-csv)
3. [数据清洗实战](#3-数据清洗实战)
4. [数据探索与分析](#4-数据探索与分析)
5. [可视化报告输出](#5-可视化报告输出)
6. [完整 Pipeline 项目实战](#6-完整-pipeline-项目实战)
7. [思考题](#7-思考题)

---

## 1. Pipeline 概念与架构

### 1.1 什么是数据分析 Pipeline？

数据分析 Pipeline 是将原始数据转化为可操作洞察的**自动化工作流**。它不是一个单一的脚本，而是一系列**有序、可复用、可监控**的处理步骤。

```
┌─────────────────────────────────────────────────────┐
│              数据分析 Pipeline 架构                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  数据源        ETL 处理         分析层      输出层   │
│                                                     │
│  ┌────┐    ┌──────────┐    ┌─────────┐  ┌───────┐ │
│  │ API │───▶│ Extract  │───▶│ Clean   │─▶│ EDA   │ │
│  └────┘    │          │    │         │  │       │ │
│  ┌────┐    │ Transform│    │ Analyze │  │ Report│ │
│  │ CSV │───▶│          │───▶│         │─▶│       │ │
│  └────┘    │          │    │         │  │       │ │
│  ┌────┐    │ Load     │    │ Visual  │  │ Alert │ │
│  │ DB  │───▶│          │───▶│         │─▶│       │ │
│  └────┘    └──────────┘    └─────────┘  └───────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 1.2 Pipeline 设计原则

| 原则 | 说明 | 实践方法 |
|------|------|---------|
| **模块化** | 每个步骤独立 | 每个函数只做一件事 |
| **可配置** | 参数外部化 | 使用配置文件/YAML |
| **可追踪** | 记录处理过程 | 日志 + 数据血缘 |
| **可复现** | 相同输入得相同输出 | 随机种子 + 版本控制 |
| **容错性** | 单步失败不影响全局 | 异常处理 + 重试机制 |
| **可观测** | 运行状态透明 | 进度条 + 指标监控 |

### 1.3 ETL 模式详解

```
Extract（抽取）                Transform（转换）           Load（加载）
┌──────────────┐              ┌──────────────┐           ┌──────────────┐
│ • 读取文件    │              │ • 缺失值处理  │           │ • 写入文件    │
│ • API 调用    │   ──────▶    │ • 类型转换    │  ──────▶  │ • 推送数据库  │
│ • 爬虫抓取    │              │ • 特征工程    │           │ • 输出报告    │
│ • 数据库查询  │              │ • 数据聚合    │           │ • 发送通知    │
└──────────────┘              └──────────────┘           └──────────────┘
```

---

## 2. 数据获取：API 与 CSV

### 2.1 CSV 文件读写

```python
import pandas as pd

# 读取 CSV
df = pd.read_csv('data.csv', encoding='utf-8', parse_dates=['date'])

# 写入 CSV
df.to_csv('output.csv', index=False, encoding='utf-8')
```

**常用参数速查：**

| 参数 | 用途 | 示例 |
|------|------|------|
| `encoding` | 编码格式 | `'utf-8'`, `'gbk'` |
| `parse_dates` | 自动解析日期列 | `['date_col']` |
| `index_col` | 指定索引列 | `['id']` |
| `usecols` | 只读取指定列 | `['name', 'age']` |
| `dtype` | 指定列类型 | `{'id': str}` |
| `na_values` | 自定义缺失值 | `['N/A', '-']` |
| `skiprows` | 跳过前 N 行 | `3` |
| `nrows` | 只读前 N 行 | `1000` |

### 2.2 API 数据获取

```python
import requests
import pandas as pd

def fetch_api_data(url, params=None, headers=None):
    """通用 API 数据获取"""
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data)
    except requests.RequestException as e:
        print(f"API 请求失败: {e}")
        return pd.DataFrame()

# 使用示例：获取 GitHub 趋势项目
url = 'https://api.github.com/search/repositories'
params = {'q': 'language:python', 'sort': 'stars', 'per_page': 10}
df = fetch_api_data(url, params)
```

### 2.3 数据源选择指南

| 数据源 | 优点 | 缺点 | 适用场景 |
|--------|------|------|---------|
| CSV | 简单、通用 | 不支持复杂类型 | 本地数据 |
| JSON API | 实时、灵活 | 有请求限制 | 实时数据 |
| 数据库 | 高效、可扩展 | 需要连接配置 | 企业数据 |
| Excel | 格式丰富 | 大文件慢 | 业务报表 |

---

## 3. 数据清洗实战

### 3.1 常见脏数据类型

```
原始数据（脏）
├── 缺失值：NaN, None, '', 'N/A'
├── 重复行：完全重复 / 部分重复
├── 类型错误：字符串存数字、日期格式混乱
├── 异常值：超出合理范围的数值
├── 格式不一致：'北京' vs 'BJ' vs 'beijing'
└── 编码问题：乱码、特殊字符
```

### 3.2 缺失值处理策略

```python
import pandas as pd
import numpy as np

# 检查缺失值
print(df.isnull().sum())
print(f"缺失率:\n{df.isnull().mean() * 100:.2f}%")

# 策略 1: 删除（缺失率 > 50% 或行数少）
df.dropna(subset=['critical_col'], inplace=True)

# 策略 2: 填充
df['age'].fillna(df['age'].median(), inplace=True)  # 数值用中位数
df['city'].fillna(df['city'].mode()[0], inplace=True)  # 分类用众数

# 策略 3: 插值（时间序列）
df['price'].interpolate(method='linear', inplace=True)

# 策略 4: 标记
df['missing_flag'] = df['col'].isnull().astype(int)
```

**缺失值处理决策树：**

```
缺失值比例是多少？
│
├── < 5%  → 删除缺失行
├── 5-30% → 填充（数值→中位数，分类→众数）
├── 30-50% → 插值 或 添加缺失标记
└── > 50% → 考虑删除该列 / 用模型预测填充
```

### 3.3 异常值检测

```python
# 方法 1: IQR（四分位距）
Q1 = df['price'].quantile(0.25)
Q3 = df['price'].quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR
outliers = df[(df['price'] < lower) | (df['price'] > upper)]

# 方法 2: Z-score
from scipy import stats
z_scores = stats.zscore(df['price'])
outliers = df[np.abs(z_scores) > 3]

# 方法 3: 可视化检测
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.boxplot(df['price'])
ax.set_title('Price Distribution - Outlier Detection')
plt.show()
```

### 3.4 数据类型转换

```python
# 日期转换
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')

# 类型强制转换
df['id'] = df['id'].astype(str)
df['amount'] = pd.to_numeric(df['amount'], errors='coerce')  # 错误值变 NaN

# 分类类型（节省内存）
df['status'] = df['status'].astype('category')

# 字符串处理
df['name'] = df['name'].str.strip().str.lower()
```

---

## 4. 数据探索与分析

### 4.1 探索性分析流程

```
Step 1: 全貌扫描
├── df.shape → 数据规模
├── df.info() → 数据类型
├── df.describe() → 统计摘要
└── df.head() → 数据预览

Step 2: 分布分析
├── 数值列 → 直方图、箱线图
├── 分类列 → 计数图、占比
└── 时间列 → 趋势折线

Step 3: 关系分析
├── 相关性 → 热力图
├── 分组对比 → groupby + 聚合
└── 交叉分析 → 交叉表

Step 4: 洞察提炼
├── 关键发现 → Top 3-5 结论
├── 异常模式 → 需要深入调查的点
└── 行动建议 → 基于数据的决策
```

### 4.2 Pandas 分析技巧

```python
# 快速统计
df.describe(include='all')

# 分组聚合
df.groupby('category')['revenue'].agg(['mean', 'median', 'std', 'count'])

# 透视表
pd.pivot_table(df, values='sales', index='region',
               columns='quarter', aggfunc='sum', fill_value=0)

# 日期分析
df['month'] = df['date'].dt.month
df['dayofweek'] = df['date'].dt.dayofweek
monthly = df.groupby('month')['revenue'].sum()
```

---

## 5. 可视化报告输出

### 5.1 自动化报告生成

```python
def generate_report(df, output_path='report.html'):
    """生成 HTML 格式的分析报告"""
    from jinja2 import Template

    template = Template("""
    <html>
    <head><title>Data Analysis Report</title></head>
    <body>
    <h1>数据分析报告</h1>
    <h2>数据概览</h2>
    <p>行数: {{ rows }} | 列数: {{ cols }}</p>
    <h2>统计摘要</h2>
    {{ stats }}
    <h2>关键发现</h2>
    {{ findings }}
    </body>
    </html>
    """)

    stats_html = df.describe().to_html()
    html = template.render(rows=len(df), cols=len(df.columns),
                           stats=stats_html, findings='<p>TODO</p>')
    with open(output_path, 'w') as f:
        f.write(html)
```

### 5.2 报告输出格式

| 格式 | 优点 | 适用场景 |
|------|------|---------|
| HTML | 交互式、美观 | Web 展示 |
| PDF | 打印友好 | 正式报告 |
| Markdown | 版本控制 | 技术文档 |
| Excel | 业务友好 | 数据共享 |

---

## 6. 完整 Pipeline 项目实战

### 6.1 项目：电商销售数据分析

下面是一个完整的数据分析 Pipeline，从数据获取到报告输出：

```python
"""
电商销售数据分析 Pipeline
完整流程：数据获取 → 清洗 → 分析 → 可视化 → 报告
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
import os

# ============================================================
# Step 1: 数据获取
# ============================================================
print("=" * 60)
print("📥 Step 1: 数据获取")
print("=" * 60)

# 模拟电商数据（实际项目中可替换为 API/CSV/数据库读取）
np.random.seed(42)
n_orders = 500

data = {
    'order_id': range(1001, 1001 + n_orders),
    'date': pd.date_range('2024-01-01', periods=n_orders, freq='4h'),
    'product': np.random.choice(['iPhone', 'MacBook', 'iPad', 'AirPods', 'Apple Watch'], n_orders),
    'category': np.random.choice(['手机', '电脑', '平板', '配件', '穿戴'], n_orders),
    'quantity': np.random.randint(1, 5, n_orders),
    'unit_price': np.random.choice([5999, 9999, 3999, 1299, 2999], n_orders),
    'region': np.random.choice(['华东', '华南', '华北', '西南', '西北'], n_orders),
    'customer_age': np.random.randint(18, 65, n_orders),
    'payment_method': np.random.choice(['支付宝', '微信', '银行卡', '花呗'], n_orders),
}

df = pd.DataFrame(data)
df['total_price'] = df['quantity'] * df['unit_price']

# 故意注入脏数据
dirty_indices = np.random.choice(n_orders, 20, replace=False)
df.loc[dirty_indices[:5], 'unit_price'] = np.nan
df.loc[dirty_indices[5:10], 'region'] = ''
df.loc[dirty_indices[10:15], 'customer_age'] = -1
df = pd.concat([df, df.iloc[:3]])  # 重复行

print(f"✅ 数据获取完成: {len(df)} 条订单")
print(f"📊 数据形状: {df.shape}")

# ============================================================
# Step 2: 数据清洗
# ============================================================
print("\n" + "=" * 60)
print("🧹 Step 2: 数据清洗")
print("=" * 60)

# 2.1 删除重复行
before = len(df)
df.drop_duplicates(inplace=True)
print(f"  去重: {before} → {len(df)} 条 (删除 {before - len(df)} 条重复)")

# 2.2 处理缺失值
missing_before = df.isnull().sum().sum()
df['unit_price'].fillna(df['unit_price'].median(), inplace=True)
df['region'].replace('', np.nan, inplace=True)
df['region'].fillna(df['region'].mode()[0], inplace=True)
missing_after = df.isnull().sum().sum()
print(f"  缺失值: {missing_before} → {missing_after}")

# 2.3 处理异常值
df['customer_age'] = df['customer_age'].clip(lower=0, upper=100)
invalid_age = (df['customer_age'] < 0).sum()
print(f"  年龄异常值: {invalid_age} 条已修正")

# 2.4 类型转换
df['date'] = pd.to_datetime(df['date'])
df['category'] = df['category'].astype('category')
df['region'] = df['region'].astype('category')

# 重新计算
df['total_price'] = df['quantity'] * df['unit_price']

print(f"✅ 清洗完成: {len(df)} 条有效数据")

# ============================================================
# Step 3: 数据分析
# ============================================================
print("\n" + "=" * 60)
print("📊 Step 3: 数据分析")
print("=" * 60)

# 3.1 基本统计
print(f"\n📋 数据概览:")
print(f"  时间范围: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"  总订单数: {len(df)}")
print(f"  总销售额: ¥{df['total_price'].sum():,.0f}")
print(f"  平均客单价: ¥{df['total_price'].mean():,.0f}")

# 3.2 分组分析
print(f"\n📊 Top 3 产品 (按销售额):")
product_sales = df.groupby('product')['total_price'].sum().sort_values(ascending=False)
for i, (prod, sales) in enumerate(product_sales.head(3).items(), 1):
    print(f"  {i}. {prod}: ¥{sales:,.0f}")

print(f"\n📊 各区域销售占比:")
region_sales = df.groupby('region')['total_price'].sum()
region_pct = (region_sales / region_sales.sum() * 100).sort_values(ascending=False)
for region, pct in region_pct.items():
    print(f"  {region}: {pct:.1f}%")

# 3.3 月度趋势
df['month'] = df['date'].dt.month
monthly_sales = df.groupby('month')['total_price'].sum()

print(f"\n📊 月度销售趋势:")
for month, sales in monthly_sales.items():
    bar = '█' * int(sales / monthly_sales.max() * 30)
    print(f"  {month:2d}月: {bar} ¥{sales:,.0f}")

# ============================================================
# Step 4: 可视化
# ============================================================
print("\n" + "=" * 60)
print("📈 Step 4: 可视化")
print("=" * 60)

plt.style.use('seaborn-v0_8')
fig = plt.figure(figsize=(18, 12))
fig.suptitle('🛒 E-Commerce Sales Analysis Report', fontsize=16, fontweight='bold')

# 图1: 产品销售额
ax1 = fig.add_subplot(2, 3, 1)
product_sales.plot(kind='bar', ax=ax1, color=sns.color_palette('husl', 5))
ax1.set_title('Sales by Product', fontsize=12)
ax1.set_ylabel('Revenue (¥)')
ax1.tick_params(axis='x', rotation=45)

# 图2: 区域占比
ax2 = fig.add_subplot(2, 3, 2)
region_pct.plot(kind='pie', ax=ax2, autopct='%1.1f%%', colors=sns.color_palette('pastel'))
ax2.set_title('Revenue by Region', fontsize=12)
ax2.set_ylabel('')

# 图3: 月度趋势
ax3 = fig.add_subplot(2, 3, 3)
monthly_sales.plot(kind='line', ax=ax3, marker='o', linewidth=2)
ax3.fill_between(monthly_sales.index, monthly_sales.values, alpha=0.2)
ax3.set_title('Monthly Revenue Trend', fontsize=12)
ax3.set_xlabel('Month')
ax3.set_ylabel('Revenue (¥)')

# 图4: 支付方式
ax4 = fig.add_subplot(2, 3, 4)
payment_sales = df.groupby('payment_method')['total_price'].sum().sort_values()
payment_sales.plot(kind='barh', ax=ax4, color=sns.color_palette('coolwarm', 4))
ax4.set_title('Payment Method Distribution', fontsize=12)
ax4.set_xlabel('Revenue (¥)')

# 图5: 客户年龄分布
ax5 = fig.add_subplot(2, 3, 5)
ax5.hist(df['customer_age'], bins=20, edgecolor='black', alpha=0.7, color='steelblue')
ax5.axvline(df['customer_age'].mean(), color='red', linestyle='--', label=f'Mean={df["customer_age"].mean():.0f}')
ax5.set_title('Customer Age Distribution', fontsize=12)
ax5.set_xlabel('Age')
ax5.legend()

# 图6: 产品 × 区域 热力图
ax6 = fig.add_subplot(2, 3, 6)
pivot = df.pivot_table(values='total_price', index='product', columns='region', aggfunc='sum')
sns.heatmap(pivot, annot=True, fmt='.0f', cmap='YlOrRd', ax=ax6, cbar_kws={'shrink': 0.8})
ax6.set_title('Product × Region Heatmap', fontsize=12)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig('sales_analysis_report.png', dpi=150, bbox_inches='tight')
print("✅ sales_analysis_report.png saved")

# ============================================================
# Step 5: 输出报告
# ============================================================
print("\n" + "=" * 60)
print("📝 Step 5: 输出报告")
print("=" * 60)

report = {
    'generated_at': datetime.now().isoformat(),
    'data_period': f"{df['date'].min().date()} ~ {df['date'].max().date()}",
    'total_orders': len(df),
    'total_revenue': float(df['total_price'].sum()),
    'avg_order_value': float(df['total_price'].mean()),
    'top_product': product_sales.index[0],
    'top_region': region_pct.index[0],
    'key_findings': [
        f"总销售额 ¥{df['total_price'].sum():,.0f}，共 {len(df)} 笔订单",
        f"最畅销产品: {product_sales.index[0]} (¥{product_sales.iloc[0]:,.0f})",
        f"最大市场: {region_pct.index[0]} ({region_pct.iloc[0]:.1f}%)",
        f"客户平均年龄: {df['customer_age'].mean():.0f} 岁",
    ]
}

with open('analysis_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print("✅ analysis_report.json saved")

print("\n" + "=" * 60)
print("🎉 Pipeline 执行完成！")
print("=" * 60)
```

---

## 7. 思考题

### 🤔 思考题

1. **在实际项目中，数据清洗通常占分析工作的 60-80%。** 你会如何设计一个可复用的数据清洗模块？需要考虑哪些边界情况？

2. **Pipeline 的每一步都可能失败。** 如何设计错误处理策略，使得单步失败不会导致整个 Pipeline 崩溃？请描述你的方案。

3. **数据量从 1 万增长到 1 亿时，你的 Pipeline 需要做哪些调整？** 列出至少 3 个性能优化方向。

4. **如何确保 Pipeline 的可复现性？** 也就是说，同样的输入数据和代码，每次运行的结果完全一致。需要控制哪些变量？

5. **当分析结果与业务预期不符时，你会如何排查？** 请列出你的 debug 流程。

---

## 📚 延伸阅读

- [Python Data Science Handbook](https://jakevdp.github.io/PythonDataScienceHandbook/)
- [Pandas 官方文档 - Missing Data](https://pandas.pydata.org/docs/user_guide/missing_data.html)
- [数据清洗最佳实践](https://towardsdatascience.com/data-cleaning-in-python/)
- [ETL Pipeline 设计模式](https://www.enterprise-integration-patterns.com/)
