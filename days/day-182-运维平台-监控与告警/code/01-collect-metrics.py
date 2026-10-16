#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 182 - 自动化运维平台（一）：服务器监控 + 告警
01 - 指标采集：主机指标 + 应用探活，统一成一份 JSON 快照

要点：
- 采集分两类：主机指标（CPU/内存/磁盘/负载/uptime）与应用指标（探活 up/down + 延迟）。
- 主机指标优先用 psutil；没装 psutil 时退到 /proc 真读内核文件（Linux），
  证明「采集」这件事本身不神秘：数字本来就在 /proc 里躺着。
- 应用探活用标准库 urllib，不依赖 requests。
- 采集结果统一成一份 JSON 快照：这是阈值判定、去重、路由的唯一输入。

用法：
    python3 01-collect-metrics.py --once                     # 采一次，人读格式
    python3 01-collect-metrics.py --once --json              # 采一次，JSON
    python3 01-collect-metrics.py --probe http://127.0.0.1:8000/ --once
    python3 01-collect-metrics.py --backend proc --once      # 强制 /proc 回退
    python3 01-collect-metrics.py --once --count 3 --interval 1
    python3 01-collect-metrics.py --self-test                # 离线自检
    python3 01-collect-metrics.py --self-test --backend proc # 自检回退路径
