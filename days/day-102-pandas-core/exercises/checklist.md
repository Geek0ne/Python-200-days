# Day 102 — Pandas 核心：练习检查表

## ✅ 今日学习完成清单

- [ ] 理解 Series 和 DataFrame 的结构与区别
- [ ] 掌握从字典、列表、NumPy 数组创建 DataFrame
- [ ] 熟练使用 head/tail/info/describe 进行数据探索
- [ ] 掌握 loc（标签）和 iloc（位置）的选择方式
- [ ] 理解布尔索引的多条件组合（& | ~ 的使用）
- [ ] 掌握 query 方法的字符串表达式查询
- [ ] 熟练使用 isin/between/str 方法进行筛选
- [ ] 能读写 CSV/Excel/JSON 等常见格式
- [ ] 完成所有代码示例的运行和理解

---

## 练习题

### 基础题

**练习 1：Series 操作**

创建一个 Series，存储 5 个城市的温度数据（包含一些缺失值），然后：
1. 计算平均温度
2. 找出最高温和最低温的城市
3. 填充缺失值为平均温度
4. 按温度排序

```python
import pandas as pd
import numpy as np
# 在这里编写代码
```

**练习 2：DataFrame 筛选**

给定以下 DataFrame：
```python
df = pd.DataFrame({
    '姓名': ['张三', '李四', '王五', '赵六', '钱七', '孙八'],
    '部门': ['技术', '产品', '技术', '设计', '运营', '技术'],
    '级别': ['P5', 'P6', 'P7', 'P5', 'P6', 'P6'],
    '薪资': [18000, 22000, 35000, 16000, 20000, 25000],
    '入职年份': [2020, 2019, 2015, 2021, 2018, 2017]
})
```
使用至少 3 种不同的方式筛选出技术部的员工。

**练习 3：统计分析**

使用练习 2 的数据，计算：
1. 各部门的平均薪资
2. 各级别的薪资范围（min-max）
3. 入职最早和最晚的员工
4. 薪资最高的 Top 3 员工

---

### 进阶题

**练习 4：CSV 数据分析**

创建一个包含 100 行的销售数据 CSV，字段包括：日期、产品、数量、单价、城市。然后：
1. 加载并预览数据
2. 计算每个产品的总销售额
3. 找出销售额最高的城市
4. 分析每日销售趋势
5. 筛选出所有高价订单（单价 > 平均单价 × 2）

**练习 5：数据合并**

创建两个 DataFrame：
```python
# 员工表
employees = pd.DataFrame({
    '工号': ['E001', 'E002', 'E003', 'E004'],
    '姓名': ['张三', '李四', '王五', '赵六'],
    '部门': ['技术', '产品', '技术', '设计']
})

# 考勤表
attendance = pd.DataFrame({
    '工号': ['E001', 'E002', 'E003', 'E005'],
    '出勤天数': [22, 20, 23, 21]
})
```
用 merge 合并两个表，展示哪些员工有考勤记录、哪些没有（两种方式：内连接和外连接）。

---

## 运行验证

```bash
cd ~/code/Learn-Python
python3 days/day-102-pandas-core/code/01-pandas-basics.py
python3 days/day-102-pandas-core/code/02-selection-advanced.py
python3 days/day-102-pandas-core/code/03-practical-recipes.py
```
