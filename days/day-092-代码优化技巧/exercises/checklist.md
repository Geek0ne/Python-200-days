# Day 092 — 代码优化技巧 · 练习清单

## ✅ 今日完成清单

- [ ] 理解优化思维框架
- [ ] 掌握数据结构选择优化
- [ ] 掌握循环优化技巧
- [ ] 使用缓存策略提升性能
- [ ] 优化字符串处理
- [ ] 理解内存优化技巧
- [ ] 能够分析和优化慢代码

---

## 📝 基础练习

### 练习 1：数据结构选择
分析以下场景，选择最合适的数据结构：
```python
# 场景1: 需要频繁查找
data = [1, 2, 3, ..., 10000]

# 场景2: 需要频繁在头部插入
data = [1, 2, 3, ..., 10000]

# 场景3: 需要统计元素出现次数
data = ["apple", "banana", "apple", "cherry", "banana"]
```

### 练习 2：循环优化
优化以下代码，减少循环次数：
```python
data = list(range(100000))

# 原始代码: 多次遍历
max_val = max(data)
min_val = min(data)
avg_val = sum(data) / len(data)
```

### 练习 3：字符串优化
对比以下三种字符串拼接方法的性能：
```python
n = 10000

# 方法1: 字符串拼接
result = ""
for i in range(n):
    result += str(i)

# 方法2: join
parts = [str(i) for i in range(n)]
result = "".join(parts)

# 方法3: StringIO
from io import StringIO
buffer = StringIO()
for i in range(n):
    buffer.write(str(i))
result = buffer.getvalue()
```

---

## 🔥 进阶挑战

### 挑战 1：优化慢代码
优化以下代码，将其提速 10 倍以上：
```python
def slow_function(data):
    result = []
    for item in data:
        if item % 2 == 0:
            transformed = item ** 2 + item * 3
            if transformed > 100:
                if transformed not in result:
                    result.append(transformed)
    return sorted(result)
```

### 挑战 2：实现缓存装饰器
实现一个缓存装饰器，支持：
- 最大缓存大小限制
- 缓存过期时间
- 缓存命中率统计

### 挑战 3：性能分析报告
编写一个性能分析报告生成器，输入两个函数，自动输出：
- 平均执行时间
- 最快/最慢执行时间
- 内存使用对比
- 速度比

---

## 🤔 思考题

1. 什么时候应该用列表，什么时候应该用集合？

2. `lru_cache` 的 `maxsize` 参数如何选择？太大或太小有什么问题？

3. 在什么情况下必须用列表，不能用生成器？

4. 过度优化会带来什么问题？如何平衡性能和可读性？

5. 如何在项目中建立性能监控，防止新代码导致性能下降？
