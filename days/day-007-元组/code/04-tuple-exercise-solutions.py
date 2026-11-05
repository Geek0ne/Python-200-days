#!/usr/bin/env python3
"""
04-tuple-exercise-solutions.py — Day 007 补充
元组练习题参考实现

包含：
1. Vector3D 三维向量运算库
2. 学生成绩管理系统（namedtuple）
3. 文本分析器
4. 路径点集合
5. 数据流聚合器

可直接运行：python3 04-tuple-exercise-solutions.py
"""

import math
from collections import namedtuple
from typing import List, Tuple, Optional, NamedTuple


# ============================================================
# 练习 1：Vector3D 三维向量运算库
# ============================================================

class Vector3D(NamedTuple):
    """三维向量"""
    x: float
    y: float
    z: float

    def __add__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def dot(self, other: 'Vector3D') -> float:
        """点积"""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: 'Vector3D') -> 'Vector3D':
        """叉积"""
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        """向量长度"""
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def normalize(self) -> 'Vector3D':
        """归一化"""
        l = self.length()
        if l == 0:
            return Vector3D(0, 0, 0)
        return Vector3D(self.x / l, self.y / l, self.z / l)

    def angle_with(self, other: 'Vector3D') -> float:
        """与另一向量的夹角（弧度）"""
        cos_theta = self.dot(other) / (self.length() * other.length())
        cos_theta = max(-1.0, min(1.0, cos_theta))  # 钳制浮点误差
        return math.acos(cos_theta)

    def __str__(self):
        return f"V({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"


def test_vector3d():
    print("=" * 60)
    print("  练习 1: Vector3D 三维向量库")
    print("=" * 60)

    v1 = Vector3D(1, 2, 3)
    v2 = Vector3D(4, 5, 6)

    print(f"\n  v1 = {v1}")
    print(f"  v2 = {v2}")
    print(f"  v1 + v2 = {v1 + v2}")
    print(f"  v1 - v2 = {v1 - v2}")
    print(f"  v1 · v2 = {v1.dot(v2)} (点积, 预期: 32)")
    print(f"  v1 × v2 = {v1.cross(v2)} (叉积, 预期: V(-3, 6, -3))")
    print(f"  |v1| = {v1.length():.4f} (长度, 预期: 3.7417)")
    print(f"  v1 归一化 = {v1.normalize()}")
    print(f"  v1 与 v2 夹角 = {math.degrees(v1.angle_with(v2)):.2f}°")

    # 验证点积与角度关系：v1·v2 = |v1||v2|cos(θ)
    dot_val = v1.dot(v2)
    product = v1.length() * v2.length() * math.cos(v1.angle_with(v2))
    print(f"\n  验证: v1·v2 = {dot_val:.4f} ≈ |v1||v2|cos(θ) = {product:.4f}")


# ============================================================
# 练习 2：学生成绩管理系统
# ============================================================

Student = namedtuple("Student", ["name", "chinese", "math", "english"])


def average_score(student: Student) -> float:
    return (student.chinese + student.math + student.english) / 3


def total_score(student: Student) -> int:
    return student.chinese + student.math + student.english


def rank_students(students: List[Student]) -> List[Student]:
    return sorted(students, key=total_score, reverse=True)


def top_student(students: List[Student]) -> Optional[Student]:
    return rank_students(students)[0] if students else None


def failing_students(students: List[Student], threshold: int = 60) -> List[Tuple[str, str, int]]:
    """返回不及格学生列表 (name, subject, score)"""
    result = []
    for s in students:
        for subj in ["chinese", "math", "english"]:
            score = getattr(s, subj)
            if score < threshold:
                result.append((s.name, subj, score))
    return result


