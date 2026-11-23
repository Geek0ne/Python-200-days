#!/usr/bin/env python3
"""
Day 103 — Pandas 进阶：数据清洗
演示缺失值、重复值、类型转换和异常值处理
"""

import pandas as pd
import numpy as np

print("=" * 60)
print("Pandas 进阶：数据清洗")
print("=" * 60)

# ── 创建包含各种问题的数据 ──
np.random.seed(42)
df = pd.DataFrame({
    '姓名': ['张三', '李四', '王五', '赵六', '钱七', '张三', None, '孙八'],
    '年龄': [25, np.nan, 35, 28, 30, 25, 22, np.nan],
    '薪资': [15000, 25000, np.nan, 22000, 18000, 15000, 12000, 20000],
    '部门': ['技术', '产品', '技术', None, '运营', '技术', '运营', '产品'],
    '入职日期': ['2020-01-15', '2019-03-20', '2015-07-01', 
                '2021-06-15', '2018-11-01', '2020-01-15', '2022-08-10', '2017-04-22']
})

print("原始数据:")
print(df)

# ══════════════════════════════════════════════════════
# 1. 缺失值检测与处理
# ══════════════════════════════════════════════════════
print("\n--- 1. 缺失值检测 ---")
print(f"缺失值矩阵:\n{df.isnull()}")
print(f"\n每列缺失数:\n{df.isnull().sum()}")
print(f"总缺失数: {df.isnull().sum().sum()}")
print(f"缺失率:\n{(df.isnull().sum() / len(df) * 100).round(1)}%")

print("\n--- 1.1 删除缺失值 ---")
print(f"删除任何含 NaN 的行:\n{df.dropna()}")
print(f"\n只看年龄列有缺失的行:\n{df[df['年龄'].isnull()]}")

print("\n--- 1.2 填充缺失值 ---")
df_filled = df.copy()

# 用均值填充年龄
df_filled['年龄'] = df_filled['年龄'].fillna(df_filled['年龄'].mean())
print(f"年龄用均值填充: {df_filled['年龄'].tolist()}")

# 用众数填充部门
mode_dept = df['部门'].mode()[0]
df_filled['部门'] = df_filled['部门'].fillna(mode_dept)
print(f"部门用众数填充: {df_filled['部门'].tolist()}")

# 用前向填充姓名
df_filled['姓名'] = df_filled['姓名'].fillna(method='ffill')
print(f"姓名前向填充: {df_filled['姓名'].tolist()}")

print(f"\n填充后缺失值: {df_filled.isnull().sum().sum()}")

# ══════════════════════════════════════════════════════
# 2. 重复值处理
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 2. 重复值处理 ---")

print(f"重复行标记:\n{df_filled.duplicated()}")
print(f"重复行数: {df_filled.duplicated().sum()}")

# 删除重复（保留第一条）
df_dedup = df_filled.drop_duplicates()
print(f"\n删除重复后: {len(df_dedup)} 行 (原 {len(df_filled)} 行)")

# 按姓名去重
df_name_dedup = df_filled.drop_duplicates(subset=['姓名'], keep='last')
print(f"按姓名去重后:\n{df_name_dedup[['姓名', '部门']]}")

# ══════════════════════════════════════════════════════
# 3. 数据类型转换
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 3. 数据类型转换 ---")

df_types = df_dedup.copy()

# 字符串转数值
df_types['年龄'] = df_types['年龄'].astype(int)

# 字符串转日期
df_types['入职日期'] = pd.to_datetime(df_types['入职日期'])

# 添加工龄
df_types['工龄'] = ((pd.Timestamp.now() - df_types['入职日期']).dt.days / 365).round(1)

print(f"转换后数据类型:\n{df_types.dtypes}")
print(f"\n转换后数据:\n{df_types}")

# ══════════════════════════════════════════════════════
# 4. 异常值处理
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 4. 异常值处理 ---")

# 创建含异常值的数据
np.random.seed(42)
data = np.random.normal(100, 20, 100)
data = np.append(data, [500, -200, 1000])  # 添加异常值
s = pd.Series(data)

# IQR 方法
Q1 = s.quantile(0.25)
Q3 = s.quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR

print(f"Q1={Q1:.2f}, Q3={Q3:.2f}, IQR={IQR:.2f}")
print(f"正常范围: [{lower:.2f}, {upper:.2f}]")

outliers = s[(s < lower) | (s > upper)]
print(f"异常值数量: {len(outliers)}")
print(f"异常值: {outliers.tolist()}")

# 截断异常值
s_clipped = s.clip(lower, upper)
print(f"\n截断后:")
print(f"  最小值: {s_clipped.min():.2f}")
print(f"  最大值: {s_clipped.max():.2f}")
print(f"  均值: {s_clipped.mean():.2f}")

# ══════════════════════════════════════════════════════
# 5. 综合清洗流程
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 5. 综合清洗流程总结 ---")

print("""
清洗步骤:
1. 识别缺失值 → 决定删除/填充/保留
2. 识别重复值 → 决定保留策略
3. 数据类型检查 → 必要时转换
4. 异常值检测 → 用 IQR/Z-score 方法
5. 数据验证 → 确保清洗后的数据符合预期
""")

print("✅ 数据清洗演示完成！")
