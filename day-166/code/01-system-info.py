#!/usr/bin/env python3
"""基础用法：系统信息采集（Day 166 — 系统监控 psutil）。

本文件演示 psutil 最常用的一组"读取本机状态"API：
1. CPU：核数 / 使用率 / 负载 / 累计时间
2. 内存：物理内存 / swap，重点区分 used 与 available
3. 磁盘：分区空间（按挂载点遍历，绝不硬编码 "/"） + IO 累计计数器
4. 网络：逐网卡 IO 累计计数器 + 接口状态
5. 系统：开机时间 / 已运行时长 / 登录用户
6. 温度与电池：--sensors 时尝试读取（很多平台不支持，属正常）

⚠ 安全边界：
- 本文件**只读**，不修改任何系统状态，不发起任何网络请求。
- 不调用任何进程的 terminate/kill。

运行：
    python3 01-system-info.py                 # 打印一份系统快照
    python3 01-system-info.py --sensors       # 额外尝试温度/电池/风扇
    python3 01-system-info.py --self-test     # 输出 SELF-TEST OK

依赖：
    pip install psutil
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
import time
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - 仅在未安装依赖时触发
    print("缺少依赖：请先执行  pip install psutil", file=sys.stderr)
    raise SystemExit(1)


# ── 小工具 ────────────────────────────────────────────────────────────────

def human_bytes(n: float) -> str:
    """把字节数格式化成人类可读（GiB/MiB/KiB）。

    为什么用 1024 而不是 1000？
      psutil 的所有内存/磁盘字段都是"字节"，而内核与 `free -h` 的惯例是 1024 进制。
      混用 1000 会让你算出来的值和运维同事看到的差 7%，对不上账。
    """
    step = 1024.0
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if abs(n) < step:
            return f"{n:,.1f} {unit}"
        n /= step
    return f"{n:,.1f} EiB"


def human_seconds(sec: float) -> str:
    """把秒数格式化成 "3d 4h 5m 6s" 这样的可读形式。"""
    sec = max(0, int(sec))
    d, rem = divmod(sec, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h or d:
        parts.append(f"{h}h")
    if m or h or d:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def safe(value: Any, default: str = "N/A") -> str:
    """把可能为 None / 抛异常的取值统一成可打印字符串。

    为什么需要它？
      很多 psutil 字段在特定平台是 None（如 cpu_count(logical=False)、
      cpu_freq()、macOS 的 sensors_temperatures()）。
      直接 f-string 会打印出难看的 None，且在 f"{None:.1f}" 时直接 TypeError。
    """
    return default if value is None else str(value)


# ── 1. CPU ───────────────────────────────────────────────────────────────

def show_cpu(interval: float) -> None:
    print("── CPU ────────────────────────────────────────────────")

    logical = psutil.cpu_count(logical=True)
    physical = psutil.cpu_count(logical=False)
    # 为什么物理核可能是 None？某些容器/虚拟化环境拿不到 CPU 拓扑信息。
    print(f"  逻辑核数 : {safe(logical)}")
    print(f"  物理核数 : {safe(physical, '未知（虚拟化/容器下常见）')}")

    freq = psutil.cpu_freq()
    if freq:
        print(f"  主频     : {freq.current:.0f} MHz (min {freq.min:.0f} / max {freq.max:.0f})")
    else:
        print("  主频     : N/A（该平台或容器不暴露 cpufreq）")

    # 系统级使用率：阻塞 interval 秒后返回"过去 interval 秒的平均值"。
    # ★ 这是唯一不需要自己预热的写法（psutil 内部自己拿了两次读数）。
    overall = psutil.cpu_percent(interval=interval)
    print(f"  总使用率 : {overall:5.1f}%  (窗口 {interval}s，为窗口内平均值)")

    # 逐核：能看出"是否只有单核打满"（单核 100% 往往意味着程序没有并行化）。
    per_core = psutil.cpu_percent(percpu=True)   # 非阻塞：复用上一次基准
    if per_core:
        shown = " ".join(f"{v:5.1f}" for v in per_core[:16])
        print(f"  逐核(%)  : {shown}" + (" ..." if len(per_core) > 16 else ""))

    # 负载均值：反映"运行队列长度"，不是百分比。
    try:
        l1, l5, l15 = psutil.getloadavg()
        cores = logical or 1
        print(f"  负载均值 : 1m={l1:.2f} 5m={l5:.2f} 15m={l15:.2f} "
              f"(核数 {cores}；> {cores} 表示有任务在排队)")
    except (AttributeError, OSError):
        print("  负载均值 : N/A（该平台不支持 getloadavg）")

    cs = psutil.cpu_stats()
    print(f"  上下文切换/中断（开机以来累计）: "
          f"ctx_switches={cs.ctx_switches:,} interrupts={cs.interrupts:,}")

    ct = psutil.cpu_times()
    # ★ 这是"累计刻度"，不要当使用率用。
    print(f"  CPU 累计时间: user={ct.user:.1f}s system={ct.system:.1f}s "
          f"idle={ct.idle:.1f}s iowait={getattr(ct, 'iowait', 0.0):.1f}s")
    print("  ⚠ 注意：上面是开机以来的累计秒数，只能用于差分，不能当使用率。")


# ── 2. 内存 ──────────────────────────────────────────────────────────────

def show_memory() -> None:
    print("── 内存 ───────────────────────────────────────────────")
    vm = psutil.virtual_memory()

    print(f"  总内存   : {human_bytes(vm.total)}")
    print(f"  可用     : {human_bytes(vm.available)}   ← 判断容量请用这个")
    print(f"  Used     : {human_bytes(vm.used)}   ← 含 page cache，常年偏高属正常")
    print(f"  Free     : {human_bytes(vm.free)}")
    print(f"  使用率   : {vm.percent:5.1f}%  (= (total-available)/total)")

    # 解释一下为什么 available 才是重点，避免读者误判。
    if vm.percent >= 80:
        print("  ⚠ 提示：used 口径偏高不代表危险；Linux 会主动用空闲内存做 page cache，")
        print("          这些内存在应用需要时可立即回收。请结合 available 判断。")

    sw = psutil.swap_memory()
    if sw.total:
        print(f"  Swap     : {human_bytes(sw.used)} / {human_bytes(sw.total)} "
              f"({sw.percent:.1f}%)  sin={sw.sin} sout={sw.sout} 页(累计)")
    else:
        print("  Swap     : 未启用（total=0；生产机上建议确认这是有意为之）")

    # 容器的真相：容器里 virtual_memory() 给的是宿主机的总量。
    limit = cgroup_memory_limit()
    if limit is not None:
        print(f"  ★ 容器限额: {human_bytes(limit)}  ← 这才是你的真实上限（cgroup）")
        if limit < vm.total:
            print("     （psutil.virtual_memory().total 读到的是宿主机内存，不要用它做容量判断）")


def cgroup_memory_limit() -> int | None:
    """读取容器内存限额（字节）。不支持的平台/环境返回 None。

    为什么必须自己读 cgroup？
      容器默认与宿主机共享 /proc 的一部分视图，/proc/meminfo 的 MemTotal
      是【整机】内存。用 64GiB 的阈值去监控一个 512MiB 的容器 = 永不告警。
    """
    # cgroup v2（现代发行版）
    v2 = "/sys/fs/cgroup/memory.max"
    try:
        with open(v2, encoding="utf-8") as fh:
            raw = fh.read().strip()
        if raw and raw != "max":
            return int(raw)
    except (OSError, ValueError):
        pass
    # cgroup v1（老发行版）
    v1 = "/sys/fs/cgroup/memory/memory.limit_in_bytes"
    try:
        with open(v1, encoding="utf-8") as fh:
            val = int(fh.read().strip())
        # v1 用"接近 2^63 的极大值"表示无限制，必须挡掉，否则会算出荒谬的限额。
        if val < (1 << 62):
            return val
    except (OSError, ValueError):
        pass
    return None


# ── 3. 磁盘 ──────────────────────────────────────────────────────────────

# 只读/伪文件系统：这类挂载点的 percent 恒为 100%（它们本来就是满的只读镜像），
# 拿来做磁盘告警是纯粹的噪声。真实运维里必须过滤掉，否则一屏全是假警报。
PSEUDO_FSTYPES = {
    "squashfs",  # snap / AppImage 的只读镜像（本次实测就是它刷屏）
    "iso9660",   # 光盘镜像
    "udf",       # 光盘/UDF 镜像
    "devtmpfs", "tmpfs", "proc", "sysfs", "cgroup", "cgroup2", "overlay",
    "ramfs", "autofs", "mqueue", "debugfs", "tracefs", "securityfs",
    "pstore", "bpf", "configfs", "fusectl", "hugetlbfs",
}


def show_disk() -> None:
    print("── 磁盘 ───────────────────────────────────────────────")
    parts = psutil.disk_partitions(all=False)
    print(f"  挂载点数量: {len(parts)}"
          "（all=False 只过滤了部分伪文件系统，仍需自行过滤）")

    # 先记下被过滤掉的，避免"静默丢数据" —— 过滤必须可见。
    skipped: list[str] = []
    checked = 0

    for part in parts:
        if part.fstype in PSEUDO_FSTYPES:
            skipped.append(part.mountpoint)
            continue
        # 为什么每个挂载点都要 try？
        #   1) 挂载点可能在两次调用之间被卸载（NoSuchFile/OSError）
        #   2) 网络文件系统不可达时会阻塞或报错
        #   3) 权限不足（如只允许 root 访问的挂载点）
        # 采集脚本的底线是"任何一个分区坏了都不能拖垮整轮采集"。
        try:
            u = psutil.disk_usage(part.mountpoint)
        except (PermissionError, FileNotFoundError, OSError) as exc:
            print(f"     {part.mountpoint:24s} [跳过: {type(exc).__name__}]")
            continue
        checked += 1
        flag = "⚠" if u.percent >= 85 else " "
        print(f" {flag}{part.mountpoint:24s} {u.percent:5.1f}%  "
              f"free {human_bytes(u.free):>10s}  / total {human_bytes(u.total):>10s}  "
              f"[{part.fstype}]")

    few = ", ".join(skipped[:3]) + (" ..." if len(skipped) > 3 else "")
    print(f"  已检查 {checked} 个真实分区；过滤伪文件系统 {len(skipped)} 个（如 {few}）")
    print("  提示: 过滤是必要的，但必须把过滤数量打出来 —— 否则你永远不知道漏了什么。")

    # IO 计数器：全是"开机以来累计"，只能差分用。
    io = psutil.disk_io_counters()
    if io:
        print(f"  磁盘 IO（累计）: read={human_bytes(io.read_bytes)} "
              f"write={human_bytes(io.write_bytes)}")
        print(f"              busy_time: read={io.read_time:,}ms write={io.write_time:,}ms（累计）")
        print("  ⚠ 这些是累计值；要得到「每秒读写速率」，必须间隔采样后相减（见 04-benchmark.py）。")
    else:
        print("  磁盘 IO: N/A（部分容器不暴露 /proc/diskstats）")

    # 空间 vs 忙碌是两个不同的东西，这里显式澄清。
    print("  提示: disk_usage 看【空间占用】，disk_io_counters 看【吞吐与忙碌度】，两者无关。")


# ── 4. 网络 ──────────────────────────────────────────────────────────────

def show_network() -> None:
    print("── 网络 ───────────────────────────────────────────────")
    stats = psutil.net_if_stats()
    per_nic = psutil.net_io_counters(pernic=True)

    for nic, st in sorted(stats.items()):
        io = per_nic.get(nic)
        state = "UP  " if st.isup else "down"
        speed = f"{st.speed}Mbps" if st.speed else "speed=?"
        if io:
            counts = (f"sent {human_bytes(io.bytes_sent)} / recv {human_bytes(io.bytes_recv)}"
                      f"  err {io.errin + io.errout}  drop {io.dropin + io.dropout}")
        else:
            counts = "（无计数器）"
        print(f"  [{state}] {nic:16s} {speed:>10s}  {counts}")

    total = psutil.net_io_counters()
    print(f"  合计（累计）: sent={human_bytes(total.bytes_sent)} recv={human_bytes(total.bytes_recv)}")
    if total.errin + total.errout or total.dropin + total.dropout:
        print("  ⚠ 检测到 err/drop 非零：网卡在丢包或报错（本身就是值得记的异常信号）。")


# ── 5. 系统信息 ──────────────────────────────────────────────────────────

def show_system() -> None:
    print("── 系统 ───────────────────────────────────────────────")
    boot = psutil.boot_time()
    now = time.time()
    print(f"  开机时刻 : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(boot))}")
    print(f"  已运行   : {human_seconds(now - boot)}")
    print(f"  主机名   : {platform.node()}")
    print(f"  系统     : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"  Python   : {platform.python_version()}  psutil {psutil.__version__}")
    print(f"  PID      : {os.getpid()}  ← 监控进程自己也会占用 CPU/内存（观测者效应）")

    users = psutil.users()
    if users:
        print(f"  登录用户 : {len(users)} 个")
        for u in users[:5]:
            started = time.strftime("%m-%d %H:%M", time.localtime(u.started))
            print(f"      {u.name:12s} tty={u.terminal or '-':10s} host={u.host or '-':16s} since {started}")
    else:
        print("  登录用户 : 无记录（容器里常见）")


# ── 6. 传感器（可选）─────────────────────────────────────────────────────

def show_sensors() -> None:
    print("── 传感器 ─────────────────────────────────────────────")
    temps = psutil.sensors_temperatures() or {}
    if temps:
        for chip, entries in temps.items():
            for e in entries:
                label = e.label or chip
                print(f"  {label:24s} {e.current:6.1f}°C"
                      f"{f'  (high {e.high:.1f})' if e.high else ''}")
    else:
        print("  温度: N/A（macOS/Windows 通常不支持；容器里也读不到宿主的 hwmon）")

    fans = psutil.sensors_fans() or {}
    if fans:
        for chip, entries in fans.items():
            for e in entries:
                print(f"  fan {e.label or chip:20s} {e.current} RPM")
    else:
        print("  风扇: N/A")

    bat = psutil.sensors_battery()
    if bat:
        plug = "已接电源" if bat.power_plugged else "电池供电"
        print(f"  电池: {bat.percent:.0f}%  {plug}"
              f"{f'  剩余 {bat.secsleft}s' if isinstance(bat.secsleft, int) else ''}")
    else:
        print("  电池: 无（台式机/服务器/容器）")


# ── 主流程 ───────────────────────────────────────────────────────────────

def self_test() -> int:
    """不依赖具体数值的自检：只验证各 API 能调用且类型合理。"""
    checks: list[tuple[str, bool]] = []

    checks.append(("cpu_count", isinstance(psutil.cpu_count(logical=True), int)))
    checks.append(("cpu_percent 范围", 0.0 <= psutil.cpu_percent(interval=0.05) <= 100.0))
    per = psutil.cpu_percent(percpu=True)
    checks.append(("percpu 列表", isinstance(per, list) and len(per) >= 1))

    vm = psutil.virtual_memory()
    checks.append(("内存总量 > 0", vm.total > 0))
    checks.append(("内存 available <= total", 0 <= vm.available <= vm.total))

    parts = psutil.disk_partitions(all=False)
    checks.append(("分区列表非空", len(parts) >= 1))
    if parts:
        try:
            u = psutil.disk_usage(parts[0].mountpoint)
            checks.append(("disk_usage 合理", 0 <= u.percent <= 100))
        except (PermissionError, FileNotFoundError, OSError):
            checks.append(("disk_usage 可访问", False))

    checks.append(("boot_time 在过去", psutil.boot_time() <= time.time()))

    me = psutil.Process(os.getpid())
    checks.append(("自己的 pid 一致", me.pid == os.getpid()))
    checks.append(("自己内存 rss > 0", me.memory_info().rss > 0))
    checks.append(("自己 status 是字符串", isinstance(me.status(), str)))
    checks.append(("human_bytes", human_bytes(1024 ** 3) == "1.0 GiB"))
    checks.append(("human_seconds", human_seconds(90061) == "1d 1h 1m 1s"))

    ok = True
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed

    if ok:
        print("SELF-TEST OK")
        return 0
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="系统信息采集（只读，安全）")
    ap.add_argument("--interval", type=float, default=0.5,
                    help="CPU 使用率采样窗口秒数（默认 0.5）")
    ap.add_argument("--sensors", action="store_true", help="额外读取温度/风扇/电池")
    ap.add_argument("--self-test", action="store_true", help="只做自检并输出 SELF-TEST OK")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    print("=" * 62)
    print(" 系统信息快照（所有数据均为只读采集）")
    print("=" * 62)

    # ★ 预热：让后续所有 cpu_percent() 调用都有参照物，避免 0.0 的迷惑值。
    psutil.cpu_percent(interval=None)

    show_cpu(args.interval)
    show_memory()
    show_disk()
    show_network()
    show_system()
    if args.sensors:
        show_sensors()

    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
