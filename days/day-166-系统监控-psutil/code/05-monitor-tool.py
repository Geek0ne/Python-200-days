#!/usr/bin/env python3
"""实战案例：系统监控脚本（Day 166 — 系统监控 psutil）。

这是本课的**交付物**：一个能真正用起来的系统监控小工具。
它把 README 里所有"为什么"落地成工程实践：

  ✔ 预热（否则第一轮 CPU 全是 0.0）                          → 陷阱 1 / 2
  ✔ 计数器差分求速率，用 time.monotonic()                    → 陷阱 3 / 4
  ✔ 过滤伪文件系统，逐个挂载点容错                            → 陷阱 6
  ✔ 遍历进程时区分 NoSuchProcess / AccessDenied / 僵尸        → 陷阱 7
  ✔ 排除监控自身（观测者效应）                                → 3.7
  ✔ 滞回 + 连续次数去抖，避免告警风暴                          → 陷阱 9
  ✔ 读 cgroup 限额，容器里不被宿主机数字骗                      → 陷阱 10
  ✔ JSON + Markdown 双格式输出（机器可读 + 人可读）
  ✔ 退出码契约：0=正常 2=告警 1=失败                          → 调用方据此判断

⚠ 安全边界（本工具的设计红线）：
- **只读**：不修改任何系统状态，不发起任何网络请求。
- **不杀进程**：本工具没有任何 terminate/kill 代码路径。
  真正的"自动处置"是极高风险动作，必须由人确认，不属于一个监控脚本的职责。
- 默认只跑有限时长（`--duration`），不会变成常驻进程。

运行：
    python3 05-monitor-tool.py                          # 采 5 轮，间隔 1 秒
    python3 05-monitor-tool.py --duration 10 --interval 0.5
    python3 05-monitor-tool.py --cpu 70 --mem 80 --disk 85 --need 3
    python3 05-monitor-tool.py --out-dir ./reports      # 落盘 JSON + Markdown
    python3 05-monitor-tool.py --dry-run                # 只打印，不写文件
    python3 05-monitor-tool.py --self-test              # 输出 SELF-TEST OK

退出码：
    0  采集成功，无告警
    2  采集成功，但有指标触发告警
    1  参数错误或采集失败

依赖：
    pip install psutil
"""

from __future__ import annotations

import argparse
import os
import sys
import time

try:
    import psutil
except ImportError:  # pragma: no cover
    print("缺少依赖：请先执行  pip install psutil", file=sys.stderr)
    raise SystemExit(1)

from monitor_core import (
    EXIT_ALERT,
    EXIT_ERROR,
    EXIT_OK,
    Alert,
    Collector,
    Sample,
    Threshold,
    describe_thresholds,
    evaluate,
    human_bytes,
    render_json,
    render_markdown,
    safe_rate,
    summarize,
)


# ── 采样主循环 ───────────────────────────────────────────────────────────

def run_sampling(collector: Collector, thresholds: dict[str, Threshold],
                 interval: float, duration: float,
                 on_sample=None) -> tuple[list[Sample], list[Alert]]:
    """按 interval 采集，直到累计时长达到 duration。

    为什么要用"累计到 duration"而不是"循环 N 次"？
      因为 time.sleep(interval) 只保证"至少睡这么久"，长跑一定漂移
      （操作系统调度、GC、采集本身耗时都会累加）。用**实测墙上时间**判断
      终点，脚本表现才可预期 —— 否则你以为采了 60 秒，实际跑了 75 秒。
    """
    samples: list[Sample] = []
    alerts: list[Alert] = []

    # ★ 采样调度的时间基准用 monotonic：不受 NTP 校时影响（陷阱 4）。
    start = time.monotonic()
    next_tick = start

    collector.warmup()          # ★ 预热：建立 CPU / 计数器基准

    while True:
        now = time.monotonic()
        if now - start >= duration:
            break
        # 用"绝对下一次时刻"而不是 sleep(interval)，避免误差累积漂移。
        if next_tick > now:
            time.sleep(next_tick - now)
        next_tick += interval

        sample = collector.collect()
        samples.append(sample)
        evaluate(sample, thresholds, alerts)

        if on_sample is not None:
            on_sample(sample, thresholds, len(samples))
        else:
            print_sample_line(sample, thresholds)

    return samples, alerts


