#!/usr/bin/env python3
"""
exercise-solutions.py
Day 008 — 练习 1~3 参考实现

包含：
1. GradeManager 学生成绩管理系统
2. URL 查询参数解析器
3. 缓存装饰器 (Memoization)

可直接运行：python3 exercise-solutions.py
"""

import time
from functools import wraps


# ============================================================
# 练习 1：学生成绩管理系统
# ============================================================

class GradeManager:
    """学生成绩管理系统"""

    def __init__(self):
        self._students: dict[str, dict] = {}

    def add_student(self, student_id: str, name: str):
        """添加学生"""
        if student_id in self._students:
            raise ValueError(f"学号 {student_id} 已存在")
        self._students[student_id] = {
            "name": name,
            "scores": {},  # subject -> score
        }

    def add_score(self, student_id: str, subject: str, score: float):
        """添加/更新某科成绩"""
        student = self._students.get(student_id)
        if not student:
            raise ValueError(f"学号 {student_id} 不存在")
        student["scores"][subject] = score

    def get_student(self, student_id: str) -> dict:
        """获取学生信息"""
        return self._students.get(student_id, {})

    def get_average(self, student_id: str) -> float:
        """计算学生平均分"""
        student = self._students.get(student_id)
        if not student or not student["scores"]:
            return 0.0
        scores = list(student["scores"].values())
        return sum(scores) / len(scores)

    def get_total_score(self, student_id: str) -> float:
        """计算学生总分"""
        student = self._students.get(student_id)
        if not student:
            return 0.0
        return sum(student["scores"].values())

    def get_class_average(self, subject: str) -> float:
        """计算全班某科平均分"""
        scores = []
        for student in self._students.values():
            if subject in student["scores"]:
                scores.append(student["scores"][subject])
        return sum(scores) / len(scores) if scores else 0.0

    def get_ranking(self, subject: str) -> list:
        """
        获取某科排名（从高到低）
        返回 [(名次, 学号, 姓名, 分数), ...]
        """
        candidates = []
        for sid, student in self._students.items():
            if subject in student["scores"]:
                candidates.append((sid, student["name"], student["scores"][subject]))

        candidates.sort(key=lambda x: -x[2])  # 按分数降序
        result = []
        for rank, (sid, name, score) in enumerate(candidates, 1):
            result.append((rank, sid, name, score))
        return result

    def get_total_ranking(self) -> list:
        """按总分排名"""
        candidates = []
        for sid, student in self._students.items():
            total = sum(student["scores"].values())
            candidates.append((sid, student["name"], total))

        candidates.sort(key=lambda x: -x[2])
        return [(i, sid, name, total) for i, (sid, name, total) in enumerate(candidates, 1)]

    def get_top_student(self, subject: str) -> str:
        """获取某科最高分学生姓名"""
        ranking = self.get_ranking(subject)
        return ranking[0][2] if ranking else ""

    def remove_student(self, student_id: str) -> bool:
        """删除学生"""
        if student_id in self._students:
            del self._students[student_id]
            return True
        return False

    def get_failing_students(self, threshold: float = 60.0) -> list:
        """获取不及格学生列表（任一科低于阈值）"""
        failing = []
        for sid, student in self._students.items():
            bad_subjects = [
                (subj, score)
                for subj, score in student["scores"].items()
                if score < threshold
            ]
            if bad_subjects:
                failing.append((sid, student["name"], bad_subjects))
        return failing

    def export_csv(self, filepath: str):
        """导出为 CSV"""
        import csv
        # 收集所有科目
        all_subjects = set()
        for student in self._students.values():
            all_subjects.update(student["scores"].keys())
        all_subjects = sorted(all_subjects)

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ["学号", "姓名"] + all_subjects + ["总分", "平均分"]
            writer.writerow(header)
            for sid in sorted(self._students.keys()):
                student = self._students[sid]
                row = [sid, student["name"]]
                for subj in all_subjects:
                    row.append(student["scores"].get(subj, ""))
                total = sum(student["scores"].values())
                avg = total / len(student["scores"]) if student["scores"] else 0
                row.extend([total, round(avg, 1)])
                writer.writerow(row)
        print(f"  ✅ 已导出到 {filepath}")


