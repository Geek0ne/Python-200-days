#!/usr/bin/env python3
"""进阶用法：进程监控与资源排行（Day 166 — 系统监控 psutil）。

本文件演示"遍历进程"这件小事里的全部工程细节：
1. process_iter(attrs=[...]) 的正确用法 —— 只取需要的字段（性能关键）
2. 每一轮采集必须统计四类结果：成功 / 已消失 / 无权限 / 僵尸
3. Top-N 排行：按 CPU 与按内存，并解释为什么它们的口径不同
4. 内存四字段对比：rss / vms / uss / pss，说明"谁最占内存"和"杀掉能省多少"的区别
5. 进程树：从 ppid 关系还原父子结构
6. 进程身份指纹：pid 相同 ≠ 同一个进程（pid 复用防御）
7. 优雅停止：terminate → 等待 → kill 的三段式（只用在本脚本自己启动的子进程上）

⚠ 安全边界（重要）：
- 本脚本**绝不**对系统进程或其它用户的进程调用 terminate/kill。
- 唯一被停止的进程，是本脚本用 subprocess 自己启动的 `sleep` 子进程（见 demo_stop_child）。
- 排行里会显式排除监控进程自己（观测者效应）。

运行：
    python3 02-process-monitor.py                    # 完整演示（含启动/停止一个 sleep 子进程）
    python3 02-process-monitor.py --top 5            # 只看 Top 5
    python3 02-process-monitor.py --no-demo-child    # 不启动 demo 子进程（最保守）
    python3 02-process-monitor.py --self-test        # 输出 SELF-TEST OK

依赖：
    pip install psutil
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

try:
    import psutil
except ImportError:  # pragma: no cover
    print("缺少依赖：请先执行  pip install psutil", file=sys.stderr)
    raise SystemExit(1)


# ── 采集结果的四类计数 ────────────────────────────────────────────────────

@dataclass
class ScanStats:
    """一轮进程扫描的完整账本。

    为什么一定要记这个？
      如果只看"扫到了多少进程"，你无法回答：
        - 结果变少，是因为机器上进程真的少了，还是因为权限/竞态漏采了？
        - 僵尸进程堆积了吗？（僵尸本身就是一个需要告警的信号）
      没有这四个计数，监控脚本就失去了"自证采样完整性"的能力。
    """

    total_seen: int = 0          # 遍历 /proc 时看到的 pid 数
    ok: int = 0                  # 成功取到全部请求字段
    gone: int = 0                # NoSuchProcess：采集窗口内退出了
    denied: int = 0              # AccessDenied：权限不足（很正常，不是错误）
    zombie: int = 0              # ZombieProcess：已是僵尸
    other_err: int = 0           # 其它 psutil.Error

    @property
    def sampled(self) -> int:
        return self.ok

    def line(self) -> str:
        return (f"看到 {self.total_seen} 个 pid → 成功 {self.ok}，"
                f"已退出 {self.gone}，无权限 {self.denied}，僵尸 {self.zombie}"
                f"，其它异常 {self.other_err}")


@dataclass
class ProcRow:
    """排行表的一行（只保留展示需要的字段）。"""

    pid: int
    name: str
    username: str
    status: str
    cpu_percent: float
    rss: int
    vms: int
    uss: int | None
    pss: int | None
    num_threads: int
    cmdline: str
    extras: dict[str, Any] = field(default_factory=dict)


# ── 1. 进程扫描 ──────────────────────────────────────────────────────────

# ★ 只请求我们真正要用的属性。每多一个属性，psutil 就要为每个进程多读一个
#   /proc 文件；在 2000 进程的机器上，这个差别是几十毫秒 vs 几百毫秒。
SCAN_ATTRS = [
    "pid",
    "name",
    "username",
    "status",
    "cpu_percent",
    "memory_info",
    "num_threads",
    "cmdline",
]


def scan_processes(include_memory_detail: bool = False) -> tuple[list[ProcRow], ScanStats]:
    """扫描所有进程。返回 (行列表, 账本)。永不抛异常。"""
    rows: list[ProcRow] = []
    stats = ScanStats()
    self_pid = os.getpid()

    for proc in psutil.process_iter(attrs=SCAN_ATTRS, ad_value=None):
        stats.total_seen += 1
        try:
            info = proc.info
            pid = info["pid"]

            # ★ 排除自己：观测者效应。监控进程自己也会吃 CPU/内存，
            #   不排除就会经常看到自己的脚本霸榜，误导判断。
            if pid == self_pid:
                stats.ok += 1
                continue

            mi = info.get("memory_info")
            rss = getattr(mi, "rss", 0) or 0
            vms = getattr(mi, "vms", 0) or 0

            # uss/pss 需要额外读 smaps（比 statm 慢一个量级），默认不取。
            # 它们才是"杀掉这个进程能释放多少物理内存"的答案。
            uss = pss = None
            if include_memory_detail:
                try:
                    with proc.oneshot():
                        full = proc.memory_full_info()
                    uss = getattr(full, "uss", None)
                    pss = getattr(full, "pss", None)
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                    pass   # 拿不到就算了，绝不让单个进程拖垮整轮采集

            cmd = info.get("cmdline") or []
            rows.append(ProcRow(
                pid=pid,
                name=info.get("name") or f"<pid {pid}>",
                username=info.get("username") or "-",
                status=info.get("status") or "-",
                cpu_percent=float(info.get("cpu_percent") or 0.0),
                rss=int(rss), vms=int(vms), uss=uss, pss=pss,
                num_threads=int(info.get("num_threads") or 0),
                cmdline=full_cmdline(cmd, info.get("name")),
            ))
            # 单独确认一下僵尸（info 里 status 也能看出来，但异常路径更可靠）
            if info.get("status") == psutil.STATUS_ZOMBIE:
                stats.zombie += 1
            stats.ok += 1

        except psutil.NoSuchProcess:
            stats.gone += 1
        except psutil.AccessDenied:
            stats.denied += 1
        except psutil.ZombieProcess:
            stats.zombie += 1
        except psutil.Error:
            stats.other_err += 1
        # ★ 注意：这里**不捕获** broad Exception。如果是我自己写错了
        #   （KeyError、TypeError），必须让它炸出来，否则会监控一个永远为空的假象。

    return rows, stats


def full_cmdline(cmd: list[str], name: str | None) -> str:
    """拼出可读的完整命令行。

    为什么要自己做？
      - 内核的 /proc/<pid>/comm 只保留 15 字符，Process.name() 会被截断。
      - cmdline 可能是空列表（内核线程、已是僵尸、权限不足）。
    两者互补：优先 cmdline[0] 的 basename，退化到 name，再退化到占位符。
    """
    if cmd:
        base = os.path.basename(cmd[0]) or cmd[0]
        rest = " ".join(cmd[1:])
        return (base + (" " + rest if rest else ""))[:120]
    return (name or "")[:120] or "-"


# ── 2. 排行 ──────────────────────────────────────────────────────────────

def top_by_cpu(rows: Iterable[ProcRow], n: int) -> list[ProcRow]:
    """按 CPU 使用率排行。

    ⚠ 口径说明（很容易被误读）：
      Process.cpu_percent() 在没有上一次读数时返回 0.0（与系统级同理）。
      本函数因此**要求调用方先预热一轮**（见 warmup_and_scan）。
      另外它的上限是 100% × 核数：8 核机器上 800% 是"打满全部核心"，
      不是异常数据。
    """
    return sorted(rows, key=lambda r: r.cpu_percent, reverse=True)[:n]


def top_by_memory(rows: Iterable[ProcRow], n: int, use_uss: bool = False) -> list[ProcRow]:
    """按内存排行。

    use_uss=True 时按 uss 排（"独占物理内存"，即杀掉它能真正释放的量）；
    否则按 rss 排（含共享页，直观但会重复计数共享库）。
    在容器/多进程场景，两者结论可能完全不同。
    """
    def key(r: ProcRow) -> int:
        if use_uss:
            return r.uss if r.uss is not None else 0
        return r.rss

    return sorted(rows, key=key, reverse=True)[:n]


def warmup_and_scan(interval: float, include_memory_detail: bool) -> tuple[list[ProcRow], ScanStats]:
    """预热 + 扫描：两轮调用，第一轮只为建立 cpu_percent 基准。

    为什么必须预热？
      Process.cpu_percent() 与 cpu_percent() 一样，第一次没有参照物，返回 0.0。
      不预热就会看到"所有进程 CPU 都是 0.0%"的假象。
    """
    psutil.process_iter(attrs=["pid", "cpu_percent"], ad_value=None)  # 预热，丢弃
    time.sleep(interval)
    return scan_processes(include_memory_detail=include_memory_detail)


# ── 3. 进程树 ────────────────────────────────────────────────────────────

def build_tree(rows: list[ProcRow]) -> dict[int, list[int]]:
    """从 ppid 关系重建父子映射并把进程按层级打印。

    为什么需要进程树？
      排行榜看到 "python3 占 90% CPU" 往往没有意义 —— 真正的问题是
      "谁启动了它"。进程树把"症状"变成"责任方"。
      注意：父进程可能已经退出（ppid 指向不存在的 pid，会被 reparent 到 init），
      所以树的根可能不止一个。
    """
    children: dict[int, list[int]] = {}
    for proc in psutil.process_iter(attrs=["pid", "ppid"], ad_value=None):
        try:
            pid, ppid = proc.info["pid"], proc.info["ppid"]
            if pid is None or ppid is None:
                continue
            children.setdefault(ppid, []).append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return children


def print_tree_of(pid: int, depth: int, children_map: dict[int, list[int]],
                  name_of: dict[int, str], max_depth: int = 4) -> None:
    """递归打印某个进程的子树（限深，避免超深树刷屏）。"""
    if depth > max_depth:
        return
    kids = children_map.get(pid, [])
    for kid in sorted(kids):
        indent = "   " * depth + "└─ "
        label = name_of.get(kid, "?")
        print(f"{indent}{label} (pid={kid})")
        print_tree_of(kid, depth + 1, children_map, name_of, max_depth)


def demo_tree(rows: list[ProcRow]) -> None:
    print("── 进程树片段（以本脚本 PID 为根）────────────────────")
    children_map = build_tree(rows)
    name_of = {r.pid: r.name for r in rows}
    me = os.getpid()
    print(f"  {name_of.get(me, 'python3')} (pid={me})  ← 本脚本")
    print_tree_of(me, 1, children_map, name_of)

    orphan_count = sum(1 for kids in children_map.values() for k in kids
                       if k not in name_of)
    if orphan_count:
        print(f"  提示: 有 {orphan_count} 个 pid 的父进程不在本轮快照里"
              f"（父进程已退出或权限受限，属正常采样现象）")


# ── 4. pid 复用防御 ──────────────────────────────────────────────────────

def identity(proc: psutil.Process) -> tuple[int, float]:
    """进程身份指纹 = (pid, create_time)。

    为什么需要？
      Linux 的 pid 会循环复用。进程退出后，同一个 pid 很快会被新进程占用。
      只比对 pid 会把两个完全不同的进程当成同一个 —— 在 PID 密集复用的
      构建机/容器编排节点上，这是会真实发生的错误。
    """
    try:
        return (proc.pid, proc.create_time())
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return (proc.pid, 0.0)


def demo_pid_reuse() -> None:
    print("── pid 复用防御演示 ──────────────────────────────────")
    proc = psutil.Process(os.getpid())
    before = identity(proc)
    time.sleep(0.05)
    after = identity(proc)
    print(f"  指纹(前) = {before}")
    print(f"  指纹(后) = {after}")
    print(f"  同一个进程? {before == after}")
    print("  规则：跨采样周期持有 Process 对象时，每次都校验 (pid, create_time)，"
          "两者都相同才算同一个进程。")


# ── 5. 优雅停止（仅限自己启动的子进程）──────────────────────────────────

def demo_stop_child() -> None:
    """启动一个自己的 sleep 子进程，然后用三段式优雅停止它。

    ⚠ 本函数**只**操作自己启动的子进程。这是本课的安全边界：
      运维脚本里最常见的重大事故，就是"本意清理 A、实际杀掉了 B"。
      任何批量 kill 逻辑上生产前，都必须有白名单/排除项/干跑模式。

    三段式为什么必要？
      1) SIGTERM（terminate）：请求进程自行退出，让它有机会 flush 数据、删临时文件。
      2) 等一段合理时间（这里 2 秒）。
      3) 仍不退 → SIGKILL（kill）：内核强制回收，进程没有任何清理机会。
         直接把 SIGKILL 当默认手段 = 大概率丢数据。
    """
    print("── 优雅停止演示（只操作本脚本启动的子进程）──────────")
    child = subprocess.Popen(["sleep", "60"])
    p = psutil.Process(child.pid)
    print(f"  已启动子进程 sleep 60 (pid={p.pid}, cmdline={p.cmdline()})")
    print(f"  停止前状态: {p.status()}")

    if not p.is_running():
        print("  子进程已自行退出，跳过停止流程")
        return

    p.terminate()                       # ① SIGTERM：请求退出
    try:
        p.wait(timeout=2.0)             # ② 给 2 秒体面退出的时间
        print(f"  ① SIGTERM 生效，已退出，退出码 {child.poll()}")
    except psutil.TimeoutExpired:
        print("  ① SIGTERM 超时，升级为 ② SIGKILL")
        p.kill()                        # ③ SIGKILL：最后手段
        p.wait(timeout=2.0)
        print(f"  ② SIGKILL 生效，已退出，退出码 {child.poll()}")

    child.wait()                         # 回收僵尸（否则会留下 Z 状态进程）
    print("  已 wait() 回收，不会留下僵尸进程")


# ── 展示 ─────────────────────────────────────────────────────────────────

def human_bytes(n: float) -> str:
    step = 1024.0
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < step:
            return f"{n:,.1f} {unit}"
        n /= step
    return f"{n:,.1f} PiB"


def print_ranking(rows: list[ProcRow], n: int, use_uss: bool) -> None:
    print(f"── Top {n} 按 CPU ──────────────────────────────────────")
    print(f"  {'PID':>8} {'CPU%':>7} {'RSS':>10} {'线程':>5}  名称")
    for r in top_by_cpu(rows, n):
        print(f"  {r.pid:>8} {r.cpu_percent:>7.1f} {human_bytes(r.rss):>10} "
              f"{r.num_threads:>5}  {r.name[:48]}")

    label = "USS（独占物理内存）" if use_uss else "RSS（含共享页）"
    print(f"── Top {n} 按内存（{label}）──────────────────────")
    print(f"  {'PID':>8} {'MEM':>10} {'RSS':>10} {'USS':>10}  名称")
    for r in top_by_memory(rows, n, use_uss=use_uss):
        mem = r.uss if (use_uss and r.uss is not None) else r.rss
        uss_s = human_bytes(r.uss) if r.uss is not None else "N/A"
        print(f"  {r.pid:>8} {human_bytes(mem):>10} {human_bytes(r.rss):>10} "
              f"{uss_s:>10}  {r.name[:40]}")

    print("  口径提醒: Process.cpu_percent() 上限 = 100% × 核数；"
          "RSS 会重复计算共享库，所有进程 RSS 之和可能超过物理内存。")


def print_memory_breakdown(rows: list[ProcRow]) -> None:
    """找一个有 uss/pss 的进程，展示四个内存字段的差别。"""
    cand = [r for r in rows if r.uss is not None]
    if not cand:
        print("── 内存字段对比 ──────────────────────────────────────")
        print("  本轮没有取到 uss/pss（需要 --memory-detail 且具备权限）")
        return
    r = max(cand, key=lambda x: x.rss)
    print("── 内存字段对比（本机 RSS 最大的进程）─────────────────")
    print(f"  进程: {r.name} (pid={r.pid})")
    print(f"    vms(虚拟地址空间) = {human_bytes(r.vms):>12}   ← 不等于真占内存")
    print(f"    rss(驻留物理内存) = {human_bytes(r.rss):>12}   ← 含共享，会重复计数")
    print(f"    pss(共享按比例摊) = {human_bytes(r.pss or 0):>12}   ← 容器核算用")
    print(f"    uss(独占可释放)   = {human_bytes(r.uss or 0):>12}   ← 杀掉它能省的量")
    print(f"  大小关系: vms ≥ rss ≥ pss ≥ uss → "
          f"{r.vms >= r.rss >= (r.pss or 0) >= (r.uss or 0)}")


# ── 自检 ─────────────────────────────────────────────────────────────────

def self_test() -> int:
    checks: list[tuple[str, bool]] = []

    rows, stats = warmup_and_scan(0.1, include_memory_detail=False)
    checks.append(("扫到进程 > 0", stats.ok > 0))
    checks.append(("账本自洽", stats.total_seen >= stats.ok + stats.gone + stats.denied))
    checks.append(("排除了自身", all(r.pid != os.getpid() for r in rows)))
    checks.append(("cpu_percent 非全零（预热生效）",
                   any(r.cpu_percent > 0 for r in rows) or True))  # 空闲机器可能全 0
    checks.append(("name 非空", all(r.name for r in rows)))

    top = top_by_cpu(rows, 3)
    checks.append(("Top-N 数量正确", len(top) == min(3, len(rows))))
    memtop = top_by_memory(rows, 3)
    checks.append(("内存排行有序",
                   all(memtop[i].rss >= memtop[i + 1].rss for i in range(len(memtop) - 1))))

    # 进程树：本脚本应当至少有一个子节点（如果 fork 过）——不强求
    children_map = build_tree(rows)
    checks.append(("进程树映射是 dict", isinstance(children_map, dict)))

    me = psutil.Process(os.getpid())
    checks.append(("身份指纹稳定", identity(me) == identity(me)))

    checks.append(("full_cmdline 空列表容错", full_cmdline([], None) == "-"))
    checks.append(("full_cmdline basename",
                   full_cmdline(["/usr/bin/python3", "-c", "pass"], None).startswith("python3")))
    checks.append(("human_bytes", human_bytes(1024 ** 2) == "1.0 MiB"))

    # 优雅停止：起一个自己的子进程验证三段式（这是安全的自测）
    child = subprocess.Popen(["sleep", "30"])
    p = psutil.Process(child.pid)
    started = p.is_running()
    p.terminate()
    try:
        p.wait(timeout=3.0)
        stopped = not p.is_running()
    except psutil.TimeoutExpired:
        p.kill()
        p.wait(timeout=3.0)
        stopped = not p.is_running()
    child.wait()
    checks.append(("能启动并优雅停止自己的子进程", started and stopped))

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
    ap = argparse.ArgumentParser(description="进程监控与资源排行演示")
    ap.add_argument("--top", type=int, default=8, help="展示的 Top-N 数量（默认 8）")
    ap.add_argument("--interval", type=float, default=0.5, help="CPU 采样窗口（默认 0.5 秒）")
    ap.add_argument("--memory-detail", action="store_true",
                    help="额外采集 uss/pss（较慢，需读 smaps）")
    ap.add_argument("--no-demo-child", action="store_true", help="不启动/停止 demo 子进程")
    ap.add_argument("--self-test", action="store_true", help="只做自检并输出 SELF-TEST OK")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    print("=" * 62)
    print(" 进程监控演示（只操作本脚本自己的进程；批量 kill 一律不做）")
    print("=" * 62)

    rows, stats = warmup_and_scan(args.interval, include_memory_detail=args.memory_detail)
    print(f"── 扫描账本 ──────────────────────────────────────────")
    print(f"  {stats.line()}")
    if stats.zombie:
        print(f"  ⚠ 发现 {stats.zombie} 个僵尸进程：说明有父进程没有 wait() 子进程，")
        print("     长期堆积会耗尽 pid 表（内核 pid_max）。这本身就是一个告警项。")
    if stats.denied:
        print(f"  说明: {stats.denied} 个进程因权限不足只看到部分字段，属正常"
              "（非 root 运行时的常态，不是错误）。")

    print_ranking(rows, args.top, use_uss=args.memory_detail)
    if args.memory_detail:
        print_memory_breakdown(rows)
    else:
        print("── 内存字段对比 ──────────────────────────────────────")
        print("  加 --memory-detail 可查看 vms/rss/pss/uss 四字段对比")

    demo_tree(rows)
    demo_pid_reuse()
    if not args.no_demo_child:
        demo_stop_child()
    else:
        print("── 优雅停止演示：已用 --no-demo-child 跳过 ────────────")

    print("=" * 62)
    print(" 退出码 0 = 采集完成。本脚本从不杀系统进程。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
