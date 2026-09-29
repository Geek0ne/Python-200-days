"""
03-数据读取合并实战.py
CSV 读写、DataFrame 合并（merge/concat）、完整实战案例

运行：python3 03-数据读取合并实战.py
"""
import pandas as pd
import numpy as np
import os
import tempfile

print("=" * 60)
print("📚 Day 080 — 数据读取与合并实战")
print("=" * 60)

# ==================== 1. CSV 读写 ====================
print("\n🔹 1. CSV 读写操作")
print("-" * 40)

# 创建示例数据
np.random.seed(42)
n = 100

orders = pd.DataFrame({
    '订单ID': [f'ORD-{i:05d}' for i in range(1, n + 1)],
    '客户ID': np.random.choice([f'C{i:03d}' for i in range(1, 21)], n),
    '产品ID': np.random.choice([f'P{i:03d}' for i in range(1, 11)], n),
    '数量': np.random.randint(1, 10, n),
    '单价': np.random.choice([29.9, 49.9, 99.9, 149.9, 199.9], n),
    '日期': pd.date_range('2024-01-01', periods=n, freq='D'),
    '状态': np.random.choice(['已完成', '待发货', '已取消', '退款中'], n, p=[0.6, 0.2, 0.1, 0.1])
})
orders['总金额'] = (orders['数量'] * orders['单价']).round(2)

# 创建产品信息表
products = pd.DataFrame({
    '产品ID': [f'P{i:03d}' for i in range(1, 11)],
    '产品名称': ['iPhone', 'iPad', 'AirPods', 'MacBook', 'Apple Watch',
              '充电器', '数据线', '保护壳', '耳机套', '屏幕膜'],
    '类别': ['电子产品', '电子产品', '电子产品', '电子产品', '电子产品',
            '配件', '配件', '配件', '配件', '配件'],
    '成本价': [500, 300, 80, 800, 250, 15, 8, 5, 3, 2]
})

# 写入 CSV
csv_path = '/tmp/orders.csv'
csv_product_path = '/tmp/products.csv'
orders.to_csv(csv_path, index=False, encoding='utf-8-sig')
products.to_csv(csv_product_path, index=False, encoding='utf-8-sig')
print(f"✅ 订单数据已写入: {csv_path}")
print(f"✅ 产品数据已写入: {csv_product_path}")

# 读取 CSV
df_orders = pd.read_csv(csv_path, parse_dates=['日期'])
df_products = pd.read_csv(csv_product_path)
print(f"\n订单数据: {df_orders.shape}")
print(f"产品数据: {df_products.shape}")

# 高级读取选项演示
print("\n📊 高级读取选项:")
# 只读取指定列
df_partial = pd.read_csv(csv_path, usecols=['订单ID', '客户ID', '总金额'])
print(f"  只读3列: {df_partial.shape}")

# 类型指定
df_typed = pd.read_csv(csv_path, dtype={'客户ID': str})
print(f"  指定类型: {df_typed.dtypes['客户ID']}")

# ==================== 2. DataFrame 合并 ====================
print("\n\n🔹 2. DataFrame 合并操作")
print("-" * 40)

# 创建客户信息表
customers = pd.DataFrame({
    '客户ID': [f'C{i:03d}' for i in range(1, 16)],  # 只有 15 个客户
    '姓名': [f'客户{i}' for i in range(1, 16)],
    '城市': np.random.choice(['北京', '上海', '广州', '深圳'], 15),
    '会员等级': np.random.choice(['金牌', '银牌', '铜牌'], 15)
})

# 创建产品详情表（含部分不匹配的产品）
product_details = pd.DataFrame({
    '产品ID': [f'P{i:03d}' for i in range(1, 13)],  # 有 12 个产品
    '供应商': [f'供应商{i}' for i in range(1, 13)],
    '库存': np.random.randint(10, 500, 12)
})

# 2.1 内连接（inner join）
print("\n📊 内连接 — 只保留两边都有的客户:")
inner_merged = pd.merge(df_orders, customers, on='客户ID', how='inner')
print(f"  订单数: {len(df_orders)} → 内连接后: {len(inner_merged)}")

