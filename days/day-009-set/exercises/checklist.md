# Day 009 — 集合（Set）完成清单与练习题

## ✅ 今日完成清单

- [ ] 理解集合的数学基础：并集、交集、差集、对称差
- [ ] 掌握集合的创建方式：`set()`、`{}`、`set comprehension`、`set(iterable)`
- [ ] 熟练使用核心方法：`add()`、`remove()`、`discard()`、`pop()`、`clear()`、`update()`
- [ ] 掌握集合运算运算符：`|`、`&`、`-`、`^`、`<=`、`>=`、`<`、`>`
- [ ] 掌握集合运算方法：`union()`、`intersection()`、`difference()`、`symmetric_difference()`
- [ ] 理解集合推导式及其 vs 列表推导式的差异
- [ ] 掌握集合的不可变方法与原地修改方法的区别
- [ ] 理解 `frozenset` 的用途：字典键、集合元素
- [ ] 理解集合 vs 列表的性能差异（O(1) vs O(n)）
- [ ] 理解集合的可哈希约束
- [ ] 完成实战：数据清洗管道

---

## 📝 练习题

### 练习 1：重复元素检测器

编写一个函数 `find_duplicates(lst)`，接受一个列表，返回其中的所有重复元素（保持原列表中第一次出现的顺序）。

```python
def find_duplicates(lst):
    """返回列表中的重复元素（按第一次出现的顺序）"""
    # 你的代码在这里
    pass

# 测试
print(find_duplicates([1, 2, 3, 2, 4, 3, 5, 1]))
# 期望输出: [2, 3, 1]
```

**要求：**
- 使用集合实现 O(n) 复杂度
- 返回的重复元素按照原列表中第一次出现的顺序排列

---

### 练习 2：用户权限验证系统

实现一个权限验证系统，支持以下功能：

```python
def check_permissions(user_permissions, required_permissions):
    """
    检查用户是否有执行操作所需的全部权限。
    
    参数：
        user_permissions: set — 用户拥有的权限集合
        required_permissions: set — 操作所需的权限集合
    
    返回：
        (has_all: bool, missing: set) — 是否有所有权限，以及缺少的权限集合
    """
    # 你的代码在这里
    pass

# 测试
user = {"read", "write", "delete"}
req1 = {"read", "write"}
req2 = {"read", "admin"}
req3 = {"read", "write", "delete", "admin"}

print(check_permissions(user, req1))  # (True, set())
print(check_permissions(user, req2))  # (False, {'admin'})
print(check_permissions(user, req3))  # (False, {'admin'})
```

**要求：**
- 使用集合运算实现
- 时间复杂度 O(len(required)) 以内

---

### 练习 3：日志分析器

给定两个日志文件的时间戳集合，找出：

1. 两个日志中都出现的时间戳（交集）
2. 只在日志 A 中出现的时间戳（差集）
3. 两个日志中所有不重复的时间戳（并集）
4. 只在一个日志中出现的时间戳（对称差）

```python
def analyze_logs(log_a, log_b):
    """
    分析两个日志文件的时间戳。
    
    参数：
        log_a: set — 日志 A 的时间戳
        log_b: set — 日志 B 的时间戳
    
    返回：
        dict — 包含交集、差集A-B、差集B-A、并集、对称差
    """
    # 你的代码在这里
    pass

# 测试
log_a = {1001, 1002, 1003, 1004, 1005}
log_b = {1003, 1004, 1005, 1006, 1007}

result = analyze_logs(log_a, log_b)
for key, value in result.items():
    print(f"{key}: {sorted(value)}")
```

**期望输出：**
```
intersection: [1003, 1004, 1005]
a_only: [1001, 1002]
b_only: [1006, 1007]
union: [1001, 1002, 1003, 1004, 1005, 1006, 1007]
symmetric_diff: [1001, 1002, 1006, 1007]
```

---

### 练习 4：标签推荐系统

给定一个用户已有的标签集合，以及所有可用的标签集合，推荐用户尚未添加的相关标签：

