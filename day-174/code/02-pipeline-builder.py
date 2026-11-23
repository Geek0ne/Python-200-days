#!/usr/bin/env python3
"""02 — 用 Python 生成 / 校验 CI 流水线（进阶：矩阵展开与依赖图）。

进阶点：
1. 把「Python 支持版本」这一份真相放在单一位置，生成 workflow 的 matrix，
   避免 YAML 里手写版本列表后跟 setup.py 里的 classifiers 脱节。
2. 校验 needs 有没有形成环——GitHub 只会报一句含糊的 "Invalid workflow"，
   而我们本地就能拓扑排序出环来。

用法：
    python3 02-pipeline-builder.py topo <workflow.yml>
    python3 02-pipeline-builder.py matrix 3.9 3.10 3.11 3.12
    python3 02-pipeline-builder.py --self-test
"""
from __future__ import annotations

import json
import sys
from collections import deque

import yaml


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_jobs(doc: dict) -> dict:
    return doc.get("jobs") or {}


def expand_matrix(strategy: dict) -> list[dict]:
    """把 strategy.matrix 展开成实际的 job 组合。

    GitHub 的矩阵是笛卡尔积，且 include/exclude 在展开后生效。
    这里实现 include（追加/覆盖）与 exclude（剔除）两条规则。
    """
    # 既接受整个 strategy（含 matrix 键），也接受裸的 matrix 映射
    if "matrix" in strategy and isinstance(strategy["matrix"], dict):
        strategy = strategy["matrix"] | {
            k: v for k, v in strategy.items() if k in ("include", "exclude")}
    matrix = {k: v for k, v in strategy.items() if k not in ("include", "exclude")}
    if not matrix:
        base = [{}]
    else:
        base = [{}]
        for key, values in matrix.items():
            nxt = []
            for combo in base:
                for value in values:
                    d = dict(combo)
                    d[key] = value
                    nxt.append(d)
            base = nxt
    for ex in strategy.get("exclude") or []:
        base = [c for c in base if not all(c.get(k) == v for k, v in ex.items())]
    for inc in strategy.get("include") or []:
        matched = False
        for combo in base:
            # include 与某个已有组合「不冲突」时视为扩展它
            if all(k in combo and combo[k] == v for k, v in inc.items() if k in combo):
                combo.update(inc)
                matched = True
        if not matched:
            base.append(dict(inc))
    return base


def topo_sort(jobs: dict) -> tuple[list[str], list[str]]:
    """Kahn 拓扑排序。返回 (顺序, 环内节点)；无环时第二项为空列表。"""
    deps = {n: ([d] if isinstance(d, str) else list(d or [])) for n, d in
            ((n, j.get("needs")) for n, j in jobs.items())}
    indeg = {n: 0 for n in jobs}
    for n, ds in deps.items():
        for d in ds:
            if d in indeg:
                indeg[n] += 1
    q = deque(sorted(n for n, k in indeg.items() if k == 0))
    order: list[str] = []
    while q:
        n = q.popleft()
        order.append(n)
        for m in sorted(jobs):
            if n in deps[m] and m not in order and m not in q:
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
    cycle = [n for n in jobs if n not in order]
    return order, cycle


def build_workflow(python_versions: list[str]) -> str:
    """由版本列表生成一个 CI workflow（单一真相源）。"""
    versions = json.dumps(python_versions)
    return f"""name: Generated CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    name: test (py ${{{{ matrix.py }}}})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        py: {versions}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.py }}}}
      - run: pip install -r requirements.txt
      - run: pytest -q
"""


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    if len(argv) > 1 and argv[1] == "topo":
        doc = load(argv[2])
        jobs = get_jobs(doc)
        order, cycle = topo_sort(jobs)
        print("执行顺序:", " -> ".join(order))
        if cycle:
            print("❌ 检测到环:", cycle)
            return 1
        for name, job in jobs.items():
            st = job.get("strategy") or {}
            if "matrix" in st:
                combos = expand_matrix(st)
                print(f"job {name}: 展开 {len(combos)} 个组合 -> "
                      f"{[c for c in combos]}")
        return 0
    if len(argv) > 1 and argv[1] == "matrix":
        print(build_workflow(argv[2:]))
        return 0
    print(__doc__)
    return 0


def self_test() -> int:
    # 1) 环检测
    jobs = {"a": {"needs": ["b"]}, "b": {"needs": ["a"]}, "c": {}}
    order, cycle = topo_sort(jobs)
    assert order == ["c"] and sorted(cycle) == ["a", "b"], (order, cycle)

    # 2) 无环
    jobs2 = {"a": {}, "b": {"needs": "a"}, "c": {"needs": ["a", "b"]}}
    order2, cycle2 = topo_sort(jobs2)
    assert cycle2 == [] and order2.index("a") < order2.index("b") < order2.index("c")

    # 3) 矩阵笛卡尔积
    combos = expand_matrix({"python-version": ["3.11", "3.12"], "os": ["ubuntu", "mac"]})
    assert len(combos) == 4, combos

    # 4) exclude
    combos = expand_matrix({"py": ["3.11", "3.12"], "os": ["ubuntu", "mac"],
                            "exclude": [{"py": "3.11", "os": "mac"}]})
    assert len(combos) == 3, combos

    # 5) include 扩展已有组合
    combos = expand_matrix({"py": ["3.11", "3.12"],
                            "include": [{"py": "3.12", "extra": "nightly"}]})
    assert any(c.get("extra") == "nightly" for c in combos), combos
    assert len(combos) == 2, combos

    # 6) 接受整个 strategy（含 matrix 键）
    wrapped = expand_matrix({"matrix": {"py": ["3.11", "3.12"]}, "fail-fast": False})
    assert len(wrapped) == 2 and wrapped[0]["py"] in ("3.11", "3.12"), wrapped

    # 7) 生成物必须是合法 YAML 且能被自己解析回来
    gen = yaml.safe_load(build_workflow(["3.11", "3.12"]))
    assert gen["jobs"]["test"]["strategy"]["matrix"]["py"] == ["3.11", "3.12"]

    print("✅ self-test 通过：环检测/拓扑/矩阵/生成 6 组断言全过")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
