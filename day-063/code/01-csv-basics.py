#!/usr/bin/env python3
"""
Day 063 - CSV 与 Excel
示例 1: csv 模块基础与进阶用法

本示例演示 Python csv 模块的核心功能：
1. reader/writer 基础读写
2. DictReader/DictWriter 字典式操作
3. 方言（Dialect）与格式自动检测
4. 大文件分块处理
5. 常见陷阱与避坑

运行方式: python3 01-csv-basics.py
"""

import csv
import io
from pathlib import Path

print("=" * 60)
print("📊 CSV 模块 —— 基础与进阶")
print("=" * 60)

# ─── 1. 基础读写 ───

print("\n--- 1. 基础读写 (reader/writer) ---")

# 准备数据
data = [
    ["name", "age", "city", "salary"],
    ["Alice", "30", "Beijing", "15000"],
    ["Bob", "25", "Shanghai", "12000"],
    ["Charlie", "35", "Shenzhen", "20000"],
    ["David", "28", "Guangzhou", "13500"],
]

# 写入 CSV
csv_path = Path("/tmp/day063_test.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(data)

print(f"已写入 {len(data)} 行到 {csv_path}")

# 读取 CSV
print("\n读取结果:")
with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for i, row in enumerate(reader):
        print(f"  行 {i}: {row}")

# ─── 2. DictReader/DictWriter ───

print("\n\n--- 2. 字典式读写 (DictReader/DictWriter) ---")

# 使用 DictWriter 写入
dict_path = Path("/tmp/day063_dict.csv")
with open(dict_path, "w", newline="", encoding="utf-8") as f:
    fieldnames = ["name", "age", "city", "salary"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)

    writer.writeheader()
    writer.writerow({"name": "Alice", "age": 30, "city": "Beijing", "salary": 15000})
    writer.writerow({"name": "Bob", "age": 25, "city": "Shanghai", "salary": 12000})
    writer.writerow({"name": "Charlie", "age": 35, "city": "Shenzhen", "salary": 20000})

print(f"DictWriter 写入完成: {dict_path}")

# 使用 DictReader 读取
print("\nDictReader 读取结果:")
with open(dict_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(f"  {row['name']:10s} | {row['age']:3s} | {row['city']:10s} | {row['salary']:>5s}")

# ─── 3. 自定义分隔符 ───

print("\n\n--- 3. 自定义分隔符 ---")

# 制表符分隔 (TSV)
tsv_data = "name\tage\tcity\nAlice\t30\tBeijing\nBob\t25\tShanghai"

print("TSV 格式数据:")
for line in tsv_data.split("\n"):
    print(f"  {line}")

# 使用 dialect 参数读取 TSV
print("\nTSV 解析结果:")
reader = csv.reader(io.StringIO(tsv_data), delimiter="\t")
for row in reader:
    print(f"  {row}")

# 竖线分隔
pipe_data = "name|age|city\nAlice|30|Beijing\nBob|25|Shanghai"

print("\nPipe 分隔数据:")
reader = csv.reader(io.StringIO(pipe_data), delimiter="|")
for row in reader:
    print(f"  {row}")

# ─── 4. 引号与转义处理 ───

print("\n\n--- 4. 引号与转义处理 ---")

# 字段中包含分隔符、换行符、引号的情况
complex_data = [
    ["Product", "Description", "Price"],
    ["Laptop", '15.6", 16GB RAM, 512GB SSD', "5999"],
    ["Book", 'Python "入门" 指南\n第2版', "99"],
    ['Coffee', "It\'s good", "29.9"],
]

complex_path = Path("/tmp/day063_complex.csv")
with open(complex_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(complex_data)

print(f"复杂数据已写入，文件内容:")
print(complex_path.read_text(encoding="utf-8"))

print("\n读取结果:")
with open(complex_path, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        print(f"  {row}")

# ─── 5. 方言（Dialect）系统 ───

print("\n\n--- 5. 方言系统 ---")

# 注册自定义方言
csv.register_dialect("custom_pipe",
    delimiter="|",
    quotechar="'",
    quoting=csv.QUOTE_ALL,
    skipinitialspace=True,
    lineterminator="\n",
)

# 使用自定义方言写入
pipe_path = Path("/tmp/day063_pipe.csv")
with open(pipe_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, dialect="custom_pipe")
    writer.writerows(data)

print(f"Pipe 方言写入，文件内容:")
print(pipe_path.read_text(encoding="utf-8"))

# 使用自定义方言读取
print("\nPipe 方言读取结果:")
with open(pipe_path, "r", encoding="utf-8") as f:
    reader = csv.reader(f, dialect="custom_pipe")
    for row in reader:
        print(f"  {row}")

# 查看预定义方言列表
print(f"\nPython 预定义方言: {csv.list_dialects()}")

# ─── 6. Sniffer 自动检测 ───

print("\n\n--- 6. Sniffer 自动检测 ---")

detect_samples = [
    "name,age,city\nAlice,30,Beijing\nBob,25,Shanghai",
    "name\tage\tcity\nAlice\t30\tBeijing\nBob\t25\tShanghai",
    "name|age|city\nAlice|30|Beijing\nBob|25|Shanghai",
    '"name","age","city"\n"Alice","30","Beijing"',
]

for i, sample in enumerate(detect_samples):
    print(f"\n样本 {i+1}: {sample[:40]}...")
    try:
        dialect = csv.Sniffer().sniff(sample)
        has_header = csv.Sniffer().has_header(sample)
        print(f"  检测结果: delimiter='{dialect.delimiter}', "
              f"quotechar='{dialect.quotechar}', "
              f"has_header={has_header}")
    except csv.Error as e:
        print(f"  检测失败: {e}")

# ─── 7. 大文件分块处理 ───

print("\n\n--- 7. 大文件分块处理 ---")

# 生成一个较大的 CSV 文件用于演示
large_path = Path("/tmp/day063_large.csv")
print(f"生成 50000 行测试数据...")
with open(large_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "name", "category", "price", "quantity"])
    for i in range(50000):
        writer.writerow([
            i + 1,
            f"Product_{i}",
            ["Electronics", "Books", "Clothing", "Food"][i % 4],
            round((i % 100) * 10 + 9.99, 2),
            (i % 50) + 1
        ])

file_size_mb = large_path.stat().st_size / 1024 / 1024
print(f"文件大小: {file_size_mb:.2f} MB")

# 分块读取并统计
print("\n分块统计（每批 10000 行）:")
batch_size = 10000
total_rows = 0
total_price = 0.0

with open(large_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    batch = []
    for row in reader:
        batch.append(row)
        if len(batch) >= batch_size:
            # 处理这一批
            batch_total = sum(float(r["price"]) * int(r["quantity"]) for r in batch)
            total_price += batch_total
            total_rows += len(batch)
            print(f"  已处理 {total_rows:>6} 行, 本批金额: {batch_total:>12.2f}")
            batch = []

    # 处理最后一批
    if batch:
        batch_total = sum(float(r["price"]) * int(r["quantity"]) for r in batch)
        total_price += batch_total
        total_rows += len(batch)
        print(f"  已处理 {total_rows:>6} 行, 本批金额: {batch_total:>12.2f}")

print(f"\n总金额: {total_price:,.2f}")
print(f"总行数: {total_rows}")

# ─── 8. 常见陷阱 ───

print("\n\n--- 8. 常见陷阱与避坑 ---")

# 陷阱 1: newline='' 的重要性
print("\n⚠️ 陷阱 1: Windows 下打开 CSV 文件必须用 newline=''")
print("   否则会在每行后多一个空行")

# 陷阱 2: 数字都是字符串
print("\n⚠️ 陷阱 2: 读取 CSV 时，数字会被当成字符串")
with open(dict_path, "r", encoding="utf-8") as f:
    row = next(csv.DictReader(f))
    print(f"  读取的 age: {row['age']!r} (类型: {type(row['age']).__name__})")
    # 需要手动转换
    age = int(row['age'])
    print(f"  转换后: {age} (类型: {type(age).__name__})")

# 陷阱 3: BOM 问题
print("\n⚠️ 陷阱 3: Excel 打开 UTF-8 CSV 乱码")
print("   使用 utf-8-sig 编码（含 BOM）解决")
bom_path = Path("/tmp/day063_bom.csv")
with open(bom_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["姓名", "年龄"])
    writer.writerow(["张三", 30])
print(f"  已用 utf-8-sig 写入: {bom_path}")
print(f"  文件头 3 字节 (BOM): {bom_path.read_bytes()[:3].hex()}")

# 陷阱 4: 空行处理
print("\n⚠️ 陷阱 4: CSV 中的空行可能会被跳过")
with open(large_path, "w", newline="", encoding="utf-8") as f:
    f.write("a,b,c\n\n1,2,3\n\n4,5,6\n")
with open(large_path, "r") as f:
    rows = list(csv.reader(f))
    print(f"  读取行数: {len(rows)}")  # 空行不会产生空列表

# 清理
for p in [csv_path, dict_path, complex_path, pipe_path, large_path, bom_path]:
    if p.exists():
        p.unlink()

print("\n✅ CSV 基础示例完成！")
