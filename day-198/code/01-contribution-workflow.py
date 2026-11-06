#!/usr/bin/env python3
"""开源协作状态机：issue -> PR -> review -> merge。

这个脚本不访问网络，也不调用 git，只用纯 Python 复刻一次真实贡献流程里
*规则* 的部分：什么状态下允许做什么、合并需要满足哪些条件、什么事件会
让已有的 approval 失效。

用法：
    python3 01-contribution-workflow.py --demo
    python3 01-contribution-workflow.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from enum import Enum


class State(str, Enum):
    NEW = "NEW"                          # issue 刚创建
    TRIAGED = "TRIAGED"                  # 维护者打了标签、确认有效
    IN_PROGRESS = "IN_PROGRESS"          # 有人认领
    CI_RUNNING = "CI_RUNNING"            # PR 已提交，CI 在跑
    REVIEW = "REVIEW"                    # CI 通过，等 review
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    MERGED = "MERGED"
    CLOSED = "CLOSED"                    # 关闭但未合并


TERMINAL = {State.MERGED, State.CLOSED}

# (当前状态, 事件) -> 下一个状态。放在表里而不是 if/elif 里，
# 是为了让「哪些操作合法」变成可被审阅的数据，而不是藏在控制流里。
TRANSITIONS: dict[tuple[State, str], State] = {
    (State.NEW, "triage"): State.TRIAGED,
    (State.NEW, "close"): State.CLOSED,
    (State.TRIAGED, "claim"): State.IN_PROGRESS,
    (State.TRIAGED, "close"): State.CLOSED,
    (State.IN_PROGRESS, "open_pr"): State.CI_RUNNING,
    (State.IN_PROGRESS, "close"): State.CLOSED,
    (State.CI_RUNNING, "ci_pass"): State.REVIEW,
    (State.CI_RUNNING, "ci_fail"): State.IN_PROGRESS,
    (State.REVIEW, "approve"): State.APPROVED,
    (State.REVIEW, "request_changes"): State.CHANGES_REQUESTED,
    (State.REVIEW, "ci_fail"): State.IN_PROGRESS,
    (State.REVIEW, "close"): State.CLOSED,
    (State.CHANGES_REQUESTED, "push_fix"): State.CI_RUNNING,
    (State.CHANGES_REQUESTED, "close"): State.CLOSED,
    (State.APPROVED, "push_fix"): State.CI_RUNNING,
    (State.APPROVED, "merge"): State.MERGED,
    (State.APPROVED, "close"): State.CLOSED,
}


class WorkflowError(RuntimeError):
    """违反协作规则时抛出。"""


@dataclass
class PullRequest:
    number: int
    title: str
    state: State = State.NEW
    ci: str | None = None            # None / "pass" / "fail"
    approvals: int = 0
    unresolved_threads: int = 0
    stale_approval: bool = False     # 新提交后旧的 approval 作废
    history: list[tuple[int, str, State, str]] = field(default_factory=list)
    _step: int = 0

    # ---------- 规则层 ----------
    def _guard(self, event: str) -> None:
        if self.state in TERMINAL:
            raise WorkflowError(f"#{self.number} 已处于终态 {self.state.value}，不能再 {event}")
        if event == "merge":
            if self.ci != "pass":
                raise WorkflowError("CI 没有通过，不能合并")
            if self.approvals < 1 or self.stale_approval:
                raise WorkflowError("缺少有效的 review approval，不能合并")
            if self.unresolved_threads > 0:
                raise WorkflowError(f"还有 {self.unresolved_threads} 条未解决评论，不能合并")

    def fire(self, event: str, note: str = "") -> State:
        self._guard(event)
        key = (self.state, event)
        if key not in TRANSITIONS:
            allowed = sorted(e for (s, e) in TRANSITIONS if s is self.state)
            raise WorkflowError(
                f"状态 {self.state.value} 不允许事件 {event!r}；允许：{allowed}"
            )
        old = self.state
        self.state = TRANSITIONS[key]
        self._apply_side_effects(event)
        self._step += 1
        self.history.append((self._step, event, self.state, note))
        return old

    def _apply_side_effects(self, event: str) -> None:
        if event == "ci_pass":
            self.ci = "pass"
        elif event == "ci_fail":
            self.ci = "fail"
        elif event == "approve":
            self.approvals += 1
            self.stale_approval = False
        elif event == "request_changes":
            self.stale_approval = True
            self.unresolved_threads += 1
        elif event == "push_fix":
            # 关键规则：任何新提交都会让旧 approval 失效（GitHub 的
            # "dismiss stale approvals" 是同一个道理）。
            self.stale_approval = True
            self.approvals = 0
            self.ci = None
        elif event == "merge":
            self.unresolved_threads = 0

    # ---------- 输出层 ----------
    def timeline(self) -> str:
        lines = [f"PR #{self.number} {self.title!r}", "-" * 56]
        for step, event, state, note in self.history:
            suffix = f"  # {note}" if note else ""
            marker = f"{step:>2}." if step else "  x"
            lines.append(f"{marker} {event:<16} -> {state.value:<18}{suffix}")
        lines.append("-" * 56)
        lines.append(f"最终状态: {self.state.value}")
        return "\n".join(lines)


def happy_path() -> PullRequest:
    pr = PullRequest(198, "fix typo in quickstart guide")
    steps = [
        ("triage", "维护者确认是文档错误"),
        ("claim", "贡献者认领"),
        ("open_pr", "提交 PR"),
        ("ci_pass", "3 个 job 全绿"),
        ("approve", "reviewer: LGTM"),
        ("merge", "squash merge"),
    ]
    for event, note in steps:
        pr.fire(event, note)
    return pr


def stale_approval_path() -> PullRequest:
    pr = PullRequest(199, "add --dry-run flag")
    for event in ("triage", "claim", "open_pr", "ci_pass", "approve"):
        pr.fire(event)
    pr.fire("push_fix", "reviewer 要求补测试，作者又推了一版")
    pr.fire("ci_pass", "新提交后 CI 重新跑绿")
    try:
        pr.fire("merge")
    except WorkflowError as exc:
        pr.history.append((0, "merge-blocked", pr.state, str(exc)))
    pr.fire("approve", "reviewer 重新看过")
    pr.fire("merge")
    return pr


def self_test() -> None:
    pr = happy_path()
    assert pr.state is State.MERGED
    assert pr.ci == "pass"

    # 1) CI 失败时不能合并
    pr = PullRequest(1, "x")
    for event in ("triage", "claim", "open_pr", "ci_pass", "approve"):
        pr.fire(event)
    pr.ci = "fail"
    try:
        pr.fire("merge")
    except WorkflowError as exc:
        assert "CI" in str(exc)
    else:
        raise AssertionError("CI 失败却允许合并")

    # 2) 未解决评论阻塞合并
    pr = PullRequest(2, "y")
    for event in ("triage", "claim", "open_pr", "ci_pass", "approve"):
        pr.fire(event)
    pr.unresolved_threads = 1
    try:
        pr.fire("merge")
    except WorkflowError as exc:
        assert "未解决" in str(exc)
    else:
        raise AssertionError("有未解决评论却允许合并")

    # 3) 新提交让 approval 失效
    pr = stale_approval_path()
    assert pr.state is State.MERGED
    blocked = [h for h in pr.history if h[1] == "merge-blocked"]
    assert blocked and "approval" in blocked[0][3]

    # 4) 终态不可再操作
    try:
        pr.fire("push_fix")
    except WorkflowError as exc:
        assert "终态" in str(exc)
    else:
        raise AssertionError("终态还能继续操作")

    # 5) 非法状态转换给出可读错误
    pr = PullRequest(3, "z")
    try:
        pr.fire("ci_pass")
    except WorkflowError as exc:
        assert "不允许事件" in str(exc)
    else:
        raise AssertionError("NEW 状态竟然允许 merge")

    print("✅ self-test passed: 5 组规则全部符合预期")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="开源协作状态机（离线可跑）")
    parser.add_argument("--demo", action="store_true", help="打印两条完整时间线")
    parser.add_argument("--self-test", action="store_true", help="运行内置断言")
    args = parser.parse_args(argv)

    if not (args.demo or args.self_test):
        parser.print_help()
        return 2
    if args.self_test:
        self_test()
    if args.demo:
        print(happy_path().timeline())
        print()
        print(stale_approval_path().timeline())
    return 0


if __name__ == "__main__":
    sys.exit(main())
