#!/usr/bin/env python3
"""
Day 185 · 示例 01 —— 进程管理基础：PID 文件、就绪等待、优雅停机

为什么要有这个文件？
    "一键部署"里 90% 的事故不是部署逻辑写错，而是**进程管理没做对**：

    坑 1：只看 PID 文件就以为服务在跑。
        PID 文件是普通文件，服务被 kill -9 之后它还在。
        更糟的是 PID 会被系统复用 —— 那个号现在可能是别人的进程，
        你一个 kill 就杀了无关进程（生产事故的经典形态）。
    坑 2：启动=端口在听就以为能用了。
        端口 listen 是内核行为，业务就绪是应用行为，两者之间隔着 warmup。
    坑 3：停止用 kill -9。
        在途请求全断，滚动发布时用户看到 502/ConnectionReset。

本文件把这三件事做成可复用的三件套：
    validate_pid()   —— PID 校验：/proc/<pid>/cmdline 必须含标记字符串，防复用/防陈旧
    wait_ready()     —— 轮询就绪探针（不是端口），超时给明确错误
    stop_service()   —— SIGTERM → 等 → 超时才 SIGKILL（两次机会）

运行方式：
    python3 01-process-runner.py --self-test        # 离线自证（自己起自己停一个真服务）
    python3 01-process-runner.py --demo             # 真机演示：起服务 → 探针 → 优雅停机
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = str(HERE / "00-platform-api.py")


def http_get(url: str, timeout: float = 2.0) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except Exception:
            return exc.code, {}
    except (urllib.error.URLError, OSError):
        return 0, {}


#: 自己启动的子进程句柄。留着它是为了 `wait` 掉退出的孩子 —— 否则会留僵尸进程，
#: 而僵尸进程的 /proc/<pid> **依然存在**，会让"服务还在跑"的判断永远为真。
_CHILDREN: dict[int, "subprocess.Popen"] = {}


def pid_alive(pid: int) -> bool:
    """进程是否真的活着。

    坑（本日真机踩到）：/proc/<pid> 存在 ≠ 进程活着。
    已退出但父进程还没 wait() 的子进程是**僵尸**（state=Z），/proc 目录还在，
    于是"停机脚本"会一直等下去，最后误判成"优雅停机失败"去 SIGKILL 一个尸体。
    正确判据是看 /proc/<pid>/stat 里的状态字符。
    """
    child = _CHILDREN.get(pid)
    if child is not None and child.poll() is not None:
        return False  # 顺手回收，避免僵尸
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except (FileNotFoundError, ProcessLookupError, PermissionError, OSError):
        return False
    # stat 格式: pid (comm) state ...   comm 里可能有空格和括号，所以从右往左找最后一个 ')'
    try:
        state = stat.rsplit(")", 1)[1].split()[0]
    except IndexError:
        return False
    return state not in ("Z", "X", "x")   # Z=僵尸 X=已死


def cmdline_of(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except (FileNotFoundError, ProcessLookupError):
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()


def validate_pid(pidfile: str, marker: str) -> tuple[bool, int, str]:
    """返回 (是否可信, pid, 原因)。

    marker 通常是被部署文件路径或服务名 —— **它才是"这个 PID 属于我们的服务"的证据**，
    PID 号本身不是。（PID 复用：服务死了之后，号会被系统分给别人。）
    """
    path = Path(pidfile)
    if not path.exists():
        return False, 0, "no-pidfile"
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return False, 0, "pidfile-not-int"
    if not pid_alive(pid):
        return False, pid, "stale-pidfile(pid-dead)"
    cmd = cmdline_of(pid)
    if marker and marker not in cmd:
        return False, pid, f"pid-reused(cmdline={cmd[:60]!r})"
    return True, pid, "ok"


def wait_ready(url: str, timeout: float = 15.0, interval: float = 0.1) -> tuple[bool, float, int]:
    """轮询就绪探针。返回 (是否就绪, 耗时秒, 最后一次状态码)。"""
    started = time.monotonic()
    last = 0
    while time.monotonic() - started < timeout:
        code, _ = http_get(url, timeout=1.0)
        last = code
        if code == 200:
            return True, time.monotonic() - started, code
        time.sleep(interval)
    return False, time.monotonic() - started, last


def start_service(port: int, pidfile: str, logfile: str, version: str = "v1.0.0",
                  ready_delay: float = 1.0, fail_ready: bool = False,
                  data: str | None = None, wait: bool = True) -> dict:
    ok, pid, why = validate_pid(pidfile, marker=API)
    if ok:
        return {"started": False, "reason": f"already-running(pid={pid})"}

    Path(pidfile).unlink(missing_ok=True)
    log_fh = open(logfile, "ab", buffering=0)
    cmd = [sys.executable, API, "--port", str(port), "--version", version,
           "--ready-delay", str(ready_delay)]
    if data:
        cmd += ["--data", data]
    if fail_ready:
        cmd.append("--fail-ready")
    proc = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT,
                            start_new_session=True)
    _CHILDREN[proc.pid] = proc
    Path(pidfile).write_text(str(proc.pid), encoding="utf-8")

    if not wait:
        # 不做就绪等待：给"我要自己观察未就绪阶段"的调用方用（03 号示例的第 2a 项检查）
        return {"started": True, "pid": proc.pid, "ready": None,
                "ready_wait_s": None, "last_ready_code": None,
                "stale_pidfile_reason": why if why != "ok" else None}

    ready, waited, code = wait_ready(f"http://127.0.0.1:{port}/readyz", timeout=15)
    return {"started": True, "pid": proc.pid, "ready": ready,
            "ready_wait_s": round(waited, 3), "last_ready_code": code,
            "stale_pidfile_reason": why if why != "ok" else None}


def stop_service(pidfile: str, timeout: float = 5.0) -> dict:
    ok, pid, why = validate_pid(pidfile, marker=API)
    if not ok:
        Path(pidfile).unlink(missing_ok=True)
        return {"stopped": False, "reason": why, "pid": pid}

    started = time.monotonic()
    os.kill(pid, signal.SIGTERM)           # 第一次机会：优雅停机
    while time.monotonic() - started < timeout:
        if not pid_alive(pid):
            Path(pidfile).unlink(missing_ok=True)
            return {"stopped": True, "pid": pid, "graceful": True,
                    "took_s": round(time.monotonic() - started, 3)}
        time.sleep(0.05)
    os.kill(pid, signal.SIGKILL)           # 第二次机会：强杀（并且要记下来，这算异常）
    Path(pidfile).unlink(missing_ok=True)
    return {"stopped": True, "pid": pid, "graceful": False,
            "took_s": round(time.monotonic() - started, 3),
            "note": "graceful 超时，已 SIGKILL —— 生产里这应该是告警"}


def self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pidfile = str(Path(tmp) / "api.pid")
        logfile = str(Path(tmp) / "api.log")

        # ① 陈旧 PID 文件：写一个"活着但完全无关"的 PID（用自己当替身）
        # 用"当前进程的 PID + 一个永远不可能出现在它 cmdline 里的标记"来模拟 PID 复用
        Path(pidfile).write_text(str(os.getpid()), encoding="utf-8")
        ok, pid, why = validate_pid(pidfile, marker=API)
        assert not ok and "reused" in why, (ok, pid, why)

        # ② 正常启动 + 就绪
        info = start_service(port=0 or 8321, pidfile=pidfile, logfile=logfile,
                             ready_delay=0.4)
        assert info["started"] and info["ready"], info
        assert info["stale_pidfile_reason"], info   # 它应该报告"覆盖了一个不可信的 pidfile"

        # ③ 重复启动应该被拒绝
        again = start_service(port=8321, pidfile=pidfile, logfile=logfile)
        assert again["started"] is False, again

        # ④ 优雅停机
        stop = stop_service(pidfile)
        assert stop["stopped"] and stop["graceful"], stop

        # ⑤ 停完之后端口应该是空的
        code, _ = http_get("http://127.0.0.1:8321/healthz")
        assert code == 0, code

    print("✅ self-test 通过：陈旧 PID 被识破、就绪等待生效、重复启动被拒、优雅停机成功")
    return 0


def demo() -> int:
    import tempfile

    tmp = tempfile.mkdtemp(prefix="day185-runner-")
    pidfile, logfile, port = str(Path(tmp) / "api.pid"), str(Path(tmp) / "api.log"), 8322
    print(f"工作目录: {tmp}")
    info = start_service(port=port, pidfile=pidfile, logfile=logfile, ready_delay=1.0)
    print("启动结果:", json.dumps(info, ensure_ascii=False))
    print("healthz:", http_get(f"http://127.0.0.1:{port}/healthz")[0],
          "readyz:", http_get(f"http://127.0.0.1:{port}/readyz")[0])
    print("停止结果:", json.dumps(stop_service(pidfile), ensure_ascii=False))
    print("停完后 healthz 状态码（0=连不上，符合预期）:",
          http_get(f"http://127.0.0.1:{port}/healthz")[0])
    print(f"清理: rm -rf {tmp}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.demo:
        return demo()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
