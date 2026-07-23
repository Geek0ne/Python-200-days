"""
01-pandas基础操作.py
Pandas Series 与 DataFrame 基础：创建、索引、筛选、排序

运行：python3 01-pandas基础操作.py
"""
import pandas as pd
import numpy as np

print("=" * 60)
print("📚 Day 080 — Pandas 基础操作")
print("=" * 60)

# ==================== 1. Series 基础 ====================
print("\n🔹 1. Series 基础操作")
print("-" * 40)

# 创建 Series
scores = pd.Series(
    [85, 92, 78, 95, 88],
    index=['数学', '英语', '物理', '化学', '生物'],
    name='期中成绩'
)
print(f"Series:\n{scores}")
print(f"\n数据类型: {type(scores)}")
print(f"索引: {scores.index.tolist()}")
print(f"值: {scores.values}")

# Series 统计
print(f"\n平均分: {scores.mean():.1f}")
print(f"最高分: {scores.max()} ({scores.idxmax()})")
print(f"最低分: {scores.min()} ({scores.idxmin()})")

# Series 索引与切片
print(f"\n数学成绩: {scores['数学']}")
print(f"前两科: \n{scores[:2]}")
print(f"90分以上: \n{scores[scores >= 90]}")

# Series 向量化运算
scores_extra = scores * 1.1  # 所有成绩加 10%
print(f"\n加分后（×1.1）:\n{scores_extra.round(1)}")

# ==================== 2. DataFrame 创建 ====================
print("\n\n🔹 2. DataFrame 创建")
print("-" * 40)

# 从字典创建
employees = pd.DataFrame({
    '姓名': ['张三', '李四', '王五', '赵六', '钱七', '孙八'],
    '部门': ['销售', '技术', '销售', '技术', '人事', '销售'],
    '入职年份': [2020, 2019, 2021, 2018, 2022, 2023],
    '薪资': [8000, 15000, 9000, 18000, 12000, 7500],
    '绩效评级': ['B', 'A', 'B', 'S', 'A', 'C']
})
print(f"员工数据:\n{employees}")
print(f"\n形状: {employees.shape}")
print(f"列名: {employees.columns.tolist()}")
print(f"数据类型:\n{employees.dtypes}")

# ==================== 3. 查看数据 ====================
print("\n\n🔹 3. 查看数据")
print("-" * 40)

print(f"前 3 行:\n{employees.head(3)}")
print(f"\n统计摘要:\n{employees.describe()}")
print(f"\n信息概览:")
employees.info()

# ==================== 4. 索引与选择 ====================
print("\n\n🔹 4. 索引与选择数据")
print("-" * 40)

# 列选择
print("单列选择（姓名）:")
print(employees['姓名'])
print(f"\n类型: {type(employees['姓名'])}")  # Series

print("\n多列选择:")
print(employees[['姓名', '薪资']])

# loc — 基于标签
print("\nloc — 标签索引:")
print(employees.loc[0:2, '姓名':'薪资'])

# iloc — 基于位置
print("\niloc — 位置索引:")
print(employees.iloc[0:3, 0:3])

# 条件筛选
print("\n条件筛选 — 技术部员工:")
tech = employees[employees['部门'] == '技术']
print(tech)

print("\n多条件筛选 — 技术部 & 入职早于2020:")
senior_tech = employees[(employees['部门'] == '技术') & (employees['入职年份'] < 2020)]
print(senior_tech)

# query 方法
print("\nquery 方法 — 薪资 > 10000 的非人事部门:")
result = employees.query('薪资 > 10000 and 部门 != "人事"')
print(result)

# ==================== 5. 修改数据 ====================
print("\n\n🔹 5. 修改数据")
print("-" * 40)

# 新增列
employees['年薪'] = employees['薪资'] * 12
print(f"新增年薪列:\n{employees[['姓名', '薪资', '年薪']]}")

# 条件赋值
employees['级别'] = employees['绩效评级'].map({
    'S': '卓越', 'A': '优秀', 'B': '良好', 'C': '待改进'
})
print(f"\n新增级别列:\n{employees[['姓名', '绩效评级', '级别']]}")

# 修改特定值
employees.loc[employees['姓名'] == '张三', '薪资'] = 8500
print(f"\n修改张三薪资后:\n{employees[employees['姓名'] == '张三']}")

# ==================== 6. 排序 ====================
print("\n\n🔹 6. 排序")
print("-" * 40)

# 单列排序
print("按薪资降序排列:")
by_salary = employees.sort_values('薪资', ascending=False)
print(by_salary[['姓名', '部门', '薪资']])

# 多列排序
print("\n按部门升序、薪资降序:")
multi_sort = employees.sort_values(['部门', '薪资'], ascending=[True, False])
print(multi_sort[['姓名', '部门', '薪资']])

print("\n✅ 基础操作演示完成！")
