# Day 012 — 函数进阶：练习题与完成清单

> 完成所有练习后，在下方勾选 ✓，巩固今日所学。

---

## 📋 完成清单

- [ ] **概念理解**：能用自己的话解释默认参数陷阱的原理
- [ ] **代码验证**：用 `id()` 和 `__defaults__` 验证默认参数陷阱
- [ ] **None 模式**：掌握可变默认参数的正确写法
- [ ] ***args 打包**：理解位置参数 → 元组的打包过程
- [ ] **kwargs 打包**：理解关键字参数 → 字典的打包过程
- [ ] **解包操作**：掌握调用时 `*列表` 和 `**字典` 的解包语法
- [ ] **参数顺序**：记住完整的参数顺序（普通→*args→默认→仅限关键字→**kwargs）
- [ ] **仅限关键字**：理解 `*` 之后参数的含义和用途
- [ ] **函数注解**：掌握基本 Type Hints 语法
- [ ] **__annotations__**：了解注解的存储机制
- [ ] **mypy**：了解静态类型检查工具的作用
- [ ] **实战代码**：理解通用数据处理器的设计思想
- [ ] **代码运行**：成功运行 `01-default-param-trap.py`
- [ ] **代码运行**：成功运行 `02-args-kwargs.py`
- [ ] **代码运行**：成功运行 `03-type-hints.py`
- [ ] **代码运行**：成功运行 `04-universal-data-processor.py`

---

## 💪 练习题

### 练习 1：修复默认参数陷阱

下面的函数有一个"陷阱"，请找出并修复它。同时解释为什么它是错的。

```python
def register_students(student_names, enrolled=[]):
    """注册学生到课程"""
    for name in student_names:
        enrolled.append(name)
    return enrolled

# 测试
print(register_students(["张三", "李四"]))
print(register_students(["王五"]))  # 预期: ["王五"], 实际呢？
```

**要求：**
1. 先用原始代码跑一遍，观察问题
2. 使用 `__defaults__` 或 `id()` 验证问题原因
3. 修复代码（使用 None 模式）
4. 验证修复后每次调用都能得到正确结果

---

### 练习 2：迷你计算器 (args/kwargs)

写一个函数 `calculator(operation, *numbers, **options)`，支持：

- `operation`: 字符串，可选 "add"、"multiply"、"power"
- `*numbers`: 任意数量的数字
- `**options`: 可选的配置项
  - `precision`（int，默认 2）— 结果保留几位小数
  - `show_steps`（bool，默认 False）— 是否打印计算过程

**示例行为：**

```python
calculator("add", 1, 2, 3, 4)           # 返回 10
calculator("multiply", 2, 3, 4)          # 返回 24
calculator("power", 2, 3, 4)             # 返回 4096 (2^3^4)
calculator("add", 1.234, 5.678, precision=1)  # 返回 6.9
calculator("add", 1, 2, 3, show_steps=True)   
# 打印: 1 + 2 = 3, 3 + 3 = 6, 6 + 4 = 10
```

**提示：**
- `power` 操作需要用循环：从第一个数开始，反复对下一个数做幂运算
- `show_steps=True` 时打印中间结果
- 使用 `**options.get("precision", 2)` 获取精度设置

---

### 练习 3：带 Type Hints 的字符串处理函数

编写一个函数 `extract_emails(text: str) -> list[str]`，从一段文本中提取所有电子邮件地址。

**要求：**
- 完整的 Type Hints（参数和返回值）
- 使用 `@` 符号作为简单检测指标
- 返回找到的所有邮箱地址（去重）
- 如果没有找到，返回空列表 `[]`

**示例：**

```python
text = "联系我们: support@example.com 或 admin@test.org, 也可以发邮件给 info@demo.com"
print(extract_emails(text))
# ['support@example.com', 'admin@test.org', 'info@demo.com']

text2 = "这里没有邮箱"
print(extract_emails(text2))
# []
```

**进阶挑战：**
给函数添加一个可选参数 `domain_filter: str | None = None`，只返回指定域名的邮箱：

```python
text = "联系: a@gmail.com 或 b@outlook.com 或 c@gmail.com"
print(extract_emails(text, domain_filter="gmail.com"))
# ['a@gmail.com', 'c@gmail.com']
```

---

### 练习 4：通用日志格式化器

利用 `*args` 和 `**kwargs` 写一个灵活的日志函数 `log_message`：

