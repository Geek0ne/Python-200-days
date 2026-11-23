#!/usr/bin/env python3
"""
Day 167 — 文件监控（watchdog）· 04 实战：文件自动分类工具
========================================================================

需求（照抄真实业务场景）：
    谁往 inbox/ 里丢文件，就自动分类到 images/ docs/ archives/ data/ others/。

必须满足的 6 条生产要求：
    ① 每个文件只处理一次            —— 防抖 + 处理后从"待办表"移除
    ② 半成品文件必须等写完再动      —— .tmp/.part/.crdownload/.swp/~ 全部忽略
    ③ 重名不覆盖                    —— 自动追加时间戳后缀
    ④ 全程审计                      —— operations.jsonl 每行一条 JSON
    ⑤ 失败可追溯                    —— errors.log 记异常堆栈
    ⑥ 首次必须能空跑                —— --dry-run 只打印不移动

设计原理（为什么这么写，而不是那么写）：
    - **为什么用防抖而不是"等文件大小不变"**：
      大小不变需要两次 stat，且对"刚创建还没写的空文件"会误判（0 == 0）。
      防抖用"静默期"判定，逻辑简单、可解释，配合忽略临时扩展名已足够稳。
    - **为什么搬运动作要丢进线程池**：
      handler 跑在 watchdog 的 dispatch 单线程里；`shutil.move` 跨设备时是
      真实的数据拷贝（可能几秒~几分钟）。卡住 dispatch 线程 = 事件队列堆积。
    - **为什么用 shutil.move 而不是 os.rename**：
      os.rename 跨文件系统会抛 OSError(EXDEV)。inbox 常在 /tmp（tmpfs），
      目标目录在磁盘上，跨设备是常态。

运行：
    python3 04-auto-classify.py --self-test
    python3 04-auto-classify.py --inbox ./sandbox/inbox --out ./sandbox/out --duration 15
    python3 04-auto-classify.py --inbox ./sandbox/inbox --out ./sandbox/out --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

try:
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    from watchdog.observers import Observer
except ModuleNotFoundError:  # pragma: no cover - 环境缺依赖时的友好提示
    sys.stderr.write("❌ 缺少依赖 watchdog，请先 `pip install watchdog`\n")
    sys.exit(3)


# ---------------------------------------------------------------------------
# 1. 分类规则表
# ---------------------------------------------------------------------------
# ⚠ 顺序即优先级：长扩展名必须排在短扩展名前面，
#    否则 ".tar.gz" 会被 ".gz"（如果存在）先匹配走，落错桶。
RULES: list[tuple[str, str]] = [
    (".tar.gz", "archives"),
    (".tar.bz2", "archives"),
    (".tar.xz", "archives"),
    (".tgz", "archives"),
    (".zip", "archives"),
    (".rar", "archives"),
    (".7z", "archives"),
    (".jpg", "images"),
    (".jpeg", "images"),
    (".png", "images"),
    (".gif", "images"),
    (".webp", "images"),
    (".svg", "images"),
    (".pdf", "docs"),
    (".md", "docs"),
    (".txt", "docs"),
    (".docx", "docs"),
    (".doc", "docs"),
    (".pptx", "docs"),
    (".csv", "data"),
    (".tsv", "data"),
    (".json", "data"),
    (".xlsx", "data"),
    (".parquet", "data"),
    (".sqlite", "data"),
]

# 半成品标记：出现在"结尾"的，一律先忽略，等它改名/写完再来
PARTIAL_SUFFIX = (".tmp", ".part", ".crdownload", ".swp", ".swx", ".filepart", "~")
# 半成品标记：只要出现在"文件名里"就忽略（浏览器/编辑器常见的中间态）
PARTIAL_CONTAINS = (".part-", ".tmp.", "~$")


def classify(name: str) -> str:
    """按扩展名把文件名分到桶里；都不匹配则 others。

    >>> classify("a.TAR.GZ")
    'archives'
    >>> classify("noext")
    'others'
    """
    low = name.lower()
    for ext, bucket in RULES:
        if low.endswith(ext):
            return bucket
    return "others"


def is_partial(name: str) -> bool:
    low = name.lower()
    if low.endswith(PARTIAL_SUFFIX):
        return True
    return any(tag in low for tag in PARTIAL_CONTAINS)


def unique_target(dest_dir: Path, name: str) -> Path:
    """重名不覆盖：a.txt -> a-20260927-060000.txt -> a-20260927-060000-1.txt"""
    target = dest_dir / name
    if not target.exists():
        return target
    stem, suffix = os.path.splitext(name)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = dest_dir / f"{stem}-{stamp}{suffix}"
    n = 1
    while target.exists():
        target = dest_dir / f"{stem}-{stamp}-{n}{suffix}"
        n += 1
    return target


# ---------------------------------------------------------------------------
# 2. 待办表：防抖的载体
# ---------------------------------------------------------------------------
@dataclass
class Pending:
    """一个"看到过、但还没到点"的文件。"""

    first_seen: float
    last_seen: float
    seen_events: int = 0


class Debouncer:
    """静默期防抖：同一路径在 delay 秒内没有新事件，才认为"写完了"。

    为什么用 dict 而不是 threading.Timer？
      Timer 是"一次性闹钟"，事件洪峰下会创建成百上千个线程对象；
      dict + 后台巡检线程是 O(1) 内存、可观测（能打印待办表长度）。
    """

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self._lock = threading.Lock()
        self._pending: dict[str, Pending] = {}

    def touch(self, path: str, now: float | None = None) -> None:
        now = now if now is not None else time.monotonic()
        with self._lock:
            p = self._pending.get(path)
            if p is None:
                self._pending[path] = Pending(first_seen=now, last_seen=now, seen_events=1)
            else:
                p.last_seen = now
                p.seen_events += 1

    def ready(self, now: float | None = None) -> list[str]:
        """取出所有"静默超时"的路径，并从待办表移除（保证只处理一次）。"""
        now = now if now is not None else time.monotonic()
        with self._lock:
            done = [p for p, v in self._pending.items() if now - v.last_seen >= self.delay]
            for p in done:
                del self._pending[p]
            return done

    def drop(self, path: str) -> None:
        with self._lock:
            self._pending.pop(path, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._pending)


# ---------------------------------------------------------------------------
# 3. Handler：只做"登记"，重活交给线程池
# ---------------------------------------------------------------------------
class ClassifyHandler(FileSystemEventHandler):
    def __init__(self, deb: Debouncer, ignore_dirs: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.deb = deb
        self.ignore_dirs = ignore_dirs

    def on_any_event(self, event: FileSystemEvent) -> None:
        # 目录不分类；临时文件不登记（直接过滤，省掉后面的无用功）
        if event.is_directory:
            return
        # ⚠ 关键：moved 事件必须看 dest_path。
        #   编辑器/浏览器/下载器的典型姿势就是 "写临时名 → rename 成正式名"，
        #   若只看 src_path（b.tmp），这个文件会永远收不到处理 —— 因为它被当成临时文件丢了。
        src = event.dest_path or event.src_path
        if any(part in src for part in self.ignore_dirs):
            return
        name = os.path.basename(src)
        if is_partial(name) or name.startswith("."):
            return
        # 关键：把路径归一化成绝对路径，否则相对/绝对两份会各登记一次
        self.deb.touch(os.path.abspath(src))


# ---------------------------------------------------------------------------
# 4. 审计日志
# ---------------------------------------------------------------------------
class AuditLog:
    def __init__(self, path: Path, error_path: Path, dry_run: bool) -> None:
        self.path = path
        self.error_path = error_path
        self.dry_run = dry_run
        self._lock = threading.Lock()
        self.counts: dict[str, int] = {}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def write(self, record: dict) -> None:
        record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "dry_run": self.dry_run, **record}
        with self._lock:
            self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._fh.flush()
            key = record.get("action", "?")
            self.counts[key] = self.counts.get(key, 0) + 1

    def error(self, msg: str) -> None:
        with self._lock:
            with self.error_path.open("a", encoding="utf-8") as fh:
                fh.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")

    def close(self) -> None:
        self._fh.close()


# ---------------------------------------------------------------------------
# 5. 主流程
# ---------------------------------------------------------------------------
class Classifier:
    def __init__(self, inbox: Path, out: Path, delay: float, workers: int, dry_run: bool):
        self.inbox = inbox
        self.out = out
        self.dry_run = dry_run
        self.deb = Debouncer(delay)
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="mover")
        self.audit = AuditLog(out / "operations.jsonl", out / "errors.log", dry_run)
        self.stop_flag = threading.Event()

    def handle(self, path: str) -> None:
        """防抖到期后的真实处理，跑在线程池里。"""
        p = Path(path)
        try:
            if not p.exists():
                self.audit.write({"action": "skip_gone", "src": path})
                return
            bucket = classify(p.name)
            dest_dir = self.out / bucket
            dest_dir.mkdir(parents=True, exist_ok=True)
            target = unique_target(dest_dir, p.name)
            if self.dry_run:
                self.audit.write({"action": "dry_move", "src": path, "dst": str(target)})
                print(f"  [dry-run] {p.name} → {bucket}/")
                return
            shutil.move(str(p), str(target))  # 跨设备自动降级为"拷贝+删除"
            self.audit.write({"action": "moved", "src": path, "dst": str(target), "bucket": bucket})
            print(f"  ✅ {p.name} → {bucket}/")
        except Exception:  # 任何异常都不能杀死工作线程
            self.audit.error(f"move failed: {path}\n{traceback.format_exc()}")

    def sweep(self) -> None:
        """后台巡检线程：把到期的待办丢进线程池。"""
        while not self.stop_flag.is_set():
            for path in self.deb.ready():
                self.pool.submit(self.handle, path)
            time.sleep(0.1)

    def stop(self) -> None:
        self.stop_flag.set()
        # 收尾：把还剩在待办表里的全部处理掉，避免"退出瞬间丢文件"
        for path in self.deb.ready(now=time.monotonic() + 10 ** 9):
            self.pool.submit(self.handle, path)
        self.pool.shutdown(wait=True)
        self.audit.close()


def self_test() -> int:
    """不依赖 watchdog 运行时，验证纯函数逻辑。"""
    assert classify("a.tar.gz") == "archives", classify("a.tar.gz")
    assert classify("A.PNG") == "images"
    assert classify("x.json") == "data"
    assert classify("mystery.bin") == "others"
    assert classify("README") == "others"

    assert is_partial("a.txt.tmp") is True
    assert is_partial("a.crdownload") is True
    assert is_partial("a~") is True
    assert is_partial("~$a.docx") is True
    assert is_partial("a.txt") is False

    deb = Debouncer(0.2)
    deb.touch("/x/a.txt", now=100.0)
    assert deb.ready(now=100.1) == [], "静态期内不该就绪"
    assert deb.ready(now=100.25) == ["/x/a.txt"], "超时后应就绪"
    assert deb.ready(now=100.5) == [], "只处理一次"
    deb.touch("/x/b.txt", now=200.0)
    assert len(deb) == 1
    deb.drop("/x/b.txt")
    assert len(deb) == 0

    print("SELF-TEST OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 167 实战：文件自动分类工具")
    ap.add_argument("--inbox", default="./sandbox/inbox", help="待分类目录")
    ap.add_argument("--out", default="./sandbox/out", help="分类输出目录")
    ap.add_argument("--delay", type=float, default=0.8, help="防抖静默期（秒）")
    ap.add_argument("--workers", type=int, default=2, help="搬运线程数")
    ap.add_argument("--duration", type=float, default=0, help="运行时长（秒），0=直到 Ctrl+C")
    ap.add_argument("--dry-run", action="store_true", help="只打印不移动")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    inbox = Path(args.inbox).resolve()
    out = Path(args.out).resolve()
    inbox.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    print(f"👀 监控 {inbox}")
    print(f"📦 输出 {out}   dry_run={args.dry_run}  delay={args.delay}s")

    clf = Classifier(inbox, out, args.delay, args.workers, args.dry_run)
    handler = ClassifyHandler(clf.deb, ignore_dirs=(str(out), ".git"))
    observer = Observer()
    observer.schedule(handler, str(inbox), recursive=True)
    observer.start()

    sweeper = threading.Thread(target=clf.sweep, name="sweeper", daemon=True)
    sweeper.start()

    def _shutdown(signum, frame):  # noqa: ARG001
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    start = time.monotonic()
    try:
        while True:
            time.sleep(0.2)
            if args.duration and time.monotonic() - start >= args.duration:
                break
            if int(time.monotonic() - start) % 5 == 0 and abs(time.monotonic() - start) > 0.001:
                pass
    except KeyboardInterrupt:
        print("\n⏹ 收到中断，收尾处理待办…")
    finally:
        # 先停观察者（不再产生新事件），再 flush 待办，最后关池
        observer.stop()
        observer.join()
        clf.stop()

    print(f"📊 统计: {clf.audit.counts}")
    print(f"📝 审计: {out / 'operations.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
