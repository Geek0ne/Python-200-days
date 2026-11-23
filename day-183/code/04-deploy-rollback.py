#!/usr/bin/env python3
"""
Day 183 · 04 — 一键部署 + 健康检查 + 回滚

一条命令把「构建好的镜像」变成「正在提供服务的容器」，并且在变坏时自己退回去：

    构建/取镜像 → 起新容器 → 等 /healthz 与 /readyz → 冒烟 → 记账（成功）
                                     │
                                     └── 超时 / 非 200 → 收日志 → 停掉 → 回滚到上一个版本

设计上有意拆成两层：
  - DockerRuntime：真正调 docker 的那层（有副作用，只在真跑时用）
  - ReleaseManager：纯逻辑（记账、判断、回滚决策），可以注入 FakeRuntime 离线自检

「回滚」的正确语义：**新版本在它被判定为坏的那一刻就从未算作可用**。
releases.json 里只留验证通过的版本，坏版本只进 history 并带失败原因。

用法：
    python3 04-deploy-rollback.py --self-test                 # 离线：纯逻辑自检，不碰 Docker
    python3 04-deploy-rollback.py --dry-run --version v1.0.0  # 降级路径：只打印计划
    python3 04-deploy-rollback.py --image day183-ops:multi --version v1.0.0
    python3 04-deploy-rollback.py --status
    python3 04-deploy-rollback.py --rollback
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_NAME = "d183-ops"
DEFAULT_PORT = 18080
DEFAULT_STATE = Path("/tmp/day183/state")
DEFAULT_TIMEOUT = 30.0


# --- 运行时抽象 ---------------------------------------------------------------
class Runtime:
    """部署动作的最小接口。真想调 docker 的实现在下面，测试里换成 Fake。"""

    def stop(self, name: str) -> None: ...
    def start(self, name: str, image: str, port: int, env: dict[str, str]) -> None: ...
    def logs(self, name: str, tail: int = 20) -> str: ...
    def health(self, port: int, timeout: float, require_ready: bool) -> tuple[bool, dict]: ...
    def smoke(self, port: int, expect_version: str) -> tuple[bool, str]: ...


class DockerRuntime(Runtime):
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        if self.verbose:
            print("    $ " + " ".join(args))
        return subprocess.run(args, capture_output=True, text=True, check=check)

    def stop(self, name: str) -> None:
        self._run(["docker", "rm", "-f", name], check=False)

    def start(self, name: str, image: str, port: int, env: dict[str, str]) -> None:
        args = ["docker", "run", "-d", "--name", name, "-p", f"{port}:8080"]
        for k, v in env.items():
            args += ["-e", f"{k}={v}"]
        args.append(image)
        p = self._run(args)
        if self.verbose:
            print("    container id: " + p.stdout.strip()[:12])

    def logs(self, name: str, tail: int = 20) -> str:
        return self._run(["docker", "logs", "--tail", str(tail), name], check=False).stdout + \
               self._run(["docker", "logs", "--tail", str(tail), name], check=False).stderr

    def health(self, port: int, timeout: float, require_ready: bool) -> tuple[bool, dict]:
        paths = ["/healthz", "/readyz"] if require_ready else ["/healthz"]
        deadline = time.monotonic() + timeout
        started = time.monotonic()
        last: dict = {}
        while time.monotonic() < deadline:
            ok, detail = True, {}
            for p in paths:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}{p}", timeout=2) as r:
                        body = json.loads(r.read().decode("utf-8"))
                        detail[p] = {"status": r.status, "body": body}
                        if r.status != 200:
                            ok = False
                except urllib.error.HTTPError as e:
                    detail[p] = {"status": e.code, "body": e.read().decode("utf-8")}
                    ok = False
                except Exception as e:  # 连不上 = 还没起来
                    detail[p] = {"status": 0, "body": str(e)}
                    ok = False
            last = detail
            if ok:
                return True, {"elapsed": round(time.monotonic() - started, 3), "detail": detail}
            time.sleep(0.5)
        return False, {"elapsed": round(time.monotonic() - started, 3), "detail": last}

    def smoke(self, port: int, expect_version: str) -> tuple[bool, str]:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/version", timeout=3) as r:
                ver = json.loads(r.read().decode("utf-8"))["version"]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/hosts", timeout=3) as r:
                hosts = json.loads(r.read().decode("utf-8"))["count"]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/summary", timeout=3) as r:
                summary = json.loads(r.read().decode("utf-8"))
            problems = []
            if expect_version and ver != expect_version:
                problems.append(f"版本不符：容器报 {ver}，期望 {expect_version}")
            if hosts != 4:
                problems.append(f"主机数异常：{hosts}")
            if summary.get("by_role") != {"web": 2, "db": 1, "cache": 1}:
                problems.append(f"聚合异常：{summary.get('by_role')}")
            if problems:
                return False, "；".join(problems)
            return True, f"version={ver} hosts={hosts} by_role={summary['by_role']}"
        except Exception as e:
            return False, f"冒烟请求失败：{e}"


# --- 发布记账（纯逻辑，可离线测）-----------------------------------------------
class ReleaseManager:
    def __init__(self, state_dir: Path, runtime: Runtime, name: str, port: int,
                 health_timeout: float = DEFAULT_TIMEOUT, verbose: bool = False):
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.rt = runtime
        self.name = name
        self.port = port
        self.health_timeout = health_timeout
        self.verbose = verbose

    # --- 状态文件 ---------------------------------------------------------
    @property
    def releases_file(self) -> Path:
        return self.dir / "releases.json"

    def load(self) -> dict:
        if self.releases_file.exists():
            return json.loads(self.releases_file.read_text(encoding="utf-8"))
        return {"current": None, "history": []}

    def save(self, state: dict) -> None:
        self.releases_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- 部署 -------------------------------------------------------------
    def deploy(self, image: str, version: str, env: dict[str, str] | None = None) -> int:
        state = self.load()
        prev = state["current"]
        env = dict(env or {})
        env.setdefault("APP_VERSION", version)
        print(f"▶ 部署 {version}（镜像 {image}）")
        if prev:
            print(f"  上一个可用版本：{prev['version']}（镜像 {prev['image']}）—— 失败时回滚到它")
        else:
            print("  没有上一个可用版本：失败时无路可回（这正是「首次上线」的风险）")

        self.rt.stop(self.name)
        self.rt.start(self.name, image, self.port, env)

        ok, detail = self.rt.health(self.port, self.health_timeout, require_ready=True)
        print(f"  健康检查：{'✅ 通过' if ok else '❌ 失败'}（用时 {detail['elapsed']}s）")
        if not ok:
            print(f"  最后一次探测结果：{json.dumps(detail['detail'], ensure_ascii=False)}")
            print("  --- 容器日志（tail 20）---")
            for line in self.rt.logs(self.name).splitlines()[-20:]:
                print("    " + line)
            return self._fail_and_rollback(state, prev, image, version, "健康检查未通过")

        sok, msg = self.rt.smoke(self.port, version)
        print(f"  冒烟测试：{'✅ 通过' if sok else '❌ 失败'} — {msg}")
        if not sok:
            return self._fail_and_rollback(state, prev, image, version, f"冒烟失败：{msg}")

        state["current"] = {"version": version, "image": image, "at": _now(), "smoke": msg}
        state["history"].append({"version": version, "image": image, "at": _now(), "result": "ok"})
        self.save(state)
        print(f"✅ {version} 已上线并记账 → {self.releases_file}")
        return 0

    def _fail_and_rollback(self, state: dict, prev: dict | None, image: str, version: str, reason: str) -> int:
        state["history"].append({"version": version, "image": image, "at": _now(),
                                 "result": "failed", "reason": reason})
        self.rt.stop(self.name)
        if not prev:
            self.save(state)
            print(f"❌ {version} 部署失败（{reason}），且没有可回滚的版本 → 服务当前是 **停的**")
            return 3
        print(f"  ↩ 回滚到 {prev['version']}（镜像 {prev['image']}）")
        state["history"].append({"version": prev["version"], "image": prev["image"],
                                 "at": _now(), "result": "rollback-target"})
        self.save(state)
        return self._restore(prev, state)

    def _restore(self, release: dict, state: dict) -> int:
        self.rt.stop(self.name)
        self.rt.start(self.name, release["image"], self.port, {"APP_VERSION": release["version"]})
        ok, detail = self.rt.health(self.port, self.health_timeout, require_ready=True)
        if not ok:
            print(f"❌ 回滚也失败了：回滚目标 {release['version']} 同样不健康 → 人工介入")
            state["current"] = None
            self.save(state)
            return 3
        state["current"] = dict(release)
        self.save(state)
        print(f"✅ 已回滚到 {release['version']}，健康检查通过（{detail['elapsed']}s）")
        print("   注意：坏版本从未进入 current —— 这就是「先判后切」和「先切后撤」的区别")
        return 2

    def rollback(self) -> int:
        state = self.load()
        good = [h for h in state["history"] if h["result"] == "ok"]
        if len(good) < 2 and not state["current"]:
            print("❌ 没有可回滚的历史版本")
            return 3
        cur = state["current"]["version"] if state["current"] else None
        candidates = [h for h in good if h["version"] != cur]
        if not candidates:
            print(f"❌ 只有一个可用版本（{cur}），没有可回滚目标")
            return 3
        target = candidates[-1]
        print(f"▶ 手动回滚：{cur} → {target['version']}")
        return self._restore(target, state)

    def status(self) -> int:
        state = self.load()
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


# --- FakeRuntime：离线自检用 --------------------------------------------------
class FakeRuntime(Runtime):
    """不碰 Docker，按剧本返回健康结果。用来测「决策」而不是「docker 命令」。"""

    def __init__(self, bad_images: set[str] | None = None, bad_versions: set[str] | None = None,
                 always_unhealthy: bool = False):
        self.bad_images = bad_images or set()
        self.bad_versions = bad_versions or set()
        self.always_unhealthy = always_unhealthy
        self.running: dict | None = None
        self.started: list[tuple[str, dict[str, str]]] = []

    def stop(self, name: str) -> None:
        self.running = None

    def start(self, name: str, image: str, port: int, env: dict[str, str]) -> None:
        self.running = {"image": image, "env": env}
        self.started.append((image, env))

    def logs(self, name: str, tail: int = 20) -> str:
        return "fake log line\n" * min(tail, 3)

    def _is_bad(self) -> bool:
        if not self.running:
            return True
        if self.always_unhealthy:
            return True
        return self.running["image"] in self.bad_images or self.running["env"].get("FAIL_MODE") == "readiness"

    def health(self, port: int, timeout: float, require_ready: bool) -> tuple[bool, dict]:
        ok = not self._is_bad()
        return ok, {"elapsed": 0.01, "detail": {"readyz": {"status": 200 if ok else 503}}}

    def smoke(self, port: int, expect_version: str) -> tuple[bool, str]:
        if self._is_bad():
            return False, "连不上"
        return True, f"version={expect_version} hosts=4"


def self_test() -> int:
    import tempfile

    checks: list[tuple[str, bool]] = []

    # 1) 首次部署成功
    with tempfile.TemporaryDirectory() as td:
        rt = FakeRuntime()
        rm = ReleaseManager(Path(td), rt, "c", 1)
        rc = rm.deploy("img:v1", "v1")
        st = rm.load()
        checks.append(("首次部署成功 rc=0", rc == 0))
        checks.append(("current 记账为 v1", st["current"]["version"] == "v1"))
        checks.append(("history 只有 1 条且 result=ok", len(st["history"]) == 1 and st["history"][0]["result"] == "ok"))

    # 2) 第二次部署失败 → 自动回滚，current 仍是 v1，坏版本不进 current
    with tempfile.TemporaryDirectory() as td:
        rt = FakeRuntime()
        rm = ReleaseManager(Path(td), rt, "c", 1)
        rm.deploy("img:v1", "v1")
        rc = rm.deploy("img:v2", "v2", env={"FAIL_MODE": "readiness"})
        st = rm.load()
        checks.append(("坏版本部署返回 rc=2（已回滚）", rc == 2))
        checks.append(("current 仍停在 v1", st["current"]["version"] == "v1"))
        checks.append(("history 里 v2 标 failed 且带原因",
                       any(h["version"] == "v2" and h["result"] == "failed" and h.get("reason") for h in st["history"])))
        checks.append(("最后一次 start 是回滚动作（镜像回到 v1）", rt.started[-1][0] == "img:v1"))

    # 3) 首次部署就失败 → 没有可回滚版本，返回 3 且 current 为空
    with tempfile.TemporaryDirectory() as td:
        rt = FakeRuntime(bad_images={"img:bad"})
        rm = ReleaseManager(Path(td), rt, "c", 1)
        rc = rm.deploy("img:bad", "v0")
        st = rm.load()
        checks.append(("首次即失败 rc=3 且 current 为 None", rc == 3 and st["current"] is None))

    # 4) 手动回滚：v1 → v2 后回滚，应回到 v1
    with tempfile.TemporaryDirectory() as td:
        rt = FakeRuntime()
        rm = ReleaseManager(Path(td), rt, "c", 1)
        rm.deploy("img:v1", "v1")
        rm.deploy("img:v2", "v2")
        rc = rm.rollback()
        st = rm.load()
        checks.append(("手动回滚 rc=2", rc == 2))
        checks.append(("回滚后 current=v1", st["current"]["version"] == "v1"))

    # 5) 只有一个版本时回滚应被拒绝
    with tempfile.TemporaryDirectory() as td:
        rt = FakeRuntime()
        rm = ReleaseManager(Path(td), rt, "c", 1)
        rm.deploy("img:v1", "v1")
        checks.append(("只有一个版本时拒绝回滚（rc=3）", rm.rollback() == 3))

    # 6) 回滚目标本身也不健康 → rc=3，且 current 置空（不假装在线）
    with tempfile.TemporaryDirectory() as td:
        rt = FakeRuntime()
        rm = ReleaseManager(Path(td), rt, "c", 1)
        rm.deploy("img:v1", "v1")
        rt.always_unhealthy = True
        rc = rm.deploy("img:v2", "v2")
        st = rm.load()
        checks.append(("回滚也无救时 rc=3 且 current 清空", rc == 3 and st["current"] is None))

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'✅' if ok else '❌'} {n}")
    if failed:
        print(f"❌ self-test 失败：{len(failed)}/{len(checks)} -> {failed}")
        return 1
    print(f"✅ self-test 通过：{len(checks)} 项断言全过（FakeRuntime，不碰 Docker）")
    return 0


def dry_run(image: str, version: str, name: str, port: int) -> int:
    print("▶ 一键部署计划（--dry-run，不执行任何命令）")
    for i, step in enumerate([
        f"docker rm -f {name}                      # 停旧容器（失败时才知道要回到哪个镜像）",
        f"docker run -d --name {name} -p {port}:8080 -e APP_VERSION={version} {image}",
        f"轮询 GET http://127.0.0.1:{port}/healthz 与 /readyz（每 0.5s 一次，总超时 "
        f"{DEFAULT_TIMEOUT:.0f}s）",
        f"冒烟：GET /version（校验 == {version}）、/api/hosts（须 4 台）、/api/summary（聚合须对）",
        "全部通过 → 写 releases.json 的 current；任一失败 → 收 tail 20 日志 → 停容器 → 起回滚目标",
    ], 1):
        print(f"  {i}. {step}")
    print("  ⚠️ 冒烟失败时，坏版本只进 history（result=failed），**不进 current**")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Day 183 · 一键部署 + 健康检查 + 回滚")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--image", default="day183-ops:multi")
    p.add_argument("--version", default=None)
    p.add_argument("--name", default=DEFAULT_NAME)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--state", default=str(DEFAULT_STATE))
    p.add_argument("--health-timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--env", action="append", default=[], help="额外的 -e KEY=VAL（可重复）")
    p.add_argument("--rollback", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.dry_run:
        return dry_run(args.image, args.version or "vX.Y.Z", args.name, args.port)

    env = {}
    for kv in args.env:
        k, _, v = kv.partition("=")
        env[k] = v

    rt = DockerRuntime(verbose=args.verbose)
    rm = ReleaseManager(Path(args.state), rt, args.name, args.port, args.health_timeout, args.verbose)

    if args.status:
        return rm.status()
    if args.rollback:
        return rm.rollback()
    if not args.version:
        print("❌ 部署需要 --version（回滚/状态用 --rollback / --status）")
        return 1
    return rm.deploy(args.image, args.version, env)


if __name__ == "__main__":
    sys.exit(main())
