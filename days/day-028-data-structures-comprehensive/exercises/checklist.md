# Day 028 — 数据结构综合：完成清单与练习题

## ✅ 完成清单

### 概念理解
- [ ] 理解栈（Stack）的 LIFO 原理
- [ ] 理解队列（Queue）的 FIFO 原理
- [ ] 理解堆（Heap）的完全二叉树结构
- [ ] 理解最小堆与最大堆的区别
- [ ] 理解二分查找算法原理
- [ ] 理解中缀、后缀表达式的区别

### Python 实现
- [ ] 能够用 list 实现栈的基本操作
- [ ] 能够用 deque 实现队列的基本操作
- [ ] 能够使用 heapq 构建最小堆/最大堆
- [ ] 能够使用 bisect 进行二分查找和有序插入
- [ ] 能够实现调度场算法（中缀转后缀）
- [ ] 能够实现后缀表达式求值

### 代码实践
- [ ] 运行 `01-basic-usage.py` 理解基础用法
- [ ] 运行 `02-advanced-usage.py` 掌握进阶应用
- [ ] 运行 `03-expression-evaluation.py` 理解表达式求值
- [ ] 完成至少 3 道练习题

---

## 📝 练习题

### 练习 1：括号匹配进阶

```python
"""
扩展括号匹配，支持三种括号 ()、[]、{}，
同时要求括号之间有正确的嵌套顺序
"""
def is_valid_parentheses(s: str) -> bool:
    # 你的代码
    pass

# 测试用例
print(is_valid_parentheses("()[]{}"))     # → True
print(is_valid_parentheses("([)]"))       # → False
print(is_valid_parentheses("{[]}"))       # → True
print(is_valid_parentheses("((()))"))     # → True
print(is_valid_parentheses("((())"))      # → False
print(is_valid_parentheses("({[)]}"))    # → False
```

### 练习 2：用栈实现浏览器的前进后退

```python
"""
实现浏览器的前进和后退功能
- visit(url): 访问新页面
- back(): 后退到上一个页面
- forward(): 前进到下一个页面
"""
class BrowserHistory:
    def __init__(self, homepage: str):
        pass

    def visit(self, url: str) -> None:
        pass

    def back(self) -> str:
        pass

    def forward(self) -> str:
        pass

# 测试
browser = BrowserHistory("google.com")
browser.visit("facebook.com")
browser.visit("youtube.com")
print(browser.back())     # → facebook.com
print(browser.back())     # → google.com
print(browser.forward())  # → facebook.com
browser.visit("twitter.com")
print(browser.forward())  # → twitter.com (注意: visit 会清空前向栈)
```

### 练习 3：合并 K 个有序数组

```python
"""
使用 heapq 合并 K 个有序数组
"""
import heapq

def merge_k_sorted_arrays(arrays):
    # 你的代码
    pass

# 测试
arrays = [
    [1, 4, 7],
    [2, 5, 8],
    [3, 6, 9]
]
print(merge_k_sorted_arrays(arrays))
# → [1, 2, 3, 4, 5, 6, 7, 8, 9]
```

### 练习 4：自定义排序成绩

```python
"""
使用 bisect 实现一个成绩管理系统
支持插入成绩并自动维护有序列表
"""
class GradeManager:
    def __init__(self):
        self.grades = []

    def add_grade(self, score: int) -> None:
        # 插入成绩，保持有序
        pass

    def get_rank(self, score: int) -> int:
        # 返回该成绩的排名（从 1 开始）
        pass

    def get_percentile(self, score: int) -> float:
        # 返回该成绩的百分位（0~100）
        pass

# 测试
gm = GradeManager()
for score in [85, 92, 78, 95, 88, 76, 99, 81, 90, 87]:
    gm.add_grade(score)
print(gm.grades)  # → [76, 78, 81, 85, 87, 88, 90, 92, 95, 99]
print(gm.get_rank(85))  # → 4 (第 4 名)
print(gm.get_percentile(85))  # → 60.0 (超过 60% 的人)
```

### 练习 5：表达式求值扩展

```python
"""
扩展表达式求值，支持幂运算 `**` 和取模 `%`
"""
def evaluate_extended(expression: str) -> float:
    # 你的代码（可以复用表达式求值实战中的代码）
    pass

# 测试
print(evaluate_extended("2 ** 3 + 4"))      # → 12.0
print(evaluate_extended("10 % 3 * 2"))       # → 2.0
print(evaluate_extended("(2 + 3) ** 2"))     # → 25.0
print(evaluate_extended("2 ** 3 ** 2"))      # → 512.0 (右结合: 2^(3^2) = 2^9 = 512)
```

---

## 📊 自评表

| 技能 | 初学者 | 理解 | 掌握 | 熟练 |
|------|--------|------|------|------|
| 栈的实现与应用 | ☐ | ☐ | ☐ | ☐ |
| 队列的实现与应用 | ☐ | ☐ | ☐ | ☐ |
| heapq 堆操作 | ☐ | ☐ | ☐ | ☐ |
| bisect 二分查找 | ☐ | ☐ | ☐ | ☐ |
| 表达式求值 | ☐ | ☐ | ☐ | ☐ |

---

## 🔗 参考资源

- [Python heapq 官方文档](https://docs.python.org/3/library/heapq.html)
- [Python bisect 官方文档](https://docs.python.org/3/library/bisect.html)
- [Python collections.deque 官方文档](https://docs.python.org/3/library/collections.html#collections.deque)
- [调度场算法 — Wikipedia](https://en.wikipedia.org/wiki/Shunting_yard_algorithm)
- [逆波兰表达式 — Wikipedia](https://en.wikipedia.org/wiki/Reverse_Polish_notation)
