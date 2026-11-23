#!/usr/bin/env python3
"""
Day 185 · 示例 05 —— 故障演练（Chaos Drill）：把"能不能恢复"变成数字

为什么要有这个文件？
    部署脚本能跑通 ≠ 系统能扛住故障。运维平台的最后一块拼图是：
    **主动把服务打死，量出恢复时间（MTTR），再决定告警阈值定多少**。
    这件事只能在本机真做一遍 —— 看别人的 MTTR 数字对你的机器没有意义。

三个演练动作（全部真机执行，产出真实时间线）：
    D1 进程被 kill -9（模拟 OOM / 崩溃）
         → 用探针轮询发现 → 重启 → 恢复业务 → 记录「发现延迟 / 恢复耗时 / 总 MTTR」
    D2 端口被别的进程占住（模拟误启动的僵尸实例 / 端口冲突）
         → 部署必须**快速失败**，并且**不能杀掉占用者**（杀了就是二次事故）
    D3 停机方式对比
         → SIGTERM：在途请求被做完（200），进程随后退出
         → SIGKILL：在途请求被切断（连接被重置）

运行方式：
    python3 05-drill-chaos.py --self-test        # 离线自证（完整跑一遍三个演练）
    python3 05-drill-chaos.py --json out.json    # 把时间线写成 JSON，便于对比历史
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str):
    path = HERE / name
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load("01-process-runner.py")
API = str(HERE / "00-platform-api.py")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def drill_kill9(port: int, pidfile: str, logfile: str, poll: float = 0.2) -> dict:
    """D1：kill -9 → 探针发现 → 重启 → 业务恢复。返回真实时间线。"""
    base = f"http://127.0.0.1:{port}"
    runner.start_service(port=port, pidfile=pidfile, logfile=logfile, ready_delay=0.3)
    code, _ = runner.http_get(base + "/healthz")
    assert code == 200, code

    pid = int(Path(pidfile).read_text())
    os.kill(pid, signal.SIGKILL)                    # ← 故障注入：不给任何收尾机会
    t_kill = time.monotonic()

    # 探针以 poll 间隔轮询，发现"服务不可用"
    detected = None
    while time.monotonic() - t_kill < 5:
        code, _ = runner.http_get(base + "/healthz", timeout=0.5)
        if code != 200:
            detected = time.monotonic() - t_kill
            break
        time.sleep(poll)

    # 发现后：拉起（等价于 systemd Restart=always / K8s 重启容器）
    t_restart = time.monotonic()
    Path(pidfile).unlink(missing_ok=True)
    runner.start_service(port=port, pidfile=pidfile, logfile=logfile, ready_delay=0.3)
    ready, waited, _ = runner.wait_ready(base + "/readyz", timeout=10)
    t_recovered = time.monotonic()
    code, _ = runner.http_get(base + "/api/v1/hosts")

    return {
        "drill": "D1-kill9",
        "probe_interval_s": poll,
        "detect_latency_s": round(detected, 3) if detected is not None else None,
        "restart_to_ready_s": round(waited, 3),
        "mttr_s": round(t_recovered - t_kill, 3),
        "business_after_recovery_code": code,
    }


def drill_port_conflict(port: int, pidfile: str, logfile: str) -> dict:
    """D2：端口被别的进程占住 → 必须快速失败且不杀占用者。"""
    blocker = subprocess.Popen(["sleep", "60"], start_new_session=True)
    blocker_sock = socket.socket()
    # SO_REUSEADDR 在这里是必须的（真机踩到 Errno 98）：
    # 上一轮演练在这个端口上留下过 TIME_WAIT 的连接对，不带这个选项 bind 会被内核拒绝，
    # 于是"模拟端口冲突"这一步自己先失败了。注意：它只让 TIME_WAIT 复用，
    # 真有别的进程在 listen，bind 依然会失败 —— 语义没被稀释。
    blocker_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blocker_sock.bind(("127.0.0.1", port))          # 让别的进程真的占住端口
    blocker_sock.listen(1)

    deploy = _load("02-deploy-oneclick.py")
    Path(pidfile).unlink(missing_ok=True)
    started = time.monotonic()
    ok, why = deploy.preflight(port, str(Path(pidfile).parent))
    fail_fast_s = round(time.monotonic() - started, 4)

    blocker_alive = runner.pid_alive(blocker.pid)
    blocker_sock.close()
    blocker.kill()

    return {
        "drill": "D2-port-conflict",
        "preflight_ok": ok,
        "preflight_reason": why,
        "fail_fast_s": fail_fast_s,
        "occupier_still_alive": blocker_alive,     # 必须 True：不能二次事故
    }


def drill_shutdown_compare(port: int, pidfile: str, logfile: str, slow_ms: int = 1200) -> dict:
    """D3：SIGTERM（优雅） vs SIGKILL（强杀），用同一个在途慢请求对比。"""
    results = {}
    for mode in ("SIGTERM", "SIGKILL"):
        if Path(pidfile).exists():
            runner.stop_service(pidfile)
        runner.start_service(port=port, pidfile=pidfile, logfile=logfile, ready_delay=0.3)
        pid = int(Path(pidfile).read_text())
        outcome: dict = {}

        def in_flight():
            t0 = time.monotonic()
            code, body = runner.http_get(f"http://127.0.0.1:{port}/slow?ms={slow_ms}", timeout=8)
            outcome.update({"code": code, "elapsed_s": round(time.monotonic() - t0, 3),
                            "body": body})

        th = threading.Thread(target=in_flight, daemon=True)
        th.start()
        time.sleep(0.25)
        os.kill(pid, signal.SIGTERM if mode == "SIGTERM" else signal.SIGKILL)
        th.join(timeout=8)
        t0 = time.monotonic()
        while runner.pid_alive(pid) and time.monotonic() - t0 < 5:
            time.sleep(0.05)
        results[mode] = {
            "in_flight_code": outcome.get("code"),
            "in_flight_elapsed_s": outcome.get("elapsed_s"),
            "exit_took_s": round(time.monotonic() - t0, 3),
        }
    runner.stop_service(pidfile)
    return {"drill": "D3-shutdown-compare", **results}


def run_all(port: int | None = None) -> dict:
    port = port or free_port()
    tmp = Path(tempfile.mkdtemp(prefix="day185-drill-"))
    pidfile, logfile = str(tmp / "api.pid"), str(tmp / "api.log")
    timeline = {"host": os.uname().nodename, "port": port, "started_at": time.time()}
    try:
        timeline["D1"] = drill_kill9(port, pidfile, logfile)
        runner.stop_service(pidfile)
        timeline["D2"] = drill_port_conflict(port, pidfile, logfile)
        timeline["D3"] = drill_shutdown_compare(port, pidfile, logfile)
    finally:
        runner.stop_service(pidfile)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    return timeline


def self_test() -> int:
    timeline = run_all()
    print(json.dumps(timeline, ensure_ascii=False, indent=2))

    d1 = timeline["D1"]
    assert d1["business_after_recovery_code"] == 200, d1
    assert d1["detect_latency_s"] is not None and d1["detect_latency_s"] < 2, d1
    assert d1["mttr_s"] < 5, d1

    d2 = timeline["D2"]
    assert d2["preflight_ok"] is False, d2            # 必须被拦住
    assert d2["occupier_still_alive"] is True, d2     # 且没杀占用者

    d3 = timeline["D3"]
    assert d3["SIGTERM"]["in_flight_code"] == 200, d3          # 优雅：在途请求做完
    assert d3["SIGKILL"]["in_flight_code"] != 200, d3          # 强杀：请求被切断

    print("\n✅ self-test 通过：")
    print(f"   D1 kill -9 → 发现 {d1['detect_latency_s']}s，"
          f"重启到就绪 {d1['restart_to_ready_s']}s，MTTR {d1['mttr_s']}s")
    print(f"   D2 端口冲突 → 预检在 {d2['fail_fast_s']}s 内失败，占用者未被杀")
    print(f"   D3 SIGTERM 在途请求={d3['SIGTERM']['in_flight_code']} / "
          f"SIGKILL 在途请求={d3['SIGKILL']['in_flight_code']}（连接被重置）")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--json", default=None)
    args = p.parse_args()
    if args.self_test:
        return self_test()
    timeline = run_all()
    print(json.dumps(timeline, ensure_ascii=False, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(timeline, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
        print(f"时间线已写入 {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