# ============================================================
# 练习 2：URL 查询参数解析器
# ============================================================

def parse_query_string(query: str) -> dict:
    """
    解析 URL 查询字符串为字典
    支持重复键 → 用列表存储
    """
    if not query:
        return {}

    result = {}
    for pair in query.split("&"):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        # URL 解码
        key = key.replace("%20", " ").replace("+", " ")
        value = value.replace("%20", " ").replace("+", " ")

        if key in result:
            # 重复键：转为列表
            existing = result[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[key] = [existing, value]
        else:
            result[key] = value

    return result


def build_query_string(params: dict) -> str:
    """
    将字典构建为 URL 查询字符串
    """
    parts = []
    for key, value in params.items():
        if isinstance(value, list):
            for v in value:
                parts.append(f"{key}={v}")
        else:
            parts.append(f"{key}={value}")
    return "&".join(parts)


def merge_query_params(base: str, extra: dict) -> str:
    """
    在已有 URL 上添加额外参数
    """
    if "?" in base:
        base_url, existing_query = base.split("?", 1)
        existing_params = parse_query_string(existing_query)
    else:
        base_url = base
        existing_params = {}

    # 合并（extra 覆盖同名字段）
    merged = {**existing_params}
    for key, value in extra.items():
        merged[key] = value

    query_string = build_query_string(merged)
    return f"{base_url}?{query_string}"


def parse_nested_query(query: str) -> dict:
    """
    解析嵌套参数：user[name]=Alice&user[age]=25
    """
    result = {}
    for pair in query.split("&"):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)

        # 检查是否是嵌套语法 user[name]
        if "[" in key and key.endswith("]"):
            outer_key, inner_part = key.split("[", 1)
            inner_key = inner_part.rstrip("]")
            if outer_key not in result:
                result[outer_key] = {}
            result[outer_key][inner_key] = value
        else:
            result[key] = value

    return result


# ============================================================
# 练习 3：缓存装饰器
# ============================================================

def memoize(max_size: int = 128):
    """缓存装饰器：用字典缓存函数调用结果"""

    def decorator(func):
        cache = {}  # key: args_tuple → (result, timestamp)
        order = []  # 用于 LRU 追踪

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 构造缓存键
            key_parts = [args]
            if kwargs:
                # 关键字参数排序以保证一致性
                key_parts.append(tuple(sorted(kwargs.items())))
            cache_key = tuple(key_parts)

            # 缓存命中
            if cache_key in cache:
                # 更新最近使用顺序
                order.remove(cache_key)
                order.append(cache_key)
                return cache[cache_key][0]

            # 缓存未命中，调用函数
            result = func(*args, **kwargs)
            cache[cache_key] = (result, time.time())

            # 追踪顺序
            order.append(cache_key)

            # 超出最大大小，淘汰最旧的
            if len(cache) > max_size:
                oldest_key = order.pop(0)
                del cache[oldest_key]

            return result

        wrapper.cache_info = lambda: {
            "size": len(cache),
            "max_size": max_size,
            "keys": list(cache.keys()),
        }
        wrapper.cache_clear = lambda: (cache.clear(), order.clear())
        wrapper.cache = cache  # 暴露给外部（调试用）

        return wrapper

    return decorator


# ============================================================
# 测试运行
# ============================================================

