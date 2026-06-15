#!/usr/bin/env python3
"""
Day 020 - File Tree Walker
文件树遍历实战：递归遍历目录结构
"""

import os
import sys
from pathlib import Path
from typing import Callable, Optional


# ============================================================
# 1. 基础：递归遍历目录
# ============================================================

def walk_directory(path: str, indent: str = "") -> None:
    """最简单的目录递归遍历 — 打印树形结构

    这是递归最自然的应用场景之一：
    目录包含文件或子目录，子目录又包含更多文件...
    这是一个天然的自相似结构。
    """
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        print(f"{indent}  ⛔ [权限不足]")
        return

    for entry in entries:
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            print(f"{indent}📁 {entry}/")
            walk_directory(full_path, indent + "    ")
        else:
            print(f"{indent}📄 {entry}")


# ============================================================
# 2. 进阶：功能完善的目录树遍历器
# ============================================================

class FileTreeWalker:
    """功能完整的文件树遍历器"""

    def __init__(self, root_path: str):
        self.root = Path(root_path).resolve()
        self.stats = {
            "dirs": 0,
            "files": 0,
            "total_size": 0,
            "errors": 0,
        }

    def walk(self) -> dict:
        """执行遍历，清空并重新统计"""
        self.stats = {"dirs": 0, "files": 0, "total_size": 0, "errors": 0}
        self._walk(self.root)
        return self.stats

    def _walk(self, current: Path) -> None:
        """递归遍历的核心实现

        递归终止条件：
        - 当前路径不是目录（由调用方保证）
        - os.listdir 返回空列表（会自动终止）

        递归调用：
        - 对每个子目录调用自身
        """
        try:
            for entry in sorted(current.iterdir()):
                if entry.is_dir():
                    self.stats["dirs"] += 1
                    self._walk(entry)  # 递归进入子目录
                elif entry.is_file():
                    self.stats["files"] += 1
                    self.stats["total_size"] += entry.stat().st_size
        except PermissionError:
            self.stats["errors"] += 1

    def print_tree(self, path: Optional[Path] = None,
                   prefix: str = "", is_last: bool = True) -> None:
        """打印美观的目录树

        使用 └── 和 ├── 绘制树枝，类似 tree 命令
        """
        if path is None:
            path = self.root
            print(path.name + "/")
            entries = self._get_sorted_entries(path)
            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                self.print_tree(entry, prefix, is_last)
            return

        # 当前节点的连接符
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{path.name}{'/' if path.is_dir() else ''}")

        if path.is_dir():
            # 子节点的前缀
            extension = "    " if is_last else "│   "
            entries = self._get_sorted_entries(path)
            for i, entry in enumerate(entries):
                self.print_tree(entry, prefix + extension,
                                i == len(entries) - 1)

    def _get_sorted_entries(self, path: Path) -> list:
        """获取排序后的条目（目录在前，文件在后）"""
        try:
            entries = list(path.iterdir())
        except PermissionError:
            return []

        # 目录在前，字母排序
        entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
        return entries

    def find_by_extension(self, ext: str) -> list:
        """按扩展名递归查找文件

        递归 + 过滤器的经典模式
        """
        results = []
        self._find_by_ext(self.root, ext.lower(), results)
        return results

    def _find_by_ext(self, current: Path, ext: str, results: list) -> None:
        """递归查找辅助函数"""
        try:
            for entry in current.iterdir():
                if entry.is_dir():
                    self._find_by_ext(entry, ext, results)
                elif entry.suffix.lower() == ext:
                    results.append(entry)
        except PermissionError:
            pass


# ============================================================
# 3. 实战：dir_size_stats（类比 Day 015 pytools）
# ============================================================

def dir_size_stats(path: str, min_size: int = 0) -> dict:
    """递归统计目录大小分布

    返回:
        {
            "total_size": 总大小（字节）,
            "total_files": 总文件数,
            "largest_file": (路径, 大小),
            "by_extension": {扩展名: 总大小},
        }
    """
    stats = {
        "total_size": 0,
        "total_files": 0,
        "largest_file": (None, 0),
        "by_extension": {},
    }

    def _recurse(current: Path):
        """内部递归函数，闭包捕获 stats"""
        nonlocal stats
        try:
            for entry in current.iterdir():
                if entry.is_dir():
                    _recurse(entry)
                elif entry.is_file():
                    size = entry.stat().st_size
                    stats["total_size"] += size
                    stats["total_files"] += 1

                    if size > stats["largest_file"][1]:
                        stats["largest_file"] = (str(entry), size)

                    ext = entry.suffix.lower() or "(no ext)"
                    stats["by_extension"][ext] = \
                        stats["by_extension"].get(ext, 0) + size
        except PermissionError:
            pass

    # ⚠️ nonlocal 不能用于嵌套在函数外的变量
    # 我们使用可变 dict 来传递累加器（类似尾递归的累加器模式）
    _recurse(Path(path))

    # 过滤小于 min_size 的扩展名
    if min_size > 0:
        stats["by_extension"] = {
            k: v for k, v in stats["by_extension"].items() if v >= min_size
        }

    return stats


