#!/usr/bin/env python3
"""
Day 102 — Pandas 核心：基础用法
演示 Series/DataFrame 的创建、属性和基本操作
"""

import pandas as pd
import numpy as np

print("=" * 60)
print("Pandas 基础：Series 与 DataFrame")
print("=" * 60)

# ── 1. Series 创建与操作 ──
print("\n--- Series 基础 ---")

# 从列表创建
s1 = pd.Series([10, 20, 30, 40])
print(f"自动索引 Series:\n{s1}")

# 从字典创建
s2 = pd.Series({'数学': 95, '英语': 88, '物理': 92, '化学': 85})
print(f"\n字典 Series:\n{s2}")

# 索引与切片
print(f"\n按标签索引 s2['数学']: {s2['数学']}")
print(f"按位置索引 s2.iloc[0]: {s2.iloc[0]}")
print(f"切片 s2['数学':'物理']:\n{s2['数学':'物理']}")

# 条件筛选
print(f"\n成绩 > 90 的科目:\n{s2[s2 > 90]}")

# 统计
print(f"\n均值: {s2.mean()}")
print(f"标准差: {s2.std():.2f}")
print(f"最高分: {s2.max()} ({s2.idxmax()})")
print(f"总分: {s2.sum()}")

# ── 2. DataFrame 创建 ──
print("\n" + "=" * 60)
print("DataFrame 创建")
print("=" * 60)

# 从字典创建
df = pd.DataFrame({
    '姓名': ['张三', '李四', '王五', '赵六', '钱七'],
    '年龄': [25, 30, 35, 28, 22],
    '城市': ['北京', '上海', '广州', '深圳', '杭州'],
    '薪资': [15000, 25000, 18000, 22000, 12000],
    '部门': ['技术', '产品', '技术', '设计', '运营']
})
print(df)

# ── 3. DataFrame 属性 ──
print("\n--- DataFrame 属性 ---")
print(f"shape: {df.shape}")       # (5, 5)
print(f"columns: {list(df.columns)}")
print(f"dtypes:\n{df.dtypes}")
print(f"index: {list(df.index)}")

# ── 4. 数据查看 ──
print("\n" + "=" * 60)
print("数据查看")
print("=" * 60)

print(f"\n前3行:\n{df.head(3)}")
print(f"\n后2行:\n{df.tail(2)}")
print(f"\n数据概览:")
df.info()
print(f"\n数值统计:\n{df.describe()}")
print(f"\n全量统计:\n{df.describe(include='all')}")

# ── 5. 列选择 ──
print("\n" + "=" * 60)
print("列选择")
print("=" * 60)

# 单列（返回 Series）
print(f"\n姓名列:\n{df['姓名']}")
print(f"类型: {type(df['姓名'])}")

# 多列（返回 DataFrame）
print(f"\n姓名+薪资:\n{df[['姓名', '薪资']]}")
print(f"类型: {type(df[['姓名', '薪资']])}")

# ── 6. loc 与 iloc ──
print("\n" + "=" * 60)
print("loc 与 iloc")
print("=" * 60)

# loc — 按标签
print(f"\nloc 选择第 0 行:\n{df.loc[0]}")
print(f"\nloc 选择第 0-2 行，姓名+城市:\n{df.loc[0:2, ['姓名', '城市']]}")

# iloc — 按位置
print(f"\niloc 选择第 0 行:\n{df.iloc[0]}")
print(f"\niloc 选择前 3 行，前 2 列:\n{df.iloc[:3, :2]}")

# 条件选择
print(f"\n薪资 > 20000 的员工:\n{df[df['薪资'] > 20000]}")

# 多条件
print(f"\n技术部且薪资 > 16000:\n{df[(df['部门'] == '技术') & (df['薪资'] > 16000)]}")

# ── 7. 排序 ──
print("\n" + "=" * 60)
print("排序")
print("=" * 60)

print(f"\n按薪资降序:\n{df.sort_values('薪资', ascending=False)}")
print(f"\n按年龄升序:\n{df.sort_values('年龄')}")

# ── 8. 添加/修改列 ──
print("\n" + "=" * 60)
print("添加/修改列")
print("=" * 60)

df['年薪'] = df['薪资'] * 12
df['薪资等级'] = df['薪资'].apply(lambda x: '高' if x >= 20000 else '中' if x >= 15000 else '低')
print(df[['姓名', '薪资', '年薪', '薪资等级']])

print("\n✅ Pandas 基础演示完成！")
