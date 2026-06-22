# Day 034 — 多态与鸭子类型：检查清单

> ✅ 完成后勾选，标记为 `[x]`

## 📚 概念理解

- [ ] 理解多态的定义：同一接口，不同实现
- [ ] 理解 Python 中的多态是动态多态（运行时绑定）
- [ ] 掌握静态多态（编译时绑定）和动态多态的区别
- [ ] 理解鸭子类型的哲学：「如果它走起来像鸭子…」
- [ ] 理解 EAFP 比 LBYL 更 Pythonic 的原因
- [ ] 掌握抽象基类（ABC）的作用：定义接口契约
- [ ] 理解虚拟子类和 `register()` 机制的应用场景
- [ ] 了解 Python 内置的 `collections.abc` 中的 ABC

## 💻 代码实践

- [ ] 编写使用继承实现多态的代码
- [ ] 编写使用鸭子类型实现多态的代码
- [ ] 用 EAFP 风格重写一个 LBYL 风格的函数
- [ ] 使用 `abc.ABC` 和 `@abstractmethod` 创建抽象基类
- [ ] 使用 `register()` 注册虚拟子类
- [ ] 实现 `__subclasshook__` 自动识别类
- [ ] 使用 `collections.abc.MutableSequence` 创建自定义序列
- [ ] 使用 `typing.Protocol` 定义结构化接口
- [ ] 实现一个完整的插件系统

## 🧪 练习题

请完成以下练习，每题创建一个单独的 `.py` 文件。

### 练习 1：形状计算器（继承多态）

设计一个形状计算系统：
- 创建抽象基类 `Shape`，包含抽象方法 `area()` 和 `perimeter()`
- 实现 `Circle`, `Rectangle`, `Triangle` 子类
- 编写一个函数，接受 `Shape` 列表并计算总面积

**示例：**
```python
shapes = [Circle(5), Rectangle(3, 4), Triangle(3, 4, 5)]
print(f"总面积: {total_area(shapes):.2f}")
# 输出: 总面积: 100.54
```

### 练习 2：鸭子类型 —— 日志系统

创建不同类型的日志记录器，它们都实现相同的接口但不继承同一个基类：
- `ConsoleLogger`：输出到控制台
- `FileLogger`：输出到文件
- `EmailLogger`：发送邮件（模拟）
- 编写一个函数，接受「任何有 log 方法的对象」

**要求：** 使用鸭子类型，不需要继承关系。

### 练习 3：EAFP 实践 —— 安全计算器

实现一个安全的计算器函数 `safe_calc(a, op, b)`：
- 使用 EAFP 风格处理所有可能的错误
- 支持 +, -, *, /, //, %, ** 操作
- 正确处理：类型错误、除零错误、溢出错误等
- 不能用 if/elif 检查类型

**示例：**
```python
safe_calc(10, '/', 0)      # None (除零)
safe_calc(10, '+', 'abc')  # None (类型错误)
safe_calc(10, '/', 3)      # 3.333...
```

### 练习 4：自定义序列（ABC）

使用 `collections.abc.Sequence` 创建一个 `Range2` 类，功能类似 `range` 但支持浮点数步长：
```python
r = Range2(0, 1, 0.1)
print(len(r))           # 10
print(r[0], r[5])       # 0.0, 0.5
print(0.5 in r)         # True
print(isinstance(r, Sequence))  # True
```

### 练习 5：迷你插件系统 —— 图片滤镜

实现一个简单的图片滤镜插件系统（使用字符串模拟）：
- 定义 `FilterBase` 抽象基类
- 实现 `BlurFilter`, `SharpenFilter`, `EdgeDetectFilter`
- 实现 `FilterPipeline` 管理滤镜链
- 支持添加、移除、重新排序滤镜
- 支持「预览」（只应用前 N 个滤镜）

---

## 📊 进度追踪

| 项目 | 完成情况 |
|------|---------|
| 阅读 README.md | [ ] |
| 运行 01-basic-usage.py | [ ] |
| 运行 02-advanced-usage.py | [ ] |
| 运行 03-plugin-system.py | [ ] |
| 练习 1：形状计算器 | [ ] |
| 练习 2：日志系统 | [ ] |
| 练习 3：安全计算器 | [ ] |
| 练习 4：自定义序列 | [ ] |
| 练习 5：迷你插件系统 | [ ] |
| 完成检查清单 | [ ] |
