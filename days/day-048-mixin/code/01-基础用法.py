"""
Day 048 - 混入(Mixin) - 基础用法
演示：Mixin 设计模式的基本概念和多重继承
"""
import json
from datetime import datetime


# ============================================
# 1. 基本 Mixin：序列化能力
# ============================================

class SerializationMixin:
    """
    序列化混入 —— 任何类添加此 Mixin 后，都能自动转为字典/JSON。

    设计要点：
    - 不依赖特定类的属性
    - 只访问 self.__dict__（所有实例属性）
    - 递归处理嵌套对象
    """

    def to_dict(self):
        """将对象转为字典，自动排除私有属性"""
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            # 递归处理嵌套的 Mixin 对象
            if hasattr(value, 'to_dict'):
                value = value.to_dict()
            # 处理列表中的 Mixin 对象
            elif isinstance(value, list):
                value = [
                    item.to_dict() if hasattr(item, 'to_dict') else item
                    for item in value
                ]
            # 处理 datetime
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[key] = value
        return result

    def to_json(self, indent=2):
        """将对象转为 JSON 字符串"""
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
            default=str  # 遇到无法序列化的类型时调用 str()
        )

    def load_from_dict(self, data):
        """从字典加载数据到对象"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


# ============================================
# 2. 基本 Mixin：比较能力
# ============================================

class ComparableMixin:
    """
    比较混入 —— 基于 __dict__ 自动实现比较操作。

    实现了 __eq__ 和 __lt__，通过 functools.total_ordering
    自动获得 __le__、__gt__、__ge__
    """
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return str(self) < str(other)


# ============================================
# 3. 应用 Mixin 到实际类
# ============================================

class User(SerializationMixin, ComparableMixin):
    """用户类 —— 组合序列化和比较能力"""

    def __init__(self, name, email, age):
        self.name = name
        self.email = email
        self.age = age
        self.created_at = datetime.now()
        self._internal_id = id(self)  # 私有属性，不会被序列化

    def __repr__(self):
        return f"User(name='{self.name}', email='{self.email}')"

    def __str__(self):
        return self.name


class Product(SerializationMixin, ComparableMixin):
    """产品类 —— 同样组合序列化和比较能力"""

    def __init__(self, name, price, stock=0):
        self.name = name
        self.price = price
        self.stock = stock

    def __repr__(self):
        return f"Product(name='{self.name}', price={self.price})"


# ============================================
# 4. 运行演示
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("Day 048 - 混入(Mixin) 基础用法")
    print("=" * 50)

    # 创建用户
    user1 = User("张三", "zhangsan@example.com", 28)
    user2 = User("李四", "lisi@example.com", 32)

    # 测试序列化 Mixin
    print("\n--- 序列化 Mixin ---")
    print("to_dict():", user1.to_dict())
    print("\nto_json():")
    print(user1.to_json())

    # 测试比较 Mixin
    print("\n--- 比较 Mixin ---")
    print(f"user1 == user2: {user1 == user2}")
    print(f"user1 != user2: {user1 != user2}")
    print(f"user1 < user2: {user1 < user2}")

    # 测试自动属性判断
    print("\n--- Mixin 自动识别 ---")
    print(f"User 是否是 SerializationMixin？ {isinstance(user1, SerializationMixin)}")
    print(f"User 是否是 ComparableMixin？ {isinstance(user1, ComparableMixin)}")

    # 产品类复用同样的 Mixin
    print("\n--- 混入复用演示 ---")
    product = Product("Python入门", 59.9, stock=100)
    print("产品字典:", product.to_dict())
    print("产品 JSON:")
    print(product.to_json())
