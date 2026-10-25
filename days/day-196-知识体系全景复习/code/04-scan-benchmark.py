#!/usr/bin/env python3
"""
04-scan-benchmark.py — 四种目录扫描方式 + 三种行数统计方式的真实性能对比

为什么复习课还要讲性能：
    「知识地图」脚本每次都要扫 196 个目录、几百个 .py 文件。
    这不是理论问题：写法不同，同一台机器上差 3~10 倍。
    复习时最容易忘的也不是 API，而是「哪种写法在什么规模下才开始值得」。

被测对象（都对同一棵 days/ 树做同样的事：找到所有 .py，统计行数）：
    A. pathlib.Path.rglob          —— 最像人话，异常处理最舒服
    B. os.walk                     —— 老牌，目录剪枝最方便
    C. 手写 os.scandir 递归         —— 最少系统调用，代码最长
    D. glob.glob("**/*.py")        —— 一行搞定，但中间列表全在内存

行数统计三法：
    1. read_text().count("\n")     —— 解码 + 计数，中文安全
    2. read_bytes().count(b"\n")   —— 不解码，最快
    3. len(read_text().splitlines()) —— 语义最准（末尾无换行也算一行），最慢

用法：
    python3 04-scan-benchmark.py --self-test
    python3 04-scan-benchmark.py --repeat 5
"""

from __future__ import annotations

import argparse
import glob
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path


def walk_pathlib(root: Path) -> tuple[int, int]:
    files = lines = 0
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files += 1
        lines += path.read_bytes().count(b"\n")
    return files, lines


def walk_os_walk(root: Path) -> tuple[int, int]:
    files = lines = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            if name.endswith(".py"):
                files += 1
                with open(os.path.join(dirpath, name), "rb") as fh:
                    lines += fh.read().count(b"\n")
    return files, lines


def walk_scandir(root: Path) -> tuple[int, int]:
    files = lines = 0
    stack = [str(root)]
    while stack:
        current = stack.pop()
        with os.scandir(current) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name != "__pycache__":
                        stack.append(entry.path)
                elif entry.name.endswith(".py"):
                    files += 1
                    with open(entry.path, "rb") as fh:
                        lines += fh.read().count(b"\n")
    return files, lines


def walk_glob(root: Path) -> tuple[int, int]:
    files = lines = 0
    pattern = os.path.join(str(root), "**", "*.py")
    for name in glob.glob(pattern, recursive=True):
        if "__pycache__" in Path(name).parts:
            continue
        files += 1
        with open(name, "rb") as fh:
            lines += fh.read().count(b"\n")
    return files, lines


def bench(fn, root: Path, repeat: int) -> tuple[float, tuple[int, int]]:
    times = []
    result = (0, 0)
    for _ in range(repeat):
        started = time.perf_counter()
        result = fn(root)
        times.append((time.perf_counter() - started) * 1000)
    return statistics.median(times), result


def line_counting(root: Path) -> list[tuple[str, float, int]]:
    """三种计数法，I/O 全部提前做掉，只比较「解码 + 计数」本身。

    第一版把 read_bytes 放在计时器里、read_text 放在外面，测出 5.5ms vs 20.4ms，
    看起来「bytes 更慢」——其实是前者没算磁盘 I/O，属于假数据。
    公平做法：先把所有文件读成 bytes（不计时），再分别计时。
    """
    targets = [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]
    blobs = [p.read_bytes() for p in targets]
    results = []
    for name, fn in (
        ("bytes.count(b'\\n')", lambda b: b.count(b"\n")),
        ("decode().count('\\n')", lambda b: b.decode("utf-8", "replace").count("\n")),
        ("decode().splitlines()", lambda b: len(b.decode("utf-8", "replace").splitlines())),
    ):
        started = time.perf_counter()
        total = sum(fn(blob) for blob in blobs)
        results.append((name, (time.perf_counter() - started) * 1000, total))
    return results


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for i in range(5):
            d = root / f"d{i}" / "__pycache__"
            d.mkdir(parents=True)
            (d / "skip.py").write_text("# x\n" * 100, encoding="utf-8")
            (root / f"d{i}" / "a.py").write_text("# 中文\n" * 10, encoding="utf-8")
            (root / f"d{i}" / "b.py").write_text("print(1)", encoding="utf-8")  # 无结尾换行
        counts = {name: fn(root) for name, fn in (
            ("pathlib", walk_pathlib), ("os.walk", walk_os_walk),
            ("scandir", walk_scandir), ("glob", walk_glob))}
        assert counts["pathlib"] == (10, 50), counts["pathlib"]
        assert len(set(counts.values())) == 1, counts
        # 行数语义差异：b.py 没有结尾换行，count("\n") 少算 1 行
        rows = line_counting(root)
        assert rows[0][2] == 50 and rows[1][2] == 50 and rows[2][2] == 55, rows
        print("✅ self-test passed: 四种扫描结果一致，行数语义差异符合预期（50 vs 55）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="目录扫描与行数统计基准")
    parser.add_argument("--root", default=str(Path.home() / "code" / "Learn-Python" / "days"))
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()

    root = Path(args.root)
    print(f"目标：{root}（{args.repeat} 次取中位数）")
    print(f"{'方式':<18}{'中位耗时(ms)':>14}{'文件':>7}{'行数':>10}")
    base = None
    for name, fn in (("pathlib.rglob", walk_pathlib), ("os.walk", walk_os_walk),
                     ("os.scandir 手写", walk_scandir), ("glob recursive", walk_glob)):
        ms, (files, lines) = bench(fn, root, args.repeat)
        base = base or ms
        print(f"{name:<18}{ms:>14.1f}{files:>7}{lines:>10,}   ×{base / ms:.2f}")

    print("\n行数统计三法（同一批文件，单位 ms）")
    for name, ms, total in line_counting(root):
        print(f"{name:<22}{ms:>8.1f}  总行数 {total:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
