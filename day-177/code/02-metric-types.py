#!/usr/bin/env python3
"""
Day 177 — Prometheus + Grafana
02 · 四种指标类型：counter / gauge / histogram / summary

Prometheus 只有这四种类型，用错类型是新手最常见的坑：
用 counter 存「当前在线人数」，或者用 gauge 存「请求总数」——
前者会被 rate() 算出负数，后者会在重启后归零，看板全废。

本脚本每种类型都真跑一遍并打印文本暴露格式，末尾附「选型对照表」。

用法：
    python3 02-metric-types.py --demo        # 打印四种类型的真实输出
    python3 02-metric-types.py --self-test   # 断言四种类型的语义
"""

import argparse
import sys
import time

try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        Summary,
        generate_latest,
    )

    HAS_LIB = True
except ImportError:
    HAS_LIB = False


def demo_counter(reg):
    """counter：只增不减。用来数「发生过多少次」。"""
    c = Counter("demo_requests_total", "请求总数", registry=reg)
    for _ in range(3):
        c.inc()
    c.inc(2)
    return c


def demo_gauge(reg):
    """gauge：可增可减、可任意设值。用来量「当前是多少」。"""
    g = Gauge("demo_queue_size", "队列当前长度", registry=reg)
    g.set(10)
    g.inc(5)
    g.dec(3)
    return g


def demo_histogram(reg):
    """histogram：服务端分桶累计，可以算分位数（P50/P95/P99）。

    注意：`_bucket` 是**累计**的，le="0.1" 的计数已经包含了 le="0.05" 的。
    """
    h = Histogram(
        "demo_latency_seconds",
        "请求耗时",
        buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
        registry=reg,
    )
    for v in (0.003, 0.02, 0.07, 0.07, 0.4, 2.0):
        h.observe(v)
    return h


def demo_summary(reg):
    """summary：客户端算 *聚合值*（_sum/_count）。

    坑（实测，prometheus_client 0.26.0）：`Summary(...)` **已经不接受 `quantiles=` 参数**，
    构造它只有 _sum 和 _count 两个样本，一个分位都没有。
    官方文档当场把你推给 Histogram：
        "You can use Histograms for aggregatable calculation of quantiles."
    所以想要 P50/P95/P99，2026 年的正确选择是 **Histogram + histogram_quantile()**。
    """
    s = Summary("demo_summary_seconds", "请求耗时（summary）", registry=reg)
    for v in (0.003, 0.02, 0.07, 0.07, 0.4, 2.0):
        s.observe(v)
    return s


def render(registry):
    return generate_latest(registry).decode("utf-8")


def interesting_lines(text):
    out = []
    for line in text.splitlines():
        if line.startswith("# TYPE"):
            out.append(line)
        elif line.startswith("demo_latency_seconds_bucket") or \
             line.startswith("demo_summary_seconds{") or \
             line.startswith("demo_summary_seconds_count") or \
             line.startswith("demo_summary_seconds_sum") or \
             line.startswith("demo_requests_total") or \
             line.startswith("demo_queue_size"):
            out.append(line)
    return out


def run_demo():
    if not HAS_LIB:
        print("需要 prometheus_client：python3 -m pip install prometheus_client")
        return 1
    reg = CollectorRegistry()
    demo_counter(reg)
    demo_gauge(reg)
    demo_histogram(reg)
    demo_summary(reg)
    text = render(reg)
    for line in interesting_lines(text):
        print(line)
    print()
    print("# 观察点：")
    print("#   1) demo_requests_total = 5（3 次 +1，1 次 +2）—— counter 只增")
    print("#   2) demo_queue_size = 12（10+5-3）—— gauge 可增可减")
    print("#   3) *_bucket 的 le=\"0.5\" 已包含前面所有桶 —— 累计语义")
    print("#   4) summary 只有 _sum/_count；**分位已被移出 API**（quantiles= 会 TypeError）")
    print("#      → 要分位请用 Histogram + histogram_quantile()")
    return 0


def self_test():
    if not HAS_LIB:
        print("SKIP: prometheus_client 未安装，无法断言类型语义")
        return 0
    reg = CollectorRegistry()
    demo_counter(reg)
    demo_gauge(reg)
    demo_histogram(reg)
    demo_summary(reg)
    text = render(reg)

    # 1) counter 单调：终值 5，且没有负值
    assert "demo_requests_total 5.0" in text, "counter 累计应为 5"
    assert '-1' not in text.split("demo_latency")[0], "counter 不该出现负值"

    # 2) gauge 可增可减：10+5-3 = 12
    assert "demo_queue_size 12.0" in text, "gauge 应为 12"

    # 3) histogram 桶累计单调不减，且最后一个桶（le=1.0）计数 = 6 - 1(超过 1.0 的那个)
    buckets = [float(l.split("}")[1]) for l in text.splitlines()
               if l.startswith("demo_latency_seconds_bucket")]
    assert buckets == sorted(buckets), "histogram 桶必须单调不减"
    assert "demo_latency_seconds_bucket{le=\"1.0\"} 5.0" in text, "le=1.0 应为 5 条"
    assert "demo_latency_seconds_bucket{le=\"+Inf\"} 6.0" in text, "+Inf 桶应等于总数"

    # 4) summary 只有 _sum/_count，没有 _bucket，且 quantiles= 已被移除
    assert 'demo_summary_seconds{quantile=' not in text, "0.26.0 不该再输出 quantile 标签"
    assert "demo_summary_seconds_count 6.0" in text, "summary 计数应为 6"
    assert "demo_summary_seconds_bucket" not in text, "summary 不该有 bucket"
    try:
        Summary("probe_summary", "probe", quantiles=(0.5,), registry=CollectorRegistry())
    except TypeError:
        pass
    else:
        raise AssertionError("预期 quantiles= 抛 TypeError（新版已移除该参数）")

    print("✅ self-test 通过：counter 单调 / gauge 可增减 / histogram 桶累计 / "
          "summary 仅 _sum+_count（quantiles= 已移除），四项语义均成立")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Day 177 · 02 四种指标类型")
    ap.add_argument("--demo", action="store_true", help="打印四种类型的真实输出")
    ap.add_argument("--self-test", action="store_true", help="断言四种类型的语义")
    args = ap.parse_args()
    if args.self_test:
        sys.exit(self_test())
    sys.exit(run_demo())


if __name__ == "__main__":
    main()
