#!/usr/bin/env python3
"""
Day 018 — 实战：数据转换流水线

展示推导式在实际数据处理中的强大能力：
1. 数据清洗（CSV 解析、去空、类型转换）
2. 数据转换（映射、过滤、聚合）
3. 矩阵运算（加法、乘法、转置）
4. 实用工具函数
5. 文件数据流水线
"""

import sys
import os
import csv
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from tools import console


def section(title: str):
    console.section(title)


# ══════════════════════════════════════════════════════════
# 1. 数据清洗流水线
# ══════════════════════════════════════════════════════════
section("1. 数据清洗流水线")

raw_data = [
    '  Alice, 85, A ',
    'Bob, 92, B+',
    '  Charlie, 73, C ',
    '  Diana, , A',       # 缺失分数
    'Eve, 88, B+',
    '',                    # 空行
    'Frank, 105, A+',     # 分数越界
    '  Grace, 67, B-',
    'Henry, -5, F',       # 分数异常
]

print("原始数据:")
for line in raw_data:
    print(f"  {repr(line)}")

print()

# 第一步：去除空白&过滤空行
cleaned = [line.strip() for line in raw_data if line.strip()]
print(f"第一步（去空白+空行）: {cleaned}")

# 第二步：解析 CSV
parsed = [line.split(',') for line in cleaned]
print(f"第二步（CSV解析）: {parsed}")

# 第三步：类型清洗 + 校验
processed = []
for parts in parsed:
    # 去除每个字段的空白
    parts = [p.strip() for p in parts]
    if len(parts) != 3:
        continue
    name, score_str, grade = parts
    # 缺失分数跳过
    if not score_str:
        continue
    score = int(score_str)
    # 过滤不合理分数
    if 0 <= score <= 100:
        processed.append({
            'name': name,
            'score': score,
            'grade': grade
        })

print(f"第三步（类型清洗+校验）:")
for p in processed:
    print(f"  {p}")

print(f"\n有效记录数: {len(processed)} / {len(raw_data)}")


# ══════════════════════════════════════════════════════════
# 2. 使用字典推导式构建查找表
# ══════════════════════════════════════════════════════════
section("2. 字典推导式构建查找表")

# 从清洗结果构建名字→分数查找表
score_lookup = {p['name']: p['score'] for p in processed}
print(f"成绩查找表: {score_lookup}")

# 按成绩等级分组
grades = ['A', 'B+', 'B-', 'C', 'F']
grade_thresholds = {'A': 90, 'B+': 80, 'B-': 70, 'C': 60, 'F': 0}

grade_groups = {g: [p['name'] for p in processed if p['score'] >= t]
                for g, t in grade_thresholds.items()}
print(f"\n等级分组:")
for g, names in grade_groups.items():
    print(f"  {g}: {names}")

# 统计等级分布
grade_counts = {g: sum(1 for p in processed if p['grade'] == g)
                for g in set(p['grade'] for p in processed)}
print(f"\n等级分布: {grade_counts}")


# ══════════════════════════════════════════════════════════
# 3. 矩阵运算
# ══════════════════════════════════════════════════════════
section("3. 矩阵运算")

A = [[1, 2, 3],
     [4, 5, 6]]

B = [[7, 8, 9],
     [10, 11, 12]]

print("矩阵 A:", A)
print("矩阵 B:", B)

# 矩阵加法
C = [[A[i][j] + B[i][j] for j in range(len(A[0]))] for i in range(len(A))]
print(f"\nA + B = {C}")

# 元素乘积
D = [[A[i][j] * B[i][j] for j in range(len(A[0]))] for i in range(len(A))]
print(f"A * B (元素积) = {D}")

# 矩阵转置
rows, cols = len(A), len(A[0])
transposed = [[A[i][j] for i in range(rows)] for j in range(cols)]
print(f"\nA 转置 = {transposed}")

# 更直观的转置：使用 zip
transposed_zip = list(list(row) for row in zip(*A))
print(f"A 转置 (zip) = {transposed_zip}")

# 矩阵乘法
print("\n--- 矩阵乘法 ---")
X = [[1, 2],
     [3, 4],
     [5, 6]]  # 3×2

Y = [[7, 8, 9],
     [10, 11, 12]]  # 2×3

def matmul(A, B):
    """A(m×n) * B(n×p) = C(m×p)"""
    m, n = len(A), len(A[0])
    p = len(B[0])
    return [
        [sum(A[i][k] * B[k][j] for k in range(n)) for j in range(p)]
        for i in range(m)
    ]

