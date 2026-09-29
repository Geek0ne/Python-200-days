#!/usr/bin/env python3
"""
Day 090 - 碰撞检测与动画: 基础碰撞检测
演示 AABB、圆形、混合碰撞检测
"""

import math
import time


# ═══════════════════════════════════════════════
# 1. AABB 碰撞检测（轴对齐包围盒）
# ═══════════════════════════════════════════════

class Rect:
    """简易矩形类"""
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
    
    @property
    def left(self):
        return self.x
    
    @property
    def right(self):
        return self.x + self.w
    
    @property
    def top(self):
        return self.y
    
    @property
    def bottom(self):
        return self.y + self.h
    
    @property
    def center_x(self):
        return self.x + self.w / 2
    
    @property
    def center_y(self):
        return self.y + self.h / 2


def aabb_collision(rect_a, rect_b):
    """
    AABB 碰撞检测
    
    原理: 两个矩形不碰撞的条件是：
    - A 在 B 左边 (A.right < B.left)
    - A 在 B 右边 (A.left > B.right)
    - A 在 B 上边 (A.bottom < B.top)
    - A 在 B 下边 (A.top > B.bottom)
    
    取反就是"碰撞"的条件
    """
    return (
        rect_a.left < rect_b.right and
        rect_a.right > rect_b.left and
        rect_a.top < rect_b.bottom and
        rect_a.bottom > rect_b.top
    )


# ═══════════════════════════════════════════════
# 2. 圆形碰撞检测
# ═══════════════════════════════════════════════

class Circle:
    """简易圆形类"""
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius


def circle_collision(circle_a, circle_b):
    """
    圆形碰撞检测
    
    原理: 两个圆心距离 <= 两半径之和 就碰撞
    """
    distance = math.sqrt(
        (circle_a.x - circle_b.x) ** 2 +
        (circle_a.y - circle_b.y) ** 2
    )
    return distance <= (circle_a.radius + circle_b.radius)


def circle_collision_fast(circle_a, circle_b):
    """
    优化版: 避免 sqrt，用距离平方比较
    """
    dx = circle_a.x - circle_b.x
    dy = circle_a.y - circle_b.y
    distance_sq = dx * dx + dy * dy
    radius_sum = circle_a.radius + circle_b.radius
    return distance_sq <= radius_sum * radius_sum


# ═══════════════════════════════════════════════
# 3. 混合碰撞检测
# ═══════════════════════════════════════════════

def rect_circle_collision(rect, circle):
    """
    矩形与圆形的碰撞检测
    
    原理: 找到矩形上离圆心最近的点，
    然后检查该点到圆心的距离是否小于半径
    """
    # 找到矩形上离圆心最近的点
    closest_x = max(rect.left, min(circle.x, rect.right))
    closest_y = max(rect.top, min(circle.y, rect.bottom))
    
    # 计算最近点到圆心的距离
    dx = circle.x - closest_x
    dy = circle.y - closest_y
    distance_sq = dx * dx + dy * dy
    
    return distance_sq <= circle.radius * circle.radius


# ═══════════════════════════════════════════════
# 4. 碰撞响应: 反射
# ═══════════════════════════════════════════════

def reflect(velocity, normal):
    """
    计算反射速度
    
    公式: v' = v - 2(v·n)n
    其中 n 是碰撞面的法线
    """
    dot = velocity[0] * normal[0] + velocity[1] * normal[1]
    return (
        velocity[0] - 2 * dot * normal[0],
        velocity[1] - 2 * dot * normal[1]
    )


# ═══════════════════════════════════════════════
# 5. 性能对比: 逐一检测 vs 空间分区
# ═══════════════════════════════════════════════

def brute_force_collision(objects):
    """暴力检测: O(n²)"""
    collisions = []
    for i in range(len(objects)):
        for j in range(i + 1, len(objects)):
            if aabb_collision(objects[i], objects[j]):
                collisions.append((i, j))
    return collisions


