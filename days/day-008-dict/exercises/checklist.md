# Day 008 — 字典（Dict）练习与检查清单

> 📌 完成每个练习后，在 `[ ]` 中打 `[x]`

---

## ✅ 今日完成清单

### 概念理解
- [ ] 理解哈希表原理：哈希函数 → 索引映射 → O(1) 查找
- [ ] 理解哈希碰撞的原因与开放寻址法
- [ ] 理解为什么 dict 的键必须是可哈希的
- [ ] 理解 Python 3.7+ 字典保持插入顺序的机制

### 基本操作
- [ ] 掌握 7 种字典创建方式
- [ ] 掌握 get / setdefault / pop / update / popitem
- [ ] 掌握四种遍历方式（keys/values/items/解包）
- [ ] 掌握字典视图的动态特性与集合运算

### 字典推导式
- [ ] 掌握基础语法 `{k: v for ...}`
- [ ] 掌握条件过滤 `{k: v for ... if cond}`
- [ ] 掌握键值互换、zip 构建等实用模式

### 进阶工具
- [ ] 掌握 defaultdict(int) — 计数器
- [ ] 掌握 defaultdict(list) — 分组器
- [ ] 掌握 defaultdict(lambda: defaultdict(...)) — 嵌套字典
- [ ] 掌握 Counter 的创建、most_common、算术运算

### 实战
- [ ] 完成词频统计器代码
- [ ] 理解停用词过滤的逻辑
- [ ] 理解词汇丰富度等统计指标

---

## 📝 练习题

### 练习 1：学生成绩管理系统

用字典实现一个学生成绩管理系统，支持 CRUD 操作：

```python
# 数据结构：{学号: {"name": 姓名, "scores": {"语文": 分, "数学": 分, "英语": 分}}}

class GradeManager:
    """学生成绩管理系统"""
    
    def __init__(self):
        self._students = {}  # key: student_id, value: dict
    
    def add_student(self, student_id: str, name: str):
        """添加学生"""
        pass
    
    def add_score(self, student_id: str, subject: str, score: float):
        """添加/更新某科成绩"""
        pass
    
    def get_student(self, student_id: str) -> dict:
        """获取学生信息（不存在返回空字典）"""
        pass
    
    def get_average(self, student_id: str) -> float:
        """计算学生平均分"""
        pass
    
    def get_class_average(self, subject: str) -> float:
        """计算全班某科平均分"""
        pass
    
    def get_ranking(self, subject: str) -> list:
        """获取某科排名（从高到低），返回 [(名次, 学号, 姓名, 分数), ...]"""
        pass
    
    def get_top_student(self, subject: str) -> str:
        """获取某科最高分学生姓名"""
        pass
    
    def remove_student(self, student_id: str) -> bool:
        """删除学生，返回是否成功"""
        pass

# 测试
manager = GradeManager()
manager.add_student("001", "Alice")
manager.add_student("002", "Bob")
manager.add_student("003", "Charlie")

manager.add_score("001", "语文", 90)
manager.add_score("001", "数学", 85)
manager.add_score("001", "英语", 92)
manager.add_score("002", "语文", 78)
manager.add_score("002", "数学", 95)
manager.add_score("002", "英语", 80)
manager.add_score("003", "语文", 88)

print(manager.get_student("001"))
print(f"Alice 平均分: {manager.get_average('001'):.1f}")
print(f"全班语文平均分: {manager.get_class_average('语文'):.1f}")
print(f"数学排名: {manager.get_ranking('数学')}")
print(f"英语最高分: {manager.get_top_student('英语')}")
```

**扩展挑战**：
- 支持导出为 CSV / JSON
- 支持按总分 / 平均分排名
- 支持不及格学生（<60 分）统计

---

### 练习 2：URL 查询参数解析器

实现一个 URL 查询字符串解析器：