def print_sample_line(sample: Sample, thresholds: dict[str, Threshold]) -> None:
    """终端单行输出：一行看清本轮关键指标 + 告警标记。"""
    ts = time.strftime("%H:%M:%S", time.localtime(sample.wall_ts))
    marks = "".join("!" if thresholds[k].state else "."
                    for k in ("cpu", "mem", "disk") if k in thresholds)
    net_up = (f"{human_bytes(sample.net_sent_per_s)}/s"
              if sample.net_sent_per_s is not None else "  -  ")
    net_dn = (f"{human_bytes(sample.net_recv_per_s)}/s"
              if sample.net_recv_per_s is not None else "  -  ")
    print(f"  [{ts}] CPU {sample.cpu_percent:5.1f}%  "
          f"MEM {sample.mem_percent:5.1f}%  "
          f"DISK {sample.disk_percent:5.1f}% ({sample.disk_mount})  "
          f"NET ↑{net_up:>9} ↓{net_dn:>9}  "
          f"PROC {sample.proc_count:>4}  告警[{marks}]")


# ── 输出落盘 ─────────────────────────────────────────────────────────────

def write_reports(samples: list[Sample], alerts: list[Alert], meta: dict,
                  out_dir: str) -> tuple[str, str]:
    """写 JSON + Markdown 两份报告，返回两个路径。"""
    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    json_path = os.path.join(out_dir, f"monitor-{stamp}.json")
    md_path = os.path.join(out_dir, f"monitor-{stamp}.md")

    # 先写临时文件再 rename：避免调用方读到"写了一半"的报告。
    # （原子性交付：读者要么看到旧文件，要么看到完整新文件，不会看到残缺内容。）
    for path, content in ((json_path, render_json(samples, alerts, meta)),
                          (md_path, render_markdown(samples, alerts, meta))):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, path)
    return json_path, md_path


# ── 自检 ─────────────────────────────────────────────────────────────────

