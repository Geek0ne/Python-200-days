#!/usr/bin/env python3
"""02-repro-card.py — 可复现实验卡片生成器（零依赖，离线可跑）

为什么需要它：
  技术文章里最贵的一句话是"我测过"。但"我测过"如果没有环境、样本量、重复次数，
  读者既不能验证也不能反驳，等于没写。这个脚本把一次命令执行变成一张
  带环境指纹、耗时分布、输出哈希的 Markdown 卡片——可以直接粘进文章。

用法:
    python3 02-repro-card.py --repeat 5 -- python3 -c "print(sum(range(1000)))"
    python3 02-repro-card.py --repeat 3 --json -- python3 -V
    python3 02-repro-card.py --self-test

判定逻辑:
    * 所有重复的 stdout 哈希相同 -> 输出可复现
    * 哈希不同                   -> 输出含随机/时间/并发因素，不能当结论引用
    * 耗时极差 / 中位数 > 20%    -> 计时噪声大，样本量不够
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import shutil
import statistics
import subprocess
import sys
import time

NOISE_THRESHOLD = 0.20  # 极差超过中位数 20% 视为计时噪声


def cpu_model() -> str:
    """从 /proc/cpuinfo 取型号；取不到就给平台名。非 Linux 不报错。"""
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as fh:
            for line in fh:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def git_head(cwd: str) -> str:
    if not shutil.which("git"):
        return "no-git"
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=cwd,
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "no-commit"
    except (OSError, subprocess.SubprocessError):
        return "no-commit"


def fingerprint() -> dict:
    uname = platform.uname()
    try:
        load = os.getloadavg()
    except OSError:
        load = (0.0, 0.0, 0.0)
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": f"{uname.system} {uname.release}",
        "machine": uname.machine,
        "cpu": cpu_model(),
        "cpu_count": os.cpu_count(),
        "load1": round(load[0], 2),
        "cwd": os.getcwd(),
        "git_head": git_head(os.getcwd()),
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def run_once(cmd: list[str]) -> dict:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    return {
        "seconds": dt,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "sha256": hashlib.sha256(proc.stdout.encode()).hexdigest()[:16],
    }


def measure(cmd: list[str], repeat: int) -> dict:
    runs = [run_once(cmd) for _ in range(repeat)]
    times = [r["seconds"] for r in runs]
    hashes = {r["sha256"] for r in runs}
    median = statistics.median(times)
    spread = (max(times) - min(times)) / median if median else 0.0
    return {
        "command": shlex.join(cmd),
        "repeat": repeat,
        "runs": runs,
        "times": [round(t, 6) for t in times],
        "min": round(min(times), 6),
        "median": round(median, 6),
        "max": round(max(times), 6),
        "spread": round(spread, 3),
        "stable_output": len(hashes) == 1,
        "output_sha256": runs[0]["sha256"],
        "noisy_timing": spread > NOISE_THRESHOLD,
        "all_zero": all(r["returncode"] == 0 for r in runs),
    }


def to_markdown(env: dict, m: dict) -> str:
    last = m["runs"][-1]
    status = "✅ 输出可复现" if m["stable_output"] else "⚠️ 输出不稳定，不可作为结论"
    timing = "⚠️ 计时噪声大" if m["noisy_timing"] else "✅ 计时稳定"
    lines = [
        "### 可复现实验卡片",
        "",
        f"- **命令**：`{m['command']}`",
        f"- **环境**：Python {env['python']} / {env['platform']} / {env['machine']} / "
        f"{env['cpu_count']} 核 / load1={env['load1']}",
        f"- **时间**：{env['utc']}（UTC），commit `{env['git_head']}`",
        f"- **重复**：{m['repeat']} 次，取 median",
        f"- **耗时**：min {m['min']*1000:.2f} ms · median {m['median']*1000:.2f} ms · "
        f"max {m['max']*1000:.2f} ms（极差/中位 {m['spread']*100:.1f}%）",
        f"- **判定**：{status}；{timing}",
        "",
        "```text",
        f"$ {m['command']}",
        last["stdout"].rstrip() or "(无输出)",
        "```",
        "",
        f"退出码 {last['returncode']}，stdout sha256 前缀 `{m['output_sha256']}`。",
    ]
    if last["stderr"].strip():
        lines += ["", "stderr：", "", "```text", last["stderr"].rstrip(), "```"]
    return "\n".join(lines)


def self_test() -> int:
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("  ✅ " if cond else "  ❌ ") + msg)
        ok = ok and bool(cond)

    m = measure([sys.executable, "-c", "print(sum(range(1000)))"], 3)
    check(m["stable_output"], "确定性命令的 stdout 哈希一致")
    check(m["all_zero"], "三次退出码都是 0")
    check(m["runs"][0]["stdout"].strip() == "499500", "取到了真实 stdout（499500）")
    check(m["median"] > 0, "记录了非零耗时")
    check(len(m["times"]) == 3, "重复了 3 次")

    bad = measure([sys.executable, "-c", "import sys; sys.exit(3)"], 2)
    check(bad["runs"][0]["returncode"] == 3, "失败命令的退出码被保留（3）")
    check(not bad["all_zero"], "失败命令不会被当成成功")

    noisy = measure([sys.executable, "-c",
                     "import random; print(random.random())"], 4)
    check(not noisy["stable_output"], "随机输出被判为不稳定")

    env = fingerprint()
    check(env["python"] == platform.python_version(), "环境指纹的 Python 版本正确")
    md = to_markdown(env, m)
    check("可复现实验卡片" in md and "499500" in md, "Markdown 卡片包含命令与真实输出")

    print("SELF-TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="把一次命令执行变成可复现实验卡片")
    ap.add_argument("--repeat", type=int, default=5, help="重复次数（默认 5）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="写入文件而不是 stdout")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="-- 之后的命令")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not cmd:
        ap.error("缺少要执行的命令，例如: -- python3 -c 'print(1)'")
    if args.repeat < 1:
        ap.error("--repeat 必须 >= 1")

    env = fingerprint()
    m = measure(cmd, args.repeat)
    text = json.dumps({"env": env, "measure": {k: v for k, v in m.items() if k != "runs"}},
                      ensure_ascii=False, indent=2) if args.json else to_markdown(env, m)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"已写入 {args.out}")
    else:
        print(text)
    return 0 if m["all_zero"] else 1


if __name__ == "__main__":
    sys.exit(main())