```python
def parse_query_string(query: str) -> dict:
    """
    解析 URL 查询字符串为字典
    
    Args:
        query: "name=Alice&age=25&city=Beijing"
    
    Returns:
        {"name": "Alice", "age": "25", "city": "Beijing"}
    """
    pass

def build_query_string(params: dict) -> str:
    """
    将字典构建为 URL 查询字符串
    
    Args:
        params: {"name": "Alice", "age": 25}
    
    Returns:
        "name=Alice&age=25"
    """
    pass

def merge_query_params(base: str, extra: dict) -> str:
    """
    在已有 URL 上添加额外参数
    
    Args:
        base: "http://example.com/api?name=Alice"
        extra: {"age": 25, "city": "Beijing"}
    
    Returns:
        "http://example.com/api?name=Alice&age=25&city=Beijing"
    """
    pass

# 测试
print(parse_query_string("name=Alice&age=25&city=Beijing"))
# {'name': 'Alice', 'age': '25', 'city': 'Beijing'}

print(build_query_string({"name": "Bob", "role": "admin", "page": 1}))
# name=Bob&role=admin&page=1

print(merge_query_params("http://example.com?lang=zh", {"theme": "dark", "font": "large"}))
# http://example.com?lang=zh&theme=dark&font=large
```

**扩展挑战**：
- 支持重复键（用列表存多个值）：`?tag=python&tag=java&tag=go`
- 处理 URL 编码/解码（`%20` → 空格）
- 支持嵌套参数：`?user[name]=Alice&user[age]=25`

---

### 练习 3：缓存装饰器（Memoization）

用字典实现一个函数缓存装饰器：

```python
from functools import wraps
import time

def memoize(max_size: int = 128):
    """
    缓存装饰器：用字典缓存函数调用结果
    
    Args:
        max_size: 缓存最大条目数（超出时清除最旧的）
    """
    def decorator(func):
        cache = {}  # key: args_tuple, value: (result, timestamp)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 1. 构造缓存键（需要考虑位置参数和关键字参数）
            # 2. 如果键在缓存中，返回缓存结果
            # 3. 否则，调用函数，缓存结果
            # 4. 如果超出 max_size，淘汰最旧的条目
            pass
        
        # 附加方法
        wrapper.cache_info = lambda: {
            "size": len(cache),
            "max_size": max_size,
        }
        wrapper.cache_clear = lambda: cache.clear()
        
        return wrapper
    return decorator


# 测试：计算斐波那契数列（未优化版本很慢）
@memoize(max_size=256)
def fibonacci(n):
    """计算斐波那契数列第 n 项"""
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


# 测试速度
start = time.time()
result = fibonacci(100)
elapsed = time.time() - start
print(f"fibonacci(100) = {result}")
print(f"耗时: {elapsed:.4f}s")
print(f"缓存信息: {fibonacci.cache_info()}")

# 对比没有缓存的版本
def fib_slow(n):
    if n < 2:
        return n
    return fib_slow(n - 1) + fib_slow(n - 2)

start = time.time()
try:
    result_slow = fib_slow(40)
    elapsed_slow = time.time() - start
    print(f"\nfib_slow(40) = {result_slow}")
    print(f"无缓存耗时: {elapsed_slow:.4f}s")
except RecursionError:
    print("\nfib_slow(40) 太慢了...")
```

**提示**：Python 标准库已有 `functools.lru_cache`，但这里要求自己实现！

---

### 练习 4：标签云生成器

给定一组带权重的标签，生成 ASCII 标签云：

```python
from collections import Counter
import math

def generate_tag_cloud(tags: list, max_tags: int = 30) -> dict:
    """
    从标签列表生成词频字典
    
    Args:
        tags: ["python", "java", "python", "go", ...]
        max_tags: 最大标签数
    
    Returns:
        {"python": 5, "java": 3, "go": 2, ...}
    """
    pass

def render_tag_cloud(tag_freq: dict, max_font_size: int = 48, min_font_size: int = 12) -> str:
    """
    渲染 ASCII 标签云
    
    Args:
        tag_freq: 标签频次字典
        max_font_size: 最大字体大小（视觉上最大显示比例）
        min_font_size: 最小字体大小
    
    Returns:
        格式化的字符串，按频次排列
    """
    if not tag_freq:
        return ""
    
    # 计算归一化权重：频次越高，"字号"越大
    max_freq = max(tag_freq.values())
    min_freq = min(tag_freq.values())
    freq_range = max_freq - min_freq if max_freq > min_freq else 1
    
    lines = []
    lines.append("=" * 50)
    lines.append("  🏷️  TAG CLOUD")
    lines.append("=" * 50)
    
    # 按频次降序排列
    sorted_tags = sorted(tag_freq.items(), key=lambda x: -x[1])
    
    for tag, freq in sorted_tags:
        # 计算"字号"等级
        normalized = (freq - min_freq) / freq_range
        font_size = int(min_font_size + normalized * (max_font_size - min_font_size))
        
        # 生成条形（""数量代表"字号"）
        bar_len = max(1, int(normalized * 20))
        bar = "▓" * bar_len
        
        lines.append(f"  {tag:<15} {freq:<5} {bar} (size={font_size})")
    
    lines.append("=" * 50)
    return "\n".join(lines)


# 测试
sample_tags = [
    "python", "javascript", "python", "go", "rust", "java",
    "python", "typescript", "go", "python", "rust", "java",
    "javascript", "python", "go", "kotlin", "swift", "python",
    "java", "go", "rust", "python", "elixir", "scala",
    "python", "javascript", "go", "python",
] * 3  # 重复 3 次让数据更丰富

tag_cloud = generate_tag_cloud(sample_tags, max_tags=10)
print(render_tag_cloud(tag_cloud))
```