```python
def recommend_tags(user_tags, all_tags, related_tags):
    """
    为用户推荐标签。
    
    参数：
        user_tags: set — 用户已有的标签
        all_tags: set — 所有可用标签
        related_tags: dict — 标签相关性映射
            {"已有标签": {"推荐标签1", "推荐标签2", ...}}
    
    返回：
        set — 推荐的标签集合（用户还没有的）
    """
    # 你的代码在这里
    pass

# 测试
user_has = {"python", "data-science"}
all_tags = {"python", "data-science", "machine-learning", "deep-learning",
            "web-dev", "devops", "database", "api"}
related = {
    "python": {"web-dev", "api", "automation"},
    "data-science": {"machine-learning", "deep-learning", "statistics"},
}

recommended = recommend_tags(user_has, all_tags, related)
print(f"推荐标签: {recommended}")
# 应该推荐: {'web-dev', 'api', 'automation', 'machine-learning', 'deep-learning'}
# 注意: 'statistics' 不在 all_tags 中，所以不应该推荐
```

**要求：**
- 使用集合运算实现
- 推荐的标签必须存在于 `all_tags` 中
- 推荐的标签不能是用户已有的标签

---

### 练习 5：数据完整性校验

给定一个数据字典列表和一个必填字段集合，实现数据完整性校验函数：

```python
def validate_data_integrity(records, required_fields):
    """
    校验数据完整性。
    
    参数：
        records: list[dict] — 数据记录列表
        required_fields: set — 必填字段集合
    
    返回：
        dict — {
            "valid": int,           # 有效记录数
            "invalid": int,         # 无效记录数
            "missing_fields": dict, # 字段缺失统计 {字段名: 缺失次数}
            "invalid_ids": list,    # 无效记录的 ID 列表
        }
    """
    # 你的代码在这里
    pass

# 测试
data = [
    {"id": 1, "name": "Alice", "email": "alice@test.com"},
    {"id": 2, "name": "Bob"},  # 缺少 email
    {"id": 3, "name": "", "email": ""},  # name 和 email 为空
    {"id": 4, "email": "david@test.com"},  # 缺少 name
    {"id": 5, "name": "Eve", "email": "eve@test.com"},
]

result = validate_data_integrity(data, {"name", "email"})
print(f"有效: {result['valid']}, 无效: {result['invalid']}")
print(f"缺失字段统计: {result['missing_fields']}")
print(f"无效记录 ID: {result['invalid_ids']}")
```

**期望输出：**
```
有效: 2, 无效: 3
缺失字段统计: {'email': 1, 'name': 2}
无效记录 ID: [2, 3, 4]
```

---

### 挑战题（选做）：朋友圈共同好友

给定一个好友关系图（字典，键为人名，值为其好友集合），找出两个人之间的**共同好友**和**你可能认识的人**（好友的好友中不是你直接好友的人）。

```python
def mutual_friends(friends_graph, person_a, person_b):
    """
    找出两个人的共同好友。
    
    参数：
        friends_graph: dict — {人名: 好友集合}
        person_a: str
        person_b: str
    
    返回：
        set — 共同好友集合
    """
    # 你的代码在这里
    pass

def people_you_may_know(friends_graph, person, max_depth=2):
    """
    找出你可能认识的人（好友的好友，但不包含直接好友）。
    
    参数：
        friends_graph: dict
        person: str
        max_depth: int
    
    返回：
        set — 推荐好友集合
    """
    # 你的代码在这里
    pass

# 测试
friends = {
    "Alice": {"Bob", "Charlie", "David"},
    "Bob": {"Alice", "Charlie", "Eve"},
    "Charlie": {"Alice", "Bob", "David", "Frank"},
    "David": {"Alice", "Charlie"},
    "Eve": {"Bob", "Frank"},
    "Frank": {"Charlie", "Eve"},
}

print(f"Alice 和 Bob 的共同好友: {mutual_friends(friends, 'Alice', 'Bob')}")
# 期望: {'Charlie'}

print(f"Alice 可能认识的人: {people_you_may_know(friends, 'Alice')}")
# Alice 的朋友: Bob, Charlie, David
# Alice 朋友的朋友（排除 Alice 自己和她的直接好友）: Eve, Frank
```

---

## 💡 提示

- 练习 1 的关键是维护一个 `seen` 集合和一个结果列表
- 练习 2-3 主要是集合运算的直接应用
- 练习 4 需要组合集合推导式
- 练习 5 需要用集合运算比较记录字段和必填字段
- 挑战题是集合运算在社交网络中的实际应用