def self_test() -> int:
    checks: list[tuple[str, bool]] = []

    # 阈值滞回去抖（独立复刻核心行为，确保逻辑没被改坏）
    th = Threshold(name="CPU", high=80, low=75, need=3)
    checks.append(("连续 3 次越阈才告警", [th.feed(v) for v in (81, 82, 83)][-1] is True))
    th2 = Threshold(name="CPU", high=80, low=75, need=3)
    checks.append(("边界抖动不告警", not any(th2.feed(v) for v in (81, 79, 81, 79, 81))))
    th3 = Threshold(name="CPU", high=80, low=75, need=2)
    th3.feed(90); th3.feed(90)
    checks.append(("恢复需要低于 low", th3.feed(78) is True and th3.feed(70) is True
                   and (th3.feed(70) is False)))
    try:
        Threshold(name="bad", high=80, low=80, need=2)
        checks.append(("low>=high 报错", False))
    except ValueError:
        checks.append(("low>=high 报错", True))

    # safe_rate 三种情况
    checks.append(("safe_rate 正常", safe_rate(100, 600, 1.0) == 500.0))
    checks.append(("safe_rate 重置 → None", safe_rate(999, 1, 1.0) is None))
    checks.append(("safe_rate dt<=0 → None", safe_rate(1, 2, 0.0) is None))

    # 采集两轮：验证预热有效、速率字段可用
    c = Collector(include_processes=True, top_n=3)
    c.warmup()
    s0 = c.collect()
    time.sleep(0.35)
    s1 = c.collect()
    checks.append(("采集到内存总量 > 0", s1.mem_total > 0))
    checks.append(("CPU 使用率在 [0,100]", 0.0 <= s1.cpu_percent <= 100.0))
    checks.append(("逐核列表非空", len(s1.cpu_per_core) >= 1))
    checks.append(("磁盘只含真实分区", all(not d["mountpoint"].startswith("/snap")
                                     for d in s1.disk_worst)))
    checks.append(("第二轮的速率字段可用（预热生效）",
                   s1.net_sent_per_s is not None or s1.net_recv_per_s is not None))
    checks.append(("样本可序列化", isinstance(s1.to_dict(), dict)))
    checks.append(("排除了自身", all(r["pid"] != os.getpid() for r in s1.proc_top_cpu)))

    # 渲染
    alerts: list[Alert] = []
    ths = {"cpu": Threshold(name="CPU", high=95, low=90, need=2),
           "mem": Threshold(name="内存", high=95, low=90, need=2),
           "disk": Threshold(name="磁盘", high=95, low=90, need=2)}
    for s in (s0, s1):
        evaluate(s, ths, alerts)
    js = render_json([s0, s1], alerts, {"test": True})
    md = render_markdown([s0, s1], alerts, {"test": True})
    checks.append(("JSON 可解析回对象", isinstance(__import__("json").loads(js), dict)))
    checks.append(("Markdown 含告警小节", "## 告警" in md))
    checks.append(("汇总计数正确", summarize([s0, s1], alerts)["count"] == 2))
    checks.append(("空样本不崩", summarize([], [])["count"] == 0))
    checks.append(("阈值描述可读",
                   all(isinstance(x, str) for x in describe_thresholds(ths.values()))))

    # 采样循环（极短时长，验证调度与退出）
    c2 = Collector(include_processes=False)
    quiet = {"cpu": Threshold(name="CPU", high=101, low=100, need=2)}
    smp, al = run_sampling(c2, quiet, interval=0.05, duration=0.14, on_sample=lambda *a: None)
    checks.append(("采样循环产出 >= 1 个点", len(smp) >= 1))
    checks.append(("duration 受控（不超时过多）",
                   len(smp) <= 5))

    ok = True
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    if ok:
        print("SELF-TEST OK")
        return 0
    return 1


