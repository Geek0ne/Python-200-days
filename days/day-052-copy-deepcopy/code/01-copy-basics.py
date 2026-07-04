"""
Day 052 - 浅拷贝与深拷贝基础
主题：copy 模块核心 API
"""

import copy


# ============================================================
# 1. 赋值 vs 浅拷贝 vs 深拷贝
# ============================================================
print("=" * 60)
print("1. 赋值 vs 浅拷贝 vs 深拷贝")
print("=" * 60)

original = [1, 2, [3, 4]]

# 赋值：只是创建新引用
assigned = original
# 浅拷贝：创建新对象，内部元素引用共享
shallow = copy.copy(original)
# 深拷贝：创建新对象，内部元素递归拷贝
deep = copy.deepcopy(original)

print(f"original: {original}")
print(f"assigned: {assigned}")
print(f"shallow:  {shallow}")
print(f"deep:     {deep}")

# 验证对象身份
print(f"\n对象身份验证:")
print(f"original is assigned: {original is assigned}")  # True - 同一对象
print(f"original is shallow: {original is shallow}")    # False - 不同对象
print(f"original is deep:    {original is deep}")       # False - 不同对象


# ============================================================
# 2. 浅拷贝的行为
# ============================================================
print("\n" + "=" * 60)
print("2. 浅拷贝的行为")
print("=" * 60)

original = [1, 2, [3, 4]]
shallow = copy.copy(original)

# 修改外层元素
shallow[0] = 99
print(f"修改浅拷贝外层后:")
print(f"  original: {original}")   # [1, 2, [3, 4]] - 没变
print(f"  shallow:  {shallow}")    # [99, 2, [3, 4]] - 变了

# 修改嵌套对象
shallow[2].append(5)
print(f"\n修改浅拷贝嵌套对象后:")
print(f"  original: {original}")   # [1, 2, [3, 4, 5]] - 被改了！
print(f"  shallow:  {shallow}")    # [99, 2, [3, 4, 5]]


# ============================================================
# 3. 深拷贝的行为
# ============================================================
print("\n" + "=" * 60)
print("3. 深拷贝的行为")
print("=" * 60)

original = [1, 2, [3, 4]]
deep = copy.deepcopy(original)

# 修改深拷贝
deep[2].append(5)
print(f"修改深拷贝嵌套对象后:")
print(f"  original: {original}")   # [1, 2, [3, 4]] - 没变
print(f"  deep:     {deep}")       # [1, 2, [3, 4, 5]] - 变了

# 验证内部元素也不共享
print(f"\n内部元素验证:")
print(f"original[2] is deep[2]: {original[2] is deep[2]}")  # False


# ============================================================
# 4. 不同类型的浅拷贝方式
# ============================================================
print("\n" + "=" * 60)
print("4. 不同类型的浅拷贝方式")
print("=" * 60)

original = [1, 2, [3, 4]]

# 方式 1: copy.copy()
copy1 = copy.copy(original)

# 方式 2: 列表的 copy 方法
copy2 = original.copy()

# 方式 3: 切片
copy3 = original[:]

# 方式 4: 列表推导式
copy4 = [x for x in original]

# 方式 5: list() 构造函数
copy5 = list(original)

print("所有浅拷贝方式:")
print(f"  copy.copy():        {copy1}")
print(f"  .copy():            {copy2}")
print(f"  [:]:                {copy3}")
print(f"  [x for x in ...]:   {copy4}")
print(f"  list():             {copy5}")

# 验证都是浅拷贝
print(f"\n验证嵌套对象共享:")
copy1[2].append(99)
print(f"  修改 copy1 嵌套后:")
print(f"  copy2 嵌套: {copy2[2]}")  # [3, 4, 99] - 被改了
print(f"  copy3 嵌套: {copy3[2]}")  # [3, 4, 99] - 被改了


# ============================================================
# 5. 不可变对象的拷贝行为
# ============================================================
print("\n" + "=" * 60)
print("5. 不可变对象的拷贝行为")
print("=" * 60)

# 整数
a = 42
b = copy.copy(a)
c = copy.deepcopy(a)
print(f"整数: a is b = {a is b}, a is c = {a is c}")  # True, True

# 字符串
s1 = "hello"
s2 = copy.copy(s1)
print(f"字符串: s1 is s2 = {s1 is s2}")  # True

# 元组（简单）
t1 = (1, 2, 3)
t2 = copy.copy(t1)
print(f"简单元组: t1 is t2 = {t1 is t2}")  # True

# 元组（包含可变元素）
t3 = (1, 2, [3, 4])
t4 = copy.copy(t3)
t4[2].append(5)
print(f"\n包含可变元素的元组:")
print(f"  t3: {t3}")  # (1, 2, [3, 4, 5]) - 被改了！
print(f"  t4: {t4}")
print(f"  t3 is t4: {t3 is t4}")  # True - 元组本身没变
print(f"  t3[2] is t4[2]: {t3[2] is t4[2]}")  # True - 列表被共享了


# ============================================================
# 6. 字典的拷贝
# ============================================================
print("\n" + "=" * 60)
print("6. 字典的拷贝")
print("=" * 60)

original = {"a": [1, 2], "b": {"c": 3}}
shallow = copy.copy(original)
deep = copy.deepcopy(original)

# 修改嵌套对象
shallow["a"].append(99)
print(f"浅拷贝后修改嵌套:")
print(f"  original['a']: {original['a']}")  # [1, 2, 99] - 被改了
print(f"  shallow['a']:  {shallow['a']}")

# 深拷贝不受影响
deep["a"].append(100)
print(f"\n深拷贝后修改嵌套:")
print(f"  original['a']: {original['a']}")  # [1, 2, 99] - 没变
print(f"  deep['a']:     {deep['a']}")      # [1, 2, 100]


# ============================================================
# 7. set 的拷贝
# ============================================================
print("\n" + "=" * 60)
print("7. set 的拷贝")
print("=" * 60)

original = {1, 2, 3}
shallow = copy.copy(original)
deep = copy.deepcopy(original)

print(f"original: {original}")
print(f"shallow:  {shallow}")
print(f"deep:     {deep}")

# frozenset
fs1 = frozenset([1, 2, 3])
fs2 = copy.copy(fs1)
print(f"\nfrozenset: fs1 is fs2 = {fs1 is fs2}")  # True - 不可变，不需要拷贝


# ============================================================
# 8. 循环引用的拷贝
# ============================================================
print("\n" + "=" * 60)
print("8. 循环引用的拷贝")
print("=" * 60)

# 创建循环引用
a = [1, 2]
a.append(a)  # a = [1, 2, [...]]
print(f"原始对象: {a}")
print(f"循环引用: a[2] is a = {a[2] is a}")

# 深拷贝可以正确处理循环引用
b = copy.deepcopy(a)
print(f"\n深拷贝:")
print(f"深拷贝: {b}")
print(f"循环保持: b[2] is b = {b[2] is b}")  # True
print(f"与原对象无关: b is a = {b is a}")     # False
