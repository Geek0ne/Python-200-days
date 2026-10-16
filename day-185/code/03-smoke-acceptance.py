#!/usr/bin/env python3
"""
Day 185 · 示例 03 —— 端到端冒烟验收（Smoke Acceptance）

为什么要有这个文件？
    "部署成功"如果只等于"脚本没报错"，那它什么也没证明。
    验收的意义是：**把"能不能用"变成一组会红/会绿的断言**。
    而且断言要挑能抓到真问题的那些 —— 比如"返回 200"远不如"返回的条数等于数据文件里的条数"。

检查项（每一项都对应一类真实事故）：
    1. /healthz = 200                    —— 进程根本没起来
    2. /readyz 先 503 后 200              —— 起来了但不能干活（warmup 没做完就被打流量）
    3. /api/v1/hosts 条数 == 数据文件条数 —— "接口通但返回空/旧数据"（最容易被忽略）
    4. /metrics 的 requests_total 增量正确 —— 指标假报，导致你看图以为没事
    5. 未知路径 404 + JSON body           —— 反代把 HTML 错误页混进 API
    6. SIGTERM 时在途请求被做完（200）     —— 优雅停机没做，发布时用户看到连接重置
    7. SIGTERM 后进程在 N 秒内退出         —— 停机卡住，滚动发布永远卡在最后一步

运行方式：
    python3 03-smoke-acceptance.py --self-test         # 一遍过（离线，无外部依赖）
    python3 03-smoke-acceptance.py --port 8501 --compare-kill   # 额外对比 SIGKILL 的破坏力

退出码：0 = 全绿；1 = 有失败项（直接用于 CI）。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import signal
import socket
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
HOSTS = [{"host": "web-01", "ip": "10.0.0.11"}, {"host": "web-02", "ip": "10.0.0.12"},
         {"host": "db-01", "ip": "10.0.0.21"}]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Checks:
    def __init__(self):
        self.results: list[dict] = []

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append({"check": name, "ok": bool(ok), "detail": detail})
        print(f"  {'✅' if ok else '❌'} {name}" + (f"  — {detail}" if detail else ""))

    @property
    def failed(self) -> list[dict]:
        return [r for r in self.results if not r["ok"]]


def run_acceptance(port: int, compare_kill: bool = False) -> int:
    checks = Checks()
    tmp = Path(tempfile.mkdtemp(prefix="day185-smoke-"))
    data = tmp / "hosts.json"
    data.write_text(json.dumps(HOSTS, ensure_ascii=False), encoding="utf-8")
    pidfile = str(tmp / "api.pid")
    logfile = str(tmp / "api.log")
    base = f"http://127.0.0.1:{port}"

    print(f"验收目标: {base}  版本 v-smoke  数据文件 {data} ({len(HOSTS)} 台主机)")
    # 刻意 wait=False：这样我们才能亲眼看到"进程在听端口但还没就绪"的阶段
    runner.start_service(port=port, pidfile=pidfile, logfile=logfile,
                         version="v-smoke", ready_delay=2.0, data=str(data), wait=False)

    try:
        # 0) 先等"端口真的在听"。
        #    为什么需要这一步（真机踩到）：wait=False 启动后立刻发请求，会拿到 code=0
        #    —— 进程还没 bind 完。把"还没开始监听"和"在监听但未就绪"混为一谈，
        #    验收报告就会给出误导性的红。
        listening = False
        t0 = time.monotonic()
        while time.monotonic() - t0 < 3:
            code, _ = runner.http_get(base + "/healthz", timeout=0.5)
            if code != 0:
                listening = True
                break
            time.sleep(0.05)
        checks.add("0. 端口已开始监听", listening, f"等待 {round(time.monotonic() - t0, 3)}s")

        # 1) 存活探针
        code, body = runner.http_get(base + "/healthz")
        checks.add("1. /healthz == 200", code == 200, f"code={code} version={body.get('version')}")

        # 2) 就绪语义：warmup 期间必须是 503
        code, body = runner.http_get(base + "/readyz")
        checks.add("2a. 未就绪时 /readyz == 503", code == 503, f"code={code}")
        ready, waited, last = runner.wait_ready(base + "/readyz", timeout=10)
        checks.add("2b. 就绪后 /readyz == 200", ready, f"就绪等待={waited:.3f}s last={last}")

        # 3) 真数据校验（不是"200 就算过"）
        code, body = runner.http_get(base + "/api/v1/hosts")
        checks.add("3. /api/v1/hosts 条数 == 数据文件条数",
                   code == 200 and body.get("count") == len(HOSTS),
                   f"code={code} count={body.get('count')} expect={len(HOSTS)}")

        # 4) 指标增量
        _, before = runner.http_get(base + "/metrics")
        for _ in range(5):
            runner.http_get(base + "/healthz")
        _, after = runner.http_get(base + "/metrics")
        delta = after.get("requests_total", 0) - before.get("requests_total", 0)
        checks.add("4. /metrics requests_total 增量 == 6", delta == 6,
                   f"before={before.get('requests_total')} after={after.get('requests_total')} delta={delta}")

        # 5) 404 必须是 JSON（API 不该把 HTML 错误页吐出来）
        code, body = runner.http_get(base + "/nope")
        checks.add("5. 未知路径 404 且 body 是 JSON", code == 404 and body.get("error") == "not found",
                   f"code={code} body_keys={list(body)[:3]}")

        # 6) 优雅停机：在途请求要被打完
        pid = int(Path(pidfile).read_text())
        outcome: dict = {}

        def in_flight():
            started = time.monotonic()
            code, body = runner.http_get(base + "/slow?ms=1200", timeout=8)
            outcome.update({"code": code, "body": body, "elapsed": round(time.monotonic() - started, 3)})

        worker = threading.Thread(target=in_flight, daemon=True)
        worker.start()
        time.sleep(0.25)                      # 确保请求已经进入服务端
        fail_open = compare_kill and False
        if compare_kill:
            # 对照组：SIGKILL（不给应用收尾机会）—— 预期在途请求被切断
            os.kill(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGTERM)
        worker.join(timeout=8)

        exit_started = time.monotonic()
        while runner.pid_alive(pid) and time.monotonic() - exit_started < 5:
            time.sleep(0.05)
        exit_took = round(time.monotonic() - exit_started, 3)

        if compare_kill:
            checks.add("6'. SIGKILL 对照组：在途请求被切断（预期失败）",
                       outcome.get("code") != 200,
                       f"请求结果={outcome}")
            checks.add("7'. SIGKILL 对照组：进程立刻消失（数据完整性由应用承担）",
                       exit_took < 0.5, f"退出耗时={exit_took}s")
        else:
            checks.add("6. SIGTERM 时在途请求被做完（200）",
                       outcome.get("code") == 200,
                       f"在途请求={outcome}")
            checks.add("7. SIGTERM 后进程及时退出（<3s）", exit_took < 3,
                       f"退出耗时={exit_took}s（完成在途请求后）")
    finally:
        runner.stop_service(pidfile)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n结果: {len(checks.results) - len(checks.failed)}/{len(checks.results)} 项通过")
    if checks.failed:
        print("失败项:", json.dumps(checks.failed, ensure_ascii=False))
        return 1
    print("✅ 冒烟验收全绿")
    return 0


def self_test() -> int:
    return run_acceptance(free_port())


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--compare-kill", action="store_true")
    args = p.parse_args()
    port = args.port or free_port()
    if args.self_test:
        return self_test()
    return run_acceptance(port, compare_kill=args.compare_kill)


if __name__ == "__main__":
    raise SystemExit(main())
