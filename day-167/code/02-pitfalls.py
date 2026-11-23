#!/usr/bin/env python3
"""
Day 167 — 文件监控（watchdog）· 02 常见陷阱与避坑
================================================

本脚本把 6 个"新手必踩"的坑**亲手复现一遍**，每条都给出 ❌ 错误写法 与 ✅ 修复写法。
所有实验都在 `tempfile.mkdtemp()` 里进行，退出自动清理。

运行：
    python3 02-pitfalls.py --self-test     # 自动跑完 6 条并断言，末尾 SELF-TEST OK
    python3 02-pitfalls.py                 # 同上，但打印更啰嗦
    python3 02-pitfalls.py --only 3        # 只跑第 3 条

陷阱清单：
    1. 事件类型 ≠ 你想的那几种：opened / closed 也会来，目录也会 modified
    2. vim/编辑器的原子写：一次"保存"产生多条事件，处理到半成品
    3. 递归监控下，新建目录里的文件漏事件（watch 补不上）
    4. handler 里做重活 → 阻塞 dispatch 线程 → 事件延迟甚至溢出
    5. 路径归一化与 dest_path：相对路径、符号链接、只有 moved 有 dest
    6. schedule 不存在的路径抛 OSError；inotify watch 配额耗尽
"""

from __future__ import annotations

import os
import queue
import shutil
import sys
import tempfile
import threading
import time

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ModuleNotFoundError:
    sys.stderr.write("❌ 缺少依赖 watchdog，请先 `pip install watchdog`\n")
    sys.exit(3)


# ═════════════════════════ 通用小工具 ═════════════════════════
class Recorder(FileSystemEventHandler):
    """线程安全的"记录仪"：只记录，不处理 —— 用来观察原始事件流。"""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.events: list[tuple[str, str, str, bool]] = []
        self.times: list[float] = []

    def on_any_event(self, event) -> None:
        with self.lock:
            self.events.append(
                (
                    event.event_type,
                    event.src_path,
                    getattr(event, "dest_path", "") or "",
                    event.is_directory,
                )
            )
            self.times.append(time.monotonic())

    def count(self) -> int:
        with self.lock:
            return len(self.events)

    def types(self) -> set[str]:
        with self.lock:
            return {e[0] for e in self.events}


class SlowHandler(FileSystemEventHandler):
    """❌ 反例：在 handler 里做耗时操作。"""

    def __init__(self, work_seconds: float) -> None:
        self.work = work_seconds
        self.latencies: list[float] = []

    def on_created(self, event):
        created_at = time.monotonic()
        time.sleep(self.work)                       # 模拟"转码/上传/解析"
        self.latencies.append(time.monotonic() - created_at)


class QueuedHandler(FileSystemEventHandler):
    """✅ 正解：handler 只入队，重活交给工作线程。"""

    def __init__(self, work_seconds: float) -> None:
        self.work = work_seconds
        self.q: queue.Queue = queue.Queue()
        self.latencies: dict[str, float] = {}
        self.enqueued_at: dict[str, float] = {}
        self._stop = threading.Event()
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def on_created(self, event):
        if event.is_directory:
            return
        path = os.path.abspath(event.src_path)
        self.enqueued_at[path] = time.monotonic()      # 入队瞬间打点
        self.q.put(path)                               # 立即返回，dispatch 线程不被拖住

    def _run(self):
        while not self._stop.is_set():
            try:
                path = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            time.sleep(self.work)                      # 重活在**自己的工作线程**里
            self.latencies[path] = time.monotonic() - self.enqueued_at[path]

    def stop(self):
        self._stop.set()
        self.worker.join(timeout=2)


def _run_observer(path: str, handler, recursive: bool, body, settle: float = 0.6):
    """启动 observer → 执行 body() → 等待 settle → 优雅停止。"""
    obs = Observer()
    obs.schedule(handler, path, recursive=recursive)
    obs.start()
    time.sleep(0.4)
    try:
        body()
        time.sleep(settle)
    finally:
        obs.stop()
        obs.join(timeout=5)


