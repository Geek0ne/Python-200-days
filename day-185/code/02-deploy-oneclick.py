#!/usr/bin/env python3
"""
Day 185 · 示例 02 —— 一键部署（预检 → 启动 → 就绪 → 验收 → 失败回滚）

为什么要有这个文件？
    "一键部署"的价值不是"少敲几条命令"，而是**把"部署成功"变成一个程序能判定的结论**：
        预检不过 → 不动线上；就绪超时 → 自动回滚；验收不过 → 退出码非 0，CI 红。
    没有这些的"一键部署"脚本，只是把事故从"手滑"升级成"批量手滑"。

本文件的流水线（每一步都有明确的失败出口）：

    [0] 预检     端口没被占、python 可用、磁盘可写   ──失败→ exit 3（什么都没改）
    [1] 记录现状 读 current.json，记住现在是哪个版本   ──用来回滚
    [2] 启动     拉起进程，写 pidfile，等待 /readyz=200 ──超时→ 走 [5] 回滚
    [3] 业务验收 /api/v1/hosts 真的能返回数据          ──失败→ 走 [5] 回滚
    [4] 落状态   current.json + history.jsonl（追加式）
    [5] 回滚     停新版本、恢复上一版本、再验收一次      ──回滚也失败→ exit 5（人工介入）

运行方式：
    # 正常部署
    python3 02-deploy-oneclick.py --port 8400 --version v1.2.0 --state-dir /tmp/d185
    # 演练"这个版本坏了"：就绪永远不成功 → 触发自动回滚
    python3 02-deploy-oneclick.py --port 8400 --version v1.2.1 --state-dir /tmp/d185 --simulate-bad-release
    # 只看不干（把要执行的步骤打出来）
    python3 02-deploy-oneclick.py --port 8400 --version v1.2.2 --state-dir /tmp/d185 --dry-run
    python3 02-deploy-oneclick.py --self-test

退出码约定（CI 依赖它，别乱改）：
    0 成功 | 3 预检失败 | 4 就绪/验收失败但已回滚 | 5 回滚也失败（需要人）
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(numbered_name: str):
    """按文件路径加载 01-process-runner.py。

    为什么不直接 import：模块名以数字开头，没法 import 语句；
    而且显式按路径加载能保证"用的就是我旁边这份代码"。
    """
    path = HERE / numbered_name
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load("01-process-runner.py")
API = str(HERE / "00-platform-api.py")


# ────────────────────── 工具 ──────────────────────

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def port_in_use(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def free_port() -> int:
    """让内核分配一个空闲端口。

    为什么自证脚本要这样拿端口：写死端口 = 上一次运行残留的进程会让这一次直接失败
    （本日真机踩到：自证脚本崩溃后没清掉子进程，第二次跑 preflight 就报"端口占用"）。
    """
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def load_state(state_dir: str) -> dict:
    p = Path(state_dir) / "current.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state_dir: str, data: dict, event: str) -> None:
    d = Path(state_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / "current.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(d / "history.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"event": event, "at": now(), **data}, ensure_ascii=False) + "\n")


# ────────────────────── 各阶段 ──────────────────────

def preflight(port: int, state_dir: str) -> tuple[bool, str]:
    """预检：**按"是不是自己的服务"判断，而不是"端口空不空"**。

    为什么不能简单地"端口被占就失败"：
        原地升级时，上一版的服务本来就在监听这个端口。如果预检把"端口被占"一律当障碍，
        第二次部署就永远做不成（本日真机踩到，断言 rc==4 却拿到 3）。
    正确做法：端口被占时去看 pidfile，用 cmdline 标记确认"占用者是不是我们的服务"：
        是自己的 → 允许继续（下一步会先优雅停掉它）；不是自己的 → 立刻失败，绝不乱杀。
    """
    if not Path(API).exists():
        return False, f"被部署的服务不存在: {API}"

    pidfile = Path(state_dir) / "api.pid"
    mine, pid, why = (False, 0, "no-pidfile")
    if pidfile.exists():
        mine, pid, why = runner.validate_pid(str(pidfile), marker=API)

    if port_in_use(port):
        if not mine:
            return False, f"端口 {port} 被**非本服务**占用，拒绝部署（不杀无名进程；pidfile 判定={why}）"
        return True, f"ok（端口 {port} 上是本服务 pid={pid}，将先优雅停掉再启动新版）"
    try:
        Path(state_dir).mkdir(parents=True, exist_ok=True)
        probe = Path(state_dir) / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return False, f"状态目录不可写: {exc}"
    return True, "ok"


def start_and_verify(port: int, pidfile: str, logfile: str, version: str,
                     ready_delay: float, fail_ready: bool, ready_timeout: float,
                     data: str | None) -> dict:
    info = runner.start_service(port=port, pidfile=pidfile, logfile=logfile, version=version,
                                ready_delay=ready_delay, fail_ready=fail_ready)
    info["ready_timeout"] = ready_timeout
    if info.get("ready"):
        code, body = runner.http_get(f"http://127.0.0.1:{port}/api/v1/hosts")
        info["business_check"] = {"code": code, "count": body.get("count")}
        info["business_ok"] = code == 200
    else:
        info["business_ok"] = False
    return info


def deploy(args) -> int:
    state_dir = args.state_dir
    previous = load_state(state_dir)
    plan = [
        f"[0] 预检：端口 {args.port} 空闲 / 状态目录可写",
        f"[1] 记录现状：current={previous.get('version', '(无)')}",
        f"[2] 启动 {args.version} → 等待 /readyz=200（超时 {args.ready_timeout}s）",
        f"[3] 业务验收：GET /api/v1/hosts 必须 200",
        f"[4] 落状态：current.json + history.jsonl",
        f"[5] 失败则回滚到 {previous.get('version', '(无旧版本)')}",
    ]
    print("部署计划:")
    for line in plan:
        print("   ", line)
    if args.dry_run:
        print("--dry-run：只打印计划，未做任何改动（退出码 0）")
        return 0

    ok, why = preflight(args.port, state_dir)
    print(f"[0] 预检: {'通过' if ok else '失败 — ' + why}")
    if not ok:
        return 3

    pidfile = str(Path(state_dir) / "api.pid")
    logfile = str(Path(state_dir) / f"api-{args.version}.log")

    # 如果上一版本还在跑，先优雅停掉（单实例部署）
    if previous.get("version"):
        stop_info = runner.stop_service(pidfile)
        print(f"[1] 停止旧版本: {json.dumps(stop_info, ensure_ascii=False)}")

    info = start_and_verify(args.port, pidfile, logfile, args.version,
                            args.ready_delay, args.simulate_bad_release,
                            args.ready_timeout, args.data)
    print(f"[2] 启动结果: {json.dumps(info, ensure_ascii=False)}")

    if not (info.get("ready") and info.get("business_ok")):
        print("[!] 新版未通过验收 → 触发自动回滚")
        runner.stop_service(pidfile)
        if previous.get("version"):
            back = start_and_verify(args.port, pidfile, logfile, previous["version"],
                                    0.3, False, args.ready_timeout, previous.get("data"))
            print(f"[5] 回滚到 {previous['version']}: {json.dumps(back, ensure_ascii=False)}")
            if back.get("ready") and back.get("business_ok"):
                save_state(state_dir, previous, event="rollback-ok")
                print("✅ 已回滚到上一个可用版本（线上没坏）")
                return 4
            save_state(state_dir, previous, event="rollback-failed")
            print("❌ 回滚也失败了 —— 需要人工介入")
            return 5
        save_state(state_dir, {"version": None}, event="deploy-failed-no-previous")
        print("❌ 新版失败且没有可回滚的旧版本")
        return 4

    save_state(state_dir, {"version": args.version, "port": args.port, "data": args.data,
                           "pid": info.get("pid"), "deployed_at": now()}, event="deploy-ok")
    print(f"✅ 部署成功: {args.version} (pid={info.get('pid')}, "
          f"就绪等待 {info.get('ready_wait_s')}s)")
    return 0


def self_test() -> int:
    """离线自证：正常部署成功 → 坏版本自动回滚 → 端口冲突时预检拦截。"""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="day185-deploy-") as tmp:
        hosts_file = Path(tmp) / "hosts.json"
        hosts_file.write_text(json.dumps([{"host": "web-01"}, {"host": "web-02"}]), encoding="utf-8")

        class A:
            port = 0
            version = "v1.0.0"
            state_dir = tmp
            ready_timeout = 8.0
            ready_delay = 0.3
            simulate_bad_release = False
            data = str(hosts_file)
            dry_run = False

        A.port = free_port()
        pidfile = str(Path(tmp) / "api.pid")
        events = []
        try:
            rc = deploy(A())
            assert rc == 0, rc
            assert load_state(tmp)["version"] == "v1.0.0", load_state(tmp)

            # 坏版本：就绪永远失败 → 应该回滚到 v1.0.0 并返回 4
            A.version = "v1.0.1-bad"
            A.simulate_bad_release = True
            A.ready_timeout = 3.0
            rc = deploy(A())
            assert rc == 4, rc
            assert load_state(tmp)["version"] == "v1.0.0", load_state(tmp)

            history = [json.loads(l)
                       for l in (Path(tmp) / "history.jsonl").read_text().splitlines()]
            events = [h["event"] for h in history]
            assert "deploy-ok" in events and "rollback-ok" in events, events
        finally:
            # 必须显式收尾：临时目录被删掉后 pidfile 就没了，子进程会变成"孤儿"继续占端口，
            # 于是下一次运行直接失败（本日真机踩到）。自证脚本的收尾和业务代码一样重要。
            runner.stop_service(pidfile)
            time.sleep(0.2)

        # 预检拦截：端口被占（自己起一个占位监听）
        with socket.socket() as blocker:
            blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            blocker.bind(("127.0.0.1", A.port))
            blocker.listen(1)
            ok, why = preflight(A.port, tmp)
            assert not ok and "占用" in why, (ok, why)

    print("✅ self-test 通过：部署成功 → 坏版本自动回滚 → 端口占用被预检拦截；事件:", events)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="一键部署（含自动回滚）")
    p.add_argument("--port", type=int, default=8400)
    p.add_argument("--version", default="v1.0.0")
    p.add_argument("--state-dir", default="/tmp/day185")
    p.add_argument("--ready-timeout", type=float, default=10.0)
    p.add_argument("--ready-delay", type=float, default=0.5)
    p.add_argument("--data", default=None)
    p.add_argument("--simulate-bad-release", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        return self_test()
    return deploy(args)


if __name__ == "__main__":
    raise SystemExit(main())
