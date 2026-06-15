# Day 022 — 生成器 练习题与检查表

## ✅ 完成检查表

### 概念理解
- [ ] 理解生成器函数和普通函数的区别
- [ ] 理解 yield 关键字的暂停/恢复机制
- [ ] 能解释生成器的状态机模型
- [ ] 理解 send/throw/close 的用法
- [ ] 理解 yield from 的双向委托机制
- [ ] 能区分生成器、迭代器、可迭代对象
- [ ] 理解惰性求值的内存优势

### 代码实践
- [ ] 能徒手写出使用 yield 的生成器函数
- [ ] 能写出生成器表达式
- [ ] 会使用 send() 向生成器传入值
- [ ] 会使用 throw() 向生成器抛异常
- [ ] 会使用 close() 关闭生成器
- [ ] 会使用 yield from 委托子生成器
- [ ] 会用生成器实现数据管道
- [ ] 会用生成器处理大文件

### 练习完成
- [ ] 基础练习（1-4 题）
- [ ] 进阶练习（5-8 题）
- [ ] 挑战练习（9-10 题）

---

## 📝 基础练习

### 练习 1：偶数生成器

写一个生成器函数 `even_numbers(max_n)`，生成 0 到 max_n 之间的所有偶数。

```python
def even_numbers(max_n):
    """生成 0 到 max_n 之间的偶数"""
    # TODO: 使用 yield
    pass

# 测试
result = list(even_numbers(10))
print(result)  # 应该输出 [0, 2, 4, 6, 8, 10]
```

<details>
<summary>提示</summary>
从 0 开始，步长为 2，不超过 max_n。
</details>

### 练习 2：生成器表达式

用一行生成器表达式完成以下任务：

```python
# 1. 生成 1 到 10 的平方
squares = (x**2 for x in range(1, 11))
print(list(squares))  # [1, 4, 9, ..., 100]

# 2. 从文本中过滤出长度大于 3 的单词
text = "Python generators are awesome"
words = text.split()
long_words = (w for w in words if len(w) > 3)  # TODO
print(list(long_words))  # ['Python', 'generators', 'awesome']

# 3. 生成 1 到 100 之间能被 3 整除但不能被 5 整除的数
# TODO: 写一个生成器表达式
result = (x for x in range(1, 101) if x % 3 == 0 and x % 5 != 0)
print(list(result))
```

### 练习 3：带状态的生成器

实现一个生成器 `running_sum`，每次 yield 当前所有收到的值的总和。

```python
def running_sum():
    """累加所有收到的值，每次 yield 当前总和"""
    total = 0
    # TODO: 接收值并累加
    pass

# 测试
gen = running_sum()
next(gen)  # 启动
print(gen.send(10))  # 10
print(gen.send(20))  # 30
print(gen.send(5))   # 35
```

### 练习 4：分块读取生成器

实现一个生成器 `read_in_chunks(file_path, chunk_size)`，以指定大小（字节）分块读取文件。

```python
def read_in_chunks(file_path, chunk_size=1024):
    """生成器：分块读取文件"""
    # TODO: 每次读取 chunk_size 字节并 yield
    pass
```

```python
# 测试（创建临时文件）
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
    f.write('x' * 2500)  # 2.5KB
    temp_path = f.name

count = 0
for chunk in read_in_chunks(temp_path, 1000):
    print(f"块 {count+1}: {len(chunk)} 字节")
    count += 1
# 预期: 块1=1000, 块2=1000, 块3=500

import os
os.unlink(temp_path)
```

---

## 🔥 进阶练习

### 练习 5：斐波那契生成器

实现一个生成器 `fibonacci()`，无限生成斐波那契数列。用 `itertools.islice` 取前 N 个。

```python
import itertools

def fibonacci():
    """生成器：无限斐波那契数列"""
    a, b = 0, 1
    while True:
        # TODO: yield 当前值并计算下一个
        pass

# 测试
first_10 = list(itertools.islice(fibonacci(), 10))
print(first_10)  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

# 找第一个大于 1000 的值
for val in fibonacci():
    if val > 1000:
        print(f"第一个 > 1000: {val}")
        break
```

### 练习 6：管道生成器

实现三个生成器，组成处理管道：

```python
def read_numbers(n):
    """生成 1 到 n 的数字"""
    # TODO: yield 1..n
    pass

def filter_even(numbers):
    """过滤出偶数"""
    # TODO: 接收生成器，yield 偶数
    pass

def square(numbers):
    """对每个数求平方"""
    # TODO: 接收生成器，yield 平方
    pass

# 管道: read → filter → square
pipeline = square(filter_even(read_numbers(10)))
print(list(pipeline))  # [4, 16, 36, 64, 100]
```

### 练习 7：文件 grep

实现一个生成器 `grep(file_path, pattern)`，逐行读取文件，返回匹配模式的行。

```python
def grep(file_path, pattern):
    """生成器：返回文件中匹配 pattern 的行"""
    # TODO: 逐行读取，如果 pattern in line，yield line
    pass

# 测试
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
    f.write("apple\nbanana\navocado\ncherry\nblueberry\n")
    temp_path = f.name

# 查找包含 'a' 的行
matches = list(grep(temp_path, 'a'))
print(f"匹配 'a': {matches}")  # ['apple', 'banana', 'avocado', 'blueberry']

import os
os.unlink(temp_path)
```

