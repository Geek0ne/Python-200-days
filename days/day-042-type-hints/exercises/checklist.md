# Day 42 完成清单

## 今日学习：类型提示与检查

- [ ] 理解类型提示的作用（开发期检查 vs 运行时行为）
- [ ] 掌握 `List`, `Dict`, `Tuple`, `Set` 等基础容器类型注解
- [ ] 理解 `Optional[T] = Union[T, None]` 的含义
- [ ] 掌握 `Union`, `Any`, `Callable`, `Literal` 的用法
- [ ] 理解类型别名与 `Final` 常量的使用场景
- [ ] 掌握 `TypeVar` 的定义和三种用法（无约束、constrained、bound）
- [ ] 掌握 `Generic[T]` 创建泛型类
- [ ] 理解 `Protocol` 结构化子类型与鸭子类型的关系
- [ ] 理解 `@overload` 的用途和限制
- [ ] 了解 `pydantic` 运行时验证的基本用法
- [ ] 能够在实际 API 封装中使用类型提示

## 练习题

### 练习 1：为函数添加类型注解

```python
# 给以下函数添加完整的类型注解，不改变实现
def add(a, b):
    return a + b

def get_user_name(users, uid):
    return users.get(uid)

def process_items(items, callback):
    result = []
    for item in items:
        result.append(callback(item))
    return result

def batch_process(*args, **kwargs):
    results = {}
    for key, value in kwargs.items():
        results[key] = sum(value)
    return results
```

### 练习 2：实现泛型队列

用 `Generic[T]` 实现一个泛型队列 `Queue[T]`，包含：
- `enqueue(item: T) -> None`：入队
- `dequeue() -> T`：出队（空队列抛出 IndexError）
- `peek() -> T`：查看队首
- `is_empty() -> bool`：是否为空
- `__len__() -> int`

### 练习 3：Protocol 实现可排序比较

定义一个 `Comparable` Protocol，要求实现 `__lt__` 方法。
然后写一个泛型排序函数 `sort_desc(items: List[T]) -> List[T]`，
要求 T 满足 Comparable 协议。

### 练习 4：pydantic 数据校验

假设有一段 JSON 数据需要校验：

```json
{
  "title": "Python 类型提示",
  "author": "Alice",
  "year": 2024,
  "tags": ["python", "typing"],
  "pages": null
}
```

用 pydantic 定义 `Book` 模型，要求：
- `title`: str, 必填
- `author`: str, 必填
- `year`: int, 必须 >= 1900
- `tags`: List[str], 默认空列表
- `pages`: Optional[int], 可选

### 练习 5：mypy 严格模式检查

在项目根目录创建 `pyproject.toml`，配置 mypy 严格模式：

```toml
[tool.mypy]
strict = true
```

然后对 `01-typing-basics.py` 运行 mypy 检查，修复所有报告的类型错误。

---

## 附加资源

- [mypy 官方文档](https://mypy-lang.org/)
- [Python typing 模块文档](https://docs.python.org/3/library/typing.html)
- [pydantic 文档](https://docs.pydantic.dev/)
- [PEP 484 – Type Hints](https://peps.python.org/pep-0484/)
- [PEP 483 – The Theory of Type Hints](https://peps.python.org/pep-0483/)
