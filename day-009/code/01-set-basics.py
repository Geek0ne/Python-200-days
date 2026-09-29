"""
Day 009 — 集合基础用法与操作演示
学习目标：掌握集合的创建、基本操作和成员检查
可独立运行，直接 python3 01-set-basics.py
"""


# ============================================================
# 一、集合的创建
# ============================================================

print("=" * 60)
print("一、集合的创建")
print("=" * 60)

# 空集合（注意：{} 是空字典）
empty_set = set()
print(f"空集合: {empty_set}, 类型: {type(empty_set)}")

# 集合字面量
fruits = {"apple", "banana", "cherry", "apple"}  # 重复的 "apple" 会被去重
print(f"水果集合: {fruits}")

# 从列表创建（自动去重）
numbers = [1, 2, 2, 3, 3, 3, 4, 4, 4, 4]
unique_numbers = set(numbers)
print(f"去重前: {numbers}")
print(f"去重后: {unique_numbers}")

# 从字符串创建
chars = set("hello world")
print(f"字符串 'hello world' 的字符集合: {chars}")

# 从 range 创建
even_set = set(range(0, 20, 2))
print(f"0-18 的偶数集合: {even_set}")

# 集合推导式
squares = {x**2 for x in range(10)}
print(f"0-9 的平方集合: {squares}")


# ============================================================
# 二、核心操作：增删改
# ============================================================

print("\n" + "=" * 60)
print("二、集合核心操作")
print("=" * 60)

s = {1, 2, 3}
print(f"初始集合: {s}")

# add() — 添加元素
s.add(4)
print(f"add(4) 后: {s}")

s.add(1)  # 已存在，无效果
print(f"add(1) 再次: {s}")

# remove() — 删除元素（不存在则抛出 KeyError）
s.remove(4)
print(f"remove(4) 后: {s}")

# discard() — 删除元素（不存在则静默忽略 ✅ 推荐）
s.discard(3)
print(f"discard(3) 后: {s}")
s.discard(999)  # 不存在，不会报错
print(f"discard(999) 后: {s} （没有报错）")

# pop() — 删除并返回任意一个元素
s = {10, 20, 30}
popped = s.pop()
print(f"pop() 删除: {popped}, 剩余: {s}")

# clear() — 清空集合
s.clear()
print(f"clear() 后: {s}")


# ============================================================
# 三、成员检查（性能重点）
# ============================================================

print("\n" + "=" * 60)
print("三、成员检查 — O(1) vs O(n)")
print("=" * 60)

# 小规模演示
fruits = {"apple", "banana", "cherry", "date", "elderberry"}
print(f"水果集合: {fruits}")

# in 操作符 — O(1)
print(f"'banana' in fruits: {'banana' in fruits}")
print(f"'grape' in fruits: {'grape' in fruits}")

# not in 操作符
print(f"'grape' not in fruits: {'grape' not in fruits}")

# 性能对比演示（百万级数据）
import time

n = 1_000_000
test_list = list(range(n))
test_set = set(range(n))
target = -1  # 最坏情况：查找不在集合中的元素

# 列表查找
start = time.perf_counter()
result = target in test_list
list_time = time.perf_counter() - start

# 集合查找
start = time.perf_counter()
result = target in test_set
set_time = time.perf_counter() - start

print(f"\n百万级数据成员检查性能对比：")
print(f"  列表查找 (O(n)):   {list_time*1000:.3f} ms")
print(f"  集合查找 (O(1)):   {set_time*1000:.3f} ms")
print(f"  集合快约 {list_time/set_time:.0f} 倍")
print(f"  注意：数据量越大，差距越明显！")


# ============================================================
# 四、集合运算
# ============================================================

print("\n" + "=" * 60)
print("四、集合运算")
print("=" * 60)

a = {1, 2, 3, 4}
b = {3, 4, 5, 6}
print(f"A = {a}")
print(f"B = {b}")

# 并集
print(f"\nA | B (并集):    {a | b}")
print(f"A.union(B):     {a.union(b)}")

# 交集
print(f"\nA & B (交集):    {a & b}")
print(f"A.intersection(B): {a.intersection(b)}")

# 差集
print(f"\nA - B (差集):    {a - b}  (在 A 中但不在 B 中)")
print(f"A.difference(B): {a.difference(b)}")
print(f"B - A (差集):    {b - a}  (在 B 中但不在 A 中)")

# 对称差
print(f"\nA ^ B (对称差):    {a ^ b}")
print(f"A.symmetric_difference(B): {a.symmetric_difference(b)}")


# ============================================================
# 五、关系判断
# ============================================================

print("\n" + "=" * 60)
print("五、集合关系判断")
print("=" * 60)

a = {1, 2, 3}
b = {1, 2, 3, 4, 5}
c = {1, 2, 3}

print(f"A = {a}")
print(f"B = {b}")
print(f"C = {c}")

print(f"\nA <= B (子集): {a <= b}")
print(f"A < B (真子集): {a < b}")
print(f"A < C (真子集): {a < c}  (相等不是真子集)")
print(f"B >= A (超集): {b >= a}")
print(f"A.isdisjoint({10, 20}): {a.isdisjoint({10, 20})}")
print(f"A.isdisjoint(B): {a.isdisjoint(b)}")


# ============================================================
# 六、不可变方法与原地修改方法
# ============================================================

