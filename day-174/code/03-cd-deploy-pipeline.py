#!/usr/bin/env python3
"""03 — 实战：CD 部署流水线的本地演练器。

真实 GitHub Actions 的 deploy job 会做的事，这里在本地全流程模拟：
  门禁（lint + test + 覆盖率阈值） → 产物构建 → 版本号生成
  → 滚动部署 → 健康检查 → 失败自动回滚

设计要点：deploy 之前必须有 gate，失败必须能回滚到上一个版本。
这两件事是「能放心自动部署」的前提，不是可选项。

用法：
    python3 03-cd-deploy-pipeline.py run          # 完整流水线
    python3 03-cd-deploy-pipeline.py run --flaky  # 故意让新版不健康，验证回滚
    python3 03-cd-deploy-pipeline.py --dry-run    # 不部署，只打印将要执行的命令
    python3 03-cd-deploy-pipeline.py --self-test  # 离线自证
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

MIN_COVERAGE = 80.0


@dataclass
class Step:
    name: str
    ok: bool
    detail: str
    secs: float = 0.0


@dataclass
class Release:
    """一次发布记录——回滚靠的就是它。"""

    version: str
    image: str
    healthy: bool
    deployed_at: float = field(default_factory=time.time)


class PipelineError(RuntimeError):
    pass


# ---------------------------------------------------------------- 步骤实现
def gate_lint() -> Step:
    """门禁 1：静态检查。"""
    t0 = time.perf_counter()
    src = Path(__file__).parent
    proc = subprocess.run(
        [sys.executable, "-m", "py_compile", str(src / "01-workflow-lint.py")],
        capture_output=True, text=True,
    )
    return Step("lint", proc.returncode == 0,
                "语法检查通过" if proc.returncode == 0 else proc.stderr.strip()[:200],
                time.perf_counter() - t0)


def gate_test() -> Step:
    """门禁 2：单元测试 + 覆盖率阈值。"""
    t0 = time.perf_counter()
    # 真实项目里这里是 pytest --cov-fail-under；本地用同样的"阈值"语义自证
    covered, total = 4, 4
    cov = covered / total * 100
    ok = cov >= MIN_COVERAGE
    return Step("test", ok, f"coverage={cov:.1f}% (阈值 {MIN_COVERAGE}%)",
                time.perf_counter() - t0)


def build_artifact(version: str, root: Path) -> Step:
    """构建产物：真实场景是 docker build + push。"""
    t0 = time.perf_counter()
    dist = root / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / f"app-{version}.tar.gz").write_bytes(b"fake-artifact")
    ok = (dist / f"app-{version}.tar.gz").exists()
    return Step("build", ok, f"产物 dist/app-{version}.tar.gz",
                time.perf_counter() - t0)


def deploy(releases: list[Release], version: str, healthy: bool,
           dry_run: bool) -> Step:
    """滚动部署：新实例起来→健康检查→不健康则回滚到上一个。"""
    t0 = time.perf_counter()
    image = f"registry.local/app:{version}"
    if dry_run:
        return Step("deploy", True, f"[dry-run] docker push {image} && deploy",
                    time.perf_counter() - t0)
    releases.append(Release(version, image, healthy))
    if not healthy:
        # 回滚：把刚上的那版撤掉，保留上一个 healthy 的版本
        releases.pop()
        prev = next((r for r in reversed(releases) if r.healthy), None)
        detail = (f"❌ {image} 健康检查失败，已回滚到 "
                  f"{prev.image if prev else '无可用版本'}")
        return Step("deploy", False, detail, time.perf_counter() - t0)
    return Step("deploy", True, f"✅ {image} 上线", time.perf_counter() - t0)


def next_version(previous: list[Release]) -> str:
    """语义化版本：vMAJOR.MINOR.PATCH，PATCH 自增。"""
    if not previous:
        return "v1.0.1"
    last = previous[-1].version.lstrip("v")
    parts = [int(x) for x in last.split(".")]
    while len(parts) < 3:
        parts.append(0)
    parts[2] += 1
    return "v" + ".".join(str(p) for p in parts)


# ---------------------------------------------------------------- 编排
def run_pipeline(flaky: bool = False, dry_run: bool = False,
                 root: Path | None = None) -> dict:
    root = root or Path("/tmp/cd-pipeline")
    root.mkdir(parents=True, exist_ok=True)
    history_file = root / "releases.json"
    history = json.loads(history_file.read_text()) if history_file.exists() else []
    releases = [Release(**r) for r in history]

    steps: list[Step] = []
    for name, fn in (("lint", gate_lint), ("test", gate_test)):
        st = fn()
        steps.append(st)
        if not st.ok:
            _save(history_file, releases)
            return _result(steps, False, f"门禁 {name} 失败，已阻断部署")
        print(f"  ✅ {st.name:6} {st.detail}  ({st.secs:.2f}s)")

    version = next_version(releases)
    st = build_artifact(version, root)
    steps.append(st)
    print(f"  ✅ {st.name:6} {st.detail}  ({st.secs:.2f}s)")

    st = deploy(releases, version, healthy=not flaky, dry_run=dry_run)
    steps.append(st)
    print(f"  {'✅' if st.ok else '❌'} {st.name:6} {st.detail}  ({st.secs:.2f}s)")

    _save(history_file, releases)
    return _result(steps, st.ok,
                   "发布成功" if st.ok else "发布失败并回滚")


def _save(path: Path, releases: list[Release]) -> None:
    path.write_text(json.dumps([asdict(r) for r in releases], indent=2))


def _result(steps: list[Step], ok: bool, message: str) -> dict:
    return {
        "ok": ok,
        "message": message,
        "steps": [asdict(s) for s in steps],
        "total_secs": round(sum(s.secs for s in steps), 3),
    }


def show(res: dict) -> None:
    print("─" * 60)
    print(f"结果: {res['message']}  总耗时 {res['total_secs']}s")
    for s in res["steps"]:
        print(f"  {'✅' if s['ok'] else '❌'} {s['name']:6} {s['detail']}")


# ---------------------------------------------------------------- 自证
def self_test() -> int:
    root = Path("/tmp/cd-selftest")
    shutil.rmtree(root, ignore_errors=True)

    # 1) 版本号自增
    assert next_version([]) == "v1.0.1"
    assert next_version([Release("v1.0.1", "i", True)]) == "v1.0.2"
    assert next_version([Release("v2.5.9", "i", True)]) == "v2.5.10"

    # 2) dry-run 不产生任何 release 记录
    r = run_pipeline(dry_run=True, root=root)
    assert r["ok"], r
    assert not (root / "releases.json").exists() or \
        json.loads((root / "releases.json").read_text()) == []

    # 3) 正常发布：产出 1 条 healthy 记录
    r = run_pipeline(root=root)
    assert r["ok"] and "发布成功" in r["message"], r
    recs = json.loads((root / "releases.json").read_text())
    assert len(recs) == 1 and recs[0]["version"] == "v1.0.1", recs
    assert recs[0]["healthy"] is True

    # 4) 连续发布：版本递增到 v1.0.2
    r = run_pipeline(root=root)
    assert r["ok"], r
    recs = json.loads((root / "releases.json").read_text())
    assert [x["version"] for x in recs] == ["v1.0.1", "v1.0.2"], recs

    # 5) 翻车：新版本不健康 → 流水线失败，且版本记录不增长（已回滚）
    r = run_pipeline(flaky=True, root=root)
    assert not r["ok"] and "回滚" in r["message"], r
    recs = json.loads((root / "releases.json").read_text())
    assert [x["version"] for x in recs] == ["v1.0.1", "v1.0.2"], recs

    # 6) 门禁必须能阻断（把阈值提到 100%）
    global MIN_COVERAGE
    MIN_COVERAGE = 100.1  # 100% 也过不了，逼出失败分支
    r = run_pipeline(root=root)
    assert not r["ok"] and "门禁" in r["message"], r
    MIN_COVERAGE = 80.0

    shutil.rmtree(root, ignore_errors=True)
    print("✅ self-test 通过：版本/发布/回滚/门禁 6 组断言全过")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="run",
                    choices=["run", "gate", "version"])
    ap.add_argument("--flaky", action="store_true", help="故意让新版不健康")
    ap.add_argument("--dry-run", action="store_true", help="只打印不部署")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if a.cmd == "version":
        print(next_version([]))
        return 0
    if a.cmd == "gate":
        for st in (gate_lint(), gate_test()):
            print(f"{'✅' if st.ok else '❌'} {st.name:6} {st.detail}")
            if not st.ok:
                return 1
        return 0
    print("▶ CD 部署流水线" + ("（dry-run）" if a.dry_run else ""))
    show(run_pipeline(flaky=a.flaky, dry_run=a.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
