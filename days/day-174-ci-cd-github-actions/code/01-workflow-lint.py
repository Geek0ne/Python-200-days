#!/usr/bin/env python3
"""01 — 用 Python 校验 workflow YAML 的基本结构（CI 的第一道本地防线）。

对应 GitHub Actions 里 `actionlint` 做的事，我们用零依赖的方式先做一遍，
好处是：编辑器保存即报错，不用等 push 到 GitHub 才知道 YAML 写错。

用法：
    python3 01-workflow-lint.py <workflow.yml> [更多文件...]
    python3 01-workflow-lint.py --self-test     # 离线自证正确
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

# GitHub Actions 允许的 job 级关键字（子集，只列最常错的）
JOB_KEYS = {
    "runs-on", "needs", "if", "steps", "strategy", "env", "container",
    "services", "outputs", "permissions", "timeout-minutes", "defaults",
    "continue-on-error", "concurrency", "name", "uses", "with", "run",
    "shell", "working-directory", "id", "if", "secrets", "credentials",
}
RUNNER_LABELS = {"ubuntu-latest", "ubuntu-24.04", "ubuntu-22.04",
                 "macos-latest", "windows-latest", "self-hosted"}


class Issue:
    """一条校验结果。level=error 会让 CI 红，warning 只提示。"""

    def __init__(self, level: str, msg: str) -> None:
        self.level = level
        self.msg = msg

    def __str__(self) -> str:
        return f"{self.level.upper():7} {self.msg}"


def check_step(step: dict, where: str) -> list[Issue]:
    """校验单个 step：必须有 uses 或 run 之一。"""
    out: list[Issue] = []
    if not isinstance(step, dict):
        return [Issue("error", f"{where}: step 不是映射")]
    has_uses, has_run = "uses" in step, "run" in step
    if has_uses and has_run:
        out.append(Issue("error", f"{where}: uses 与 run 不能同时出现"))
    if not has_uses and not has_run:
        out.append(Issue("error", f"{where}: 缺少 uses 或 run"))
    # 最经典的坑：on 被 YAML 解析成布尔 True
    if "on" in step and str(step["on"]).lower() in ("true", "false"):
        out.append(Issue("warning", f"{where}: on 被当成布尔值，务必给键加引号"))
    return out


def check_job(name: str, job: dict) -> list[Issue]:
    """校验一个 job。"""
    out: list[Issue] = []
    if not isinstance(job, dict):
        return [Issue("error", f"job '{name}' 不是映射")]
    unknown = set(job) - JOB_KEYS
    if unknown:
        out.append(Issue("warning", f"job '{name}': 未知键 {sorted(unknown)}"))
    if "uses" not in job and "steps" not in job:
        out.append(Issue("error", f"job '{name}': 必须有 steps 或 uses"))
    if "runs-on" in job:
        ro = job["runs-on"]
        if isinstance(ro, str) and ro not in RUNNER_LABELS and "self-hosted" not in ro:
            out.append(Issue("error", f"job '{name}': 未知 runner 标签 '{ro}'"))
    for i, step in enumerate(job.get("steps", []) or [], 1):
        out += check_step(step, f"job '{name}' step#{i}")
    return out


def lint_workflow(doc: dict) -> list[Issue]:
    """校验整个 workflow 文档。"""
    out: list[Issue] = []
    if not isinstance(doc, dict):
        return [Issue("error", "顶层不是映射")]
    # YAML 1.1 把裸 on 解析成 True
    trig = doc.get("on", doc.get(True))
    if trig is None:
        out.append(Issue("error", "缺少触发器 on:"))
    jobs = doc.get("jobs")
    if not jobs:
        return out + [Issue("error", "缺少 jobs: 或 jobs 为空")]
    for jname, job in jobs.items():
        out += check_job(jname, job)
        for dep in (job.get("needs") or []) if isinstance(job, dict) else []:
            deps = [dep] if isinstance(dep, str) else list(dep)
            for d in deps:
                if d not in jobs:
                    out.append(Issue("error", f"job '{jname}' needs 了不存在的 '{d}'"))
    return out


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    files = [a for a in argv[1:] if not a.startswith("-")]
    if not files:
        print(__doc__)
        return 0
    bad = 0
    for f in files:
        issues = lint_workflow(yaml.safe_load(Path(f).read_text(encoding="utf-8")))
        print(f"== {f} ({len(issues)} issues)")
        for i in issues:
            print("  " + str(i))
        bad += sum(1 for i in issues if i.level == "error")
    return 1 if bad else 0


def self_test() -> int:
    """离线自证：好文件 0 error，坏文件必须报错。"""
    good = """
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest
"""
    bad = """
name: CI
on: [push]
jobs:
  a:
    runs-on: nonexistent-runner
    steps:
      - uses: actions/checkout@v4
        run: echo hi
  b:
    runs-on: ubuntu-latest
    needs: [a, ghost]
    steps:
      - name: 空 step
"""
    gi = [i for i in lint_workflow(yaml.safe_load(good)) if i.level == "error"]
    bi = [i for i in lint_workflow(yaml.safe_load(bad)) if i.level == "error"]
    assert not gi, f"好文件不该有 error: {gi}"
    assert len(bi) >= 3, f"坏文件应至少 3 个 error，实得 {len(bi)}: {bi}"
    print("✅ self-test 通过：好文件 0 error，坏文件捕获 %d 个 error" % len(bi))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