# ═════════════════════════ 陷阱 1 ═════════════════════════
def pitfall_1(tmp: str) -> bool:
    print("\n" + "=" * 72)
    print("陷阱 1：事件类型不止 created/modified/deleted/moved")
    print("=" * 72)
    rec = Recorder()
    target = os.path.join(tmp, "p1")
    os.makedirs(target, exist_ok=True)

    def body():
        with open(os.path.join(target, "x.txt"), "w") as fp:
            fp.write("data")

    _run_observer(target, rec, False, body)

    for t, src, dest, is_dir in rec.events:
        print(f"   {t:<9s} dir={is_dir!s:<5s} {os.path.basename(src)}")
    got = rec.types()
    print(f"\n   实际收到的类型集合：{sorted(got)}")
    print("   ❌ 错误认知：以为只有 4 种事件，直接写 `if event.event_type == 'created'`")
    print("   ✅ 正解：")
    print("      · 用 on_any_event 做统一入口，再按需分派")
    print("      · 目录也会 modified（子项增删导致 mtime 变）→ 先判 is_directory")
    print("      · opened/closed 只在部分后端出现，业务逻辑别依赖它们")
    # 断言：必须能观察到"目录的 modified"这一现象
    dir_mod = any(t == "modified" and d for t, _, _, d in rec.events)
    if not dir_mod:
        print("   ⚠ 本次未观察到目录 modified（后端差异），不影响结论")
    return rec.count() > 0


# ═════════════════════════ 陷阱 2 ═════════════════════════
def pitfall_2(tmp: str) -> bool:
    print("\n" + "=" * 72)
    print("陷阱 2：编辑器的原子写 → 一次保存 = 多条事件 + 半成品文件")
    print("=" * 72)
    target = os.path.join(tmp, "p2")
    os.makedirs(target, exist_ok=True)
    final = os.path.join(target, "report.csv")

    processed: list[str] = []

    class NaiveHandler(FileSystemEventHandler):
        def on_any_event(self, event):
            if event.is_directory:
                return
            # ❌ 只要事件到了就当"文件写好了"处理
            processed.append(f"{event.event_type}:{os.path.basename(event.src_path)}")

    rec = Recorder()
    _run_observer(target, rec, False, lambda: _atomic_save(final))

    # 用 Recorder 记录的真实事件流水，喂给 NaiveHandler 看会发生什么
    for t, src, dest, is_dir in rec.events:
        if is_dir:
            continue
        processed.append(f"{t}:{os.path.basename(src)}")

    print("   模拟编辑器保存的动作：写 report.csv.tmp → rename 成 report.csv")
    print(f"   原始事件流水（{len(processed)} 条）：")
    for item in processed:
        print(f"     - {item}")

    tmp_events = [p for p in processed if ".tmp" in p]
    print("\n   ❌ 错误写法：每条事件都触发一次业务动作")
    print(f"      → 触发 {len(processed)} 次，其中 {len(tmp_events)} 次作用在 .tmp 临时文件上（半成品！）")
    print("   ✅ 正解：")
    print("      · 先按名字过滤：.tmp/.swp/.swx/~/.part/.crdownload/#...# 一律忽略")
    print("      · 再对同一路径做防抖（静默 T 秒），只处理最终稳定版本")
    print("      · 需要更精确：依赖 on_closed，或检查文件大小连续两次不变")
    bad = len(tmp_events) > 0
    if not bad:
        print("   ⚠ 本次未捕捉到 .tmp 事件（时序差异），结论不变")
    return True


def _atomic_save(final: str) -> None:
    tmp = final + ".tmp"
    with open(tmp, "w") as fp:
        fp.write("a,b,c\n1,2,3\n")
    os.replace(tmp, final)      # POSIX 原子替换，正是编辑器的做法


# ═════════════════════════ 陷阱 3 ═════════════════════════
def pitfall_3(tmp: str) -> bool:
    print("\n" + "=" * 72)
    print("陷阱 3：递归监控下，新建目录里的文件可能漏事件")
    print("=" * 72)
    target = os.path.join(tmp, "p3")
    os.makedirs(target, exist_ok=True)
    rec = Recorder()

    newdir = os.path.join(target, "incoming")
    created_files = []

    def body():
        os.makedirs(newdir)
        # ⚠ 关键：目录刚建好就立刻写文件，此时 watchdog 可能还没补上 watch
        for i in range(3):
            p = os.path.join(newdir, f"f{i}.txt")
            with open(p, "w") as fp:
                fp.write(str(i))
            created_files.append(p)
            time.sleep(0.05)

    _run_observer(target, rec, True, body, settle=1.0)

    seen = {os.path.abspath(e[1]) for e in rec.events if not e[3]}
    missed = [p for p in created_files if os.path.abspath(p) not in seen]
    print(f"   新建目录：{os.path.basename(newdir)}，随后写入 {len(created_files)} 个文件")
    print(f"   收到的事件：{rec.count()} 条；漏掉的写入：{len(missed)} 个")
    for p in missed:
        print(f"     ❌ 漏：{os.path.basename(p)}")
    print("\n   根因：内核 inotify 不支持递归，watchdog 要在收到 IN_CREATE(is_dir) 后")
    print("         **异步**补 watch；补上之前发生的写入，内核根本不知道有监听者。")
    print("   ✅ 缓解办法（可叠加）：")
    print("      ① 让生产者先建完目录、sleep 一拍，再放文件（治标）")
    print("      ② 收到目录 created 事件后，主动 os.walk 一次做**兜底扫描**（治本，下面演示）")
    print("      ③ 对关键目录改用 PollingObserver（放弃事件，换确定性）")

    # 兜底扫描：目录 created 时立刻全量扫一遍，把漏掉的补回来
    catch_up = set()
    if os.path.isdir(newdir):
        for name in os.listdir(newdir):
            catch_up.add(os.path.abspath(os.path.join(newdir, name)))
    recovered = [p for p in created_files if os.path.abspath(p) in catch_up]
    print(f"   → 兜底扫描找回：{len(recovered)}/{len(created_files)} 个文件 ✅")
    return len(recovered) == len(created_files)