**预期输出示例**：
```
==================================================
  🏷️  TAG CLOUD
==================================================
  python          9  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ (size=48)
  go              6  ▓▓▓▓▓▓▓▓▓▓▓▓▓        (size=36)
  java            5  ▓▓▓▓▓▓▓▓▓▓▓▓▓        (size=36)
  javascript      4  ▓▓▓▓▓▓▓▓▓▓▓          (size=31)
  rust            4  ▓▓▓▓▓▓▓▓▓▓▓          (size=31)
  ...（数量会因重复次数不同而异）
==================================================
```

---

### 练习 5：嵌套 JSON 查询工具（进阶）

用字典实现一个简易的 JSON 数据查询语言：

```python
def json_query(data: dict, path: str):
    """
    使用点号路径语法查询嵌套 JSON 数据
    
    Args:
        data: 嵌套字典
        path: "users.0.name" 表示 data["users"][0]["name"]
              "settings.theme.color" 表示 data["settings"]["theme"]["color"]
    
    Returns:
        查询到的值，如果路径不存在返回 None
    """
    pass


# 测试数据
data = {
    "users": [
        {
            "name": "Alice",
            "age": 25,
            "address": {
                "city": "Beijing",
                "district": "Haidian"
            },
            "scores": [95, 87, 92]
        },
        {
            "name": "Bob",
            "age": 30,
            "address": {
                "city": "Shanghai",
                "district": "Pudong"
            },
            "scores": [78, 85, 90]
        }
    ],
    "settings": {
        "theme": {
            "color": "dark",
            "font_size": 14
        },
        "notifications": True
    },
    "metadata": {
        "version": "2.0",
        "last_updated": "2024-01-15"
    }
}

# 测试查询
print(json_query(data, "users.0.name"))             # Alice
print(json_query(data, "users.1.address.city"))     # Shanghai
print(json_query(data, "users.0.scores.2"))         # 92
print(json_query(data, "settings.theme.color"))     # dark
print(json_query(data, "settings.theme"))           # {"color": "dark", "font_size": 14}
print(json_query(data, "metadata.version"))         # 2.0
print(json_query(data, "users.2.name"))             # None（越界）
print(json_query(data, "nonexistent.path"))         # None
```

**扩展挑战**：
- 支持通配符：`users.*.name` 返回所有用户的名字列表
- 支持条件过滤：`users[?age>25].name`
- 支持 `..` 递归搜索语法

---

## 📖 参考链接

- [Python 官方文档 — dict](https://docs.python.org/3/library/stdtypes.html#mapping-types-dict)
- [Python 官方文档 — collections](https://docs.python.org/3/library/collections.html)
- [CPython dict 实现详解](https://github.com/python/cpython/blob/main/Objects/dictobject.c)
- [Python 3.6 紧凑字典实现](https://mail.python.org/pipermail/python-dev/2016-September/146327.html)
- [Brandon Rhodes: The Mighty Dictionary (PyCon)](https://www.youtube.com/watch?v=C4Kc8xzcA68)

---

## 💡 今日重点回顾

```
哈希表核心 → O(1) 查找的奥秘
    ↓
五种操作模式 → 增 / 删 / 查 / 改 / 合
    ↓
get vs setdefault → 安全读取 vs 惰性初始化
    ↓
字典推导式 → 一行代码构建复杂字典
    ↓
defaultdict → 规避 KeyError 的优雅方案
    ↓
Counter → 不仅会计数，还会做集合运算
    ↓
词频统计器 → 从文本到数据分析的完整管道
```
