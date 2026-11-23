#!/usr/bin/env python3
"""常见陷阱与避坑（Day 166 — 系统监控 psutil）。

本文件把 README 第 5 节的 Top 10 陷阱**逐条跑给你看**：
每条都给出「错误写法 → 观察到的现象 → 根因 → 正确写法」。

陷阱清单：
  1. cpu_percent() 首次调用返回 0.0
  2. interval=None 并不等于"瞬时值"
  3. 把累计计数器（counter）当瞬时值（gauge）用
  4. 用 time.time() 算采样间隔（NTP 校时会让 Δt 变负）
  5. Process.name() 被内核截断到 15 字符
  6. disk_usage('/') 硬编码 + 伪文件系统刷屏
  7. 遍历进程时不处理 NoSuchProcess / AccessDenied
  8. Process.cpu_percent() 可以 > 100%（不是 bug）
  9. 阈值抖动 → 告警风暴（用滞回 + 连续次数去抖修复）
 10. 容器里读到宿主机的内存/核数（用 cgroup 修正）

⚠ 安全边界：
- 只读本机指标；不修改任何系统状态。
- 唯一启动的进程是本脚本自己的短命子进程，用完立即回收（wait）。
- 不杀任何非本脚本创建的进程。

运行：
    python3 03-pitfalls.py                # 逐条演示全部陷阱
    python3 03-pitfalls.py --only 3       # 只演示第 3 条
    python3 03-pitfalls.py --self-test    # 输出 SELF-TEST OK

依赖：
    pip install psutil
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from typing import Callable

try:
    import psutil
except ImportError:  # pragma: no cover
    print("缺少依赖：请先执行  pip install psutil", file=sys.stderr)
    raise SystemExit(1)


# ── 演示框架 ─────────────────────────────────────────────────────────────

DEMOS: dict[int, tuple[str, Callable[[], None]]] = {}


def demo(num: int, title: str) -> Callable[[Callable[[], None]], Callable[[], None]]:
    """注册一个陷阱演示，便于 --only 单独运行。"""
    def deco(fn: Callable[[], None]) -> Callable[[], None]:
        DEMOS[num] = (title, fn)
        return fn
    return deco


def show(num: int, text: str) -> None:
    print(f"\n{'=' * 68}")
    print(f"陷阱 {num}: {text}")
    print("=" * 68)


# ── 陷阱 1 ───────────────────────────────────────────────────────────────

@demo(1, "cpu_percent() 首次调用返回 0.0")
def pitfall_1() -> None:
    show(1, "cpu_percent() 首次调用返回 0.0")

    # 为了演示"首次调用"，需要清理 psutil 的内部基准缓存。
    # 这里不直接动私有变量（那是坏习惯），而是重启一个子解释器来保证"全新进程"。
    code = "import psutil; print(f'  [子进程首调] cpu_percent() = {psutil.cpu_percent()}')"
    subprocess.run([sys.executable, "-c", code], check=False)

    print("  现象: 明明机器在忙，第一次调用却拿到 0.0")
    print("  根因: 使用率 = Δbusy/Δtotal 算出来的；第一次没有上一次的读数做参照。")
    print("  正确写法（三选一）:")
    print("    ① psutil.cpu_percent(interval=0.5)      # 阻塞式，内部自己拿两次读数")

    psutil.cpu_percent(interval=None)            # 预热：建立基准
    time.sleep(0.5)
    v = psutil.cpu_percent(interval=None)
    print(f"    ② 先预热再读 → cpu_percent() = {v:.1f}%   ← 这才是真实值")

    per = psutil.cpu_percent(interval=0.2, percpu=True)
    print(f"    ③ 逐核读: percpu=True → {[round(x, 1) for x in per[:6]]}{' ...' if len(per) > 6 else ''}")


# ── 陷阱 2 ───────────────────────────────────────────────────────────────

@demo(2, "interval=None 并不等于「瞬时值」")
def pitfall_2() -> None:
    show(2, "interval=None 并不等于「瞬时值」")

    psutil.cpu_percent(interval=None)   # 预热
    samples = []
    for _ in range(8):
        samples.append(psutil.cpu_percent(interval=None))
        # 不等：窗口被压到微秒级
    print(f"  不等待就连续调 8 次: {[round(s, 1) for s in samples]}")
    print("  现象: 大量 0.0 或剧烈跳变")
    print("  根因: interval=None 是非阻塞的，返回「自上次调用以来」的平均值；")
    print("        上一次是 0.001 秒前 → 窗口太小 → 采样噪声吞掉一切。")

    psutil.cpu_percent(interval=None)
    print("  正确写法（非阻塞 + 自己控制节奏）:")
    for i in range(3):
        time.sleep(0.3)
        print(f"    第 {i + 1} 次（间隔 0.3s）: {psutil.cpu_percent(interval=None):5.1f}%")
    print("  结论: 非阻塞模式下，采样窗口 = 你的调用间隔。窗口必须自己保证。")


# ── 陷阱 3 ───────────────────────────────────────────────────────────────

@demo(3, "把累计计数器（counter）当瞬时值（gauge）")
def pitfall_3() -> None:
    show(3, "把累计计数器（counter）当瞬时值（gauge）")

    print("  ❌ 错误写法: 直接打印 net_io_counters().bytes_sent")
    for _ in range(3):
        print(f"     bytes_sent = {psutil.net_io_counters().bytes_sent:,} bytes")
        time.sleep(0.2)
    print("     现象: 数字一直涨 → 误读成「流量在暴增」")
    print("     真相: 这是【开机以来累计】值，和速率毫无关系。")

    print("\n  ✅ 正确写法: 差分 ÷ 实测间隔（用单调时钟）")
    t0 = time.monotonic()
    n0 = psutil.net_io_counters().bytes_sent
    time.sleep(0.5)
    t1 = time.monotonic()
    n1 = psutil.net_io_counters().bytes_sent
    dt = t1 - t0
    rate = (n1 - n0) / dt
    print(f"     Δbytes = {n1 - n0:,}  实测Δt = {dt:.4f}s  速率 = {rate:,.0f} B/s "
          f"({rate / 1024:.1f} KiB/s)")

    print("\n  计数器重置防护（网卡重启/容器重启会让计数器归零 → 差分为负）:")
    print("     检测 delta < 0 → 视为计数器重置，丢弃该样本并记一次异常事件，")
    print("     绝不能让负数进入速率计算（会得到荒谬的负速率）。")

    # 演示 safe_rate
    def safe_rate(prev: int, cur: int, dt: float) -> float | None:
        if dt <= 0:
            return None
        delta = cur - prev
        if delta < 0:
            return None            # 计数器被重置：本次样本不可信
        return delta / dt

    print(f"     正常: safe_rate(1000, 1500, 1.0) = {safe_rate(1000, 1500, 1.0)}")
    print(f"     重置: safe_rate(999999, 10, 1.0) = {safe_rate(999999, 10, 1.0)}  ← 丢弃")


# ── 陷阱 4 ───────────────────────────────────────────────────────────────

@demo(4, "用 time.time() 算采样间隔")
def pitfall_4() -> None:
    show(4, "用 time.time() 算采样间隔（NTP 校时会让 Δt 变负）")

    print("  time.time()      = CLOCK_REALTIME，会被 NTP 校时 / 手动改时间【往回拨】")
    print("  time.monotonic() = 单调时钟，只会向前，不受校时影响")
    t = time.time()
    m = time.monotonic()
    time.sleep(0.2)
    print(f"  time.time()      间隔 = {time.time() - t:.6f}s")
    print(f"  time.monotonic() 间隔 = {time.monotonic() - m:.6f}s")
    print("  现象: 若这 0.2 秒内 NTP 把时钟拨回 1 秒 → time.time() 差值为 -0.8")
    print("         → 速率 = bytes / (-0.8) = 负值；若恰好为 0 → ZeroDivisionError / inf")
    print("  正确写法: 测【间隔】一律用 time.monotonic()。")

    # 对比: 算"进程存活时长"要用 time.time() - create_time()，因为两者同基准
    p = psutil.Process(os.getpid())
    age_wall = time.time() - p.create_time()
    print(f"\n  对照: 进程存活时长必须用 time.time() - create_time()（同为 REALTIME 基准）")
    print(f"        本进程已存活约 {age_wall:.2f} 秒")
    print("  ⚠ 千万不要把 time.monotonic() 和 create_time() 相减 —— 基准不同，结果无意义。")


# ── 陷阱 5 ───────────────────────────────────────────────────────────────

@demo(5, "Process.name() 被内核截断到 15 字符")
def pitfall_5() -> None:
    show(5, "Process.name() 被内核截断到 15 字符")

    # 为什么要复制一份 sleep？
    #   Process.name() 读的是内核的 /proc/<pid>/comm，而 comm 默认就是
    #   可执行文件的 basename（被 exec -a 改掉的只是 argv[0]，不会改 comm）。
    #   所以想真实验证"截断"，必须让可执行文件名本身很长。
    long_base = "very-long-application-name-exceeds-comm-limit"
    tmp_path = f"/tmp/{long_base}"

    child: subprocess.Popen | None = None
    try:
        import shutil
        shutil.copy("/bin/sleep", tmp_path)
        os.chmod(tmp_path, 0o755)

        child = subprocess.Popen([tmp_path, "5"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p = psutil.Process(child.pid)
        time.sleep(0.15)

        try:
            name = p.name()
        except psutil.Error as exc:
            name = f"<{type(exc).__name__}>"
        try:
            cmd = p.cmdline()
        except psutil.Error:
            cmd = []

        # 直接读内核的 comm 原始值：这才是"截断"发生的地方。
        kernel_comm = read_kernel_comm(p.pid)

        print(f"  可执行文件 basename 真实长度 = {len(long_base)} 字符")
        print(f"    实际名字: {long_base}")
        print(f"  内核 /proc/<pid>/comm       = {kernel_comm!r}   "
              f"（长度 {len(kernel_comm)}，已是截断值）")
        print(f"  Process.name()              = {name!r}   （长度 {len(name)}）")
        print(f"  cmdline()[0] 的 basename    = "
              f"{os.path.basename(cmd[0]) if cmd else 'N/A'!r}")

        truncated = kernel_comm is not None and len(kernel_comm) < len(long_base)
        recovered = len(name) > len(kernel_comm or "")

        if truncated:
            print(f"  → 内核确实截断了：comm 只保留前 {len(kernel_comm)} 个字符。")
            print("     根因：/proc/<pid>/comm 的字段上限是 TASK_COMM_LEN=16 字节（含结尾 \\0），")
            print("           所以最多放 15 个可见字符。这是内核限制，不是 psutil 的 bug。")
        else:
            print("  → 本平台内核未截断 comm（新内核可能放宽了该限制）。")

        if truncated and recovered:
            print(f"  → 但 psutil.name() 把完整名字【拿回来了】（{len(name)} 字符）。")
            print("     为什么？psutil 发现 name 长度 >= 15 时，会去读 cmdline()，")
            print("     若 cmdline[0] 的 basename 以该截断名开头，就返回完整版本。")
            print("     （这是 psutil 的兼容策略，源码见 Process.name 的 POSIX 分支。）")
        elif truncated and not recovered:
            print("  → psutil 没能拿回完整名字：因为 cmdline() 为空或不可读。")

        print("  所以真正的风险不在「名字被截断」，而在下面三种情况：")
        print("    ① 内核线程：cmdline() 为空 → 你只能拿到 15 字符甚至空名")
        print("    ② 僵尸进程：可以读到 name()，但 cmdline() 会抛 ZombieProcess")
        print("    ③ 无权限：cmdline() 抛 AccessDenied → 回退到截断值")
        print("  正确写法：用 cmdline()[0] 的 basename 优先，失败时回退 name()，")
        print("            再失败就输出占位符（如 <pid 1234>）并计入「身份不全」计数。")
    except OSError as exc:
        # /tmp 不可写或无 /bin/sleep 时，退回纯文字说明，不让演示崩掉。
        print(f"  [本机无法完成文件复制演示: {type(exc).__name__}: {exc}]")
        print("  结论仍然成立：comm 字段上限 16 字节（含 \\0），name() 最多 15 字符。")
    finally:
        # 无论演示成功与否，都要回收子进程与临时文件 —— 这是"不留垃圾"的基本要求。
        if child is not None:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ── 陷阱 6 ───────────────────────────────────────────────────────────────

@demo(6, "disk_usage('/') 硬编码 + 伪文件系统刷屏")
def pitfall_6() -> None:
    show(6, "disk_usage('/') 硬编码 + 伪文件系统刷屏")

    print("  ❌ 错误写法: psutil.disk_usage('/')")
    print("     问题 1: Windows 上没有 '/'，直接抛异常")
    print("     问题 2: 容器里 '/' 可能不是你要观察的那个分区")
    try:
        u = psutil.disk_usage("/")
        print(f"     本机 '/' → {u.percent:.1f}% used（这里能跑，不代表随处能跑）")
    except Exception as exc:      # 演示用：这里故意宽泛捕获以展示平台差异
        print(f"     本机 '/' 也不可用: {type(exc).__name__}: {exc}")

    print("\n  ❌ 更隐蔽的问题: all=False 也挡不住 squashfs/iso9660")
    parts = psutil.disk_partitions(all=False)
    noisy = [p for p in parts if p.fstype in ("squashfs", "iso9660", "udf")]
    for p in noisy[:5]:
        try:
            uu = psutil.disk_usage(p.mountpoint)
            print(f"     ⚠ {p.mountpoint:40s} {uu.percent:5.1f}%  [{p.fstype}] ← 假警报")
        except OSError:
            continue
    print(f"     共 {len(noisy)} 个伪只读挂载点，percent 恒为 100%，必须过滤。")

    print("\n  ✅ 正确写法: 遍历 + 过滤伪文件系统 + 每个挂载点单独容错")
    PSEUDO = {"squashfs", "iso9660", "udf", "devtmpfs", "tmpfs", "proc", "sysfs",
              "cgroup", "cgroup2", "overlay", "ramfs", "autofs", "mqueue"}
    ok = 0
    for p in parts:
        if p.fstype in PSEUDO:
            continue
        try:
            uu = psutil.disk_usage(p.mountpoint)
        except (PermissionError, FileNotFoundError, OSError):
            continue          # 已卸载/不可达：跳过但不应崩
        ok += 1
        print(f"     {p.mountpoint:30s} {uu.percent:5.1f}%  [{p.fstype}]")
    print(f"     已检查 {ok} 个真实分区。过滤后必须把过滤数量打印出来（可观测性）。")


# ── 陷阱 7 ───────────────────────────────────────────────────────────────

@demo(7, "遍历进程时不处理 NoSuchProcess / AccessDenied")
def pitfall_7() -> None:
    show(7, "遍历进程时不处理 NoSuchProcess / AccessDenied")

    print("  现象: 脚本在「某个进程刚好退出」时随机崩溃 —— 取决于时序，极难复现。")

    # 制造一个必然消失的进程：起一个短命进程，拿它的 pid，等它退出后再访问。
    child = subprocess.Popen(["sleep", "0.05"])
    pid = child.pid
    child.wait()                    # 已退出并被回收：这个 pid 现在不存在了

    print(f"\n  ① 访问一个已退出的 pid（{pid}）但【不】catch:")
    try:
        psutil.Process(pid).name()
        print("     （本平台该 pid 已被复用，未触发异常）")
    except psutil.NoSuchProcess as exc:
        print(f"     → 抛出 psutil.NoSuchProcess: {exc}")
        print("     → 没有 try/except 的脚本到这里就崩了")

    print("\n  ② 访问不存在的 pid（999999）：")
    try:
        psutil.Process(999999).name()
    except psutil.NoSuchProcess as exc:
        print(f"     → psutil.NoSuchProcess: {exc}")

    print("\n  ③ 正确写法: 三类异常分别处理，并区分「目标不可测」与「我写错了」")
    code = '''
try:
    rss = psutil.Process(pid).memory_info().rss
except psutil.NoSuchProcess:      # 进程没了 —— 预期内的正常情况
    rss = None
except psutil.AccessDenied:       # 权限不够 —— 也是正常情况（记一次 denied）
    rss = None
except psutil.ZombieProcess:      # 僵尸进程 —— 信息读不全，本身是告警信号
    rss = None
'''
    print(code.rstrip())

    print("\n  ⚠ 反例: except Exception: pass  —— 连自己代码里的 TypeError 都被吞掉，")
    print("     结果你会监控一个「永远返回空值」的假象，比崩溃更危险。")

    # 演示正确写法能跑通整轮扫描
    stats = {"ok": 0, "gone": 0, "denied": 0}
    for proc in psutil.process_iter(attrs=["pid"], ad_value=None):
        try:
            proc.info["pid"]
            stats["ok"] += 1
        except psutil.NoSuchProcess:
            stats["gone"] += 1
        except psutil.AccessDenied:
            stats["denied"] += 1
    print(f"\n  正确写法扫描一轮结果: 成功 {stats['ok']}，已退出 {stats['gone']}，"
          f"无权限 {stats['denied']}  —— 未崩溃 ✅")


# ── 陷阱 8 ───────────────────────────────────────────────────────────────

@demo(8, "Process.cpu_percent() 可以 > 100%（不是 bug）")
def pitfall_8() -> None:
    show(8, "Process.cpu_percent() 可以 > 100%（不是 bug）")

    cores = psutil.cpu_count(logical=True) or 1
    print(f"  本机逻辑核数 = {cores} → 单进程 CPU 使用率上限 = {cores * 100}%")

    # 启动一个真正吃 CPU 的子进程（2 个忙线程，跑约 1.5 秒）
    burner = (
        "import threading,time\n"
        "def burn():\n"
        "    t=time.time()\n"
        "    while time.time()-t < 2.0: pass\n"
        "for _ in range(2):\n"
        "    threading.Thread(target=burn, daemon=True).start()\n"
        "time.sleep(2.2)\n"
    )
    child = subprocess.Popen([sys.executable, "-c", burner])
    try:
        p = psutil.Process(child.pid)
        p.cpu_percent()                    # 预热
        time.sleep(1.0)
        cpu = p.cpu_percent()
        print(f"\n  一个用 2 个线程满载的进程: cpu_percent() = {cpu:.1f}%")
        if cpu > 100:
            print("  → 超过 100% 是【正常】的：它表示同时占用了多个核心。")
        else:
            print("  → 本次未超过 100%（机器核数多 / 调度分片），但上限确实是 "
                  f"{cores * 100}%。")
        print(f"  判断依据: user+system 的累计 CPU 秒数 ÷ 墙上时间 = {cpu / 100:.2f} 核")
        print("  正确写法: 阈值按「核数 × 目标利用率」定义，而不是拍一个 80%。")
    finally:
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


# ── 陷阱 9 ───────────────────────────────────────────────────────────────

@demo(9, "阈值抖动 → 告警风暴（滞回 + 去抖修复）")
def pitfall_9() -> None:
    show(9, "阈值抖动 → 告警风暴（滞回 + 去抖修复）")

    # 造一段在阈值附近抖动的样本
    series = [78, 81, 79, 83, 77, 82, 79, 84, 78, 80, 85, 79, 81, 80, 86,
              79, 78, 81, 80, 79, 82, 81, 80, 79, 78, 80, 81]
    TH = 80.0

    naive_alerts = sum(1 for v in series if v >= TH)
    print(f"  样本: {series}")
    print(f"  阈值: {TH}")
    print(f"\n  ❌ 朴素写法（v >= 阈值就告警）: 触发 {naive_alerts} 次告警！")
    print("     → 运维收到 17 条通知，实际系统没有任何持续性问题。这就是告警疲劳的来源。")

    class DebouncedThreshold:
        """带滞回（hysteresis）与连续次数去抖的阈值判定。

        high: 超过则累计一次"异常"
        low:  低于则累计一次"正常"（必须 < high，形成滞回带，避免在边界反复翻转）
        need: 连续多少次才真正翻转状态
        """

        def __init__(self, high: float, low: float, need: int = 3):
            if low >= high:
                raise ValueError("low 必须小于 high，否则滞回带为空，去抖失效")
            self.high, self.low, self.need = high, low, need
            self.state = False
            self._streak = 0
            self.transitions = 0

        def feed(self, value: float) -> bool:
            if self.state:
                if value < self.low:
                    self._streak += 1
                    if self._streak >= self.need:
                        self.state, self._streak = False, 0
                        self.transitions += 1
                else:
                    self._streak = 0
            else:
                if value >= self.high:
                    self._streak += 1
                    if self._streak >= self.need:
                        self.state, self._streak = True, 0
                        self.transitions += 1
                else:
                    self._streak = 0
            return self.state

    d = DebouncedThreshold(high=80.0, low=75.0, need=3)
    fired = 0
    prev = False
    trace = []
    for v in series:
        st = d.feed(v)
        trace.append("⚠" if st else "·")
        if st and not prev:
            fired += 1
        prev = st
    print(f"\n  ✅ 去抖写法（high=80, low=75, 连续 3 次才翻转）:")
    print(f"     状态轨迹: {' '.join(trace)}   (共 {len(trace)} 个样本)")
    print(f"     → 真正告警次数 = {fired}，状态翻转 {d.transitions} 次")
    print("     关键: low < high 形成的【滞回带】让 79%/81% 的横跳无法翻转状态，")
    print("           连续次数要求进一步过滤掉孤立尖峰。")


# ── 陷阱 10 ──────────────────────────────────────────────────────────────

@demo(10, "容器里读到宿主机的内存/核数")
def pitfall_10() -> None:
    show(10, "容器里读到宿主机的内存/核数（用 cgroup 修正）")

    vm = psutil.virtual_memory()
    print(f"  psutil.virtual_memory().total = {vm.total / 2**30:.1f} GiB")
    print(f"  psutil.cpu_count(logical=True) = {psutil.cpu_count(logical=True)}")
    print("  现象: 在容器里这两个值是【宿主机】的，不是容器的限额。")
    print("        用它做阈值 → 监控一个 512MiB 的容器却按 64GiB 判断 → 永不告警。")

    limit = read_cgroup_memory_limit()
    quota = read_cgroup_cpu_quota()
    print("\n  正确来源（cgroup）:")
    if limit:
        print(f"     内存限额 memory.max        = {limit / 2**30:.2f} GiB "
              f"({limit:,} bytes)")
    else:
        print("     内存限额: 未设置（不在容器内 / cgroup v1 无限制 / 读取失败）")
    if quota is not None:
        print(f"     CPU 限额 cpu.max           = {quota:.2f} 核")
    else:
        print("     CPU 限额: 未设置或不可读")
    cur = read_cgroup_memory_current()
    if cur:
        print(f"     当前用量 memory.current    = {cur / 2**20:.1f} MiB")
    else:
        print("     当前用量: 不可读")

    print("\n  检查顺序建议:")
    print("     ① 读 cgroup 限额（真实上限）")
    print("     ② 读 cgroup 当前用量（真实占用）")
    print("     ③ 只有两个都拿不到时，才退回 psutil.virtual_memory()，")
    print("        并在报告里显式标注「本数值为宿主机口径」—— 绝不能默默混用。")


def read_kernel_comm(pid: int) -> str | None:
    """直接读内核的 /proc/<pid>/comm（未经 psutil 加工）。

    为什么要绕过 psutil？
      为了看清"截断"到底发生在哪一层。psutil 会做兼容回退，
      直接读内核文件才能展示底层真相（TASK_COMM_LEN=16 字节上限）。
    """
    try:
        with open(f"/proc/{pid}/comm", encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return None


def read_cgroup_memory_limit() -> int | None:
    """容器内存限额（字节）；无限制/不支持返回 None。"""
    try:
        with open("/sys/fs/cgroup/memory.max", encoding="utf-8") as fh:   # cgroup v2
            raw = fh.read().strip()
        if raw and raw != "max":
            return int(raw)
    except (OSError, ValueError):
        pass
    try:
        with open("/sys/fs/cgroup/memory/memory.limit_in_bytes", encoding="utf-8") as fh:
            val = int(fh.read().strip())      # cgroup v1
        # v1 用接近 2^63 的极大值表示"无限制"，必须挡掉
        return val if val < (1 << 62) else None
    except (OSError, ValueError):
        return None


def read_cgroup_memory_current() -> int | None:
    for path in ("/sys/fs/cgroup/memory.current",
                 "/sys/fs/cgroup/memory/memory.usage_in_bytes"):
        try:
            with open(path, encoding="utf-8") as fh:
                return int(fh.read().strip())
        except (OSError, ValueError):
            continue
    return None


def read_cgroup_cpu_quota() -> float | None:
    """CPU 限额（单位：核）。cgroup v2 的 cpu.max 形如 "50000 100000" = 0.5 核。"""
    try:
        with open("/sys/fs/cgroup/cpu.max", encoding="utf-8") as fh:
            parts = fh.read().split()
        if len(parts) == 2 and parts[0] != "max":
            quota, period = int(parts[0]), int(parts[1])
            return quota / period if period else None
    except (OSError, ValueError):
        pass
    try:
        with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us", encoding="utf-8") as fh:
            quota = int(fh.read().strip())
        with open("/sys/fs/cgroup/cpu/cpu.cfs_period_us", encoding="utf-8") as fh:
            period = int(fh.read().strip())
        if quota > 0 and period > 0:
            return quota / period
    except (OSError, ValueError):
        pass
    return None


# ── 自检 ─────────────────────────────────────────────────────────────────

def self_test() -> int:
    checks: list[tuple[str, bool]] = []

    checks.append(("陷阱注册完整（10 条）", len(DEMOS) == 10))

    # 陷阱 3 的 safe_rate 逻辑
    def safe_rate(prev: int, cur: int, dt: float) -> float | None:
        if dt <= 0:
            return None
        delta = cur - prev
        return None if delta < 0 else delta / dt

    checks.append(("safe_rate 正常", safe_rate(1000, 1500, 1.0) == 500.0))
    checks.append(("safe_rate 重置返回 None", safe_rate(999999, 10, 1.0) is None))
    checks.append(("safe_rate dt<=0 返回 None", safe_rate(1, 2, 0.0) is None))

    # 去抖逻辑（与陷阱 9 相同的实现，独立复刻以验证行为）
    class D:
        def __init__(self, high: float, low: float, need: int):
            # 与陷阱 9 的生产实现保持同一约束：滞回带为空就等于没有去抖。
            if low >= high:
                raise ValueError("low 必须小于 high")
            self.high, self.low, self.need = high, low, need
            self.state, self._s = False, 0

        def feed(self, v: float) -> bool:
            if self.state:
                if v < self.low:
                    self._s += 1
                    if self._s >= self.need:
                        self.state, self._s = False, 0
                else:
                    self._s = 0
            else:
                if v >= self.high:
                    self._s += 1
                    if self._s >= self.need:
                        self.state, self._s = True, 0
                else:
                    self._s = 0
            return self.state

    d = D(80, 75, 3)
    first = [d.feed(v) for v in [81, 82, 83]]
    checks.append(("连续 3 次越阈 → 告警", first[-1] is True))
    d2 = D(80, 75, 3)
    jitter = [d2.feed(v) for v in [81, 79, 81, 79, 81, 79]]
    checks.append(("边界抖动不触发告警", not any(jitter)))

    try:
        D(80, 80, 3)
        checks.append(("low>=high 应报错", False))
    except ValueError:
        checks.append(("low>=high 应报错", True))

    checks.append(("cgroup 读取不抛异常",
                   read_cgroup_memory_limit() is None or read_cgroup_memory_limit() > 0))
    checks.append(("cpu quota 类型正确",
                   read_cgroup_cpu_quota() is None or read_cgroup_cpu_quota() > 0))
    checks.append(("boot_time 在过去", psutil.boot_time() <= time.time()))

    ok = True
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    if ok:
        print("SELF-TEST OK")
        return 0
    return 1


# ── 主流程 ───────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="psutil 十大常见陷阱逐条演示")
    ap.add_argument("--only", type=int, default=None,
                    help="只演示指定的陷阱编号（1-10）")
    ap.add_argument("--self-test", action="store_true", help="只做自检并输出 SELF-TEST OK")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.only is not None:
        if args.only not in DEMOS:
            print(f"未知的陷阱编号 {args.only}（可选 1-10）", file=sys.stderr)
            return 1
        DEMOS[args.only][1]()
        return 0

    print("=" * 68)
    print(" psutil 十大常见陷阱演示（全程只读；仅操作本脚本创建的子进程）")
    print("=" * 68)
    for num in sorted(DEMOS):
        title, fn = DEMOS[num]
        try:
            fn()
        except Exception as exc:      # 演示脚本：单条失败不应中断其余演示
            print(f"  [演示 {num} 出错] {type(exc).__name__}: {exc}")

    print(f"\n{'=' * 68}")
    print(" 十条陷阱回顾: 预热 / 窗口 / counter≠gauge / monotonic / comm 截断")
    print("                 / 伪文件系统 / 异常处理 / >100% 正常 / 去抖 / cgroup")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
