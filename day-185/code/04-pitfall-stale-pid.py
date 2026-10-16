#!/usr/bin/env python3
"""
Day 185 · 示例 04 —— 翻车复现：陈旧 PID 文件会杀掉无辜进程

为什么要有这个文件？
    部署脚本最常见的写法是：

        if [ -f app.pid ]; then kill $(cat app.pid); fi

    这一行里有两个洞，两个都能造成生产事故：

    洞 1：PID 文件是"上次谁写的"的化石。
        服务被 kill -9 / 机器重启后，PID 文件还在。于是脚本认为"服务在跑"，
        部署流程直接跳过启动 → 线上其实一直没起来，而 CI 显示绿色。
    洞 2：PID 会被系统复用。
        那个号现在可能是 cron、是 sshd、是数据库进程。你照着化石 kill 一下，
        就杀了完全无关的东西 —— 而且是**静默**的，报错都没有。

本文件把两个洞都真机演一遍（真起一个无辜进程，真把它杀掉给你看），
再给出正确姿势：**用 /proc/<pid>/cmdline 里的标记验证身份**（01 号示例的 validate_pid）。

运行方式：
    python3 04-pitfall-stale-pid.py --demo       # 真机演示两个洞（会杀掉一个无辜的 sleep）
    python3 04-pitfall-stale-pid.py --self-test  # 断言两种行为差异
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
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


def naive_is_running(pidfile: str) -> bool:
    """教科书里的错误写法：只看 PID 文件存不存在、PID 进程在不在。"""
    p = Path(pidfile)
    if not p.exists():
        return False
    try:
        pid = int(p.read_text().strip())
    except ValueError:
        return False
    return runner.pid_alive(pid)          # 注意：这里连 cmdline 都不看


def naive_stop(pidfile: str) -> dict:
    """教科书里的错误写法：直接 kill -9 那个 PID。"""
    pid = int(Path(pidfile).read_text().strip())
    os.kill(pid, 9)
    return {"killed": pid, "by": "naive(kill -9, 未验证身份)"}


def scenario_reused_pid(tmp: str) -> dict:
    """洞 2：PID 文件里是一个活着、但完全不是我们服务的进程。"""
    # 起一个"无辜进程"：一个要睡 120 秒的 sleep（相当于别的服务/别的部署）
    victim = subprocess.Popen(["sleep", "120"], start_new_session=True)
    time.sleep(0.2)
    pidfile = str(Path(tmp) / "innocent.pid")
    Path(pidfile).write_text(str(victim.pid), encoding="utf-8")

    naive_says = naive_is_running(pidfile)
    ok, pid, why = runner.validate_pid(pidfile, marker=API)
    correct_says = ok

    # 演示：naive_stop 会把无辜进程杀掉
    result = naive_stop(pidfile) if naive_says else {"killed": None}
    time.sleep(0.3)
    victim_alive_after = runner.pid_alive(victim.pid)
    if victim_alive_after:
        victim.kill()   # 收尾，别留垃圾

    return {
        "scenario": "pidfile-指向别的进程（PID 复用）",
        "victim_pid": victim.pid,
        "naive_is_running": naive_says,
        "correct_is_running": correct_says,
        "correct_reason": why,
        "naive_action": result,
        "victim_alive_after_naive_kill": victim_alive_after,
    }


def scenario_dead_pid(tmp: str) -> dict:
    """洞 1：PID 文件里的进程早就死了，但文件还在。"""
    proc = subprocess.Popen(["sleep", "60"], start_new_session=True)
    pid = proc.pid
    proc.kill()
    proc.wait()                      # 回收，确保不是僵尸（僵尸会干扰判断）
    time.sleep(0.2)

    pidfile = str(Path(tmp) / "dead.pid")
    Path(pidfile).write_text(str(pid), encoding="utf-8")

    naive_says = naive_is_running(pidfile)
    ok, _pid, why = runner.validate_pid(pidfile, marker=API)
    return {
        "scenario": "pidfile-指向已死进程",
        "pid": pid,
        "naive_is_running": naive_says,
        "correct_is_running": ok,
        "correct_reason": why,
    }


def self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="day185-pid-") as tmp:
        a = scenario_reused_pid(tmp)
        print("  洞2:", json.dumps(a, ensure_ascii=False))
        assert a["naive_is_running"] is True, a          # naive 认为"在跑"
        assert a["correct_is_running"] is False, a       # 正确实现识破（cmdline 不匹配）
        assert "reused" in a["correct_reason"] or "cmdline" in a["correct_reason"], a
        assert a["victim_alive_after_naive_kill"] is False, a   # ← 无辜进程真的被杀了

        b = scenario_dead_pid(tmp)
        print("  洞1:", json.dumps(b, ensure_ascii=False))
        assert b["naive_is_running"] is False and b["correct_reason"] == "stale-pidfile(pid-dead)", b

    print("✅ self-test 通过：naive 会杀掉一个无关进程（真的杀了）；正确实现用 cmdline 标记识破身份")
    print("   关键结论：PID 号不是身份凭证，/proc/<pid>/cmdline 才是。")
    return 0


def demo() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="day185-pid-demo-") as tmp:
        print("=== 洞 2：PID 文件指向一个无关的活进程 ===")
        print(json.dumps(scenario_reused_pid(tmp), ensure_ascii=False, indent=2))
        print("\n对比：正确实现会拒绝操作，并给出原因（cmdline 不匹配）。")
        print("\n=== 洞 1：PID 文件指向已死进程 ===")
        print(json.dumps(scenario_dead_pid(tmp), ensure_ascii=False, indent=2))
        print("\n正确实现会返回 stale-pidfile，于是部署脚本知道「它没在跑，该启动」。")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    if "--demo" in sys.argv[1:]:
        return demo()
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