# 2.2 左连接（left join）
print("\n📊 左连接 — 保留所有订单，客户信息可选:")
left_merged = pd.merge(df_orders, customers, on='客户ID', how='left')
missing_customers = left_merged['姓名'].isnull().sum()
print(f"  订单数: {len(left_merged)}")
print(f"  无匹配客户信息的订单: {missing_customers} 条")

# 2.3 右连接
print("\n📊 右连接 — 保留所有客户，即使没订单:")
right_merged = pd.merge(df_orders, customers, on='客户ID', how='right')
customers_with_orders = right_merged['订单ID'].notnull().sum()
print(f"  有订单的客户: {customers_with_orders}/{len(customers)}")

# 2.4 外连接
print("\n📊 外连接 — 保留所有记录:")
outer_merged = pd.merge(
    df_orders, product_details,
    on='产品ID', how='outer'
)
print(f"  外连接结果: {len(outer_merged)} 行")

# 2.5 不同键名合并
print("\n📊 不同键名合并:")
# 模拟：订单表的客户ID列名改为 customer_id
df_orders_renamed = df_orders.rename(columns={'客户ID': 'customer_id'})
merged = pd.merge(
    df_orders_renamed, customers,
    left_on='customer_id', right_on='客户ID',
    how='inner'
)
print(f"  用 left_on/right_on 合并: {len(merged)} 行")

# ==================== 3. concat 拼接 ====================
print("\n\n🔹 3. concat 拼接操作")
print("-" * 40)

# 模拟两个月的订单
orders_jan = orders.head(30).copy()
orders_jan['月份'] = '1月'
orders_feb = orders.iloc[30:60].copy()
orders_feb['月份'] = '2月'

# 纵向拼接（行增加）
combined = pd.concat([orders_jan, orders_feb], ignore_index=True)
print(f"纵向拼接: {len(orders_jan)} + {len(orders_feb)} = {len(combined)} 行")

# 横向拼接（列增加）
summary = orders.groupby('状态').agg(
    订单数=('订单ID', 'count'),
    总金额=('总金额', 'sum')
).round(2)
detail = orders.groupby('状态')['数量'].mean().round(1).rename('平均数量')
side_by_side = pd.concat([summary, detail], axis=1)
print(f"\n横向拼接结果:")
print(side_by_side)

# ==================== 4. 完整实战案例 ====================
print("\n\n🔹 4. 完整实战案例 — 电商数据分析报告")
print("-" * 40)

# 合并所有数据
full_data = pd.merge(df_orders, products, on='产品ID', how='left')
full_data['利润'] = (full_data['总金额'] - full_data['数量'] * full_data['成本价']).round(2)
full_data['利润率'] = (full_data['利润'] / full_data['总金额'] * 100).round(2)

print("\n📊 分析报告 1 — 各产品利润分析:")
product_profit = full_data.groupby(['产品ID', '产品名称']).agg(
    销量=('数量', 'sum'),
    总收入=('总金额', 'sum'),
    总成本=('成本价', lambda x: (x * full_data.loc[x.index, '数量']).sum()),
    总利润=('利润', 'sum'),
    平均利润率=('利润率', 'mean')
).round(2)
print(product_profit.sort_values('总利润', ascending=False))

print("\n📊 分析报告 2 — 各状态订单分析:")
status_analysis = full_data.groupby('状态').agg(
    订单数=('订单ID', 'count'),
    总金额=('总金额', 'sum'),
    平均金额=('总金额', 'mean'),
    总利润=('利润', 'sum')
).round(2)
status_analysis['金额占比'] = (status_analysis['总金额'] / status_analysis['总金额'].sum() * 100).round(2)
print(status_analysis.sort_values('总金额', ascending=False))

print("\n📊 分析报告 3 — 按类别统计:")
category_analysis = full_data.groupby('类别').agg(
    订单数=('订单ID', 'count'),
    总收入=('总金额', 'sum'),
    总利润=('利润', 'sum'),
    平均利润率=('利润率', 'mean')
).round(2)
print(category_analysis)

# 导出分析结果
output_path = '/tmp/analysis_report.csv'
full_data.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\n✅ 完整分析数据已导出: {output_path}")

# 清理临时文件
os.remove(csv_path)
os.remove(csv_product_path)
os.remove(output_path)

print("\n✅ 数据读取与合并实战演示完成！")
