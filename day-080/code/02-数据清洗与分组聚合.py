"""
02-数据清洗与分组聚合.py
缺失值处理、重复值处理、GroupBy 分组聚合、透视表

运行：python3 02-数据清洗与分组聚合.py
"""
import pandas as pd
import numpy as np

print("=" * 60)
print("📚 Day 080 — 数据清洗与分组聚合")
print("=" * 60)

# ==================== 1. 生成含脏数据的数据集 ====================
print("\n🔹 1. 生成模拟脏数据")
print("-" * 40)

np.random.seed(42)
n = 200

raw_data = pd.DataFrame({
    '订单ID': [f'ORD-{i:05d}' for i in range(1, n + 1)],
    '日期': pd.date_range('2024-01-01', periods=n, freq='6h'),
    '产品类别': np.random.choice(['电子产品', '服装', '食品', '家居', '运动'], n),
    '金额': np.random.lognormal(mean=4.5, sigma=1.2, size=n).round(2),
    '数量': np.random.randint(1, 15, n),
    '地区': np.random.choice(['北京', '上海', '广州', '深圳', '杭州'], n),
    '客户等级': np.random.choice(['VIP', '普通', '新客户', None], n, p=[0.1, 0.4, 0.3, 0.2])
})

# 人为制造一些问题
# 重复行
dup_rows = raw_data.sample(5, random_state=1)
raw_data = pd.concat([raw_data, dup_rows], ignore_index=True)

# 金额中加入缺失值
mask = np.random.random(len(raw_data)) < 0.08
raw_data.loc[mask, '金额'] = np.nan

# 负数金额（异常值）
raw_data.loc[10, '金额'] = -50.0
raw_data.loc[50, '金额'] = -120.0

print(f"原始数据形状: {raw_data.shape}")
print(f"缺失值统计:\n{raw_data.isnull().sum()}")
print(f"重复行数: {raw_data.duplicated().sum()}")

# ==================== 2. 数据清洗 ====================
print("\n\n🔹 2. 数据清洗流程")
print("-" * 40)

df = raw_data.copy()

# Step 1: 删除完全重复的行
before = len(df)
df = df.drop_duplicates()
print(f"Step 1 — 去重: {before} → {len(df)} 行（删除 {before - len(df)} 行重复）")

# Step 2: 处理异常值（负数金额）
negative_count = (df['金额'] < 0).sum()
print(f"Step 2 — 发现 {negative_count} 条负数金额")
df = df[df['金额'] >= 0]
print(f"  已过滤，剩余 {len(df)} 行")

# Step 3: 缺失值处理
print(f"\nStep 3 — 处理缺失值:")
print(f"  金额缺失: {df['金额'].isnull().sum()} 条")
print(f"  客户等级缺失: {df['客户等级'].isnull().sum()} 条")

# 金额：用同类别的中位数填充
for cat in df['产品类别'].unique():
    median_val = df[df['产品类别'] == cat]['金额'].median()
    df.loc[(df['产品类别'] == cat) & (df['金额'].isna()), '金额'] = median_val

# 客户等级：填充为"未知"
df['客户等级'] = df['客户等级'].fillna('未知')

print(f"\n清洗后缺失值: {df.isnull().sum().sum()}")

# Step 4: 添加衍生列
df['单价'] = (df['金额'] / df['数量']).round(2)
df['月份'] = df['日期'].dt.month
df['星期'] = df['日期'].dt.dayofweek  # 0=周一

print(f"\n清洗后数据前 5 行:")
print(df.head().to_string(index=False))

# ==================== 3. GroupBy 分组聚合 ====================
print("\n\n🔹 3. GroupBy 分组聚合")
print("-" * 40)

# 3.1 单列分组
print("\n📊 按产品类别分组:")
cat_group = df.groupby('产品类别').agg(
    订单数=('订单ID', 'count'),
    总销售额=('金额', 'sum'),
    平均单价=('单价', 'mean'),
).round(2)
cat_group['销售额占比'] = (cat_group['总销售额'] / cat_group['总销售额'].sum() * 100).round(2)
print(cat_group.sort_values('总销售额', ascending=False))

# 3.2 多列分组
print("\n📊 按地区 × 产品类别分组:")
region_cat = df.groupby(['地区', '产品类别']).agg(
    订单数=('订单ID', 'count'),
    总销售额=('金额', 'sum')
).round(2)
print(region_cat.head(10))

# 3.3 自定义聚合
print("\n📊 自定义聚合 — 各地区销售额统计:")
region_stats = df.groupby('地区').agg(
    总销售额=('金额', 'sum'),
    平均销售额=('金额', 'mean'),
    最大单笔=('金额', 'max'),
    订单数=('订单ID', 'count'),
    销售额标准差=('金额', 'std')
).round(2)
print(region_stats.sort_values('总销售额', ascending=False))

# 3.4 transform — 保持原始形状
print("\n📊 transform — 计算每个订单占地区总额的比例:")
df['地区总销售额'] = df.groupby('地区')['金额'].transform('sum')
df['地区销售占比'] = (df['金额'] / df['地区总销售额'] * 100).round(2)
print(df[['订单ID', '地区', '金额', '地区总销售额', '地区销售占比']].head(10))

# ==================== 4. 透视表 ====================
print("\n\n🔹 4. 透视表")
print("-" * 40)

# 4.1 基本透视表
print("\n📊 地区 × 产品类别 销售额透视表:")
pivot1 = df.pivot_table(
    values='金额',
    index='地区',
    columns='产品类别',
    aggfunc='sum',
    margins=True,
    margins_name='合计'
).round(2)
print(pivot1)

# 4.2 多聚合透视表
print("\n📊 地区 × 产品类别 多指标透视表:")
pivot2 = df.pivot_table(
    values='金额',
    index='地区',
    columns='产品类别',
    aggfunc=['sum', 'mean', 'count']
).round(2)
print(pivot2.head(10))

# 4.3 月份趋势透视表
print("\n📊 月度 × 产品类别 销售趋势:")
monthly_pivot = df.pivot_table(
    values='金额',
    index='月份',
    columns='产品类别',
    aggfunc='sum'
).round(2)
print(monthly_pivot)

# ==================== 5. 客户等级分析 ====================
print("\n\n🔹 5. 客户等级分析")
print("-" * 40)

customer_stats = df.groupby('客户等级').agg(
    订单数=('订单ID', 'count'),
    总消费=('金额', 'sum'),
    平均客单价=('金额', 'mean'),
    平均数量=('数量', 'mean')
).round(2)
customer_stats['消费占比'] = (customer_stats['总消费'] / customer_stats['总消费'].sum() * 100).round(2)
print(customer_stats.sort_values('总消费', ascending=False))

print("\n✅ 数据清洗与分组聚合演示完成！")