# ============================================================
# 4. 高级：自定义回调遍历
# ============================================================

def walk_with_callback(root: str,
                       file_callback: Callable[[str], None] = None,
                       dir_callback: Callable[[str], None] = None,
                       max_depth: int = -1) -> None:
    """带回调函数和最大深度的目录遍历

    参数:
        root: 根目录
        file_callback: 遇到文件时调用 f(file_path)
        dir_callback: 遇到目录时调用 f(dir_path)
        max_depth: 最大递归深度，-1 表示无限制
    """
    def _walk(current: str, depth: int = 0):
        if max_depth >= 0 and depth > max_depth:
            return

        try:
            for entry in sorted(os.listdir(current)):
                full_path = os.path.join(current, entry)
                if os.path.isdir(full_path):
                    if dir_callback:
                        dir_callback(full_path)
                    _walk(full_path, depth + 1)
                elif os.path.isfile(full_path):
                    if file_callback:
                        file_callback(full_path)
        except PermissionError:
            pass

    _walk(root)


# ============================================================
# 5. 实践：查找大文件
# ============================================================

def find_large_files(root: str, min_mb: int = 10) -> list:
    """递归查找大于指定大小的文件

    返回: [(size_in_mb, path), ...] 按大小降序排列
    """
    min_bytes = min_mb * 1024 * 1024
    results = []

    def _search(current: str):
        try:
            with os.scandir(current) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        _search(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        size = entry.stat().st_size
                        if size >= min_bytes:
                            results.append((size / (1024 * 1024), entry.path))
        except PermissionError:
            pass

    _search(root)
    results.sort(reverse=True)
    return results


# ============================================================
# Demo
# ============================================================

def main():
    print("=" * 60)
    print("文件树遍历实战 - 递归经典应用")
    print("=" * 60)

    # 使用当前目录作为示例
    demo_path = os.path.dirname(os.path.abspath(__file__))
    print(f"\n📂 遍历目录: {demo_path}")
    print("=" * 60)

    # 1. 简单遍历
    print("\n1️⃣ 简单目录遍历:")
    walk_directory(demo_path)

    # 2. 高级遍历器
    print("\n\n2️⃣ 文件树遍历器（带统计）:")
    walker = FileTreeWalker(demo_path)

    stats = walker.walk()
    print(f"   目录数: {stats['dirs']}")
    print(f"   文件数: {stats['files']}")
    total_mb = stats['total_size'] / (1024 * 1024)
    print(f"   总大小: {total_mb:.2f} MB")
    print(f"   错误数: {stats['errors']}")

    # 3. 按扩展名查找
    print("\n3️⃣ 查找 .py 文件:")
    py_files = walker.find_by_extension(".py")
    for f in py_files[:5]:  # 最多显示 5 个
        print(f"   {f}")
    if len(py_files) > 5:
        print(f"   ... 还有 {len(py_files) - 5} 个")

    # 4. 目录大小统计
    print("\n4️⃣ 目录大小统计:")
    size_stats = dir_size_stats(demo_path)
    print(f"   总大小: {size_stats['total_size']:,} 字节")
    print(f"   总文件: {size_stats['total_files']}")
    if size_stats['largest_file'][0]:
        largest_mb = size_stats['largest_file'][1] / (1024 * 1024)
        print(f"   最大文件: {size_stats['largest_file'][0]} "
              f"({largest_mb:.2f} MB)")
    print(f"   按扩展名:")
    for ext, size in sorted(size_stats['by_extension'].items(),
                            key=lambda x: -x[1])[:5]:
        print(f"     {ext}: {size:,} 字节")

    # 5. 带回调的遍历
    print("\n5️⃣ 带回调的遍历（仅打印 Python 文件）:")
    def print_py(path):
        if path.endswith(".py"):
            print(f"   🐍 {path}")

    walk_with_callback(demo_path, file_callback=print_py, max_depth=2)

    print("\n✅ 文件树遍历实战完成！")


if __name__ == "__main__":
    main()