"""

import argparse
import json
import os
import shutil
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# /proc 里 CPU 使用率要读两次求差，间隔取小一点省时间；psutil 也复用这个值。
CPU_SAMPLE_SECONDS = 0.10


# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #
def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_psutil():
    try:
        import psutil  # noqa: F401

        return psutil
    except ImportError:
        return None


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# --------------------------------------------------------------------------- #
# 主机指标：两种后端，产出同一个字典结构
# --------------------------------------------------------------------------- #
def _proc_cpu_percent(sample=CPU_SAMPLE_SECONDS):
    """读 /proc/stat 两次求差。idle+ iowait 算空闲，其余算忙。"""

    def snap():
        with open("/proc/stat", "r") as fh:
            fields = fh.readline().split()
        vals = [int(x) for x in fields[1:]]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        return idle, sum(vals)

    i1, t1 = snap()
    time.sleep(sample)
    i2, t2 = snap()
    dt = t2 - t1
    if dt <= 0:
        return float("nan")
    return round(100.0 * (1.0 - float(i2 - i1) / float(dt)), 1)


def _proc_mem_percent():
    total = available = None
    with open("/proc/meminfo", "r") as fh:
        for line in fh:
            key, _, rest = line.partition(":")
            value = rest.strip().split()[0]
            if key == "MemTotal":
                total = int(value)
            elif key == "MemAvailable":
                available = int(value)
            if total is not None and available is not None:
                break
    if not total:
        return float("nan")
    used = total - (available or 0)
    return round(100.0 * used / total, 1)


def _proc_uptime_seconds():
    with open("/proc/uptime", "r") as fh:
        return int(float(fh.read().split()[0]))


def collect_host_proc():
    load1, load5, load15 = os.getloadavg()
    du = shutil.disk_usage("/")
    return {
        "backend": "proc",
        "cpu_percent": _proc_cpu_percent(),
        "mem_percent": _proc_mem_percent(),
        "disk_percent": round(100.0 * du.used / du.total, 1),
        "load1": round(load1, 2),
        "load5": round(load5, 2),
        "load15": round(load15, 2),
        "cpu_count": os.cpu_count(),
        "uptime_seconds": _proc_uptime_seconds(),
    }


def collect_host_psutil(psutil):
    load1, load5, load15 = os.getloadavg()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "backend": "psutil",
        "cpu_percent": psutil.cpu_percent(interval=CPU_SAMPLE_SECONDS),
        "mem_percent": mem.percent,
        "disk_percent": disk.percent,
        "load1": round(load1, 2),
        "load5": round(load5, 2),
        "load15": round(load15, 2),
        "cpu_count": os.cpu_count(),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }


def collect_host(backend="auto"):
    """backend: auto | psutil | proc。auto 时有 psutil 用 psutil，否则 /proc。"""
    psutil = load_psutil()
    if backend == "psutil" and psutil is None:
        raise RuntimeError("指定了 --backend psutil，但本机没装 psutil（pip install psutil）")
    if backend == "proc":
        if not os.path.exists("/proc/stat"):
            raise RuntimeError("指定了 --backend proc，但本机没有 /proc（非 Linux？）")
        return collect_host_proc()
    if backend == "psutil":
        return collect_host_psutil(psutil)
    if psutil is not None:
        return collect_host_psutil(psutil)
    if os.path.exists("/proc/stat"):
        return collect_host_proc()
    raise RuntimeError("既没有 psutil，也没有 /proc，无法采集主机指标")


# --------------------------------------------------------------------------- #
# 应用探活（应用指标）
# --------------------------------------------------------------------------- #
def probe_http(url, timeout=2.0):
    """
    探活定义（本平台统一口径）：
      status=up    收到了 HTTP 响应（2xx/4xx/5xx 都算「进程活着在应答」）
      status=down  连接失败/超时/DNS 失败——进程或网络不可用
    http_code 单独记录，用来区分「活着但在报 500」和「活着且健康」。
    """
    t0 = time.perf_counter()
    out = {
        "target": url,
        "status": "down",
        "http_code": None,
        "latency_ms": None,
        "error": None,
    }
    try:
        req = urllib.request.Request(
            url, method="GET", headers={"User-Agent": "day182-monitor/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out["http_code"] = resp.getcode()
            out["status"] = "up"
            resp.read(256)
    except urllib.error.HTTPError as exc:
        # 有响应就是活着，500 也是「up 但不健康」
        out["http_code"] = exc.code
        out["status"] = "up"
    except Exception as exc:  # URLError / timeout / socket.error ...
        out["error"] = type(exc).__name__ + ": " + str(exc)
    out["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    return out


def build_snapshot(probes, backend="auto"):
    return {
        "ts": now_iso(),
        "host": socket.gethostname(),
        "host_metrics": collect_host(backend),
        "app_metrics": [probe_http(u) for u in probes],
    }


# --------------------------------------------------------------------------- #
# 自检用的本地 HTTP 桩
# --------------------------------------------------------------------------- #
class _ProbeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ok":
            code, body = 200, b"ok"
        elif self.path == "/slow":
            time.sleep(0.25)
            code, body = 200, b"slow"
        else:
            code, body = 404, b"nope"
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass   # 探活方超时后先断开，服务端写回时就会撞上 BrokenPipe

    def log_message(self, *args):  # 静音
        pass


def self_test(backend):
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
        print(("  PASS  " if cond else "  FAIL  ") + msg)

    print("== 01 采集自检 ==")

    # 1) 本地 HTTP 桩：验证探活两种结果 + 延迟有值
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _ProbeHandler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.05)
    try:
        up = probe_http("http://127.0.0.1:%d/ok" % port)
        check(up["status"] == "up", "探活 200 -> up（实测 status=%s code=%s）" % (up["status"], up["http_code"]))
        check(up["http_code"] == 200, "探活 200 记录 http_code=200")
        check(up["latency_ms"] is not None and up["latency_ms"] >= 0, "探活记录延迟（实测 %.3f ms）" % up["latency_ms"])

        miss = probe_http("http://127.0.0.1:%d/missing" % port)
        check(miss["status"] == "up" and miss["http_code"] == 404, "探活 404 -> up（进程活着在应答）")

        slow = probe_http("http://127.0.0.1:%d/slow" % port, timeout=2.0)
        check(slow["latency_ms"] >= 200, "探活慢请求延迟 >= 200ms（实测 %.3f ms）" % slow["latency_ms"])

        timeout_probe = probe_http("http://127.0.0.1:%d/slow" % port, timeout=0.05)
        check(timeout_probe["status"] == "down", "超时 -> down（实测 error=%s）" % timeout_probe["error"])
    finally:
        srv.shutdown()
        srv.server_close()

    dead_port = free_port()
    dead = probe_http("http://127.0.0.1:%d/" % dead_port, timeout=1.0)
    check(dead["status"] == "down", "端口无人监听 -> down（实测 error=%s）" % dead["error"])

    # 2) 主机指标：两种后端都要能出数且范围合法
    for name in (["auto", "proc", "psutil"] if backend == "auto" else [backend]):
        try:
            hm = collect_host(name)
        except RuntimeError as exc:
            print("  SKIP  backend=%s（%s）" % (name, exc))
            continue
        ok_range = (
            0.0 <= hm["cpu_percent"] <= 100.0
            and 0.0 <= hm["mem_percent"] <= 100.0
            and 0.0 <= hm["disk_percent"] <= 100.0
        )
        check(
            ok_range,
            "backend=%-6s 指标范围合法 cpu=%.1f%% mem=%.1f%% disk=%.1f%% load1=%.2f"
            % (name, hm["cpu_percent"], hm["mem_percent"], hm["disk_percent"], hm["load1"]),
        )
        check(hm["uptime_seconds"] > 0, "backend=%-6s uptime>0（实测 %d s）" % (name, hm["uptime_seconds"]))

    # 3) 快照 JSON 可往返
    snap = {
        "ts": now_iso(),
        "host": socket.gethostname(),
        "host_metrics": collect_host(backend),
        "app_metrics": [dead],
    }
    raw = json.dumps(snap, ensure_ascii=False)
    back = json.loads(raw)
    check(back["app_metrics"][0]["status"] == "down", "快照 JSON 往返保真（%d 字节）" % len(raw.encode("utf-8")))

    if failures:
        print("self-test 失败 %d 项" % len(failures))
        return 1
    print("self-test 通过 | 探活 5 例 + 主机指标 + JSON 往返 全部成立")
    return 0


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #
def render(snap):
    lines = []
    hm = snap["host_metrics"]
    lines.append("[%s] %s  (backend=%s)" % (snap["ts"], snap["host"], hm["backend"]))
    lines.append(
        "  主机  cpu=%5.1f%%  mem=%5.1f%%  disk=%5.1f%%  load=%s/%s/%s  cores=%s  uptime=%ss"
        % (
            hm["cpu_percent"],
            hm["mem_percent"],
            hm["disk_percent"],
            hm["load1"],
            hm["load5"],
            hm["load15"],
            hm["cpu_count"],
            hm["uptime_seconds"],
        )
    )
    if not snap["app_metrics"]:
        lines.append("  应用  （未指定 --probe，跳过应用探活）")
    for pm in snap["app_metrics"]:
        lines.append(
            "  应用  %-34s %-4s code=%-5s latency=%sms  %s"
            % (
                pm["target"],
                pm["status"],
                pm["http_code"],
                pm["latency_ms"],
                pm["error"] or "",
            )
        )
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Day 182 · 01 指标采集（主机 + 应用探活）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--self-test", action="store_true", help="离线自检，不起长期服务")
    ap.add_argument("--once", action="store_true", help="采集一次并打印")
    ap.add_argument("--count", type=int, default=1, help="采集次数（默认 1）")
    ap.add_argument("--interval", type=float, default=1.0, help="采集间隔秒（默认 1.0）")
    ap.add_argument("--probe", action="append", default=[], metavar="URL", help="要探活的应用地址，可重复")
    ap.add_argument("--backend", choices=["auto", "psutil", "proc"], default="auto")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出（每行一份快照）")
    ap.add_argument("--out", metavar="FILE", help="把快照追加写入文件（JSON Lines）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test(args.backend)

    if not args.once and args.count == 1:
        args.once = True
    if not args.once and args.count <= 1:
        ap.error("请用 --once 或 --count N 指定采集次数")

    out_fh = open(args.out, "a", encoding="utf-8") if args.out else None
    try:
        for idx in range(args.count):
            if idx > 0:
                time.sleep(args.interval)
            try:
                snap = build_snapshot(args.probe, args.backend)
            except RuntimeError as exc:
                print("采集失败：%s" % exc, file=sys.stderr)
                return 2
            line = json.dumps(snap, ensure_ascii=False)
            if out_fh:
                out_fh.write(line + "\n")
                out_fh.flush()
            print(line if args.json else render(snap))
    finally:
        if out_fh:
            out_fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
