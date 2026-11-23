"""
Day 035 — 特殊方法：实战案例
===============================

实战：完整的多维向量类 —— 展示所有魔术方法的协同工作

支持功能：
- 任意维度向量
- 加法、减法、标量乘法
- 点积、叉积（3D）
- 归一化、模长
- 索引访问、迭代、切片
- 字符串表示、相等性
- 可哈希（作为字典键）
"""

import math
import functools
from typing import List, Union, Iterator, Tuple

Number = Union[int, float]


# ====================================
# Vector 类 — 完整的魔术方法实现
# ====================================

@functools.total_ordering
class Vector:
    """
    多维向量类

    特性：
    - 支持任意维度
    - 完整的运算符重载
    - 可哈希（可用作字典键）
    - 支持比较（按模长）
    - 支持索引和迭代
    """

    def __init__(self, *components: Number):
        """创建向量，例如 Vector(3, 4) 或 Vector(1, 2, 3)"""
        self._data = [float(c) for c in components]

    # ── 工厂方法 ──

    @classmethod
    def zeros(cls, dim: int) -> 'Vector':
        """创建零向量"""
        return cls(*([0.0] * dim))

    @classmethod
    def ones(cls, dim: int) -> 'Vector':
        """创建全 1 向量"""
        return cls(*([1.0] * dim))

    @classmethod
    def from_list(cls, data: List[Number]) -> 'Vector':
        """从列表创建向量"""
        return cls(*data)

    # ═══════════════════════════════════════
    # 属性协议
    # ═══════════════════════════════════════

    @property
    def dim(self) -> int:
        """向量维度"""
        return len(self._data)

    def __getitem__(self, index):
        """v[i] — 索引访问，支持切片"""
        if isinstance(index, slice):
            return Vector(*self._data[index])
        return self._data[index]

    def __setitem__(self, index, value):
        """v[i] = x — 索引赋值"""
        self._data[index] = float(value)

    def __len__(self) -> int:
        """len(v) — 返回维度"""
        return self.dim

    def __iter__(self) -> Iterator[float]:
        """for x in v — 迭代分量"""
        return iter(self._data)

    def __contains__(self, item) -> bool:
        """x in v — 成员检查"""
        return item in self._data

    # ═══════════════════════════════════════
    # 字符串表示
    # ═══════════════════════════════════════

    def __repr__(self) -> str:
        """repr(v) — 开发者表示"""
        components = ", ".join(f"{c:.2f}" for c in self._data)
        return f"Vector({components})"

    def __str__(self) -> str:
        """str(v) / print(v) — 用户友好表示"""
        parts = ", ".join(f"{c:.2f}" for c in self._data)
        return f"[{parts}]"

    # ═══════════════════════════════════════
    # 比较协议
    # ═══════════════════════════════════════

    def __eq__(self, other) -> bool:
        """v1 == v2 — 相等比较"""
        if not isinstance(other, Vector):
            return NotImplemented
        return self._data == other._data

    def __lt__(self, other) -> bool:
        """v1 < v2 — 按模长排序"""
        if not isinstance(other, Vector):
            return NotImplemented
        return abs(self) < abs(other)

    def __hash__(self) -> int:
        """hash(v) — 支持作为字典键"""
        return hash(tuple(self._data))

    # ═══════════════════════════════════════
    # 一元运算
    # ═══════════════════════════════════════

    def __neg__(self) -> 'Vector':
        """-v — 取反"""
        return Vector(*[-c for c in self._data])

    def __pos__(self) -> 'Vector':
        """+v — 正值"""
        return Vector(*self._data)

    def __abs__(self) -> float:
        """abs(v) — 模长（L2 范数）"""
        return math.sqrt(sum(c ** 2 for c in self._data))

    def __bool__(self) -> bool:
        """bool(v) — 零向量为 False"""
        return any(c != 0 for c in self._data)

    # ═══════════════════════════════════════
    # 算术运算
    # ═══════════════════════════════════════

    def __add__(self, other) -> 'Vector':
        """v1 + v2 — 向量加法"""
        if isinstance(other, Vector):
            self._check_dim(other)
            return Vector(*[a + b for a, b in zip(self._data, other._data)])
        return NotImplemented

    def __sub__(self, other) -> 'Vector':
        """v1 - v2 — 向量减法"""
        if isinstance(other, Vector):
            self._check_dim(other)
            return Vector(*[a - b for a, b in zip(self._data, other._data)])
        return NotImplemented

    def __mul__(self, other):
        """
        v * s — 标量乘法
        v1 * v2 — 点积
        """
        if isinstance(other, (int, float)):
            return Vector(*[c * other for c in self._data])
        if isinstance(other, Vector):
            self._check_dim(other)
            return sum(a * b for a, b in zip(self._data, other._data))
        return NotImplemented

    def __rmul__(self, other):
        """s * v — 反向标量乘法"""
        return self.__mul__(other)

    def __truediv__(self, scalar: Number) -> 'Vector':
        """v / s — 标量除法"""
        if isinstance(scalar, (int, float)):
            if scalar == 0:
                raise ZeroDivisionError("向量除法：不能除以零")
            return Vector(*[c / scalar for c in self._data])
        return NotImplemented

    def __floordiv__(self, scalar: Number) -> 'Vector':
        """v // s — 标量整除"""
        if isinstance(scalar, (int, float)):
            if scalar == 0:
                raise ZeroDivisionError("向量除法：不能除以零")
            return Vector(*[c // scalar for c in self._data])
        return NotImplemented

    # ═══════════════════════════════════════
    # 原地运算
    # ═══════════════════════════════════════

    def __iadd__(self, other) -> 'Vector':
        """v1 += v2 — 原地加法"""
        if isinstance(other, Vector):
            self._check_dim(other)
            for i in range(self.dim):
                self._data[i] += other._data[i]
            return self
        return NotImplemented

    def __isub__(self, other) -> 'Vector':
        """v1 -= v2 — 原地减法"""
        if isinstance(other, Vector):
            self._check_dim(other)
            for i in range(self.dim):
                self._data[i] -= other._data[i]
            return self
        return NotImplemented

    def __imul__(self, scalar: Number) -> 'Vector':
        """v *= s — 原地标量乘法"""
        if isinstance(scalar, (int, float)):
            self._data = [c * scalar for c in self._data]
            return self
        return NotImplemented

    # ═══════════════════════════════════════
    # 类型转换
    # ═══════════════════════════════════════

    def __list__(self) -> List[float]:
        """list(v) — 转换为列表"""
        return list(self._data)

    def __tuple__(self) -> Tuple[float, ...]:
        """tuple(v) — 转换为元组"""
        return tuple(self._data)

    # ═══════════════════════════════════════
    # 可调用
    # ═══════════════════════════════════════

    def __call__(self, index: int) -> float:
        """v(i) — 通过函数式调用访问分量"""
        return self._data[index]

    # ═══════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════

    def _check_dim(self, other: 'Vector') -> None:
        """检查维度是否匹配"""
        if self.dim != other.dim:
            raise ValueError(
                f"向量维度不匹配: {self.dim} vs {other.dim}"
            )

    def normalize(self) -> 'Vector':
        """归一化 — 返回单位向量"""
        magnitude = abs(self)
        if magnitude == 0:
            raise ValueError("零向量无法归一化")
        return self / magnitude

    def dot(self, other: 'Vector') -> float:
        """点积（内积）"""
        return self * other

    def cross(self, other: 'Vector') -> 'Vector':
        """叉积（仅 3D 向量）"""
        if self.dim != 3 or other.dim != 3:
            raise ValueError("叉积仅支持 3 维向量")
        x1, y1, z1 = self._data
        x2, y2, z2 = other._data
        return Vector(
            y1 * z2 - z1 * y2,
            z1 * x2 - x1 * z2,
            x1 * y2 - y1 * x2
        )

    def angle(self, other: 'Vector') -> float:
        """与另一个向量的夹角（弧度）"""
        cos_theta = self.dot(other) / (abs(self) * abs(other))
        cos_theta = max(-1.0, min(1.0, cos_theta))  # 钳制数值误差
        return math.acos(cos_theta)

    def project(self, other: 'Vector') -> 'Vector':
        """向量 self 在 other 上的投影"""
        other_norm = other.normalize()
        return other_norm * self.dot(other_norm)

    def distance(self, other: 'Vector') -> float:
        """到另一个向量的欧氏距离"""
        return abs(self - other)

    def is_zero(self, tolerance: float = 1e-10) -> bool:
        """是否为零向量"""
        return abs(self) < tolerance

    def is_parallel(self, other: 'Vector', tolerance: float = 1e-10) -> bool:
        """是否平行"""
        return abs(self.cross(other)) < tolerance if self.dim == 3 else False

    def is_orthogonal(self, other: 'Vector', tolerance: float = 1e-10) -> bool:
        """是否垂直"""
        return abs(self.dot(other)) < tolerance


# ====================================
# 演示
# ====================================

def demo():
    print("=" * 60)
    print("🎯 多维向量类 — 完整演示")
    print("=" * 60)

    # 创建向量
    v1 = Vector(3, 4)
    v2 = Vector(1, 2)
    v3 = Vector(1, 0, 0)
    v4 = Vector(0, 1, 0)

    print(f"\n📦 向量创建:")
    print(f"  v1 = {v1}")
    print(f"  v2 = {v2}")
    print(f"  v3 = {v3}")
    print(f"  Vector.zeros(3) = {Vector.zeros(3)}")
    print(f"  Vector.ones(4) = {Vector.ones(4)}")

    # 字符串表示
    print(f"\n📝 字符串表示:")
    print(f"  str(v1) = {str(v1)}")
    print(f"  repr(v1) = {repr(v1)}")

    # 属性
    print(f"\n📐 属性访问:")
    print(f"  v1.dim = {v1.dim}")
    print(f"  v1[0] = {v1[0]}, v1[1] = {v1[1]}")
    print(f"  list(v1) = {list(v1)}")

    v1[0] = 6
    print(f"  修改后 v1[0] = 6 → {v1}")
    v1 = Vector(3, 4)  # 恢复

    # 迭代
    print(f"\n🔄 迭代:")
    print("  v2 分量: ", end="")
    for c in v2:
        print(c, end=" ")
    print()

    # 算术运算
    print(f"\n🧮 算术运算:")
    print(f"  v1 + v2 = {v1 + v2}")
    print(f"  v1 - v2 = {v1 - v2}")
    print(f"  v1 * 2  = {v1 * 2}")
    print(f"  3 * v1  = {3 * v1}")
    print(f"  v1 / 2  = {v1 / 2}")
    print(f"  -v1     = {-v1}")

    # 点积
    dot_product = v1 * v2  # 3*1 + 4*2 = 11
    print(f"\n🎯 点积: v1 · v2 = {dot_product}")

    # 叉积 (3D)
    cross = v3.cross(v4)
    print(f"\n🎯 叉积: {v3} × {v4} = {cross}")

    # 模长和归一化
    print(f"\n📏 模长和归一化:")
    print(f"  |v1| = {abs(v1):.3f}")
    print(f"  v1.normalize() = {v1.normalize()}")
    print(f"  |v1.normalize()| = {abs(v1.normalize()):.10f}")

    # 角度
    print(f"\n📐 角度:")
    angle = v1.angle(v2)
    print(f"  v1 与 v2 夹角: {angle:.4f} rad = {math.degrees(angle):.2f}°")
    print(f"  v3 与 v4 夹角: {math.degrees(v3.angle(v4)):.1f}°")

    # 投影和距离
    print(f"\n🔮 投影和距离:")
    print(f"  v1 在 v2 上的投影: {v1.project(v2)}")
    print(f"  v1 到 v2 的距离: {v1.distance(v2):.3f}")

    # 垂直和平行检查
    print(f"\n🔍 关系检查:")
    print(f"  v3 ⊥ v4: {v3.is_orthogonal(v4)}")
    print(f"  v3 ∥ 2*v3: {v3.is_parallel(Vector(2, 0, 0))}")
    print(f"  v1 ⊥ Vector(-4, 3): {v1.is_orthogonal(Vector(-4, 3))}")

    # 比较
    print(f"\n⚖️ 比较运算:")
    print(f"  v1 == Vector(3, 4): {v1 == Vector(3, 4)}")
    print(f"  v1 < v2: {v1 < v2}")  # |v1|=5, |v2|≈2.236
    print(f"  v1 > v2: {v1 > v2}")

    # 哈希（作为字典键）
    print(f"\n🔑 哈希支持:")
    v_map = {
        Vector(1, 0): "x 轴单位向量",
        Vector(0, 1): "y 轴单位向量",
        Vector(0, 0, 1): "z 轴单位向量 (3D)",
    }
    print(f"  Vector(1,0) → {v_map[Vector(1, 0)]}")

    # 布尔值
    print(f"\n✅ 布尔值:")
    print(f"  bool(v1): {bool(v1)}")
    print(f"  bool(Vector(0, 0)): {bool(Vector(0, 0))}")

    # 原地运算
    print(f"\n🔄 原地运算:")
    v_copy = Vector(1, 2)
    v_copy += Vector(3, 4)
    print(f"  v += Vector(3,4) → {v_copy}")
    v_copy *= 2
    print(f"  v *= 2 → {v_copy}")

    # 数学运算
    print(f"\n🧪 数学运算:")
    v5 = Vector(2, 3, 4)
    print(f"  v5 = {v5}")
    print(f"  v5.is_zero() = {v5.is_zero()}")
    print(f"  v5.distance(Vector.ones(3)) = {v5.distance(Vector.ones(3)):.3f}")

    print("\n" + "=" * 60)
    print("✅ 向量类演示完成")
    print(f"   总共实现 {len(dir(Vector))} 个方法")
    print("=" * 60)


if __name__ == "__main__":
    demo()
