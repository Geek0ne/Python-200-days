# Day 035 — 特殊方法：检查清单

> ✅ 完成后勾选，标记为 `[x]`

## 📚 概念理解

- [ ] 理解 `__str__` 和 `__repr__` 的区别和用途
- [ ] 掌握 `__repr__` 的 `eval()` 重建约定
- [ ] 理解 `__getitem__` 如何同时支持索引和切片
- [ ] 理解 `__len__` 和 `__bool__` 的关系
- [ ] 掌握运算符重载的正向和反向机制
- [ ] 理解 `NotImplemented` 的作用（不是异常！）
- [ ] 理解原地运算符（`__iadd__` 等）与普通运算符的区别
- [ ] 理解 `__hash__` 和 `__eq__` 必须一起实现
- [ ] 理解 `__call__` 的应用场景
- [ ] 掌握 `__enter__` / `__exit__` 协议

## 💻 代码实践

- [ ] 实现带有 `__str__` 和 `__repr__` 的类
- [ ] 实现支持索引和切片的容器类
- [ ] 实现至少 3 个算术运算符重载
- [ ] 实现反向运算符（`__radd__`, `__rmul__`）
- [ ] 实现 `__eq__` 和 `__hash__` 使对象可哈希
- [ ] 使用 `__call__` 创建可调用对象
- [ ] 使用 `__enter__` / `__exit__` 创建上下文管理器
- [ ] 使用 `@functools.total_ordering` 简化比较运算符
- [ ] 运行并理解实战中的向量类

## 🧪 练习题

请完成以下练习，每题创建一个单独的 `.py` 文件。

### 练习 1：自定义字符串类

创建一个 `SmartString` 类，封装字符串并提供更多功能：

```python
s = SmartString("hello")
print(len(s))           # 5（实现 __len__）
print(s[0], s[-1])      # h, o（实现 __getitem__）
print(s[::-1])          # olleh（支持切片）
print('h' in s)         # True（__contains__ 或退化）
print(str(s))           # HELLO（__str__ 返回大写）
print(repr(s))          # SmartString('hello')
```

### 练习 2：复数计算器

实现一个 `Complex` 类（不要使用内置的 `complex` 类型）：

- 支持加、减、乘、除
- 支持比较（按模长）
- 支持 `abs()` 求模
- 支持转换为内置 `complex` 类型
- 可以使用 `conjugate()` 方法求共轭

**提示：** 复数的共轭：`(a + bi) 的共轭 = (a - bi)`

### 练习 3：缓存计算器

创建一个可调用类 `CachedCalculator`，实现计算斐波那契数的功能并缓存结果：

```python
calc = CachedCalculator()
calc(10)  # 计算并缓存
calc(10)  # 从缓存返回，不重新计算
calc.hits    # 命中次数
calc.misses  # 未命中次数
calc.clear() # 清空缓存
```

### 练习 4：时间范围迭代器

创建一个 `TimeRange` 类，表示一个时间范围，支持迭代：

```python
from datetime import time, timedelta

tr = TimeRange(time(9, 0), time(17, 0), timedelta(hours=1))
for t in tr:
    print(t)  # 09:00, 10:00, ..., 17:00

print(len(tr))    # 9（不是 8！包括首尾）
print(tr[0])      # 09:00
print(tr[-1])     # 17:00
print(time(12, 0) in tr)  # True
```

### 练习 5：矩阵类

实现一个简单的 `Matrix` 类（2D 矩阵）：

- 使用 `__init__` 从嵌套列表创建
- 支持 `m[i][j]` 访问（通过 `__getitem__` 返回行）
- 支持加法、减法、标量乘法
- 支持矩阵乘法 `@`
- 支持转置 `.T`（属性）
- 支持 `__repr__` 格式化显示

**示例：**
```python
m1 = Matrix([[1, 2], [3, 4]])
m2 = Matrix([[5, 6], [7, 8]])
print(m1 + m2)     # [[6, 8], [10, 12]]
print(m1 @ m2)     # [[19, 22], [43, 50]]
print(m1.T)        # [[1, 3], [2, 4]]
```

---

## 📊 进度追踪

| 项目 | 完成情况 |
|------|---------|
| 阅读 README.md | [ ] |
| 运行 01-basic-usage.py | [ ] |
| 运行 02-advanced-usage.py | [ ] |
| 运行 03-vector-class.py | [ ] |
| 练习 1：SmartString | [ ] |
| 练习 2：Complex 类 | [ ] |
| 练习 3：缓存计算器 | [ ] |
| 练习 4：TimeRange | [ ] |
| 练习 5：Matrix 类 | [ ] |
| 完成检查清单 | [ ] |