def test_grade_system():
    print("\n" + "=" * 60)
    print("  练习 2: 学生成绩管理系统")
    print("=" * 60)

    students = [
        Student("Alice", 90, 85, 92),
        Student("Bob", 78, 88, 80),
        Student("Charlie", 95, 92, 98),
    ]

    print(f"\n  学生列表:")
    for s in students:
        total = total_score(s)
        avg = average_score(s)
        print(f"    {s.name}: 语文{s.chinese} 数学{s.math} 英语{s.english}")
        print(f"      总分={total}, 平均分={avg:.1f}")

    print(f"\n  总分排名:")
    for rank, s in enumerate(rank_students(students), 1):
        print(f"    第{rank}名: {s.name} ({total_score(s)}分)")

    top = top_student(students)
    print(f"\n  第一名: {top.name} ({total_score(top)}分)")

    # namedtuple 的 _replace 方法
    print(f"\n  _replace 更新成绩:")
    bob_updated = students[1]._replace(math=95)
    print(f"    Bob 原始: {students[1]}")
    print(f"    Bob 更新数学后: {bob_updated}")


# ============================================================
# 练习 3：文本分析器
# ============================================================

def test_text_analyzer():
    print("\n" + "=" * 60)
    print("  练习 3: 文本分析器")
    print("=" * 60)

    text = "Alice:85,Bob:92,Charlie:78,Diana:95"

    # 1. 解析为 (name, score) 元组列表
    pairs = []
    for part in text.split(","):
        name, score_str = part.split(":")
        pairs.append((name, int(score_str)))

    print(f"\n  解析结果:")
    for name, score in pairs:
        print(f"    {name}: {score}")

    # 2. 最高分
    top_name, top_score = max(pairs, key=lambda x: x[1])
    print(f"\n  最高分: {top_name} ({top_score})")

    # 3. 平均分
    scores_only = [score for _, score in pairs]
    avg = sum(scores_only) / len(scores_only)
    print(f"  平均分: {avg:.1f}")

    # 4. 更 Pythonic 的写法
    names, scores = zip(*pairs)  # 元组拆包反操作！
    print(f"\n  拆包反操作 zip(*pairs):")
    print(f"    names  = {names}")
    print(f"    scores = {scores}")

    # 5. 给分差评级
    def grade_score(score):
        if score >= 90: return "A"
        elif score >= 80: return "B"
        elif score >= 70: return "C"
        elif score >= 60: return "D"
        return "F"

    graded = [(name, score, grade_score(score)) for name, score in pairs]
    print(f"\n  评级:")
    for name, score, grade in graded:
        print(f"    {name}: {score} → {grade}")


# ============================================================
# 练习 4：路径点集合
# ============================================================

Point = namedtuple("Point", ["x", "y"])


def distance(p1: Point, p2: Point) -> float:
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def total_path_length(points: List[Point]) -> float:
    if len(points) < 2:
        return 0.0
    return sum(distance(points[i], points[i + 1]) for i in range(len(points) - 1))


def longest_segment(points: List[Point]) -> Tuple[Point, Point, float]:
    """返回距离最长的 (点A, 点B, 距离)"""
    if len(points) < 2:
        return (Point(0, 0), Point(0, 0), 0.0)

    max_pair = max(
        ((points[i], points[i + 1], distance(points[i], points[i + 1]))
         for i in range(len(points) - 1)),
        key=lambda x: x[2]
    )
    return max_pair


def simplify_path(points: List[Point], min_dist: float = 2.0) -> List[Point]:
    """简化路径：跳过距离过短的点"""
    if len(points) < 3:
        return points

    simplified = [points[0]]
    for i in range(1, len(points)):
        if distance(simplified[-1], points[i]) >= min_dist:
            simplified.append(points[i])
        else:
            print(f"    ⏭ 跳过 {points[i]} (距上一点 < {min_dist})")

    # 确保终点在简化路径中
    if simplified[-1] != points[-1]:
        simplified.append(points[-1])

    return simplified


