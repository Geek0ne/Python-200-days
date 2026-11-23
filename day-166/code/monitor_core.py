"""监控核心逻辑（Day 166 — 系统监控 psutil）。

供 `05-monitor-tool.py` 使用。把"采集 / 差分 / 判定 / 渲染"四件事分开，
是为了让它们各自可测、可替换：

    Collector   → 只负责"把此刻的系统状态变成一个 Sample"
    safe_rate   → 只负责"两次计数器读数 → 速率（含重置防护）"
    Threshold   → 只负责"一串数值 → 告警状态（含滞回去抖）"
    render_*    → 只负责"样本列表 → JSON / Markdown 文本"

⚠ 本模块只读取系统指标，不做任何修改，不启动/停止任何进程。
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

import psutil


# ── 常量 ─────────────────────────────────────────────────────────────────

EXIT_OK = 0          # 采集成功，所有指标在阈值内
EXIT_ERROR = 1       # 采集失败 / 参数错误（"我的错"）
EXIT_ALERT = 2       # 采集成功但触发告警（"被监控对象的问题"）

# 只读/伪文件系统：percent 恒为 100%，必须过滤，否则全是假警报。
PSEUDO_FSTYPES = {
    "squashfs", "iso9660", "udf", "devtmpfs", "tmpfs", "proc", "sysfs",
    "cgroup", "cgroup2", "overlay", "ramfs", "autofs", "mqueue", "debugfs",
    "tracefs", "securityfs", "pstore", "bpf", "configfs", "fusectl", "hugetlbfs",
}


# ── 小工具 ───────────────────────────────────────────────────────────────

def human_bytes(n: float) -> str:
    """字节 → 可读字符串（1024 进制，与 free -h 口径一致）。"""
    step = 1024.0
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if abs(n) < step:
            return f"{n:,.1f} {unit}"
        n /= step
    return f"{n:,.1f} EiB"


def safe_rate(prev: float, cur: float, dt: float) -> float | None:
    """(计数器差分 ÷ 实测间隔) → 速率；不可信时返回 None。

    三种不可信情况：
      1) dt <= 0              —— 时钟异常或除零
      2) cur < prev           —— 计数器被重置（网卡/容器重启）或回绕
      3) dt 大得离谱          —— 进程被挂起/系统休眠，平均值已无意义
    返回 None 让调用方**显式**处理，而不是拿到一个荒谬的数字。
    """
    if dt <= 0:
        return None
    delta = cur - prev
    if delta < 0:
        return None
    return delta / dt


# ── 阈值判定（滞回 + 连续次数去抖）───────────────────────────────────────

@dataclass
class Threshold:
    """带滞回（hysteresis）与连续次数去抖的阈值判定。

    为什么不能"超过阈值就告警"？
      真实指标会在阈值附近来回抖动（79/81/79/81...），朴素写法会每帧发一次告警，
      运维收到几百条通知后就会开始无视所有告警 —— 这叫告警疲劳，
      它比"漏报一次"危险得多。

    两个机制各管一件事：
      - 滞回带 [low, high)：进入告警要 >= high，退出告警要 < low。
        low < high 让边界抖动**无法**翻转状态。
      - need 连续次数：要求连续 need 次满足条件才真正翻转，
        过滤掉孤立尖峰（一次 GC 造成的瞬时打满）。
    """

    name: str
    high: float
    low: float
    need: int = 2
    unit: str = "%"
    state: bool = False
    _streak: int = 0
    transitions: int = 0

    def __post_init__(self) -> None:
        if self.low >= self.high:
            raise ValueError(
                f"{self.name}: low({self.low}) 必须小于 high({self.high})，"
                "否则滞回带为空，去抖失效"
            )
        if self.need < 1:
            raise ValueError(f"{self.name}: need 必须 >= 1")

    def feed(self, value: float) -> bool:
        """送入一个样本，返回当前告警状态。"""
        if self.state:
            if value < self.low:
                self._streak += 1
                if self._streak >= self.need:
                    self.state, self._streak = False, 0
                    self.transitions += 1
            else:
                # 已在告警态、但还没低于 low：重置"恢复计数"。
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

    def describe(self) -> str:
        return (f"{self.name}: 告警阈值 ≥{self.high:g}{self.unit}，"
                f"恢复阈值 <{self.low:g}{self.unit}，连续 {self.need} 次才翻转")


@dataclass
class Alert:
    """一条告警记录。"""

    ts: float
    metric: str
    value: float
    threshold: float
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── 样本 ─────────────────────────────────────────────────────────────────

@dataclass
class Sample:
    """一次完整采样的结果。所有字段都是"那一刻"的读数。"""

    ts: float                      # 单调时钟（用于算间隔）
    wall_ts: float                 # 墙上时间（用于展示）
    cpu_percent: float
    cpu_per_core: list[float]
    load_avg: tuple[float, float, float] | None
    mem_total: int
    mem_available: int
    mem_percent: float
    swap_percent: float | None
    disk_percent: float            # 最有压力的那个真实分区
    disk_mount: str
    disk_worst: list[dict[str, Any]] = field(default_factory=list)
    net_sent_per_s: float | None = None
    net_recv_per_s: float | None = None
    disk_read_per_s: float | None = None
    disk_write_per_s: float | None = None
    proc_count: int = 0
    proc_zombie: int = 0
    proc_top_cpu: list[dict[str, Any]] = field(default_factory=list)
    proc_top_mem: list[dict[str, Any]] = field(default_factory=list)
    cgroup_mem_limit: int | None = None
    cgroup_mem_current: int | None = None
    cgroup_cpu_quota: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── 采集器 ───────────────────────────────────────────────────────────────

class Collector:
    """系统指标采集器。

    用法（顺序很重要）：
        c = Collector(include_processes=True)
        c.warmup()                 # ① 建立 CPU / 计数器基准（否则第一轮全是 0）
        s0 = c.collect()           # ② 第一轮
        time.sleep(interval)
        s1 = c.collect()           # ③ 第二轮：此时速率类字段才有意义
    """

    def __init__(self, include_processes: bool = True, top_n: int = 5) -> None:
        self.include_processes = include_processes
        self.top_n = top_n
        self._prev_net: tuple[float, int, int] | None = None
        self._prev_disk: tuple[float, int, int] | None = None
        self.self_pid = os.getpid()

    # -- 预热 ---------------------------------------------------------
    def warmup(self) -> None:
        """建立所有"需要两次读数"的基准。返回值全部丢弃。"""
        psutil.cpu_percent(interval=None)             # 系统级 CPU 基准
        psutil.process_iter(attrs=["pid", "cpu_percent"], ad_value=None)  # 进程级基准
        net = psutil.net_io_counters()
        disk = psutil.disk_io_counters()
        t = time.monotonic()
        self._prev_net = (t, net.bytes_sent, net.bytes_recv) if net else None
        self._prev_disk = (t, disk.read_bytes, disk.write_bytes) if disk else None

    # -- 单次采集 -----------------------------------------------------
    def collect(self) -> Sample:
        now = time.monotonic()
        cpu = psutil.cpu_percent(interval=None)          # 非阻塞，窗口 = 距上次调用
        per_core = psutil.cpu_percent(percpu=True)

        try:
            load = psutil.getloadavg()
        except (AttributeError, OSError):
            load = None

        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()

        worst_percent, worst_mount = 0.0, "-"
        worst_list: list[dict[str, Any]] = []
        for part in psutil.disk_partitions(all=False):
            if part.fstype in PSEUDO_FSTYPES:
                continue
            try:
                u = psutil.disk_usage(part.mountpoint)
            except (PermissionError, FileNotFoundError, OSError):
                continue      # 已卸载/不可达：单个分区失败不能拖垮整轮
            worst_list.append({
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "percent": round(u.percent, 1),
                "free": u.free,
                "total": u.total,
            })
            if u.percent > worst_percent:
                worst_percent, worst_mount = u.percent, part.mountpoint

        # 速率类字段：需要上一次读数
        net_sent = net_recv = disk_read = disk_write = None
        net = psutil.net_io_counters()
        if net and self._prev_net:
            t0, s0, r0 = self._prev_net
            dt = now - t0
            net_sent = safe_rate(s0, net.bytes_sent, dt)
            net_recv = safe_rate(r0, net.bytes_recv, dt)
            self._prev_net = (now, net.bytes_sent, net.bytes_recv)
        disk_io = psutil.disk_io_counters()
        if disk_io and self._prev_disk:
            t0, rd0, wr0 = self._prev_disk
            dt = now - t0
            disk_read = safe_rate(rd0, disk_io.read_bytes, dt)
            disk_write = safe_rate(wr0, disk_io.write_bytes, dt)
            self._prev_disk = (now, disk_io.read_bytes, disk_io.write_bytes)

        proc_count = zombie = 0
        top_cpu: list[dict[str, Any]] = []
        top_mem: list[dict[str, Any]] = []
        if self.include_processes:
            rows: list[dict[str, Any]] = []
            for proc in psutil.process_iter(
                    attrs=["pid", "name", "cpu_percent", "memory_info",
                           "num_threads", "status"], ad_value=None):
                try:
                    info = proc.info
                    if info["pid"] == self.self_pid:
                        continue                      # 排除监控自身（观测者效应）
                    proc_count += 1
                    if info.get("status") == psutil.STATUS_ZOMBIE:
                        zombie += 1
                    mi = info.get("memory_info")
                    rows.append({
                        "pid": info["pid"],
                        "name": (info.get("name") or "?")[:48],
                        "cpu": round(float(info.get("cpu_percent") or 0.0), 1),
                        "rss": getattr(mi, "rss", 0) or 0,
                        "threads": int(info.get("num_threads") or 0),
                    })
                except psutil.NoSuchProcess:
                    continue
                except psutil.AccessDenied:
                    continue
                except psutil.ZombieProcess:
                    zombie += 1
                    continue
                # 其它异常（含自己写错的）故意不捕 —— 必须暴露出来
            top_cpu = sorted(rows, key=lambda r: r["cpu"], reverse=True)[:self.top_n]
            top_mem = sorted(rows, key=lambda r: r["rss"], reverse=True)[:self.top_n]

        return Sample(
            ts=now,
            wall_ts=time.time(),
            cpu_percent=round(cpu, 1),
            cpu_per_core=[round(v, 1) for v in per_core],
            load_avg=tuple(round(v, 2) for v in load) if load else None,   # type: ignore[arg-type]
            mem_total=vm.total,
            mem_available=vm.available,
            mem_percent=round(vm.percent, 1),
            swap_percent=round(sw.percent, 1) if sw.total else None,
            disk_percent=round(worst_percent, 1),
            disk_mount=worst_mount,
            disk_worst=sorted(worst_list, key=lambda d: d["percent"], reverse=True)[:3],
            net_sent_per_s=net_sent,
            net_recv_per_s=net_recv,
            disk_read_per_s=disk_read,
            disk_write_per_s=disk_write,
            proc_count=proc_count,
            proc_zombie=zombie,
            proc_top_cpu=top_cpu,
            proc_top_mem=top_mem,
            cgroup_mem_limit=read_cgroup_memory_limit(),
            cgroup_mem_current=read_cgroup_memory_current(),
            cgroup_cpu_quota=read_cgroup_cpu_quota(),
        )


# ── cgroup（容器真实限额）─────────────────────────────────────────────────

def read_cgroup_memory_limit() -> int | None:
    """容器内存限额（字节）；无限制/不支持返回 None。"""
    try:
        with open("/sys/fs/cgroup/memory.max", encoding="utf-8") as fh:
            raw = fh.read().strip()
        if raw and raw != "max":
            return int(raw)
    except (OSError, ValueError):
        pass
    try:
        with open("/sys/fs/cgroup/memory/memory.limit_in_bytes", encoding="utf-8") as fh:
            val = int(fh.read().strip())
        return val if val < (1 << 62) else None      # v1 用极大值表示无限制
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
    """CPU 限额（单位：核）。cpu.max 形如 "50000 100000" = 0.5 核。"""
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
        return quota / period if quota > 0 and period > 0 else None
    except (OSError, ValueError):
        return None


# ── 判定 ─────────────────────────────────────────────────────────────────

def evaluate(sample: Sample, thresholds: dict[str, Threshold],
             alerts: list[Alert]) -> dict[str, bool]:
    """把样本喂给各阈值，返回 {指标名: 是否告警}，并把新翻转记入 alerts。

    只在新进入告警态时记一条 Alert（由 Threshold.transitions 保证），
    避免每轮都刷一条相同告警 —— 这与 9 号陷阱是同一个问题。
    """
    values = {
        "cpu": sample.cpu_percent,
        "mem": sample.mem_percent,
        "disk": sample.disk_percent,
    }
    state: dict[str, bool] = {}
    for key, th in thresholds.items():
        v = values.get(key)
        if v is None:
            continue
        before = th.transitions
        now_state = th.feed(v)
        state[key] = now_state
        if th.transitions > before and now_state:      # 刚进入告警
            alerts.append(Alert(
                ts=sample.wall_ts,
                metric=key,
                value=v,
                threshold=th.high,
                message=(f"{th.name} 达到 {v:g}{th.unit}，"
                         f"超过阈值 {th.high:g}{th.unit}"
                         f"（连续 {th.need} 次确认）"),
            ))
    # 僵尸进程是"状态类"信号：出现即值得记录，不做去抖
    if sample.proc_zombie > 0:
        state["zombie"] = True
    return state


# ── 渲染 ─────────────────────────────────────────────────────────────────

def render_json(samples: list[Sample], alerts: list[Alert],
                meta: dict[str, Any]) -> str:
    """稳定、可 diff 的 JSON 报告。"""
    doc = {
        "generated_by": "day-166 系统监控（psutil）",
        "meta": meta,
        "summary": summarize(samples, alerts),
        "samples": [s.to_dict() for s in samples],
        "alerts": [a.to_dict() for a in alerts],
    }
    return json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True)


def summarize(samples: list[Sample], alerts: list[Alert]) -> dict[str, Any]:
    """汇总统计。空样本时返回零值而不是抛异常。"""
    if not samples:
        return {"count": 0}
    cpu = [s.cpu_percent for s in samples]
    mem = [s.mem_percent for s in samples]
    disk = [s.disk_percent for s in samples]
    return {
        "count": len(samples),
        "duration_s": round(samples[-1].wall_ts - samples[0].wall_ts, 3),
        "cpu": {"avg": round(sum(cpu) / len(cpu), 2), "max": max(cpu)},
        "mem": {"avg": round(sum(mem) / len(mem), 2), "max": max(mem)},
        "disk": {"avg": round(sum(disk) / len(disk), 2), "max": max(disk)},
        "alerts": len(alerts),
        "zombie_max": max(s.proc_zombie for s in samples),
    }


def render_markdown(samples: list[Sample], alerts: list[Alert],
                    meta: dict[str, Any]) -> str:
    """人类可读的 Markdown 报告。"""
    lines: list[str] = []
    lines.append("# 系统监控报告")
    lines.append("")
    lines.append(f"- 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    lines.append(f"- 采样点数: {len(samples)}")
    for k, v in meta.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    # 告警优先——报告的第一屏必须是"有没有问题"，而不是"数据长什么样"。
    lines.append("## 告警")
    if alerts:
        for a in alerts:
            ts = time.strftime("%H:%M:%S", time.localtime(a.ts))
            lines.append(f"- ⚠ [{ts}] {a.message}")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 汇总")
    s = summarize(samples, alerts)
    if s.get("count"):
        lines.append("| 指标 | 平均 | 峰值 |")
        lines.append("|:---|:---:|:---:|")
        lines.append(f"| CPU | {s['cpu']['avg']}% | {s['cpu']['max']}% |")
        lines.append(f"| 内存 | {s['mem']['avg']}% | {s['mem']['max']}% |")
        lines.append(f"| 磁盘 | {s['disk']['avg']}% | {s['disk']['max']}% |")
        lines.append("")
        lines.append(f"僵尸进程峰值: {s['zombie_max']}")
    lines.append("")

    lines.append("## 采样明细")
    lines.append("")
    lines.append("| 时刻 | CPU% | 内存% | 磁盘% | NET↑ | NET↓ |")
    lines.append("|:---|:---:|:---:|:---:|:---:|:---:|")
    for smp in samples:
        ts = time.strftime("%H:%M:%S", time.localtime(smp.wall_ts))
        up = human_bytes(smp.net_sent_per_s) + "/s" if smp.net_sent_per_s is not None else "-"
        down = human_bytes(smp.net_recv_per_s) + "/s" if smp.net_recv_per_s is not None else "-"
        lines.append(f"| {ts} | {smp.cpu_percent} | {smp.mem_percent} | "
                     f"{smp.disk_percent} | {up} | {down} |")
    lines.append("")

    if samples and samples[-1].proc_top_cpu:
        last = samples[-1]
        lines.append("## 最后一轮的进程 Top（已排除监控自身）")
        lines.append("")
        lines.append("| PID | CPU% | RSS | 线程 | 名称 |")
        lines.append("|:---:|:---:|:---:|:---:|:---|")
        for row in last.proc_top_cpu:
            lines.append(f"| {row['pid']} | {row['cpu']} | {human_bytes(row['rss'])} "
                         f"| {row['threads']} | {row['name']} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("> 退出码约定：0 = 正常，2 = 触发告警，1 = 采集失败。")
    lines.append("> 数据均为只读采集；本工具不修改任何系统状态。")
    lines.append("")
    return "\n".join(lines)


def describe_thresholds(thresholds: Iterable[Threshold]) -> list[str]:
    return [t.describe() for t in thresholds]
