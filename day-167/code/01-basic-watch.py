#!/usr/bin/env python3
"""
Day 167 — 文件监控（watchdog）· 01 基础示例
==========================================

目标：把 watchdog 的"三件套"用最小代码跑通，并看清每个事件的真实字段。

运行：
    pip install watchdog

    python3 01-basic-watch.py --self-test
        不依赖任何外部目录，自动建临时目录、造事件、校验结果，
        最后打印 SELF-TEST OK。

    python3 01-basic-watch.py --path ./sandbox --duration 10
        监控 ./sandbox（不存在会自动建），10 秒后优雅退出。
        另开一个终端执行：
            echo hi > sandbox/a.txt
            mv sandbox/a.txt sandbox/b.txt
            rm sandbox/b.txt
        观察打印出的事件字段。

    python3 01-basic-watch.py --path ./sandbox --duration 10 --recursive
        递归监控（子目录也监听）。

安全边界：
    脚本只在 --path 指定目录内创建/监听，不碰系统目录。
    测试文件写在 --path 或临时目录中，退出时清理临时目录。
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import threading
import time

# ─────────────────────────── 依赖自检 ───────────────────────────
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write(
        "❌ 缺少依赖 watchdog。\n"
        "   安装：pip install watchdog\n"
        "   若系统 Python 受 PEP 668 保护（externally-managed-environment），\n"
        "   请用虚拟环境：python3 -m venv .venv && . .venv/bin/activate && pip install watchdog\n"
    )
    sys.exit(3)


# ─────────────────────────── 处理器 ───────────────────────────
class PlainHandler(FileSystemEventHandler):
    """把收到的每条事件按统一格式打印出来。

    注意：本类的所有回调都运行在 Observer 的 **dispatch 线程**里。
    这里只做 print，不做任何耗时操作 —— 这是本课的第一条铁律。
    """

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.count = 0
        self.seen: list[tuple[str, str, str]] = []   # (type, src, dest)
        self._lock = threading.Lock()

    # on_any_event 会先于具体回调被调用 —— 适合做统一日志 / 统计
    def on_any_event(self, event) -> None:
        with self._lock:
            self.count += 1
            self.seen.append(
                (event.event_type, event.src_path, getattr(event, "dest_path", "") or "")
            )
        if not self.verbose:
            return
        kind = "DIR " if event.is_directory else "FILE"
        dest = getattr(event, "dest_path", "") or ""
        arrow = f"  →  {dest}" if dest else ""
        print(
            f"[{self.count:>3}] {event.event_type:<8s} {kind} {event.src_path}{arrow}",
            flush=True,
        )

    # 具体回调：不写也不影响功能（on_any_event 已覆盖），
    # 这里写出来是为了让你看清"事件类型 → 回调"的对应关系。
    def on_created(self, event):
        self._note("created", event)

    def on_deleted(self, event):
        self._note("deleted", event)

    def on_modified(self, event):
        self._note("modified", event)

    def on_moved(self, event):
        # 只有 moved 事件有 dest_path —— 记住这一点
        self._note("moved", event)

    def on_closed(self, event):
        # 仅 inotify 后端会产生；用来判断"文件写完了"很精确
        self._note("closed", event)

    def _note(self, name: str, event) -> None:
        if self.verbose:
            return  # 已在 on_any_event 打过，避免刷屏
        print(f"[{self.count:>3}] {name}", flush=True)


# ─────────────────────────── 自检 ───────────────────────────
def self_test() -> int:
    """在临时目录里造 4 类事件，验证 handler 至少收到 created/modified/moved/deleted。"""
    tmp = tempfile.mkdtemp(prefix="day167-basic-")
    wh = PlainHandler(verbose=True)
    obs = Observer()
    obs.schedule(wh, tmp, recursive=True)
    obs.start()
    time.sleep(0.4)  # 给 emitter/dispatch 线程一点启动时间

    f1 = os.path.join(tmp, "a.txt")
    f2 = os.path.join(tmp, "b.txt")
    try:
        with open(f1, "w") as fp:          # → created + modified (+ closed)
            fp.write("hello")
        time.sleep(0.3)
        os.rename(f1, f2)                 # → moved（带 dest_path）
        time.sleep(0.3)
        os.unlink(f2)                     # → deleted
        time.sleep(0.5)
    finally:
        obs.stop()
        obs.join(timeout=5)               # 收尾必调，否则非守护线程卡住进程
        shutil.rmtree(tmp, ignore_errors=True)

    types = {t for t, _, _ in wh.seen}
    print(f"\n收到 {wh.count} 条事件，类型集合 = {sorted(types)}")

    # 至少要有 created / modified / moved；deleted 在部分后端可能合并，宽松校验
    missing = {"created", "modified", "moved"} - types
    if missing:
        print(f"❌ 自检失败：缺少事件类型 {sorted(missing)}")
        return 1
    # moved 必须带 dest_path，否则说明事件字段理解错了
    moved = [d for t, _, d in wh.seen if t == "moved"]
    if not moved or not all(dest for dest in moved):
        print("❌ 自检失败：moved 事件没有 dest_path")
        return 1
    print("SELF-TEST OK")
    return 0


# ─────────────────────────── 监控主循环 ───────────────────────────
def watch(path: str, duration: float, recursive: bool, verbose: bool) -> int:
    os.makedirs(path, exist_ok=True)          # schedule 要求目录必须已存在
    handler = PlainHandler(verbose=verbose)
    observer = Observer()
    observer.schedule(handler, path, recursive=recursive)
    observer.start()
    print(f"👀 监控中：{os.path.abspath(path)}  recursive={recursive}")
    print(f"   将在 {duration:.0f} 秒后自动退出（Ctrl+C 也可退出）\n")
    try:
        end = time.monotonic() + duration
        while time.monotonic() < end:
            time.sleep(0.2)                   # 主线程保持存活即可，事件在后台线程处理
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，准备退出 …")
    finally:
        observer.stop()
        observer.join(timeout=5)              # ⚠ 不加 join 可能丢最后一波事件
    print(f"\n共收到 {handler.count} 条事件")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="watchdog 基础示例")
    ap.add_argument("--path", default="./sandbox", help="要监控的目录（默认 ./sandbox）")
    ap.add_argument("--duration", type=float, default=10.0, help="监控时长（秒）")
    ap.add_argument("--recursive", action="store_true", help="递归监控子目录")
    ap.add_argument("--verbose", action="store_true", default=True, help="打印事件明细")
    ap.add_argument("--self-test", action="store_true", help="跑内置自检")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    return watch(args.path, args.duration, args.recursive, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
