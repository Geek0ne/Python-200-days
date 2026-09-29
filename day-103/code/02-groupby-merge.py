#!/usr/bin/env python3
"""
Day 103 — Pandas 进阶：分组聚合与合并连接
演示 groupby/agg/transform 和 merge/concat/join
"""

import pandas as pd
import numpy as np

print("=" * 60)
print("Pandas 进阶：分组聚合与合并连接")
print("=" * 60)

# ══════════════════════════════════════════════════════
# 1. 分组聚合
# ══════════════════════════════════════════════════════
print("\n--- 1. 分组聚合 ---")

np.random.seed(42)
df = pd.DataFrame({
    '部门': np.random.choice(['技术', '产品', '设计', '运营'], 20),
    '员工': [f'员工{i}' for i in range(1, 21)],
    '薪资': np.random.randint(12000, 40000, 20),
    '绩效': np.random.choice(['A', 'B', 'C'], 20, p=[0.2, 0.5, 0.3]),
    '入职年份': np.random.choice(range(2015, 2024), 20)
})
print("员工数据:")
print(df)

# 1.1 基础分组
print("\n--- 1.1 基础分组 ---")
print(f"各部门平均薪资:\n{df.groupby('部门')['薪资'].mean()}")
print(f"\n各部门人数:\n{df.groupby('部门')['员工'].count()}")
print(f"\n各部门薪资范围:\n{df.groupby('部门')['薪资'].agg(['min', 'max', 'mean'])}")

# 1.2 多函数聚合 agg
print("\n--- 1.2 多函数聚合 ---")
result = df.groupby('部门').agg(
    人数=('员工', 'count'),
    平均薪资=('薪资', 'mean'),
    最高薪资=('薪资', 'max'),
    薪资标准差=('薪资', 'std'),
    绩效A比例=('绩效', lambda x: (x == 'A').mean())
).round(2)
print(result)

# 1.3 transform — 保持原始行数
print("\n--- 1.3 transform ---")
df['部门平均薪资'] = df.groupby('部门')['薪资'].transform('mean')
df['薪资排名'] = df.groupby('部门')['薪资'].rank(ascending=False).astype(int)
df['部门内占比'] = (df['薪资'] / df.groupby('部门')['薪资'].transform('sum') * 100).round(1)
print(df[['员工', '部门', '薪资', '部门平均薪资', '薪资排名', '部门内占比']])

# 1.4 filter — 筛选组
print("\n--- 1.4 filter ---")
high_salary_dept = df.groupby('部门').filter(lambda x: x['薪资'].mean() > 25000)
print(f"平均薪资 > 25000 的部门:\n{high_salary_dept['部门'].unique()}")

# 1.5 apply — 灵活操作
print("\n--- 1.5 apply ---")
def dept_summary(group):
    return pd.Series({
        '人数': len(group),
        '平均薪资': group['薪资'].mean(),
        '最高绩效人数': (group['绩效'] == 'A').sum()
    })

summary = df.groupby('部门').apply(dept_summary)
print(summary)

# ══════════════════════════════════════════════════════
# 2. 合并连接
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 2. 合并连接 ---")

# 创建示例数据
employees = pd.DataFrame({
    '工号': ['E001', 'E002', 'E003', 'E004', 'E005'],
    '姓名': ['张三', '李四', '王五', '赵六', '钱七'],
    '部门': ['技术', '产品', '技术', '设计', '运营']
})

salaries = pd.DataFrame({
    '工号': ['E001', 'E002', 'E003', 'E006'],
    '薪资': [18000, 22000, 35000, 20000]
})

performance = pd.DataFrame({
    '工号': ['E001', 'E003', 'E004', 'E005', 'E007'],
    '绩效': ['A', 'B', 'A', 'C', 'B']
})

# 2.1 内连接
print("\n--- 2.1 内连接 ---")
inner = pd.merge(employees, salaries, on='工号', how='inner')
print(f"employees ∩ salaries:\n{inner}")

# 2.2 左连接
print("\n--- 2.2 左连接 ---")
left = pd.merge(employees, salaries, on='工号', how='left')
print(f"employees LEFT JOIN salaries:\n{left}")

# 2.3 外连接
print("\n--- 2.3 外连接 ---")
outer = pd.merge(employees, salaries, on='工号', how='outer')
print(f"employees FULL JOIN salaries:\n{outer}")

# 2.4 多表合并
print("\n--- 2.4 多表合并 ---")
merged = employees.merge(salaries, on='工号', how='left') \
                  .merge(performance, on='工号', how='left')
print(merged)

# 2.5 concat 纵向拼接
print("\n--- 2.5 concat 纵向拼接 ---")
df1 = pd.DataFrame({'产品': ['手机', '电脑'], '销量': [100, 50]})
df2 = pd.DataFrame({'产品': ['耳机', '平板'], '销量': [200, 80]})
df3 = pd.DataFrame({'产品': ['手表'], '销量': [60]})

combined = pd.concat([df1, df2, df3], ignore_index=True)
print(combined)

# 2.6 concat 横向拼接
print("\n--- 2.6 concat 横向拼接 ---")
scores = pd.DataFrame({
    '工号': ['E001', 'E002', 'E003'],
    '考试成绩': [85, 92, 78]
})
result = pd.merge(employees.head(3), scores, on='工号', how='left')
print(result)

print("\n✅ 分组聚合与合并连接演示完成！")