# ═══════════════════════════════════════════════
# 主函数: 演示所有碰撞检测方法
# ═══════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Day 090 — 碰撞检测基础演示")
    print("=" * 60)
    
    # --- AABB 碰撞检测 ---
    print("\n【1. AABB 碰撞检测】")
    print("-" * 40)
    
    r1 = Rect(10, 10, 50, 50)   # (10,10) 到 (60,60)
    r2 = Rect(40, 40, 50, 50)   # (40,40) 到 (90,90)
    r3 = Rect(100, 100, 50, 50) # (100,100) 到 (150,150)
    
    print(f"  矩形 A: ({r1.x},{r1.y}) 大小 {r1.w}x{r1.h}")
    print(f"  矩形 B: ({r2.x},{r2.y}) 大小 {r2.w}x{r2.h}")
    print(f"  矩形 C: ({r3.x},{r3.y}) 大小 {r3.w}x{r3.h}")
    print()
    print(f"  A vs B: {aabb_collision(r1, r2)}  ← 重叠区域")
    print(f"  A vs C: {aabb_collision(r1, r3)}  ← 远离")
    print(f"  B vs C: {aabb_collision(r2, r3)}  ← 远离")
    
    # --- 圆形碰撞检测 ---
    print("\n【2. 圆形碰撞检测】")
    print("-" * 40)
    
    c1 = Circle(0, 0, 5)
    c2 = Circle(8, 0, 5)
    c3 = Circle(20, 0, 3)
    
    print(f"  圆 A: 圆心({c1.x},{c1.y}) 半径{c1.radius}")
    print(f"  圆 B: 圆心({c2.x},{c2.y}) 半径{c2.radius}")
    print(f"  圆 C: 圆心({c3.x},{c3.y}) 半径{c3.radius}")
    print()
    print(f"  A vs B: {circle_collision(c1, c2)}  ← 距离=8, 半径和=10")
    print(f"  A vs C: {circle_collision(c1, c3)}  ← 距离=20, 半径和=8")
    print(f"  B vs C: {circle_collision(c2, c3)}  ← 距离=12, 半径和=8")
    
    # 优化版对比
    print(f"\n  优化版 A vs B: {circle_collision_fast(c1, c2)}")
    
    # --- 矩形-圆形碰撞 ---
    print("\n【3. 矩形-圆形碰撞检测】")
    print("-" * 40)
    
    rect = Rect(30, 30, 40, 40)  # (30,30) 到 (70,70)
    circ = Circle(75, 50, 10)    # 圆心(75,50) 半径10
    
    print(f"  矩形: ({rect.x},{rect.y}) 大小 {rect.w}x{rect.h}")
    print(f"  圆形: 圆心({circ.x},{circ.y}) 半径{circ.radius}")
    print(f"  结果: {rect_circle_collision(rect, circ)}")
    
    # --- 反射碰撞 ---
    print("\n【4. 反射碰撞响应】")
    print("-" * 40)
    
    velocity = (10, -5)     # 向右下移动
    normal = (0, 1)         # 碰到水平面（向下法线）
    reflected = reflect(velocity, normal)
    
    print(f"  原始速度: {velocity}")
    print(f"  碰撞面法线: {normal}")
    print(f"  反射速度: {reflected}")
    print(f"  解释: 水平速度不变, 垂直速度反转")
    
    # --- 性能对比 ---
    print("\n【5. 碰撞检测性能对比】")
    print("-" * 40)
    
    import random
    random.seed(42)
    
    # 生成随机矩形
    for n in [100, 500, 1000]:
        objects = [
            Rect(random.randint(0, 1000), random.randint(0, 1000),
                 random.randint(10, 50), random.randint(10, 50))
            for _ in range(n)
        ]
        
        start = time.time()
        collisions = brute_force_collision(objects)
        elapsed = time.time() - start
        
        print(f"  {n:>5} 个物体: {len(collisions):>5} 次碰撞, "
              f"耗时 {elapsed*1000:.2f}ms")
    
    print("\n✅ 碰撞检测基础演示完成!")


if __name__ == "__main__":
    main()
