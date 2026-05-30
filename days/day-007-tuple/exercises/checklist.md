# Day 007 — 元组（Tuple）练习与检查清单

> 📌 完成每个练习后，在 `[ ]` 中打 `[x]`

---

## ✅ 今日完成清单

### 概念理解
- [ ] 理解元组的不可变性及其内存原理
- [ ] 理解元组与列表的本质区别
- [ ] 理解为什么元组可以哈希但列表不可以

### 基本操作
- [ ] 掌握元组的 7 种创建方式
- [ ] 掌握索引、切片、拼接、成员检查
- [ ] 掌握 count() 与 index() 方法

### 元组拆包
- [ ] 掌握基础拆包 `x, y = point`
- [ ] 掌握星号拆包 `first, *middle, last`
- [ ] 掌握嵌套拆包 `a, (b, c) = data`
- [ ] 能运用函数多返回值拆包

### namedtuple
- [ ] 掌握 `collections.namedtuple` 的使用
- [ ] 掌握 `typing.NamedTuple` 类语法
- [ ] 理解 namedtuple 的不可变性
- [ ] 掌握 `_replace()`、`_asdict()`、`_make()`、`_fields`

### 列表 vs 元组
- [ ] 理解两者的性能差异原因
- [ ] 能根据场景正确选择列表或元组

### 实战
- [ ] 完成坐标系统代码
- [ ] 理解元组作为字典键的应用

---

## 📝 练习题

### 练习 1：实现三维向量运算库

用 `namedtuple` 或 `typing.NamedTuple` 定义一个 `Vector3D` 类型，实现以下函数：

```python
# TODO: 定义 Vector3D，包含 x, y, z

def vector_add(v1, v2):
    """向量加法"""
    pass

def dot_product(v1, v2):
    """点积：v1·v2 = x1*x2 + y1*y2 + z1*z2"""
    pass

def cross_product(v1, v2):
    """叉积：v1 × v2 = (y1*z2 - z1*y2, z1*x2 - x1*z2, x1*y2 - y1*x2)"""
    pass

def vector_length(v):
    """向量长度"""
    pass

def normalize(v):
    """向量归一化（单位向量）"""
    pass

# 测试数据
v1 = Vector3D(1, 2, 3)
v2 = Vector3D(4, 5, 6)

print(vector_add(v1, v2))   # 预期: Vector3D(5, 7, 9)
print(dot_product(v1, v2))  # 预期: 32
print(cross_product(v1, v2)) # 预期: Vector3D(-3, 6, -3)
print(vector_length(v1))    # 预期: 3.74...
```

**提示**：Vector3D 继承 NamedTuple，上面所有函数都可以作为方法写在类内部！

---

### 练习 2：学生成绩管理系统

不使用数据库，用元组和 namedtuple 实现一个简单的学生成绩管理系统。

```python
from collections import namedtuple
from typing import List

# 定义 Student 类型（含有 name, chinese, math, english 四个字段）
# TODO: 你的代码

def average_score(student):
    """计算平均分"""
    pass

def rank_students(students: List) -> List:
    """按总分排序（从高到低）"""
    pass

def top_student(students: List):
    """返回第一名"""
    pass

# 测试数据
students = [
    Student("Alice", 90, 85, 92),
    Student("Bob", 78, 88, 80),
    Student("Charlie", 95, 92, 98),
]

# 输出每个学生的信息
for s in students:
    print(f"{s.name}: 总分={s.chinese + s.math + s.english}, 平均分={average_score(s):.1f}")

# 输出排名
print("\n排名:")
for rank, s in enumerate(rank_students(students), 1):
    total = s.chinese + s.math + s.english
    print(f"第{rank}名: {s.name} ({total}分)")
```

**扩展挑战**：为 Student 添加 `_replace` 来更新某一门成绩。

---

### 练习 3：文本分析器

给定以下文本，用元组拆包技巧完成字符串解析任务：

```python
text = "Alice:85,Bob:92,Charlie:78,Diana:95"

# 1. 将文本解析为 (name, score) 元组列表
# 2. 找出最高分的同学
# 3. 计算平均分
# 4. 输出格式化的成绩报告

# TODO: 你的代码

# 预期输出:
# Alice: 85
# Bob: 92
# Charlie: 78
# Diana: 95
# 最高分: Diana (95)
# 平均分: 87.5
```

**提示**：`"Alice:85".split(":")` 返回 `["Alice", "85"]`，可以用拆包接收。

---

### 练习 4：路径点集合

```python
from collections import namedtuple
from typing import List

# Point 类型
Point = namedtuple('Point', ['x', 'y'])

# 一条路径由一系列点组成
path = [
    Point(0, 0),
    Point(1, 2),
    Point(3, 5),
    Point(6, 1),
    Point(10, 4),
]

# 1. 计算路径总长度（从第一个点到最后一个点的连线距离之和）
# 2. 找到路径中某段距离最长的两个相邻点
# 3. 压缩路径：如果某段距离小于 2.0，跳过该点（简化路径）

def total_path_length(points: List[Point]) -> float:
    """计算路径总长度"""
    pass

def longest_segment(points: List[Point]) -> tuple:
    """返回距离最长的 (点A, 点B, 距离)"""
    pass

def simplify_path(points: List[Point], min_dist: float = 2.0) -> List[Point]:
    """简化和压缩路径"""
    pass

# TODO: 实现上述函数并测试
```

---

### 练习 5：数据流聚合器（进阶）

```python
from collections import namedtuple

# 传感器数据流
SensorReading = namedtuple('SensorReading', ['timestamp', 'temperature', 'humidity'])

readings = [
    SensorReading(1, 25.3, 60.1),
    SensorReading(2, 25.7, 59.8),
    SensorReading(3, 26.1, 59.2),
    SensorReading(4, 26.8, 58.5),
    SensorReading(5, 27.2, 57.9),
]

# 1. 计算温度与湿度的平均值
# 2. 找到温度最高和最低的采样点
# 3. 如果温度变化率超过 0.5/单位时间，标记为异常
# 4. 使用 zip() 和拆包从多个元组列表中提取温度序列

# TODO: 你的代码
```

---

## 📖 参考链接

- [Python 官方文档 — tuple](https://docs.python.org/3/library/stdtypes.html#tuple)
- [Python 官方文档 — collections.namedtuple](https://docs.python.org/3/library/collections.html#collections.namedtuple)
- [Python 官方文档 — typing.NamedTuple](https://docs.python.org/3/library/typing.html#typing.NamedTuple)
- [PEP 448 — Additional Unpacking Generalizations](https://peps.python.org/pep-0448/)

---

## 💡 今日重点回顾

```
元组的不可变性 → 数据安全 + 可哈希
        ↓
  可做字典键  → 坐标、配置常量、数据库记录
        ↓
  namedtuple  → 自描述性 + 可拆包 + 轻量不可变数据结构
        ↓
  性能优势     → 内存小、创建快、迭代快
        ↓
  适合场景     → 固定结构数据、多返回值、常量集合
```
