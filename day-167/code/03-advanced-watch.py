#!/usr/bin/env python3
"""
Day 167 — 文件监控（watchdog）· 03 进阶：防抖 / 规则过滤 / 事件聚合 / 线程池
==========================================================================

生产可用的文件监控，只靠"事件来了就干事"是不够的，必须补上四件东西：

    ① 过滤（Filter）      —— 忽略临时文件、隐藏目录、不关心的扩展名
    ② 归一化（Normalize） —— 所有路径统一成 abspath，防抖 key 才准
    ③ 防抖（Debounce）    —— 一次"保存"只触发一次业务动作
    ④ 卸载重活（Offload） —— handler 只入队，重活交给线程池

本脚本把这四件都实现了，可以直接抄进项目。

运行：
    python3 03-advanced-watch.py --self-test
    python3 03-advanced-watch.py --path ./sandbox --delay 0.8 --duration 15
    python3 03-advanced-watch.py --path ./sandbox --backend polling --poll-timeout 2
    python3 03-advanced-watch.py --path ./sandbox --include '.*\\.csv$' --workers 4
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ModuleNotFoundError:
    sys.stderr.write("❌ 缺少依赖 watchdog，请先 `pip install watchdog`\n")
    sys.exit(3)


# ═══════════════════════ ① 过滤器 ═══════════════════════
@dataclass
class EventFilter:
    """路径过滤规则。

    为什么默认忽略这些：
        .tmp/.swp/.part/.crdownload  → 写入中的半成品
        ~ / #...#                    → 备份文件（Emacs 用 #x#，vim 用 x~）
        .git / __pycache__ / node_modules → 会产生海量无用事件
    注意 fnmatch 的 `*` 会匹配路径分隔符，这里只对**文件名**做匹配。
    """

    ignore_suffixes: tuple[str, ...] = (
        ".tmp", ".temp", ".swp", ".swx", ".part", ".crdownload",
        ".filepart", ".partial", "~",
    )
    ignore_names: tuple[str, ...] = (".DS_Store", "Thumbs.db")
    ignore_dirs: tuple[str, ...] = (
        ".git", "__pycache__", "node_modules", ".venv", "venv", ".idea",
    )
    include_regex: str | None = None
    _inc: re.Pattern | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.include_regex:
            self._inc = re.compile(self.include_regex)

    def accept(self, path: str) -> bool:
        parts = os.path.normpath(path).split(os.sep)
        if any(d in self.ignore_dirs for d in parts):
            return False
        name = os.path.basename(path)
        if not name or name in self.ignore_names:
            return False
        if name.startswith("#") and name.endswith("#"):
            return False
        if any(name.endswith(s) for s in self.ignore_suffixes):
            return False
        # 明确的目标文件名像 .env / .gitignore —— 允许，但以点开头的临时文件忽略
        if name.startswith(".") and not name.startswith((".env", ".gitignore", ".config")):
            return False
        if self._inc and not self._inc.search(path):
            return False
        return True


# ═══════════════════════ ② 防抖器 ═══════════════════════
class Debouncer:
    """"静默 T 秒后执行一次"的防抖器（线程安全）。

    使用要点（不看就会写出偶发并发的 bug）：
      · 每个 key 独立计时，key 用 abspath
      · timer 已被 cancel 后仍可能已经在跑 → _fire 里先把自己摘掉再执行
      · 必须加锁：trigger 在 dispatch 线程，_fire 在 Timer 线程
      · flush() 用于退出前"把待触发的都立即触发"，避免丢最后一波
    """

    def __init__(self, delay: float, action) -> None:
        self.delay = delay
        self.action = action
        self.lock = threading.Lock()
        # key -> (timer, token)。token 只用于"这枚计时器是否仍是当前登记的那枚"
        self.timers: dict[str, tuple[threading.Timer, object]] = {}

    def trigger(self, key: str, *args) -> None:
        with self.lock:
            old = self.timers.pop(key, None)
            if old is not None:
                old[0].cancel()
            token = object()                     # 独一无二的"世代"标记
            t = threading.Timer(self.delay, self._fire, args=(key, token, args))
            t.daemon = True
            self.timers[key] = (t, token)
            t.start()

    def _fire(self, key: str, token: object, args: tuple) -> None:
        """计时器到期。

        为什么必须比对 token：
          `Timer.cancel()` 对"已经开始执行"的计时器无效 —— 它照样会调用 _fire。
          若期间又来了新事件（trigger 会登记新 token），或 flush 已接管，
          这枚"幽灵计时器"再跑一次 business action，就会出现"一次保存触发两次"。
          token 比对 = 让过期世代安静地退出。
        """
        with self.lock:
            cur = self.timers.get(key)
            if cur is None or cur[1] is not token:
                return
            del self.timers[key]
        self.action(key, *args)

    def flush(self) -> int:
        """退出前调用：取消所有定时器并**立即**执行，返回冲刷条数。"""
        with self.lock:
            pending = list(self.timers.items())
            self.timers.clear()
        for key, (t, _token) in pending:
            t.cancel()
            self.action(key, "flush")
        return len(pending)

    def pending(self) -> int:
        with self.lock:
            return len(self.timers)


# ═══════════════════════ ③ 聚合统计 ═══════════════════════
@dataclass
class Stats:
    raw: dict[str, int] = field(default_factory=dict)
    filtered_out: int = 0
    settled: int = 0
    processed: int = 0
    failed: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def bump(self, key: str, n: int = 1) -> None:
        with self._lock:
            self.raw[key] = self.raw.get(key, 0) + n

    def report(self) -> dict:
        with self._lock:
            return {
                "raw_events": dict(sorted(self.raw.items())),
                "raw_total": sum(self.raw.values()),
                "filtered_out": self.filtered_out,
                "settled": self.settled,
                "processed": self.processed,
                "failed": self.failed,
            }


# ═══════════════════════ ④ 处理器 ═══════════════════════
class DebouncedHandler(FileSystemEventHandler):
    """过滤 → 归一化 → 防抖 → 线程池卸载，四步一条龙。

    这个 handler 的每个回调都**非常快**（纳秒级到微秒级），
    真正的耗时逻辑在 action()，跑在线程池里。
    """

    def __init__(
        self,
        flt: EventFilter,
        delay: float,
        workers: int,
        stats: Stats,
        action=None,
    ) -> None:
        self.flt = flt
        self.stats = stats
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="worker")
        self.deb = Debouncer(delay, self._on_settled)
        self.action = action or self._default_action

    # —— 统一入口：所有事件先到这里 ——
    def on_any_event(self, event) -> None:
        self.stats.bump(event.event_type)
        if event.is_directory:
            # 目录事件仅计数；目录本身的 created 可用于"兜底扫描"（见 README 陷阱 3）
            return
        raw = event.dest_path or event.src_path
        path = os.path.abspath(os.path.realpath(raw))     # 归一化：防抖 key 必须一致
        if not self.flt.accept(path):
            self.stats.filtered_out += 1
            return
        self.deb.trigger(path, event.event_type)

    def _on_settled(self, path: str, last_event_type: str) -> None:
        """静默 delay 秒后触发：此时文件应该是最终稳定版本。"""
        self.stats.settled += 1
        self.pool.submit(self._run_action, path, last_event_type)

    def _run_action(self, path: str, last_event_type: str) -> None:
        try:
            self.action(path, last_event_type)
            self.stats.processed += 1
        except Exception as exc:                      # 单个文件失败不能拖垮整个监控
            self.stats.failed += 1
            print(f"   ⚠ 处理失败 {path}: {type(exc).__name__}: {exc}", flush=True)

    def _default_action(self, path: str, last_event_type: str) -> None:
        size = os.path.getsize(path) if os.path.exists(path) else -1
        print(f"   ✅ settled[{last_event_type}] {path}  size={size}", flush=True)

    # —— 收尾 ——
    def shutdown(self) -> int:
        flushed = self.deb.flush()          # 把还没触发的补上，避免丢事件
        self.pool.shutdown(wait=True)
        return flushed


# ═══════════════════════ 自检 ═══════════════════════
def self_test() -> int:
    import tempfile

    print("自检 1：EventFilter 规则")
    flt = EventFilter(include_regex=r".*\.csv$")
    cases = {
        "/data/a.csv": True,
        "/data/a.csv.tmp": False,
        "/data/.a.csv": False,
        "/data/a.txt": False,
        "/data/__pycache__/a.csv": False,
        "/data/node_modules/a.csv": False,
        "/data/a.csv~": False,
    }
    ok1 = True
    for path, want in cases.items():
        got = flt.accept(path)
        flag = "✅" if got == want else "❌"
        ok1 &= got == want
        print(f"   {flag} accept({path!r}) = {got}（期望 {want}）")

    print("\n自检 2：Debouncer 把 20 次 trigger 收敛成 1 次动作")
    fired: list[tuple] = []
    deb = Debouncer(0.3, lambda k, *a: fired.append((k, a)))
    for i in range(20):
        deb.trigger("/tmp/x.txt", f"ev{i}")
        time.sleep(0.01)                     # 共 0.2s，短于 0.3s → 应被不断推迟
    ok2 = deb.pending() == 1
    time.sleep(0.6)
    ok2 &= len(fired) == 1
    print(f"   触发次数写入 = 20，实际执行 = {len(fired)}，pending 检查 = {ok2}")

    print("\n自检 3：不同 key 互不干扰")
    fired.clear()
    deb2 = Debouncer(0.25, lambda k, *a: fired.append((k, a)))
    deb2.trigger("/tmp/a.txt", "c")
    deb2.trigger("/tmp/b.txt", "c")
    time.sleep(0.6)
    ok3 = len(fired) == 2
    print(f"   两个不同 key → 执行 {len(fired)} 次（期望 2）")

    print("\n自检 4：端到端 —— 真实文件事件被过滤 + 防抖 + 线程池处理")
    with tempfile.TemporaryDirectory(prefix="day167-adv-") as tmp:
        stats = Stats()
        seen: list[tuple[str, str]] = []
        seen_lock = threading.Lock()

        def record(path: str, last_event_type: str) -> None:   # 注入式 action，便于断言
            with seen_lock:
                seen.append((os.path.basename(path), last_event_type))

        handler = DebouncedHandler(EventFilter(), delay=0.3, workers=2, stats=stats, action=record)
        obs = Observer()
        obs.schedule(handler, tmp, recursive=True)
        obs.start()
        time.sleep(0.4)
        # 1) 正常写一个文件（多次 modified 应被防抖成 1 次 settled）
        for i in range(5):
            with open(os.path.join(tmp, "real.txt"), "a") as fp:
                fp.write(f"line{i}\n")
            time.sleep(0.05)
        # 2) 造一个临时文件，应被过滤掉
        with open(os.path.join(tmp, "junk.txt.tmp"), "w") as fp:
            fp.write("half")
        # 等待：所有定时器都已到期并执行完（delay * 5 留足裕量）
        time.sleep(1.6)
        obs.stop()
        obs.join(timeout=5)
        flushed = handler.shutdown()
        rep = stats.report()
        names = {n for n, _ in seen}
        print(f"   统计：{rep}  冲刷={flushed}")
        print(f"   实际处理：{seen}")
        # 断言 4 件事：
        #   ① 只处理 real.txt（junk.txt.tmp 被过滤）
        #   ② 全程无失败
        #   ③ 有事件被过滤掉（证明过滤器生效）
        #   ④ 原始事件数 >> 处理数（证明防抖确实收敛了，而不是每事件一次）
        ok4 = (
            names == {"real.txt"}
            and rep["failed"] == 0
            and rep["filtered_out"] > 0
            and rep["raw_total"] > rep["processed"]
        )
        if not ok4:
            print("   ❌ 期望：只处理 real.txt、无失败、有过滤、原始事件数 > 处理数")

    if ok1 and ok2 and ok3 and ok4:
        print("\nSELF-TEST OK")
        return 0
    print("\nSELF-TEST FAILED")
    return 1


# ═══════════════════════ 运行 ═══════════════════════
def run(args) -> int:
    os.makedirs(args.path, exist_ok=True)
    flt = EventFilter(include_regex=args.include)
    stats = Stats()
    handler = DebouncedHandler(flt, args.delay, args.workers, stats)

    if args.backend == "polling":
        from watchdog.observers.polling import PollingObserver
        observer = PollingObserver(timeout=args.poll_timeout)
        print(f"🔁 使用 PollingObserver(timeout={args.poll_timeout}s) —— 网络盘/容器场景")
    else:
        observer = Observer()
        print("⚡ 使用 InotifyObserver —— 本机文件系统")

    watch = observer.schedule(handler, args.path, recursive=args.recursive)
    observer.start()
    print(f"👀 监控 {os.path.abspath(args.path)}  recursive={args.recursive}")
    print(f"   防抖 {args.delay}s · 线程池 {args.workers} · 时长 {args.duration}s")

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())

    end = time.monotonic() + args.duration
    try:
        while not stop.is_set() and time.monotonic() < end:
            stop.wait(0.2)
    finally:
        observer.unschedule(watch) if args.unschedule_first else None
        observer.stop()
        observer.join(timeout=5)
        flushed = handler.shutdown()

    rep = stats.report()
    print("\n📊 本次监控统计")
    for k, v in rep.items():
        if k == "raw_events":
            print(f"   原始事件分布: {v}")
        else:
            print(f"   {k}: {v}")
    print(f"   退出前冲刷(flush)的待处理条目: {flushed}")
    print("\n解读提示：")
    print("   · raw_total 远大于 settled → 防抖在起作用（正常，符合预期）")
    print("   · filtered_out > 0 → 忽略规则拦下了临时/无关文件")
    print("   · failed > 0 → 去看上面的 ⚠ 行")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="watchdog 进阶示例：防抖/过滤/聚合/线程池")
    ap.add_argument("--path", default="./sandbox")
    ap.add_argument("--duration", type=float, default=15.0)
    ap.add_argument("--delay", type=float, default=0.8, help="防抖静默窗口（秒）")
    ap.add_argument("--workers", type=int, default=2, help="工作线程数")
    ap.add_argument("--recursive", action="store_true", default=True)
    ap.add_argument("--backend", choices=["inotify", "polling"], default="inotify")
    ap.add_argument("--poll-timeout", type=float, default=2.0, help="PollingObserver 扫描间隔")
    ap.add_argument("--include", default=None, help="只处理匹配该正则的路径")
    ap.add_argument("--unschedule-first", action="store_true", help="退出前先取消 watch")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
