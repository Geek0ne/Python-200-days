# 检查清单与练习题

> Day 013: 作用域与命名空间

---

## ✅ 今日完成清单

- [ ] 理解作用域（Scope）的概念与设计目的（命名隔离）
- [ ] 理解命名空间（Namespace）—— 变量名到对象的映射字典
- [ ] 掌握 LEGB 查找规则及每一层的作用范围
- [ ] 理解变量遮蔽（Shadowing）及如何发生
- [ ] 区分"读取变量"和"赋值变量"的不同行为
- [ ] 掌握 `global` 关键字的用途和使用场景
- [ ] 掌握 `nonlocal` 关键字的用途和使用场景
- [ ] 理解 `global` vs `nonlocal` 的区别
- [ ] 理解闭包（Closure）的定义和底层实现（`__closure__`, `cell`）
- [ ] 理解闭包如何延长变量生命周期
- [ ] 掌握闭包的应用场景：函数工厂、数据封装
- [ ] 理解闭包的延迟绑定陷阱及解决方案（默认参数、额外闭包层）
- [ ] 理解变量的生命周期与各作用域的创建/销毁时机
- [ ] 完成实战：计数器工厂
- [ ] 能解释闭包和类的各自优劣

---

## 📝 练习题

### 练习 1：调试 LEGB 查找

下面的代码会输出什么？为什么？

```python
x = 10

def outer():
    x = 20

    def inner():
        print(x)

    inner()

outer()
print(x)
```

**进阶**：如果给 `inner` 加上 `x = 30` 放在 `print(x)` 之前会怎样？之后呢？

---

### 练习 2：实现一个简易状态机

使用闭包实现一个简单的红绿灯状态机，状态循环为：`红灯 → 绿灯 → 黄灯 → 红灯`。

要求：
- `create_traffic_light()` 创建一个红绿灯
- 返回的灯有 `next()` 方法切换状态
- `current()` 方法查看当前状态
- 初始状态为红灯

```python
# 期望行为
light = create_traffic_light()
print(light.current())  # → 红灯
light.next()
print(light.current())  # → 绿灯
light.next()
print(light.current())  # → 黄灯
light.next()
print(light.current())  # → 红灯（循环）
```

---

### 练习 3：修复闭包陷阱

下面的代码期望输出 `[0, 1, 4, 9, 16]`（0到4的平方），但实际输出有 bug。找出并修复问题。

```python
def create_squarers():
    funcs = []
    for n in range(5):
        def squarer():
            return n * n
        funcs.append(squarer)
    return funcs

results = [f() for f in create_squarers()]
print(results)  # 期望 [0, 1, 4, 9, 16]，实际是？
```

要求：给出至少两种不同的修复方案。

---

### 练习 4：非局部变量修改

不使用 `nonlocal` 关键字，如何在一个嵌套函数中修改外层函数的变量？（提示：可变对象）

```python
def counter_without_nonlocal():
    # 请补全，要求不使用 nonlocal
    # 但仍然能在内层函数中修改 count
    pass
```

---

### 练习 5：作用域探针

编写一个函数 `analyze_scope(func)`，它接收一个函数作为参数，打印该函数的所有作用域相关信息：

- 局部变量名列表
- 自由变量名列表（如果有）
- 闭包 cell 的内容（如果有）
- 全局变量引用（通过检查 `__globals__`）

```python
def analyze_scope(func):
    """分析函数的作用域信息"""
    # 补全代码
    pass

# 测试
def test():
    x = 10
    def inner():
        y = x + 1
        return y
    return inner

analyze_scope(test())
```

---

## 📊 自我评估

| 知识点 | 理解程度 (1-5) | 备注 |
|--------|---------------|------|
| LEGB 规则 | ⚪⚪⚪⚪⚪ | |
| global 声明 | ⚪⚪⚪⚪⚪ | |
| nonlocal 声明 | ⚪⚪⚪⚪⚪ | |
| 闭包原理 | ⚪⚪⚪⚪⚪ | |
| 变量生命周期 | ⚪⚪⚪⚪⚪ | |
| 延迟绑定陷阱 | ⚪⚪⚪⚪⚪ | |

> 😊 完成练习题后，标记检查清单的对应项，并在自我评估中打分。
