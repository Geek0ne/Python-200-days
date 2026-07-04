"""
Day 052 - 深拷贝进阶：自定义拷贝行为
主题：__copy__ / __deepcopy__ / memo 参数
"""

import copy
from datetime import datetime


# ============================================================
# 1. 自定义浅拷贝 (__copy__)
# ============================================================
print("=" * 60)
print("1. 自定义浅拷贝 (__copy__)")
print("=" * 60)

class Config:
    def __init__(self, name, settings, tags):
        self.name = name
        self.settings = settings
        self.tags = tags
        self.created_at = datetime.now()

    def __copy__(self):
        """自定义浅拷贝：共享 settings 和 tags"""
        print(f"  [__copy__] 拷贝 Config({self.name})")
        new_obj = Config(self.name, self.settings, self.tags)
        return new_obj

    def __repr__(self):
        return f"Config({self.name!r}, settings={self.settings!r})"


config = Config("prod", {"db": "localhost"}, ["important"])
copied = copy.copy(config)

print(f"原始: {config}")
print(f"拷贝: {copied}")
print(f"是同一个对象: {config is copied}")
print(f"settings 共享: {config.settings is copied.settings}")
print(f"tags 共享: {config.tags is copied.tags}")
print(f"created_at 不同: {config.created_at is not copied.created_at}")

# 修改共享对象
copied.settings["port"] = 5432
print(f"\n修改拷贝的 settings 后:")
print(f"  原始 settings: {config.settings}")  # 也被改了
print(f"  拷贝 settings: {copied.settings}")


# ============================================================
# 2. 自定义深拷贝 (__deepcopy__)
# ============================================================
print("\n" + "=" * 60)
print("2. 自定义深拷贝 (__deepcopy__)")
print("=" * 60)

class GameState:
    def __init__(self, player_name, score, inventory):
        self.player_name = player_name
        self.score = score
        self.inventory = inventory
        self.created_at = datetime.now()

    def __deepcopy__(self, memo):
        """自定义深拷贝：完全独立副本"""
        print(f"  [__deepcopy__] 深拷贝 GameState({self.player_name})")

        # 检查是否已经拷贝过（处理循环引用）
        if id(self) in memo:
            return memo[id(self)]

        # 创建新对象，递归深拷贝所有属性
        new_state = GameState(
            self.player_name,
            self.score,
            copy.deepcopy(self.inventory, memo)
        )
        # 记录到 memo 中
        memo[id(self)] = new_state
        return new_state

    def __repr__(self):
        return f"GameState({self.player_name!r}, score={self.score})"


# 测试
game = GameState("Alice", 1000, {"sword": 1, "potion": 5})
saved = copy.deepcopy(game)

print(f"原始: {game}")
print(f"深拷贝: {saved}")
print(f"是同一个对象: {game is saved}")

# 修改深拷贝
saved.score = 2000
saved.inventory["shield"] = 1
print(f"\n修改深拷贝后:")
print(f"  原始: {game}")      # 不变
print(f"  深拷贝: {saved}")   # 变了


# ============================================================
# 3. memo 参数的作用
# ============================================================
print("\n" + "=" * 60)
print("3. memo 参数的作用")
print("=" * 60)

class TreeNode:
    def __init__(self, value, children=None):
        self.value = value
        self.children = children or []

    def add_child(self, child):
        self.children.append(child)
        return self

    def __deepcopy__(self, memo):
        """使用 memo 处理循环引用和对象去重"""
        print(f"  深拷贝 TreeNode({self.value})")

        # 如果已经拷贝过，返回已拷贝的对象
        if id(self) in memo:
            return memo[id(self)]

        # 创建新节点
        new_node = TreeNode(self.value)

        # 记录到 memo（在递归之前，处理循环引用）
        memo[id(self)] = new_node

        # 递归拷贝子节点
        new_node.children = copy.deepcopy(self.children, memo)

        return new_node


# 创建树结构
root = TreeNode("root")
child1 = TreeNode("child1")
child2 = TreeNode("child2")
root.add_child(child1).add_child(child2)

# 创建循环引用
child2.add_child(root)

print("原始树:")
print(f"  root.value = {root.value}")
print(f"  root.children = {[c.value for c in root.children]}")
print(f"  child2.children[0] is root = {child2.children[0] is root}")

# 深拷贝
copy_root = copy.deepcopy(root)
print(f"\n深拷贝树:")
print(f"  copy_root.value = {copy_root.value}")
print(f"  copy_root.children = {[c.value for c in copy_root.children]}")

# 验证循环引用保持
copy_child2 = copy_root.children[1]
print(f"  copy_child2.children[0] is copy_root = {copy_child2.children[0] is copy_root}")
print(f"  copy_root is root = {copy_root is root}")


# ============================================================
# 4. 深拷贝去重
# ============================================================
print("\n" + "=" * 60)
print("4. 深拷贝去重（memo 的作用）")
print("=" * 60)

class SharedObject:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"SharedObject({self.name!r})"

# 创建共享引用
shared = SharedObject("shared")
container = [shared, shared, shared]  # 三个引用指向同一对象

print(f"原始容器:")
print(f"  container[0] is container[1]: {container[0] is container[1]}")
print(f"  container[0] is container[2]: {container[0] is container[2]}")

# 深拷贝
copy_container = copy.deepcopy(container)
print(f"\n深拷贝容器:")
print(f"  copy[0] is copy[1]: {copy_container[0] is copy_container[1]}")
print(f"  copy[0] is copy[2]: {copy_container[0] is copy_container[2]}")
print(f"  copy[0] is container[0]: {copy_container[0] is container[0]}")

# 修改一个
copy_container[0].name = "modified"
print(f"\n修改 copy[0] 后:")
print(f"  container[0]: {container[0]}")   # 不变
print(f"  copy[0]: {copy_container[0]}")   # 变了
print(f"  copy[1]: {copy_container[1]}")   # 也变了（共享）
print(f"  copy[2]: {copy_container[2]}")   # 也变了（共享）


# ============================================================
# 5. 性能对比
# ============================================================
print("\n" + "=" * 60)
print("5. 性能对比")
print("=" * 60)

import time

# 创建复杂嵌套对象
def create_complex_object(n):
    return {f"key_{i}": [j for j in range(100)] for i in range(n)}

data = create_complex_object(1000)

# 浅拷贝性能
start = time.perf_counter()
for _ in range(100):
    copy.copy(data)
shallow_time = time.perf_counter() - start

# 深拷贝性能
start = time.perf_counter()
for _ in range(100):
    copy.deepcopy(data)
deep_time = time.perf_counter() - start

print(f"对象大小: 1000 个键，每个键包含 100 个元素的列表")
print(f"浅拷贝 100 次: {shallow_time:.4f}s")
print(f"深拷贝 100 次: {deep_time:.4f}s")
print(f"深拷贝/浅拷贝 比率: {deep_time/shallow_time:.1f}x")


# ============================================================
# 6. 特殊对象的拷贝
# ============================================================
print("\n" + "=" * 60)
print("6. 特殊对象的拷贝")
print("=" * 60)

import sys

# 不支持拷贝的对象
unsupported = [
    lambda x: x,
    sys.stdout,
    type,
]

for obj in unsupported:
    try:
        copy.copy(obj)
        print(f"✅ {type(obj).__name__}: 支持浅拷贝")
    except TypeError as e:
        print(f"❌ {type(obj).__name__}: {e}")

# 文件对象
import io
f = io.StringIO("hello")
try:
    copy.copy(f)
    print(f"\n✅ StringIO: 支持浅拷贝")
except TypeError as e:
    print(f"\n❌ StringIO: {e}")
