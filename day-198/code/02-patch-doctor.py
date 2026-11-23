#!/usr/bin/env python3
"""patch-doctor：给 unified diff / git format-patch 做体检。

为什么需要它：git am 失败时的报错往往只说「patch does not apply」，
不说为什么。真正的原因通常是下面几类，而且都能在本地提前查出来：

1. hunk 头里的行数和实际行数对不上（手工编辑 patch 最常见）
2. 新增行有尾随空白（git apply --whitespace=error 直接拒绝）
3. 文件用了 CRLF，或者最后一行没有换行符
4. 新增行超过 79 列（CPython 的 PEP 8 检查会拦）
5. 提交信息格式不符合仓库约定（subject 太长 / 没有 gh- issue 前缀）

用法：
    python3 02-patch-doctor.py fix.patch
    cat fix.patch | python3 02-patch-doctor.py
    python3 02-patch-doctor.py --self-test
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
SUBJECT_RE = re.compile(r"^Subject: (.*)$")
ISSUE_RE = re.compile(r"^(gh-\d+|bpo-\d+): \S")


@dataclass(frozen=True)
class Finding:
    severity: str      # "error" | "warn"
    where: str         # file:line 或 header
    message: str

    def render(self) -> str:
        return f"{self.severity:<5} {self.where:<28} {self.message}"


@dataclass
class FilePatch:
    path: str
    added: int = 0
    removed: int = 0
    hunks: int = 0
    binary: bool = False


def strip_mail_header(text: str) -> tuple[list[str], list[str]]:
    """把 format-patch 的邮件头和数据部分分开。"""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("diff --git "):
            return lines[:i], lines[i:]
    return [], lines


def check_subject(header: list[str]) -> list[Finding]:
    out: list[Finding] = []
    subjects = [m.group(1) for line in header if (m := SUBJECT_RE.match(line))]
    if not subjects:
        return out
    subject = subjects[0].replace("[PATCH] ", "", 1).strip()
    if len(subject) > 72:
        out.append(Finding("warn", "header", f"subject 长度 {len(subject)} > 72"))
    if not ISSUE_RE.match(subject):
        out.append(Finding("warn", "header", "subject 建议以 gh-<issue>: 开头"))
    if subject.endswith("."):
        out.append(Finding("warn", "header", "subject 结尾不要加句号"))
    return out


def check_diff(lines: list[str]) -> tuple[list[Finding], list[FilePatch]]:
    findings: list[Finding] = []
    files: list[FilePatch] = []
    current: FilePatch | None = None
    hunk: dict | None = None
    old_remaining = new_remaining = 0

    def close_hunk() -> None:
        nonlocal hunk
        if hunk is None:
            return
        if old_remaining != 0 or new_remaining != 0:
            findings.append(Finding(
                "error", f"{hunk['path']}:{hunk['line']}",
                f"hunk 头声明 -{hunk['old_count']}/+{hunk['new_count']}，"
                f"实际剩余 -{old_remaining}/+{new_remaining}",
            ))
        hunk = None

    for line in lines:
        if line.startswith("diff --git "):
            close_hunk()
            path = line.split(" b/")[-1]
            current = FilePatch(path)
            files.append(current)
            continue
        if current is None:
            continue
        if line.startswith("GIT binary patch") or line.startswith("Binary files "):
            current.binary = True
            continue
        if line.startswith("@@ "):
            close_hunk()
            m = HUNK_RE.match(line)
            if not m:
                findings.append(Finding("error", current.path, f"无法解析 hunk 头: {line[:40]}"))
                continue
            old_count = int(m.group(2) if m.group(2) is not None else 1)
            new_count = int(m.group(4) if m.group(4) is not None else 1)
            old_remaining, new_remaining = old_count, new_count
            current.hunks += 1
            hunk = {"path": current.path, "line": m.group(1),
                    "old_count": old_count, "new_count": new_count}
            continue
        if hunk is None:
            continue
        if old_remaining == 0 and new_remaining == 0:
            # hunk 已经读完，后面的内容（签名行 "-- "、版本号）不参与计数
            continue
        if line.startswith("+") and not line.startswith("+++"):
            new_remaining -= 1
            current.added += 1
            body = line[1:]
            if body != body.rstrip():
                findings.append(Finding("error", current.path, "新增行有尾随空白"))
            if body.endswith("\r"):
                findings.append(Finding("error", current.path, "新增行使用了 CRLF"))
            if len(body) > 79:
                findings.append(Finding("warn", current.path, f"新增行长度 {len(body)} > 79"))
            if "\t" in body and current.path.endswith(".py"):
                findings.append(Finding("warn", current.path, "Python 新增行含制表符"))
        elif line.startswith("-") and not line.startswith("---"):
            old_remaining -= 1
            current.removed += 1
        elif line.startswith(" "):
            old_remaining -= 1
            new_remaining -= 1
        elif line.startswith("\\"):
            # "\ No newline at end of file" 不影响行数
            findings.append(Finding("warn", current.path, "文件末尾缺少换行符"))
    close_hunk()
    return findings, files


def check_text(text: str) -> tuple[list[Finding], list[FilePatch]]:
    header, diff = strip_mail_header(text)
    findings = check_subject(header)
    diff_findings, files = check_diff(diff)
    findings.extend(diff_findings)
    if not files:
        findings.append(Finding("error", "patch", "没有找到 diff --git 段"))
    for f in files:
        if f.binary:
            findings.append(Finding("warn", f.path, "二进制补丁，无法做行级检查"))
    return findings, files


def report(path: str, findings: list[Finding], files: list[FilePatch]) -> bool:
    errors = sum(1 for f in findings if f.severity == "error")
    warns = len(findings) - errors
    print(f"patch: {path}")
    total_add = sum(f.added for f in files)
    total_del = sum(f.removed for f in files)
    print(f"files: {len(files)}  hunks: {sum(f.hunks for f in files)}  +{total_add} -{total_del}")
    for f in findings:
        print("  " + f.render())
    print(f"{errors} error(s), {warns} warning(s)")
    return errors == 0


GOOD_PATCH = "\n".join([
    "From 1234567890abcdef Mon Sep 17 00:00:00 2001",
    "From: Alice <alice@example.com>",
    "Subject: [PATCH] gh-424242: fix typo in quickstart guide",
    "",
    "---",
    " guide.rst | 2 +-",
    " 1 file changed, 1 insertion(+), 1 deletion(-)",
    "",
    "diff --git a/guide.rst b/guide.rst",
    "index 2fc1d51..5547754 100644",
    "--- a/guide.rst",
    "+++ b/guide.rst",
    "@@ -3,6 +3,6 @@ Quickstart",
    " ",
    " Install the package with pip.",
    " ",
    "-A common error occured when the config file is missing.",
    "+A common error occurred when the config file is missing.",
    " ",
    " Run tool --help to see all the options.",
])

BAD_PATCH = GOOD_PATCH.replace(
    "+A common error occurred when the config file is missing.",
    "+A common error occurred when the config file is missing.   ",
).replace("@@ -3,6 +3,6 @@", "@@ -3,7 +3,7 @@") + "\n"


def self_test() -> None:
    good_findings, good_files = check_text(GOOD_PATCH)
    assert not [f for f in good_findings if f.severity == "error"], good_findings
    assert len(good_files) == 1 and good_files[0].hunks == 1

    bad_findings, _ = check_text(BAD_PATCH)
    messages = " | ".join(f.message for f in bad_findings)
    assert "尾随空白" in messages, messages
    assert "hunk 头声明" in messages, messages

    no_diff, _ = check_text("just a mail body\n")
    assert any(f.message == "没有找到 diff --git 段" for f in no_diff)

    print("✅ self-test passed: 正常 patch / 尾随空白 / hunk 计数错误 / 非 patch 输入")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="unified diff 体检器")
    parser.add_argument("patches", nargs="*", help="patch 文件；留空则读 stdin")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--strict", action="store_true", help="把 warning 也当成失败")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        return 0

    ok = True
    if not args.patches:
        text = sys.stdin.read()
        findings, files = check_text(text)
        ok = report("<stdin>", findings, files)
    else:
        for path in args.patches:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            findings, files = check_text(text)
            ok = report(path, findings, files) and ok
            if args.strict and any(f.severity == "warn" for f in findings):
                ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
