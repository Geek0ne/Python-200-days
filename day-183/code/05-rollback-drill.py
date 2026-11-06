#!/usr/bin/env python3
"""
Day 183 · 05 — 回滚演练（真起容器，真失败，真回滚）

这不是演示动画，是一段真跑的脚本：它连续做两次真实部署，
第二次的容器**真的**会在就绪探针上返回 503，然后看系统能不能自己退回去。

演练四幕：
    第一幕  部署 v1.0.0        → 期望 rc=0（上线成功）
    第二幕  部署 v2.0.0（带故障注入 FAIL_MODE=readiness）
                               → 期望 rc=2（健康检查失败 + 自动回滚）
    第三幕  独立复核：现在服务的是哪个版本？（不能只信部署脚本自己说）
    第四幕  打印账本 releases.json

第三幕是重点：**部署脚本报「已回滚」不等于服务真回来了**，
所以要用一个独立于它的方式（直接 curl）再确认一次。

用法：
    python3 05-rollback-drill.py --dry-run    # 打印四幕剧本，不执行
    python3 05-rollback-drill.py              # 真跑（需要 Docker + 已构建 day183-ops:multi）
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEPLOY = HERE / "04-deploy-rollback.py"
IMAGE = "day183-ops:multi"
NAME = "d183-ops"
PORT = 18080
STATE = "/tmp/day183/state"


def curl_version(port: int) -> str:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/version", timeout=3) as r:
        return json.loads(r.read().decode("utf-8"))["version"]


def curl_status(port: int, path: str) -> int:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", 0)


def run_deploy(*extra: str) -> tuple[int, float, str]:
    cmd = [sys.executable, str(DEPLOY), "--image", IMAGE, "--name", NAME,
           "--port", str(PORT), "--state", STATE, *extra]
    t0 = time.monotonic()
    p = subprocess.run(cmd, capture_output=True, text=True)
    dur = time.monotonic() - t0
    out = p.stdout
    print(out.rstrip())
    if p.stderr.strip():
        print("STDERR: " + p.stderr.strip(), file=sys.stderr)
    return p.returncode, dur, out


def dry_run() -> int:
    print("▶ 回滚演练剧本（--dry-run）")
    print(f"  第一幕  python3 04-deploy-rollback.py --image {IMAGE} --version v1.0.0")
    print("          期望 rc=0；容器上线，releases.json 的 current=v1.0.0")
    print(f"  第二幕  python3 04-deploy-rollback.py --image {IMAGE} --version v2.0.0 "
          f"--env FAIL_MODE=readiness")
    print("          期望 rc=2；/readyz 返 503 → 收日志 → 停容器 → 回滚 v1.0.0")
    print(f"  第三幕  curl -s http://127.0.0.1:{PORT}/version   ← 独立复核，别信部署脚本自述")
    print(f"          期望 version=v1.0.0")
    print("  第四幕  cat /tmp/day183/state/releases.json")
    print("          期望 history 里 v2.0.0 是 failed 且带 reason，且**从未**成为 current")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Day 183 · 回滚演练")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if args.dry_run:
        return dry_run()

    results: list[tuple[str, int, int, float, str]] = []

    print("=" * 72)
    print("第一幕 · 部署 v1.0.0（正常版本）")
    print("=" * 72)
    rc1, d1, _ = run_deploy("--version", "v1.0.0")
    results.append(("部署 v1.0.0", rc1, 0, d1, "上线成功" if rc1 == 0 else "意外失败"))

    print()
    print("=" * 72)
    print("第二幕 · 部署 v2.0.0（故障注入：FAIL_MODE=readiness，就绪探针必挂）")
    print("=" * 72)
    rc2, d2, _ = run_deploy("--version", "v2.0.0", "--env", "FAIL_MODE=readiness")
    results.append(("部署 v2.0.0（坏）", rc2, 2, d2, "失败并回滚" if rc2 == 2 else f"意外 rc={rc2}"))

    print()
    print("=" * 72)
    print("第三幕 · 独立复核（直接 curl，不信部署脚本的自述）")
    print("=" * 72)
    time.sleep(1)
    try:
        ver = curl_version(PORT)
        code_ok = curl_status(PORT, "/healthz")
        code_nope = curl_status(PORT, "/readyz")
        print(f"  GET /version -> {ver}")
        print(f"  GET /healthz -> {code_ok}")
        print(f"  GET /readyz  -> {code_nope}")
        expected = "v1.0.0"
        third = "✅ 服务确实是 v1.0.0（回滚生效）" if ver == expected else f"❌ 期望 {expected}，实际 {ver}"
        print(f"  {third}")
        results.append(("独立复核 /version", 0 if ver == expected else 1, 0, 0.0, ver))
    except Exception as e:
        print(f"  ❌ 复核失败：{e}")
        results.append(("独立复核 /version", 1, 0, 0.0, str(e)))

    print()
    print("=" * 72)
    print("第四幕 · 账本 releases.json")
    print("=" * 72)
    state_file = Path(STATE) / "releases.json"
    print(state_file.read_text(encoding="utf-8") if state_file.exists() else "（没有账本文件）")

    print()
    print("=" * 72)
    print("演练汇总")
    print("=" * 72)
    print(f"  {'动作':<22}{'rc':>4}{'期望':>6}{'耗时':>9}  结论")
    all_ok = True
    for label, rc, want, dur, note in results:
        good = rc == want
        all_ok = all_ok and good
        print(f"  {label:<22}{rc:>4}{want:>6}{dur:>8.2f}s  {'✅' if good else '❌'} {note}")
    print()
    print("  ✅ 演练通过：坏版本被拦住、服务退回到 v1.0.0" if all_ok else "  ❌ 演练未达预期")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
