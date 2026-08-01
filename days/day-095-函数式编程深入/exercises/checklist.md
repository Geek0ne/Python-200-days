# Day 095 — 函数式编程深入 · 练习清单

## ✅ 今日完成清单

- [ ] 掌握 functools 模块的所有高级函数
- [ ] 理解柯里化与偏函数的区别
- [ ] 学习不可变数据结构的使用场景
- [ ] 实现自定义管道组合
- [ ] 理解惰性求值的优势

---

## 📝 练习题

### 基础题

**1. functools 实战**

使用 functools 模块完成以下任务：
- 使用 `reduce` 实现字典扁平化（嵌套字典转一层字典）
- 使用 `lru_cache` 优化斐波那契数列，并统计缓存命中率
- 使用 `singledispatch` 实现一个多类型序列化器

```python
# 测试用例
nested = {"a": {"b": 1, "c": 2}, "d": 3}
# flatten_dict(nested) → {"a.b": 1, "a.c": 2, "d": 3}
```

**2. 柯里化管道**

使用柯里化创建一个数据处理管道生成器：
- 输入：函数列表
- 输出：柯里化版本的管道函数
- 支持部分应用

```python
pipeline = make_pipeline(
    str.strip,
    str.lower,
    lambda s: s.replace(" ", "_"),
)
# pipeline("  Hello World  ") → "hello_world"
# pipeline("  Good Bye  ") → "good_bye"
```

**3. 不可变数据操作**

实现一个不可变的栈（Stack）数据结构：
- `push(item)` → 返回新栈（原栈不变）
- `pop()` → 返回 (新栈, 弹出的元素)
- `peek()` → 查看栈顶元素
- `size()` → 返回大小

### 进阶题

**4. 惰性求值迭代器**

实现一个惰性求值的 Range 类：
- 支持 `map`, `filter`, `take` 操作
- 只在迭代时才计算
- 支持无限序列

```python
lazy = LazyRange(1, 1000000).filter(lambda x: x % 2 == 0).map(lambda x: x * 2).take(5)
print(list(lazy))  # [4, 8, 12, 16, 20]
```

**5. 函数式状态机**

使用不可变数据和函数组合实现一个有限状态机：
- 状态：OFF, ON, ERROR
- 转换：turn_on, turn_off, error_occurred, reset
- 每次转换返回新状态对象

```python
machine = StateMachine(initial="OFF")
machine = machine.transition("turn_on")  # OFF → ON
machine = machine.transition("error")    # ON → ERROR
```

**6. 数据验证管道**

构建一个可组合的数据验证管道：
- 每个验证规则是一个函数
- 管道支持短路（第一个失败就停止）
- 支持错误消息聚合

```python
validator = ValidationPipeline(
    required("username"),
    min_length("username", 3),
    max_length("username", 20),
    pattern("email", r'^[\w.-]+@[\w.-]+\.\w+$'),
)

result = validator.validate({"username": "alice", "email": "alice@example.com"})
# {"valid": True, "data": {...}}
```

---

## 🔍 检查点

完成后，确认你能回答以下问题：

1. `reduce` 和 `sum` 的区别是什么？什么时候用 `reduce`？
2. `lru_cache` 的 `maxsize` 参数设为 `None` 和设为具体数值有什么区别？
3. 柯里化和偏函数（partial）的区别是什么？各自的使用场景？
4. 为什么 `frozenset` 可以作为字典键，而 `set` 不行？
5. 惰性求值在处理大数据时有什么优势？