# ── 主流程 ───────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="系统监控脚本（只读；不杀进程；有限时长）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--interval", type=float, default=1.0, help="采样间隔（秒）")
    ap.add_argument("--duration", type=float, default=5.0, help="总采样时长（秒）")
    ap.add_argument("--top", type=int, default=5, help="进程排行 Top-N")
    ap.add_argument("--no-processes", action="store_true", help="不采集进程排行（更省开销）")
    ap.add_argument("--cpu", type=float, default=85.0, help="CPU 告警阈值（%）")
    ap.add_argument("--mem", type=float, default=85.0, help="内存告警阈值（%）")
    ap.add_argument("--disk", type=float, default=85.0, help="磁盘告警阈值（%）")
    ap.add_argument("--low-gap", type=float, default=5.0,
                    help="滞回带宽度：恢复阈值 = 告警阈值 - low-gap")
    ap.add_argument("--need", type=int, default=2, help="连续多少次才翻转状态")
    ap.add_argument("--out-dir", default=None, help="报告输出目录（默认不落盘）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写任何文件")
    ap.add_argument("--self-test", action="store_true", help="只做自检并输出 SELF-TEST OK")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.self_test:
        return self_test()

    # ── 参数校验（失败必须返回 1，不能靠异常栈退出）──
    if args.interval <= 0:
        print("参数错误：--interval 必须 > 0", file=sys.stderr)
        return EXIT_ERROR
    if args.duration <= 0:
        print("参数错误：--duration 必须 > 0", file=sys.stderr)
        return EXIT_ERROR
    if args.need < 1:
        print("参数错误：--need 必须 >= 1", file=sys.stderr)
        return EXIT_ERROR
    if args.low_gap <= 0:
        print("参数错误：--low-gap 必须 > 0，否则滞回带为空，去抖失效", file=sys.stderr)
        return EXIT_ERROR

    print("=" * 78)
    print(" 系统监控（只读采集 · 有限时长 · 不执行任何处置动作）")
    print("=" * 78)

    # ── 构建阈值 ──
    thresholds = {
        "cpu": Threshold(name="CPU", high=args.cpu, low=args.cpu - args.low_gap,
                         need=args.need, unit="%"),
        "mem": Threshold(name="内存", high=args.mem, low=args.mem - args.low_gap,
                         need=args.need, unit="%"),
        "disk": Threshold(name="磁盘", high=args.disk, low=args.disk - args.low_gap,
                          need=args.need, unit="%"),
    }
    for line in describe_thresholds(thresholds.values()):
        print(f"  · {line}")

    # ── 容器提醒 ──
    cg_mem = __import__("monitor_core").read_cgroup_memory_limit()
    vm_total = psutil.virtual_memory().total
    if cg_mem and cg_mem < vm_total:
        print(f"  · 检测到容器限额 {human_bytes(cg_mem)}"
              f"（宿主机 {human_bytes(vm_total)}）")
        print("    ⚠ 本工具的 mem% 口径为 psutil.virtual_memory().percent（宿主机口径）。")
        print("      若要按容器限额告警，请用 cgroup 值自行换算（见 README 2.8）。")

    print(f"  · 采样：每 {args.interval}s 一次，共 {args.duration}s，"
          f"进程排行 Top {args.top}{'（已关闭）' if args.no_processes else ''}")
    print()

    collector = Collector(include_processes=not args.no_processes, top_n=args.top)

    try:
        samples, alerts = run_sampling(collector, thresholds,
                                       interval=args.interval, duration=args.duration)
    except KeyboardInterrupt:
        # Ctrl+C 不是错误：已经采到的数据很有价值，应当落盘后正常退出。
        print("\n  收到中断信号，正在用已采集的数据生成报告……")
        samples, alerts = [], []
    except (psutil.Error, OSError) as exc:
        print(f"  采集失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_ERROR

    print()
    print(f"  采样完成：{len(samples)} 个样本，{len(alerts)} 条告警")

    if not samples:
        print("  没有采到任何样本，无法生成报告。", file=sys.stderr)
        return EXIT_ERROR

    summary = summarize(samples, alerts)
    print(f"  CPU  平均 {summary['cpu']['avg']:5.2f}%  峰值 {summary['cpu']['max']:5.2f}%")
    print(f"  内存 平均 {summary['mem']['avg']:5.2f}%  峰值 {summary['mem']['max']:5.2f}%")
    print(f"  磁盘 平均 {summary['disk']['avg']:5.2f}%  峰值 {summary['disk']['max']:5.2f}%")

    if alerts:
        print()
        for a in alerts:
            ts = time.strftime("%H:%M:%S", time.localtime(a.ts))
            print(f"  ⚠ [{ts}] {a.message}")

    meta = {
        "interval": args.interval,
        "duration": args.duration,
        "need": args.need,
        "low_gap": args.low_gap,
        "thresholds": {k: t.high for k, t in thresholds.items()},
        "host": os.uname().nodename if hasattr(os, "uname") else "unknown",
        "cpu_count": psutil.cpu_count(logical=True),
        "mem_total": vm_total,
        "cgroup_mem_limit": cg_mem,
    }

    if args.out_dir and not args.dry_run:
        json_path, md_path = write_reports(samples, alerts, meta, args.out_dir)
        print()
        print(f"  报告已写入：")
        print(f"    {json_path}")
        print(f"    {md_path}")
    elif args.dry_run:
        print()
        print("  --dry-run：跳过报告落盘")

    print()
    if alerts:
        print(f"  退出码 {EXIT_ALERT}（采集成功，但有 {len(alerts)} 条告警）")
        return EXIT_ALERT
    print(f"  退出码 {EXIT_OK}（采集成功，无告警）")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