def test_path_analysis():
    print("\n" + "=" * 60)
    print("  练习 4: 路径点集合分析")
    print("=" * 60)

    path = [
        Point(0, 0),
        Point(1, 2),
        Point(1.5, 2.4),  # 与上一个点距离很短
        Point(3, 5),
        Point(3.2, 5.1),  # 同上
        Point(6, 1),
        Point(10, 4),
    ]

    print(f"\n  原始路径 ({len(path)} 个点):")
    for i, p in enumerate(path):
        print(f"    {i}: {p}")

    total = total_path_length(path)
    print(f"\n  路径总长度: {total:.4f}")

    longest = longest_segment(path)
    print(f"  最长段: {longest[0]} → {longest[1]}, 距离={longest[2]:.4f}")

    print(f"\n  路径简化 (min_dist=2.0):")
    simplified = simplify_path(path, 2.0)
    print(f"  简化后 ({len(simplified)} 个点):")
    for p in simplified:
        print(f"    {p}")
    print(f"  简化后路径长度: {total_path_length(simplified):.4f}")


# ============================================================
# 练习 5：数据流聚合器
# ============================================================

SensorReading = namedtuple("SensorReading", ["timestamp", "temperature", "humidity"])


def analyze_sensor_data(readings: List[SensorReading]) -> dict:
    """分析传感器数据流"""
    if not readings:
        return {}

    temps = [r.temperature for r in readings]
    hums = [r.humidity for r in readings]

    result = {
        "temperature": {
            "avg": sum(temps) / len(temps),
            "min": min(temps),
            "max": max(temps),
            "range": max(temps) - min(temps),
        },
        "humidity": {
            "avg": sum(hums) / len(hums),
            "min": min(hums),
            "max": max(hums),
            "range": max(hums) - min(hums),
        },
        "readings_count": len(readings),
    }

    # 找出温度变化率异常的点
    if len(readings) >= 2:
        anomalies = []
        for i in range(1, len(readings)):
            dt = readings[i].timestamp - readings[i - 1].timestamp
            if dt == 0:
                continue
            delta_t = readings[i].temperature - readings[i - 1].temperature
            rate = abs(delta_t / dt)
            if rate > 0.5:
                anomalies.append({
                    "timestamp": readings[i].timestamp,
                    "rate": rate,
                    "from": readings[i - 1].temperature,
                    "to": readings[i].temperature,
                })
        result["anomalies"] = anomalies

    return result


def test_sensor_analysis():
    print("\n" + "=" * 60)
    print("  练习 5: 传感器数据流聚合器")
    print("=" * 60)

    readings = [
        SensorReading(1, 25.3, 60.1),
        SensorReading(2, 25.7, 59.8),
        SensorReading(3, 26.1, 59.2),
        SensorReading(4, 26.8, 58.5),
        SensorReading(5, 27.2, 57.9),
    ]

    print(f"\n  传感器数据:")
    for r in readings:
        print(f"    t={r.timestamp}: {r.temperature}°C, {r.humidity}%")

    analysis = analyze_sensor_data(readings)

    print(f"\n  分析结果:")
    print(f"    温度: 平均={analysis['temperature']['avg']:.1f}°C, "
          f"范围=[{analysis['temperature']['min']}~{analysis['temperature']['max']}]")
    print(f"    湿度: 平均={analysis['humidity']['avg']:.1f}%, "
          f"范围=[{analysis['humidity']['min']}~{analysis['humidity']['max']}]")

    if analysis.get("anomalies"):
        print(f"\n  ⚠️ 异常温度变化:")
        for a in analysis["anomalies"]:
            print(f"    t={a['timestamp']}: {a['from']}°C → {a['to']}°C "
                  f"(变化率: {a['rate']:.2f}°C/单位时间)")

    # 使用 zip 提取温度序列
    temps = [r.temperature for r in readings]
    print(f"\n  zip 技巧: 提取温度序列 = {temps}")


# ============================================================
# 主程序
# ============================================================

def main():
    test_vector3d()
    test_grade_system()
    test_text_analyzer()
    test_path_analysis()
    test_sensor_analysis()

    print("\n" + "=" * 60)
    print("  ✅ 全部练习题完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