### 练习 8：生成器协程 — 计数器

实现一个协程 `counter()`，每次 send 时，yield 当前收到的总次数。

```python
def counter():
    """协程：每次接收数据，返回已接收的总次数"""
    count = 0
    # TODO: 实现接收 → 计数 → yield 的逻辑
    pass

# 测试
c = counter()
next(c)  # 启动
print(c.send('a'))  # 1
print(c.send('b'))  # 2
print(c.send('c'))  # 3
```

---

## 🏆 挑战练习

### 练习 9：CSV 到 JSON 的转换器

用生成器实现一个 CSV 到 JSON（字典列表）的转换器。

```python
def csv_to_json(file_path):
    """生成器：将 CSV 每行转为字典

    CSV 格式（第一行为标题）:
    name,age,city
    Alice,28,Beijing
    Bob,32,Shanghai

    输出:
    {'name': 'Alice', 'age': '28', 'city': 'Beijing'}
    {'name': 'Bob', 'age': '32', 'city': 'Shanghai'}
    """
    # TODO: 读取 CSV，第一行做 header，后续每行转为 dict
    pass

# 测试
import tempfile
csv_content = """name,age,city
Alice,28,Beijing
Bob,32,Shanghai
Charlie,25,Guangzhou"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
    f.write(csv_content)
    temp_path = f.name

for row in csv_to_json(temp_path):
    print(row)
# 预期输出:
# {'name': 'Alice', 'age': '28', 'city': 'Beijing'}
# {'name': 'Bob', 'age': '32', 'city': 'Shanghai'}
# {'name': 'Charlie', 'age': '25', 'city': 'Guangzhou'}

import os
os.unlink(temp_path)
```

### 练习 10：重试生成器

实现一个生成器 `with_retry(generator, max_retries=3)`，在生成器抛出异常时自动重试。

```python
def with_retry(generator_func, max_retries=3):
    """包装生成器，失败时自动重试

    generator_func: 一个返回生成器的函数（无参）
    max_retries: 最大重试次数
    """
    # TODO: 每次 yield 时捕获异常，如果出错则重新创建生成器继续
    pass

# 测试
attempt = [0]

def unstable_gen():
    """不稳定的生成器，前两次调用会失败"""
    attempt[0] += 1
    for i in range(3):
        if attempt[0] <= 2 and i == 1:  # 前两次调用的第二个元素会失败
            raise ConnectionError("Network error!")
        yield i

# 使用重试包装
retry_gen = with_retry(unstable_gen, max_retries=3)
result = list(retry_gen)
print(f"结果: {result}")  # 应该输出 [0, 1, 2]（虽然中间失败了但自动重试）
print(f"尝试次数: {attempt[0]}")  # 3（第一次失败重试，第二次失败重试，第三次成功）
```

<details>
<summary>提示</summary>
在 yield 外层加 try/except，捕获异常后重新创建生成器对象。
但要注意：重新创建意味着从头开始，所以要确保调用者能接上之前的状态。
可以这样实现：
```python
def with_retry(generator_func, max_retries=3):
    gen = generator_func()
    for attempt in range(max_retries + 1):
        try:
            for value in gen:
                yield value
        except Exception:
            if attempt >= max_retries:
                raise
            gen = generator_func()
```
</details>

---

## 💡 思考题

1. 生成器函数中的 `return` 和普通函数中的 `return` 有什么区别？
2. 为什么生成器能"记住"局部变量的值？底层是如何实现的？
3. `yield from` 和 `for item in sub:` 在处理子生成器的 `return` 值时有什么区别？
4. 在什么场景下应该用生成器函数，什么场景下应该用生成器表达式？
5. 生成器的 `gi_frame` 属性在生成器消耗后变成什么？这意味着什么？
6. 一个生成器调用另一个生成器（非 yield from）会有什么问题？
7. 如何实现一个可无限使用的生成器？（提示：每次调用返回新的）
8. 生成器 pipeline 和 Unix pipe 有什么异同？

## 📊 自我评估

| 技能 | 😰 不熟练 | 🤔 基本掌握 | 💪 熟练 |
|------|----------|------------|--------|
| yield 暂停/恢复 | | | |
| 生成器表达式 | | | |
| send/throw/close | | | |
| yield from 委托 | | | |
| 惰性求值理解 | | | |
| 大文件处理 | | | |
| 数据管道（pipeline） | | | |
| 协程概念 | | | |
| 生成器状态机 | | | |
| 生成器 vs 迭代器选择 | | | |

---

## 🧪 挑战题解答思路

### 练习 9：CSV 转 JSON 生成器

```python
def csv_to_json(file_path):
    with open(file_path, 'r') as f:
        header = None
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split(',')
            if header is None:
                header = parts
                continue

            yield dict(zip(header, parts))
```

### 练习 10：重试生成器

```python
def with_retry(generator_func, max_retries=3):
    for attempt in range(max_retries + 1):
        gen = generator_func()
        try:
            yield from gen
            break  # 成功了就退出循环
        except Exception as e:
            if attempt >= max_retries:
                raise
            print(f"  重试 {attempt + 1}/{max_retries} (错误: {e})")
            # 继续循环，重新创建生成器
    # 注意：这种实现会导致已 yield 的值在重试时重新生成
    # 更复杂的版本需要记录已 yield 的位置并恢复
```