# ═════════════════════════ 陷阱 4 ═════════════════════════
def pitfall_4(tmp: str) -> bool:
    print("\n" + "=" * 72)
    print("陷阱 4：handler 里做重活 → 阻塞 dispatch 线程 → 事件延迟/溢出")
    print("=" * 72)
    work = 0.15
    n = 4

    def make_files(d: str):
        def body():
            for i in range(n):
                with open(os.path.join(d, f"s{i}.txt"), "w") as fp:
                    fp.write("x")
        return body

    d1 = os.path.join(tmp, "p4-slow")
    os.makedirs(d1, exist_ok=True)
    slow = SlowHandler(work)
    t0 = time.monotonic()
    _run_observer(d1, slow, False, make_files(d1), settle=work * n + 0.5)
    slow_total = time.monotonic() - t0

    d2 = os.path.join(tmp, "p4-fast")
    os.makedirs(d2, exist_ok=True)
    fast = QueuedHandler(work)
    t1 = time.monotonic()
    _run_observer(d2, fast, False, make_files(d2), settle=0.5)
    fast_total = time.monotonic() - t1
    fast.stop()

    print(f"   ❌ handler 内 sleep({work}s)：处理 {n} 个文件，observer 停止前共耗时 "
          f"{slow_total:.2f}s（事件在 dispatch 线程里排队）")
    print(f"   ✅ 入队 + 工作线程：observer 主体在 {fast_total:.2f}s 内就停止，"
          f"事后工作线程仍在消费队列")
    print(f"      慢 handler 最后一条延迟 ≈ {slow.latencies[-1]:.3f}s"
          if slow.latencies else "      （未收到事件）")
    print(f"      快 handler 延迟记录 = "
          f"{ {os.path.basename(k): round(v, 3) for k, v in fast.latencies.items()} }")
    print("\n   为什么严重：dispatch 线程只有一个；inotify 队列容量有限，")
    print("              handler 变慢 = 消费变慢 = 队列堆积 = 溢出丢事件（还很难发现）。")
    return slow_total >= fast_total


# ═════════════════════════ 陷阱 5 ═════════════════════════
def pitfall_5(tmp: str) -> bool:
    print("\n" + "=" * 72)
    print("陷阱 5：路径归一化 与 dest_path 只有 moved 才有")
    print("=" * 72)
    base = os.path.join(tmp, "p5")
    os.makedirs(base, exist_ok=True)
    src = os.path.join(base, "a.txt")
    dst = os.path.join(base, "b.txt")

    def make_move():
        with open(src, "w") as fp:
            fp.write("hi")
        os.replace(src, dst)

    # ── 情形 A：用**绝对路径** schedule ──
    rec_abs = Recorder()
    _run_observer(base, rec_abs, False, make_move)
    abs_paths = [e[1] for e in rec_abs.events]

    # ── 情形 B：用**相对路径** schedule（切 cwd，让相对路径可解析）──
    rec_rel = Recorder()
    old_cwd = os.getcwd()
    os.chdir(tmp)
    try:
        _run_observer("p5", rec_rel, False, make_move)
    finally:
        os.chdir(old_cwd)
    rel_paths = [e[1] for e in rec_rel.events]

    a_abs = bool(abs_paths) and all(os.path.isabs(p) for p in abs_paths)
    b_abs = bool(rel_paths) and all(os.path.isabs(p) for p in rel_paths)
    print(f"   A) schedule 绝对路径 → 事件路径是否绝对？ {a_abs}  示例：{abs_paths[:2]}")
    print(f"   B) schedule 相对路径 → 事件路径是否绝对？ {b_abs}  示例：{rel_paths[:2]}")

    all_events = rec_abs.events + rec_rel.events
    moved_dest = [e[2] for e in all_events if e[0] == "moved"]
    print(f"   moved 事件的 dest_path → {moved_dest}")
    print("\n   ❗ 结论：事件里的路径**跟随你 schedule 时给的路径形态**，")
    print("      不同 watchdog 版本/后端还可能收紧成绝对路径 —— 不要赌，自己归一化。")
    print("   ❌ 错误写法：")
    print("      · 拿 event.src_path 直接和相对路径规则比对（'p5/a.txt' vs '/abs/p5/a.txt'）")
    print("      · 用 getattr(event, 'dest_path') 处理 created/deleted（它是空串）")
    print("   ✅ 正解：")
    print("      · 防抖 key 与规则匹配统一用 os.path.abspath(os.path.realpath(...))")
    print("      · 取『改了哪个路径』统一写：`p = event.dest_path or event.src_path`")
    return bool(moved_dest) and all(moved_dest)