result = matmul(X, Y)
print(f"X = {X}")
print(f"Y = {Y}")
print(f"X × Y = {result}")


# ══════════════════════════════════════════════════════════
# 4. 实用工具函数
# ══════════════════════════════════════════════════════════
section("4. 实用工具函数")


def flatten(nested):
    """扁平化嵌套列表"""
    return [item for sublist in nested for item in sublist]


def chunked(lst, n):
    """将列表分割为 n 个一组"""
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def unique_stable(lst):
    """稳定去重（保持首次出现顺序）"""
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


def group_by(items, key_func):
    """按 key_func 分组"""
    result = {}
    for item in items:
        key = key_func(item)
        if key not in result:
            result[key] = []
        result[key].append(item)
    return result


# 测试工具函数
data = [1, 2, 2, 3, 4, 3, 5, 1]

nested_list = [[1, 2], [3, 4, 5], [6], [7, 8, 9, 10]]
print(f"嵌套列表: {nested_list}")
print(f"扁平化: {flatten(nested_list)}")

print(f"\n稳定去重: {unique_stable(data)}")
print(f"分块(3): {chunked(list(range(10)), 3)}")

people = [
    {'name': 'Alice', 'age': 25, 'dept': 'Engineering'},
    {'name': 'Bob', 'age': 30, 'dept': 'Engineering'},
    {'name': 'Charlie', 'age': 35, 'dept': 'Design'},
    {'name': 'Diana', 'age': 28, 'dept': 'Marketing'},
    {'name': 'Eve', 'age': 32, 'dept': 'Design'},
]

by_dept = group_by(people, lambda p: p['dept'])
print(f"\n按部门分组:")
for dept, members in by_dept.items():
    names = [m['name'] for m in members]
    print(f"  {dept}: {names}")

# 从分组中提取统计信息
dept_summary = {
    dept: {
        'count': len(members),
        'avg_age': sum(m['age'] for m in members) / len(members),
        'members': [m['name'] for m in members]
    }
    for dept, members in by_dept.items()
}
print(f"\n部门统计:")
for dept, info in dept_summary.items():
    print(f"  {dept}: {info['count']}人, 平均年龄 {info['avg_age']:.1f}")


# ══════════════════════════════════════════════════════════
# 5. 模拟文件处理流水线
# ══════════════════════════════════════════════════════════
section("5. 模拟文件处理流水线")

# 模拟从 CSV 文件读取数据
csv_content = """name,age,city,score
Alice,28,Beijing,85
Bob,32,Shanghai,92
Charlie,25,Guangzhou,73
Diana,30,Shenzhen,
Eve,27,Beijing,88
Frank,35,Shanghai,
"""

print("模拟 CSV 数据:")
reader = csv.DictReader(io.StringIO(csv_content))
rows = list(reader)
for row in rows:
    print(f"  {row}")

print()

# 数据清洗流水线（全推导式风格）
valid_rows = [
    {**row, 'score': int(row['score'])}
    for row in rows
    if row['score'].strip()  # 过滤缺失
    if row['name'].strip()
    if int(row['score']) <= 100  # 分数合理
]
# 注意: 用 {**row, ...} 而不是直接修改
# 这样每一行得到的是新字典，可以安全地在推导式中使用

print(f"有效记录 ({len(valid_rows)} / {len(rows)}):")
for row in valid_rows:
    print(f"  {row}")

# 按城市分组统计
city_scores = {}
for row in valid_rows:
    city = row['city']
    if city not in city_scores:
        city_scores[city] = []
    city_scores[city].append(row['score'])

city_avg = {city: f"{sum(scores)/len(scores):.1f}"
            for city, scores in city_scores.items()}
print(f"\n城市平均分: {city_avg}")

# 按年龄分组
age_groups = {
    'young': [r for r in valid_rows if r['age'] < 30],
    'middle': [r for r in valid_rows if 30 <= r['age'] < 40],
    'senior': [r for r in valid_rows if r['age'] >= 40],
}

print(f"\n年龄分组:")
for group, members in age_groups.items():
    names = [m['name'] for m in members]
    print(f"  {group}: {names}")


if __name__ == '__main__':
    print("\n✅ Day 018 — 数据转换流水线实战完成")
    print("📌 流水线设计模式：")
    print("   1. 数据清洗 → 2. 类型转换 → 3. 校验过滤 → 4. 分组聚合")
    print("   每一步都可以用推导式表达，组合成强大的数据处理链")
