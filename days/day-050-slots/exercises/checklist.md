# Day 050 — 槽（__slots__）练习清单

## ✅ 今日完成清单

- [ ] 理解 `__slots__` 的定义和内存优化原理
- [ ] 掌握 `__slots__` 与普通类的对比
- [ ] 理解 `__slots__` 与继承的关系
- [ ] 知道 `__slots__` 的常见陷阱和解决方案
- [ ] 能够在实际项目中应用 `__slots__`

---

## 📝 基础练习题

### 练习1：实现 `Vector` 类

```python
class Vector:
    __slots__ = ('x', 'y', 'z')

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, other): ...
    def __mul__(self, scalar): ...
    def magnitude(self): ...
    def normalize(self): ...
```

### 练习2：比较内存占用

创建 100,000 个普通类对象和 __slots__ 类对象，测量总内存占用差异。

### 练习3：只读 Slot

实现一个 `Config` 类，使用 `__slots__` 并通过 `@property` 实现只读属性。

---

## 🔥 进阶挑战题

### 挑战1：支持弱引用的 Slot

```python
class CacheEntry:
    __slots__ = ('key', 'value', '__weakref__')

    def __init__(self, key, value):
        self.key = key
        self.value = value

# 测试弱引用
import weakref
entry = CacheEntry("test", 42)
ref = weakref.ref(entry)
assert ref() is entry
```

### 挑战2：支持 Pickle 的 Slot

```python
class PickleableSlot:
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __getstate__(self):
        return {slot: getattr(self, slot) for slot in self.__slots__}

    def __setstate__(self, state):
        for slot, value in state.items():
            setattr(self, slot, value)
```

### 挑战3：Slot + dataclass 手动实现

在 Python 3.10 之前，手动实现 `@dataclass(slots=True)` 的功能。

---

## 📚 参考资源

- Python 官方文档：https://docs.python.org/3/reference/datamodel.html#slots
- PEP 572：Assignment Expressions
- 《Fluent Python》第9章：符合Python风格的对象