print("\n" + "=" * 60)
print("六、原地修改 vs 不可变操作")
print("=" * 60)

a = {1, 2, 3}
b = {3, 4, 5}
print(f"A = {a}")
print(f"B = {b}")

# 不可变版：返回新集合，原集合不变
result = a.union(b)
print(f"\na.union(b) = {result}")
print(f"a 没有被修改: {a}")

# 原地修改版：修改原集合
a.update(b)
print(f"\na.update(b) 后 a = {a}")

# 重新设置
a = {1, 2, 3}

# 使用运算符的原地版本
a |= b  # 等同于 a.update(b)
print(f"a |= b 后 a = {a}")


# ============================================================
# 七、集合的遍历
# ============================================================

print("\n" + "=" * 60)
print("七、集合遍历")
print("=" * 60)

colors = {"red", "green", "blue", "yellow", "purple"}
print(f"颜色集合: {colors}")

print("\n遍历元素（顺序不固定）:")
for color in colors:
    print(f"  {color}")

print("\n排序后遍历:")
for color in sorted(colors):
    print(f"  {color}")

print("\n带枚举遍历（临时顺序）:")
for idx, color in enumerate(colors):
    print(f"  {idx}: {color}")


# ============================================================
# 八、集合推导式
# ============================================================

print("\n" + "=" * 60)
print("八、集合推导式")
print("=" * 60)

# 基本用法
squares_set = {x**2 for x in range(10)}
print(f"0-9 平方集合: {squares_set}")

# 条件过滤
evens = {x for x in range(20) if x % 2 == 0}
print(f"0-19 偶数集合: {evens}")

# 字符串处理
text = "The quick brown fox jumps over the lazy dog"
unique_vowels = {c.lower() for c in text if c.lower() in "aeiou"}
print(f"文本中出现的元音字母: {sorted(unique_vowels)}")

# 嵌套推导
matrix = [[1, 2, 3], [2, 3, 4], [3, 4, 5]]
unique_values = {x for row in matrix for x in row}
print(f"矩阵中的不重复值: {sorted(unique_values)}")


# ============================================================
# 九、经典实战模式
# ============================================================

print("\n" + "=" * 60)
print("九、经典实战模式")
print("=" * 60)

# 模式 1：快速去重
print("\n▶ 快速去重:")
raw = [1, 2, 2, 3, 3, 3, 4]
deduped = list(set(raw))
print(f"原始: {raw}")
print(f"去重: {deduped} (注意顺序不保证)")

# 保持顺序去重
seen = set()
ordered_deduped = []
for x in raw:
    if x not in seen:
        seen.add(x)
        ordered_deduped.append(x)
print(f"去重（保持顺序）: {ordered_deduped}")

# 模式 2：数据对比
print("\n▶ 数据对比:")
old_users = {"Alice", "Bob", "Charlie", "David"}
new_users = {"Bob", "David", "Eve", "Frank"}
print(f"旧用户: {old_users}")
print(f"新用户: {new_users}")

added = new_users - old_users
removed = old_users - new_users
retained = old_users & new_users
print(f"新增: {added}")
print(f"移除: {removed}")
print(f"持续: {retained}")

# 模式 3：权限检查
print("\n▶ 权限检查:")
user_perms = {"read", "write"}
required = {"read", "write", "admin"}
print(f"用户权限: {user_perms}")
print(f"所需权限: {required}")
print(f"是否有全部权限: {required <= user_perms}")
print(f"缺少权限: {required - user_perms}")

# 模式 4：重复元素检测
print("\n▶ 重复元素检测:")
data = [10, 20, 30, 20, 40, 50, 30, 60]
seen_set = set()
duplicates = set()
for x in data:
    if x in seen_set:
        duplicates.add(x)
    else:
        seen_set.add(x)
print(f"数据: {data}")
print(f"重复元素: {duplicates}")


# ============================================================
# 十、frozenset 用法
# ============================================================

print("\n" + "=" * 60)
print("十、frozenset — 不可变集合")
print("=" * 60)

# 创建 frozenset
fs = frozenset([1, 2, 3, 3, 4])
print(f"frozenset: {fs}")
print(f"类型: {type(fs)}")

# 只读操作
print(f"\n只读操作:")
print(f"3 in fs: {3 in fs}")
print(f"len(fs): {len(fs)}")
print(f"fs | {5, 6}: {fs | {5, 6}}")
print(f"fs & {{2, 3}}: {fs & {2, 3}}")

# frozenset 作为字典键 — set 不能做的！
permission_map = {
    frozenset({"read"}): "只读访问",
    frozenset({"read", "write"}): "读写访问",
    frozenset({"read", "write", "execute"}): "完全访问",
}

# 注意：frozenset 无视顺序
test_key = frozenset({"write", "read"})
print(f"\n权限映射:")
print(f"  frozenset({{'write', 'read'}})) → '{permission_map[test_key]}'")

# frozenset 作为集合元素 — set 也不能做！
group_a = frozenset({"Alice", "Bob"})
group_b = frozenset({"Charlie", "David"})
group_c = frozenset({"Eve"})
groups = {group_a, group_b, group_c}
print(f"\n分组集合: {groups}")
print(f"frozenset({{'Bob', 'Alice'}}) in groups: {frozenset({'Bob', 'Alice'}) in groups}")


print("\n✅ 运行完成！Day 009 集合基础操作演示结束。")
