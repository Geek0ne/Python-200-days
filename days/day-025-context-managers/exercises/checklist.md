# Day 025 — 上下文管理器 练习题与检查表

## ✅ 完成检查表

### 概念理解
- [ ] 理解 `with` 语句的底层执行流程（`__enter__` → 代码块 → `__exit__`）
- [ ] 能解释 `__enter__` 返回值与 `as` 子句的关系
- [ ] 理解 `__exit__` 的三个参数（exc_type, exc_val, exc_tb）的含义
- [ ] 理解 `__exit__` 返回 True/False 对异常传播的影响
- [ ] 能区分上下文管理器和 try/finally 的优劣
- [ ] 理解 `@contextmanager` 装饰器的 yield 模式
- [ ] 理解 `contextlib.suppress`, `contextlib.closing`, `contextlib.redirect_stdout` 的用途
- [ ] 理解 `ExitStack` 动态管理多个上下文管理器的原理
- [ ] 理解异步上下文管理器 `__aenter__` / `__aexit__`

### 代码实践
- [ ] 能手动实现基于类的上下文管理器（`__enter__` / `__exit__`）
- [ ] 能使用 `@contextmanager` 装饰器实现上下文管理器
- [ ] 能在 `__exit__` 中正确处理异常（抑制/传播/记录）
- [ ] 能使用 `contextlib.closing` 管理资源的 close 方法
- [ ] 能使用 `contextlib.suppress` 静默忽略异常
- [ ] 能使用 `contextlib.ExitStack` 管理动态数量的资源
- [ ] 能使用 `contextlib.nullcontext` 实现条件性上下文
- [ ] 能实现带有回滚机制的上下文管理器（如原子写入）
- [ ] 能实现异步上下文管理器
- [ ] 能组合嵌套多个上下文管理器

### 练习完成
- [ ] 基础练习（1-3 题）
- [ ] 进阶练习（4-6 题）
- [ ] 挑战练习（7-8 题）

---

## 📝 基础练习

### 练习 1：手动实现一个计时器上下文管理器

不使用 `@contextmanager`，编写一个基于类的 `Timer` 上下文管理器。

要求：
- 在 `__enter__` 中记录开始时间
- 在 `__exit__` 中计算并打印耗时（毫秒）
- 支持 `as t` 绑定，通过 `t.elapsed` 获取耗时
- 异常情况下仍然记录耗时

```python
with Timer("MyTask") as t:
    time.sleep(0.5)
    # 一些操作
print(f"耗时: {t.elapsed:.2f}s")  # → 约 0.5s
```

### 练习 2：实现一个文件读取统计器

实现上下文管理器 `FileStats`，它可以统计：
- 文件总行数
- 总字符数
- 读取耗时

```python
with FileStats("data.txt") as stats:
    content = stats.read()
print(f"行数: {stats.lines}, 字符数: {stats.chars}, "
      f"耗时: {stats.elapsed*1000:.1f}ms")
```

### 练习 3：使用 closing 管理网络连接

假设有以下模拟的 Socket 类，使用 `contextlib.closing` 管理它的生命周期：

```python
class MockSocket:
    def __init__(self, host, port):
        print(f"连接到 {host}:{port}")
    def send(self, data):
        print(f"发送: {data}")
    def close(self):
        print("连接已关闭")

# 用 contextlib.closing 包装
```

---

## 🔧 进阶练习

### 练习 4：自动重试上下文管理器

实现 `RetryOnFailure` 上下文管理器，在 with 块内发生指定异常时自动抑制异常并记录日志，让程序继续执行。同时支持配置：

```python
# 静默忽略 ValueError
with RetryOnFailure(max_retries=3):
    ...

# 只忽略特定异常
with RetryOnFailure(max_retries=3, catch=(ConnectionError, TimeoutError)):
    ...
```

**提示**：`__exit__` 返回 True 时异常被抑制，但 with 块不会重新执行。要实现"真正的重试"，需要使用循环包裹。

### 练习 5：临时环境上下文

实现 `TempEnv` 上下文管理器，能在进入 with 块时设置环境变量，退出时恢复：

```python
with TempEnv(DATABASE_URL="test.db", DEBUG="1"):
    # 这里 os.environ 中包含了新设置
    pass
# 这里 os.environ 恢复原状
```

### 练习 6：HTML 标签生成器

使用 `@contextmanager` 实现一个 HTML 标签上下文管理器：

```python
with html_tag("div", class_="container") as t:
    with html_tag("p"):
        print("Hello, World!")
```

期望输出：
```html
<div class="container">
  <p>
    Hello, World!
  </p>
</div>
```

---

## 🏆 挑战练习

### 练习 7：数据库事务管理器

实现一个模拟的数据库事务上下文管理器 `Transaction`，支持：

1. 正常退出 → 自动 COMMIT
2. 异常退出 → 自动 ROLLBACK
3. 支持 Savepoint（保存点）/ 子事务
4. 支持嵌套事务（使用 ExitStack）

```python
with Transaction("accounts") as tx:
    tx.execute("UPDATE users SET balance = balance - 100 WHERE id = 1")
    with tx.savepoint():
        tx.execute("UPDATE users SET balance = balance + 100 WHERE id = 2")
        # 如果这里失败，只回滚到 savepoint
    # 外层事务正常提交
```

### 练习 8：Python 装饰器 + 上下文管理器统一

实现一个 `timeit` 对象，既可以用作装饰器，也可以用作上下文管理器：

```python
@timeit("排序")
def sort_data():
    ...

# 等价于
with timeit("排序"):
    sort_data()
```

---

## 📖 参考资源

- [PEP 343 — The "with" Statement](https://peps.python.org/pep-0343/)
- [Python 官方文档 — contextlib](https://docs.python.org/3/library/contextlib.html)
- [Python 官方文档 — With Statement Context Managers](https://docs.python.org/3/reference/datamodel.html#context-managers)

## 💡 提示

- 调试上下文管理器时，可以在 `__enter__` 和 `__exit__` 中添加 `print` 语句观察执行顺序
- `@contextmanager` 装饰的生成器必须 yield 精确一次，不能多也不能少
- `ExitStack` 的回调函数（callback）可以用来注册任意的清理操作
- `__exit__` 中如果要处理异常，注意不要意外返回 True 而掩盖 bug
