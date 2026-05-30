#!/usr/bin/env python3
"""
02-coordinate-system.py
Day 007 — 实战：坐标系统

构建一个完整的坐标系统，演示元组和 namedtuple 在真实场景中的应用：
- Point2D/Point3D 坐标类型（namedtuple）
- 距离计算、坐标变换
- 坐标数据库（元组作为字典键）
- 查找附近城市
- CSV 格式坐标数据解析

可直接运行：python3 02-coordinate-system.py
"""

import math
from collections import namedtuple
from typing import List, Tuple, Optional, NamedTuple


# ============================================================
# 一、定义坐标类型
# ============================================================

# 2D 坐标（使用 collections.namedtuple）
Point2D = namedtuple('Point2D', ['x', 'y'])


# 3D 坐标（使用 typing.NamedTuple 类语法 — 支持方法和类型注解）
class Point3D(NamedTuple):
    """3D 空间坐标点"""
    x: float
    y: float
    z: float

    def distance_to(self, other: 'Point3D') -> float:
        """计算到另一个 3D 点的距离"""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def __str__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"


# ============================================================
# 二、坐标计算引擎
# ============================================================

class GeometryEngine:
    """2D 几何计算引擎"""

    @staticmethod
    def distance(p1: Point2D, p2: Point2D) -> float:
        """欧几里得距离"""
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

    @staticmethod
    def midpoint(p1: Point2D, p2: Point2D) -> Point2D:
        """线段中点"""
        return Point2D((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)

    @staticmethod
    def translate(point: Point2D, dx: float, dy: float) -> Point2D:
        """平移"""
        return Point2D(point.x + dx, point.y + dy)

    @staticmethod
    def rotate(point: Point2D, angle_deg: float, origin: Point2D = Point2D(0, 0)) -> Point2D:
        """绕原点（或指定点）旋转"""
        # 将角度转为弧度
        rad = math.radians(angle_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        # 平移到原点坐标系
        dx = point.x - origin.x
        dy = point.y - origin.y

        # 旋转
        new_x = dx * cos_a - dy * sin_a + origin.x
        new_y = dx * sin_a + dy * cos_a + origin.y

        return Point2D(round(new_x, 6), round(new_y, 6))

    @staticmethod
    def polygon_area(points: List[Point2D]) -> float:
        """计算多边形面积（鞋带公式 Shoelace formula）"""
        n = len(points)
        if n < 3:
            return 0.0

        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i].x * points[j].y
            area -= points[j].x * points[i].y

        return abs(area) / 2.0

    @staticmethod
    def polygon_perimeter(points: List[Point2D]) -> float:
        """计算多边形周长"""
        n = len(points)
        if n < 2:
            return 0.0

        perimeter = 0.0
        for i in range(n):
            j = (i + 1) % n
            perimeter += GeometryEngine.distance(points[i], points[j])
        return perimeter


# ============================================================
# 三、坐标数据库（使用元组作为字典键）
# ============================================================

class GeoDatabase:
    """
    地理坐标数据库

    关键设计：使用元组 (lat, lng) 或 namedtuple Point2D 作为字典键。
    这是因为：
    1. 元组不可变 → 可哈希 → 可以做字典键
    2. 列表可变 → 不可哈希 → 不能做字典键
    3. namedtuple 继承 tuple → 同样可哈希
    """

    def __init__(self):
        # 方式 A：普通元组 (lat, lng) 作为键
        self._cities: dict[Tuple[float, float], str] = {}

        # 方式 B：namedtuple Point2D 作为键
        self._landmarks: dict[Point2D, dict] = {}

    def add_city(self, name: str, lat: float, lng: float):
        """添加城市坐标"""
        self._cities[(lat, lng)] = name

    def find_city(self, lat: float, lng: float) -> Optional[str]:
        """根据坐标查找城市名"""
        return self._cities.get((lat, lng))

    def add_landmark(self, name: str, description: str, lat: float, lng: float):
        """添加地标"""
        point = Point2D(lat, lng)
        self._landmarks[point] = {
            'name': name,
            'description': description,
        }

    def find_landmark(self, lat: float, lng: float) -> Optional[dict]:
        """根据坐标查找地标"""
        return self._landmarks.get(Point2D(lat, lng))

    def nearby_cities(self, center_lat: float, center_lng: float,
                      radius_km: float) -> List[Tuple[str, float]]:
        """
        查找指定半径内的城市
        简化算法：1纬度 ≈ 111km，1经度 ≈ 111*cos(lat) km
        """
        results: List[Tuple[str, float]] = []

        for (lat, lng), name in self._cities.items():
            # 近似距离（不适用于极地和高精度场景）
            dlat = (lat - center_lat) * 111  # km
            dlon = (lng - center_lng) * 111 * math.cos(math.radians(center_lat))
            dist = math.sqrt(dlat ** 2 + dlon ** 2)

            if dist <= radius_km:
                results.append((name, round(dist, 1)))

        return sorted(results, key=lambda x: x[1])

    def get_all_cities(self) -> List[Tuple[str, float, float]]:
        """获取所有城市数据"""
        return [(name, lat, lng) for (lat, lng), name in self._cities.items()]

    def city_count(self) -> int:
        return len(self._cities)


# ============================================================
# 四、坐标序列化工具
# ============================================================

class CoordinateSerializer:
    """坐标数据的序列化与反序列化"""

    @staticmethod
    def points_to_csv(points: List[Point2D], filename: str):
        """将点列表保存为 CSV 文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("x,y\n")
            for p in points:
                f.write(f"{p.x},{p.y}\n")
        print(f"  ✅ 已保存 {len(points)} 个点到 {filename}")

    @staticmethod
    def csv_to_points(filename: str) -> List[Point2D]:
        """从 CSV 文件读取点列表"""
        points = []
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 跳过表头
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            x_str, y_str = line.split(',')
            points.append(Point2D(float(x_str), float(y_str)))

        return points

    @staticmethod
    def filter_points_by_distance(points: List[Point2D],
                                  center: Point2D,
                                  max_dist: float) -> List[Point2D]:
        """过滤出距离中心点一定范围内的所有点"""
        engine = GeometryEngine()
        return [p for p in points if engine.distance(p, center) <= max_dist]


# ============================================================
# 五、主程序演示
# ============================================================

def main():
    print("=" * 65)
    print("📍 坐标系统 — 完整实战演示")
    print("=" * 65)

    # ---- 1. 基础 2D 操作 ----
    print("\n📐 1. 2D 几何基础")
    p1 = Point2D(1.0, 2.0)
    p2 = Point2D(4.0, 6.0)
    engine = GeometryEngine()

    print(f"   点 A: {p1}")
    print(f"   点 B: {p2}")
    print(f"   距离: {engine.distance(p1, p2):.4f}")
    print(f"   中点: {engine.midpoint(p1, p2)}")

    # ---- 2. 坐标变换 ----
    print("\n🔄 2. 坐标变换")
    p = Point2D(3, 4)

    # 平移
    moved = engine.translate(p, 10, -5)
    print(f"   原点: {p}")
    print(f"   平移 (10, -5): {moved}")

    # 旋转
    rotated = engine.rotate(p, 90)
    print(f"   绕原点旋转 90°: {rotated}")
    rotated_45 = engine.rotate(p, 45)
    print(f"   绕原点旋转 45°: {rotated_45}")

    # 绕任意点旋转
    center = Point2D(1, 1)
    rotated_around = engine.rotate(p, 90, center)
    print(f"   绕 (1,1) 旋转 90°: {rotated_around}")

    # ---- 3. 多边形计算 ----
    print("\n🔺 3. 多边形计算")

    # 3-4-5 直角三角形
    triangle = [
        Point2D(0, 0),
        Point2D(3, 0),
        Point2D(0, 4),
    ]
    area = engine.polygon_area(triangle)
    perimeter = engine.polygon_perimeter(triangle)
    print(f"   三角形顶点: {triangle}")
    print(f"   面积: {area:.2f} (应为 6.0)")
    print(f"   周长: {perimeter:.2f} (应为 12.0)")

    # 正方形
    square = [
        Point2D(0, 0),
        Point2D(4, 0),
        Point2D(4, 4),
        Point2D(0, 4),
    ]
    area_sq = engine.polygon_area(square)
    perimeter_sq = engine.polygon_perimeter(square)
    print(f"\n   正方形面积: {area_sq:.2f} (应为 16.0)")
    print(f"   正方形周长: {perimeter_sq:.2f} (应为 16.0)")

    # ---- 4. 3D 空间 ----
    print("\n🌌 4. 3D 空间操作")
    pp1 = Point3D(0, 0, 0)
    pp2 = Point3D(1, 2, 3)

    print(f"   3D 点: {pp1}")
    print(f"   3D 点: {pp2}")
    print(f"   3D 距离: {pp1.distance_to(pp2):.4f}")
    print(f"   3D 距离 (对称): {pp2.distance_to(pp1):.4f}")

    # ---- 5. 地理坐标数据库 ----
    print("\n🗺️  5. 地理坐标数据库")
    db = GeoDatabase()

    # 添加城市
    cities_data = [
        ("北京", 39.9042, 116.4074),
        ("上海", 31.2304, 121.4737),
        ("广州", 23.1291, 113.2644),
        ("深圳", 22.5431, 114.0579),
        ("成都", 30.5728, 104.0668),
        ("杭州", 30.2741, 120.1551),
        ("武汉", 30.5928, 114.3055),
        ("西安", 34.3416, 108.9398),
        ("重庆", 29.4316, 106.9123),
        ("南京", 32.0603, 118.7969),
    ]

    for name, lat, lng in cities_data:
        db.add_city(name, lat, lng)

    print(f"   已添加 {db.city_count()} 个城市")

    # 查找城市
    city = db.find_city(31.2304, 121.4737)
    print(f"   find (31.23, 121.47) → {city}")

    # 添加地标
    db.add_landmark("天安门", "北京中心地标", 39.9042, 116.3972)
    db.add_landmark("东方明珠塔", "上海浦东标志建筑", 31.2397, 121.4997)
    db.add_landmark("广州塔", "广州第一高塔", 23.1065, 113.3246)

    # 查找地标
    lm = db.find_landmark(39.9042, 116.3972)
    if lm:
        print(f"   find 地标 → {lm['name']}: {lm['description']}")

    # 附近城市搜索
    print("\n   🏙️  上海周边 500km 以内的城市:")
    nearby = db.nearby_cities(31.2304, 121.4737, 500)
    for name, dist in nearby:
        print(f"      {name}: {dist:.0f}km")

    print("\n   🏙️  成都周边 300km 以内的城市:")
    nearby_cd = db.nearby_cities(30.5728, 104.0668, 300)
    for name, dist in nearby_cd:
        print(f"      {name}: {dist:.0f}km")

    # ---- 6. CSV 序列化演示 ----
    print("\n💾 6. CSV 序列化")
    sample_points = [
        Point2D(1.5, 2.5),
        Point2D(3.0, 4.0),
        Point2D(5.5, 6.5),
        Point2D(7.0, 8.0),
        Point2D(9.5, 10.5),
    ]
    CoordinateSerializer.points_to_csv(sample_points, "/tmp/points.csv")

    loaded = CoordinateSerializer.csv_to_points("/tmp/points.csv")
    print(f"   读取 CSV: {loaded}")

    # ---- 7. 元组作为函数多返回值的应用 ----
    print("\n🔙 7. 多重返回值的坐标工具函数")


    def find_farthest(points: List[Point2D], reference: Point2D) -> Tuple[Point2D, float, int]:
        """
        找到距离参考点最远的点
        返回: (最远点, 距离, 索引)
        """
        if not points:
            return (Point2D(0, 0), 0.0, -1)

        farthest = None
        max_dist = -1.0
        farthest_idx = -1

        for i, p in enumerate(points):
            d = engine.distance(p, reference)
            if d > max_dist:
                max_dist = d
                farthest = p
                farthest_idx = i

        return (farthest, max_dist, farthest_idx)


    origin = Point2D(0, 0)
    farthest_point, distance, idx = find_farthest(sample_points, origin)
    print(f"   参考点: {origin}")
    print(f"   最远点: {farthest_point} (距离: {distance:.2f}, 索引: {idx})")

    # ---- 8. 总结 ----
    print("\n" + "=" * 65)
    print("✅ 本演示展示了以下元组核心技术：")
    print("   1. namedtuple 定义坐标类型（可读性 + 不可变性）")
    print("   2. 普通元组作为字典键存储坐标") 
    print("   3. 元组拆包接收函数多返回值")
    print("   4. 元组不可变性保障坐标安全")
    print("   5. NamedTuple 类语法支持方法定义")
    print("=" * 65)


if __name__ == "__main__":
    main()