# ═════════════════════════ 陷阱 6 ═════════════════════════
def pitfall_6(tmp: str) -> bool:
    print("\n" + "=" * 72)
    print("陷阱 6：schedule 不存在的路径抛 OSError；inotify watch 有配额")
    print("=" * 72)
    ghost = os.path.join(tmp, "no-such-dir")
    try:
        obs = Observer()
        obs.schedule(Recorder(), ghost)
        obs.start()
        obs.stop()
        obs.join(timeout=3)
        print("   ⚠ 竟然没抛异常（不同 watchdog 版本行为可能不同），请以实测为准")
    except FileNotFoundError as exc:
        print(f"   ✅ 如期抛出：FileNotFoundError: {exc}")
        print("      → 生产代码必须先 os.makedirs(path, exist_ok=True) 再 schedule")
    except OSError as exc:
        print(f"   ✅ 如期抛出 OSError: {exc}")

    print("\n   另一个更阴的 OSError：递归监控大目录树时耗尽内核 watch 配额")
    for f in (
        "/proc/sys/fs/inotify/max_user_watches",
        "/proc/sys/fs/inotify/max_user_instances",
        "/proc/sys/fs/inotify/max_queued_events",
    ):
        try:
            with open(f) as fp:
                print(f"     {f} = {fp.read().strip()}")
        except OSError:
            print(f"     {f} = (不可读)")
    print("   → 一个目录一个 watch；监控 node_modules / 大站日志目录前，先数目录量：")
    print("       find <path> -type d | wc -l")
    print("   超限的正解：加忽略规则 / 只监控需要的子目录 / 临时调大配额后重启观察者")
    return True


# ═════════════════════════ 主入口 ═════════════════════════
PITFALLS = {
    1: ("事件类型不止 4 种", pitfall_1),
    2: ("编辑器原子写与半成品文件", pitfall_2),
    3: ("新目录漏事件", pitfall_3),
    4: ("慢 handler 阻塞 dispatch", pitfall_4),
    5: ("路径归一化与 dest_path", pitfall_5),
    6: ("不存在的路径与 watch 配额", pitfall_6),
}


def main(argv: list[str]) -> int:
    only = None
    quiet = False
    for arg in argv:
        if arg == "--self-test":
            quiet = True
        elif arg == "--only":
            print("用法：--only <编号>，例如 --only 3")
            return 2
        elif arg.startswith("--only="):
            only = int(arg.split("=", 1)[1])
        elif arg.startswith("--only") and arg[6:].isdigit():
            only = int(arg[6:])

    # 兼容 `--only 3` 的写法
    if "--only" in argv:
        idx = argv.index("--only")
        if idx + 1 < len(argv):
            only = int(argv[idx + 1])

    selected = [only] if only else sorted(PITFALLS)
    results: dict[int, bool] = {}
    for n in selected:
        name, fn = PITFALLS[n]
        tmp = tempfile.mkdtemp(prefix=f"day167-p{n}-")
        try:
            results[n] = bool(fn(tmp))
        except Exception as exc:               # 自检要稳：单条失败不影响其他条
            print(f"   ❌ 陷阱 {n} 执行异常：{type(exc).__name__}: {exc}")
            results[n] = False
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("六条陷阱回顾")
    print("=" * 72)
    for n in sorted(results):
        mark = "✅" if results[n] else "❌"
        print(f"   {mark} 陷阱 {n}：{PITFALLS[n][0]}")

    if quiet:
        if all(results.values()):
            print("\nSELF-TEST OK")
            return 0
        print("\nSELF-TEST FAILED")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