```python
def log_message(level, *messages, **options):
    """
    level: 日志级别 (INFO, WARN, ERROR)
    *messages: 任意数量的消息
    **options: 可选的格式选项
        - timestamp (bool): 是否显示时间戳
        - separator (str): 多个消息之间的分隔符
        - output (str): "console" 或 "file"
    """
    # 你的代码在这里
```

**要求：**
1. 用 `[]` 包裹日志级别，如 `[INFO]`, `[WARN]`
2. 如果有时间戳，格式为 `[2026-06-04 18:30:00]`
3. 多个消息之间用 `separator` 分隔（默认是空格）
4. 如果 `output="file"`，除了打印还要返回格式化后的字符串

**示例行为：**

```python
log_message("INFO", "系统启动", "加载配置", timestamp=True)
# 输出: [2026-06-04 18:30:00] [INFO] 系统启动 加载配置

log_message("ERROR", "连接失败", "重试中", "放弃", separator=" → ")
# 输出: [ERROR] 连接失败 → 重试中 → 放弃

log = log_message("WARN", "磁盘不足", output="file")
print(log)  # 同时打印并返回字符串
```

---

### 练习 5：综合 — 灵活的报告生成器

写一个函数 `generate_report(title, *data_points, agg_func=None, **options)`，综合利用今天的所有知识点。

**规格：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `title` | `str` | 报告标题 |
| `*data_points` | `int \| float` | 数据点 |
| `agg_func` | `Callable \| None` | 自定义聚合函数；None 时使用内置聚合 |
| `**options` | — | 见下表 |

**options 支持：**

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `builtin_method` | `str` | `"sum"` | 内置聚合方法（sum/mean/max/min） |
| `sort_data` | `bool` | `False` | 是否排序数据 |
| `show_distribution` | `bool` | `False` | 是否显示分布（计算最大值-最小值） |
| `precision` | `int` | `2` | 结果精度 |

**示例：**

```python
# 基本使用
print(generate_report("销售数据", 100, 200, 150, 300, 250))
# 输出格式: 报告 [销售数据]: sum = 1000.00

# 自定义聚合
print(generate_report("测试", 1, 2, 3, agg_func=lambda x: sum(x) / len(x)))

# 完整配置
print(generate_report("学生成绩", 85, 92, 78, 95, 88,
                      sort_data=True,
                      show_distribution=True,
                      precision=1,
                      builtin_method="mean"))
```

**提示：**
- 如果 `agg_func` 不为 None，优先使用自定义聚合函数
- 自定义函数接收一个列表参数，返回一个值
- 使用 `isinstance(agg_func, Callable)` 来判断

---

## 📝 挑战题（选做）

### 挑战：默认可变参数的"合法"利用

虽然默认参数陷阱通常被认为是 bug，但有一种技术叫 **memoization（记忆化/缓存）** 有意识地利用了这个特性。请实现一个带缓存的斐波那契数列计算器：

```python
def fibonacci(n, cache={}):
    """计算第 n 个斐波那契数，利用默认参数缓存中间结果"""
    # 你的代码
```

**要求：**
1. 不使用类、不使用全局变量
2. 利用默认参数陷阱中的 cache 字典自动缓存计算结果
3. 计算 `fibonacci(50)` 应该瞬间完成（而不是数分钟）
4. 解释为什么这种方法"有效"

**延伸思考：**
- 这个方法有什么缺点？
- 你会用什么样的"更干净"的方式实现同样的缓存功能？
- 如果用户意外传入一个 `cache` 参数会怎样？

---

## 🔍 课后自查

学完今天的内容后，检查自己是否能回答以下问题：

- [ ] 为什么 `def f(lst=[])` 是陷阱？Python 什么时候创建默认参数对象？
- [ ] `*args` 在函数定义和函数调用中的含义有什么不同？
- [ ] Type Hints 是"强制的"还是"提示性的"？用什么工具可以强制执行？
- [ ] 为什么 `**kwargs` 必须在参数列表的最后？
- [ ] 仅限关键字参数的语法是什么？为什么需要这个特性？

---

> **提示：** 所有练习的答案不在仓库中，建议你在实际运行代码中探索和学习。遇到不懂的可以：
> 1. 在代码中加 `print()` 打印中间结果
> 2. 使用 `type()` 和 `id()` 观察对象
> 3. 在 Python 交互式环境（REPL）中实验
