# Day 43 完成清单

## 今日学习：数据类（dataclass）

> 每个知识点请至少看完对应代码并理解后再勾选 ✅

### 概念理解

- [ ] 理解 `@dataclass` 装饰器自动生成哪些方法（`__init__`/`__repr__`/`__eq__`/`__hash__`）
- [ ] 理解 `init`、`repr`、`eq`、`order`、`frozen` 五个装饰器参数的作用
- [ ] 理解 `field()` 的核心参数：`default`, `default_factory`, `init`, `repr`, `compare`, `hash`, `metadata`
- [ ] 理解 `__post_init__` 钩子的用途（验证、转换、计算）
- [ ] 理解为什么可变类型默认值必须用 `default_factory` 
- [ ] 理解 dataclass 的哈希行为规则（frozen → 可哈希 / 默认 → 不可哈希）
- [ ] 理解 dataclass vs namedtuple vs 普通类的各自适用场景

### 代码实践

- [ ] 运行 `code/01-basic-usage.py`，观察自动生成的方法
- [ ] 运行 `code/02-field-advanced.py`，理解 field() 各参数的用法
- [ ] 运行 `code/03-dataclass-vs-namedtuple.py`，对比三种方式的性能与灵活性
- [ ] 运行 `code/04-config-manager.py`，体验完整的配置管理实战

---

## 练习题

### 练习 1：最短 dataclass

用 `@dataclass` 定义一个 `Book` 类，包含以下字段：
- `title`: str（必填）
- `author`: str（必填）
- `year`: int（可选，默认 2024）
- `isbn`: str（可选，默认空字符串）

要求：
- 提供友好的 `__repr__`（用自动生成的）
- 两个相同内容的 `Book` 实例应该相等（用自动生成的）

```python
# 你的代码
from dataclasses import dataclass

@dataclass
class Book:
    ...
```

### 练习 2：带验证的学生类

用 `@dataclass` 定义一个 `Student` 类，使用 `__post_init__` 做以下验证：

```python
@dataclass
class Student:
    name: str
    age: int
    grades: list[int]   # 成绩列表
    average: float = field(init=False)  # 自动计算

    def __post_init__(self):
        # TODO:
        # 1. 年龄必须在 6-100 之间
        # 2. 成绩列表不能为空
        # 3. 每个成绩必须在 0-100 之间
        # 4. 自动计算 average（平均分，保留两位小数）
```

### 练习 3：订单管理系统

用 `@dataclass` 实现一个订单管理系统：
- `OrderItem`: 商品名称、数量、单价
- `Order`: 订单号（自动生成 UUID 前 8 位）、商品列表、总金额（自动计算）

要求：
- `OrderItem` 支持比较（只按单价比较）
- `Order` 的 `frozen=True`，确保订单创建后不可修改
- `Order` 的 `__repr__` 隐藏商品列表（只显示订单号和金额）

```python
from dataclasses import dataclass, field
from typing import List

@dataclass(order=True)
class OrderItem:
    ...

@dataclass(frozen=True)
class Order:
    ...
```

### 练习 4：dataclass vs namedtuple 重构

将以下 namedtuple 重构为 dataclass，并添加缺失功能：

```python
from typing import NamedTuple

class Employee(NamedTuple):
    name: str
    department: str
    salary: float

# 请重构为 dataclass，并添加：
# 1. 新增 employee_id 字段（自动生成，UUID 前 8 位，不在 __init__ 中）
# 2. 薪资验证（必须 > 0）
# 3. 年薪计算属性：annual_salary
# 4. repr 隐藏 employee_id（只显示姓名和部门）
```

### 练习 5：配置验证器

扩展课堂的配置管理系统，新增 `CacheConfig` 配置块：

```python
@dataclass
class CacheConfig:
    backend: str = "memory"     # memory / redis / memcached
    ttl: int = 300               # 缓存过期时间（秒）
    max_size: int = 1000         # 最大缓存条目数
    namespace: str = "default"

    def __post_init__(self):
        # TODO:
        # 1. backend 必须是 "memory", "redis", "memcached" 之一
        # 2. ttl 必须在 1-86400 之间（1秒到1天）
        # 3. max_size 必须在 10-100000 之间
```

然后将 `CacheConfig` 整合到 `AppConfig` 中（在 `04-config-manager.py` 基础上修改）。

### 练习 6：实战挑战 —— 序列化工具

写一个通用的 dataclass 序列化工具函数，支持：

```python
def dataclass_to_dict(obj) -> dict:
    """
    将 dataclass 递归转换为普通字典。
    处理嵌套 dataclass、列表、可选值。
    隐藏 repr=False 的字段。
    """
    ...

def dict_to_dataclass(cls, data: dict):
    """
    将字典递归还原为 dataclass 实例。
    处理嵌套 dataclass。
    """
    ...
```

应用场景：读取 `config.json` → 转换为配置 dataclass → 修改 → 保存回 `config.json`。

---

## 完成标准

- [ ] 我已运行所有示例代码并理解输出
- [ ] 我已独立完成至少 4 道练习题
- [ ] 我理解何时选择 dataclass 而不是 namedtuple 或普通类
- [ ] 我理解 `field(default_factory=list)` 的必要性
- [ ] 我能够在实际项目中使用 dataclass 构建配置系统

---

## 附加资源

- [PEP 557 – Data Classes](https://peps.python.org/pep-0557/)
- [Python 官方 dataclasses 文档](https://docs.python.org/3/library/dataclasses.html)
- [Real Python: Data Classes in Python 3.7+](https://realpython.com/python-data-classes/)
- [Raymond Hettinger 的 PyCon 2018 演讲](https://www.youtube.com/watch?v=T-TwcmT6Rcw)