def test_grade_manager():
    print("=" * 50)
    print("📚 测试：学生成绩管理系统")
    print("=" * 50)

    mgr = GradeManager()
    mgr.add_student("001", "Alice")
    mgr.add_student("002", "Bob")
    mgr.add_student("003", "Charlie")

    mgr.add_score("001", "语文", 90)
    mgr.add_score("001", "数学", 85)
    mgr.add_score("001", "英语", 92)
    mgr.add_score("002", "语文", 78)
    mgr.add_score("002", "数学", 95)
    mgr.add_score("002", "英语", 80)
    mgr.add_score("003", "语文", 88)
    mgr.add_score("003", "数学", 72)

    print(f"\n  Alice: {mgr.get_student('001')}")
    print(f"  Alice 平均分: {mgr.get_average('001'):.1f}")
    print(f"  全班语文平均分: {mgr.get_class_average('语文'):.1f}")

    print(f"\n  数学排名:")
    for rank, sid, name, score in mgr.get_ranking("数学"):
        print(f"    第{rank}名: {name} ({score}分)")

    print(f"\n  英语最高分: {mgr.get_top_student('英语')}")

    print(f"\n  总分排名:")
    for rank, sid, name, total in mgr.get_total_ranking():
        print(f"    第{rank}名: {name} (总分 {total})")

    print(f"\n  不及格学生 (< 75):")
    for sid, name, subjects in mgr.get_failing_students(75):
        subs = ", ".join(f"{s}:{sc}" for s, sc in subjects)
        print(f"    {name}: {subs}")

    mgr.export_csv("/tmp/grade_report.csv")


def test_url_parser():
    print("\n" + "=" * 50)
    print("🔗 测试：URL 查询参数解析器")
    print("=" * 50)

    # 基础解析
    parsed = parse_query_string("name=Alice&age=25&city=Beijing")
    print(f"  解析: name=Alice&age=25&city=Beijing")
    print(f"  结果: {parsed}")

    # 构建
    built = build_query_string({"name": "Bob", "role": "admin", "page": 1})
    print(f"\n  构建: {{'name': 'Bob', 'role': 'admin', 'page': 1}}")
    print(f"  结果: {built}")

    # 合并
    merged = merge_query_params("http://example.com?lang=zh", {"theme": "dark"})
    print(f"\n  合并: http://example.com?lang=zh + {{'theme': 'dark'}}")
    print(f"  结果: {merged}")

    # 重复键
    repeating = parse_query_string("tag=python&tag=java&tag=go")
    print(f"\n  重复键: tag=python&tag=java&tag=go")
    print(f"  结果: {repeating}")

    # 嵌套参数
    nested = parse_nested_query("user[name]=Alice&user[age]=25&lang=zh")
    print(f"\n  嵌套参数: user[name]=Alice&user[age]=25&lang=zh")
    print(f"  结果: {nested}")


def test_memoize():
    print("\n" + "=" * 50)
    print("⚡ 测试：缓存装饰器")
    print("=" * 50)

    @memoize(max_size=256)
    def fibonacci(n):
        if n < 2:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)

    # 热缓存
    start = time.time()
    result_100 = fibonacci(100)
    elapsed = time.time() - start
    print(f"  fibonacci(100) = {result_100}")
    print(f"  耗时: {elapsed:.6f}s")
    print(f"  缓存: {fibonacci.cache_info()}")

    # 再次调用（缓存命中）
    start = time.time()
    result_100_again = fibonacci(100)
    elapsed = time.time() - start
    print(f"\n  再次调用 fibonacci(100) = {result_100_again}")
    print(f"  耗时: {elapsed:.6f}s (缓存命中！)")

    # 测试多个值
    for n in [10, 20, 30, 40, 50]:
        start = time.time()
        r = fibonacci(n)
        t = time.time() - start
        print(f"  fibonacci({n}) = {r}  ({t:.6f}s)")

    print(f"\n  最终缓存状态: {fibonacci.cache_info()}")

    # 清除缓存
    fibonacci.cache_clear()
    print(f"\n  清除后: {fibonacci.cache_info()}")


if __name__ == "__main__":
    test_grade_manager()
    test_url_parser()
    test_memoize()
    print("\n" + "=" * 50)
    print("✅ 所有练习测试完成！")
    print("=" * 50)
