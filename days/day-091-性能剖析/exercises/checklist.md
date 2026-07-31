# Day 091 — 性能剖析 · 练习清单

## ✅ 今日完成清单

- [ ] 理解性能剖析的意义和流程
- [ ] 掌握 cProfile 基本使用
- [ ] 掌握 line_profiler 行级剖析
- [ ] 了解 memory_profiler 内存剖析
- [ ] 使用 timeit 进行精确计时
- [ ] 能够分析性能剖析结果
- [ ] 识别常见性能陷阱

---

## 📝 基础练习

### 练习 1：使用 cProfile 剖析
剖析以下函数，找出最耗时的部分：
```python
def find_primes(n):
    """查找 n 以内的所有素数"""
    primes = []
    for num in range(2, n):
        is_prime = True
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
    return primes
```

### 练习 2：timeit 对比
使用 timeit 对比以下两种方法的性能：
```python
# 方法1: 列表推导
result1 = [x ** 2 for x in range(10000)]

# 方法2: map函数
result2 = list(map(lambda x: x ** 2, range(10000)))
```

### 练习 3：内存分析
分析以下代码的内存使用情况：
```python
def create_data():
    data = []
    for i in range(100000):
        data.append({"id": i, "value": i ** 2})
    return data
```

---

## 🔥 进阶挑战

### 挑战 1：性能对比报告
编写一个性能对比报告生成器，输入两个函数，自动输出：
- 平均执行时间
- 最快/最慢执行时间
- 内存使用对比
- 速度比

### 挑战 2：自动性能测试
创建一个装饰器，自动记录函数的：
- 调用次数
- 平均执行时间
- 最大/最小执行时间
- 内存峰值

### 挑战 3：性能回归检测
实现一个性能测试套件，能够：
- 记录基准性能
- 检测新代码是否导致性能下降
- 生成性能报告

---

## 🤔 思考题

1. 为什么 cProfile 的 tottime 和 cumtime 可能差别很大？

2. line_profiler 的输出中，Hits 列有什么意义？

3. 为什么 timeit 默认执行多次？只执行一次有什么问题？

4. 如何在生产环境中进行性能监控？

5. 性能剖析本身会影响程序性能吗？如何最小化影响？
