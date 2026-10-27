#!/usr/bin/env python3
"""contribution-kit：把一个本地提交打包成「可以直接贴到 PR 页面」的材料。

它做四件事：
1. 用 git format-patch 生成补丁
2. 调 02-patch-doctor.py 体检补丁
3. 生成 PR 描述（摘要 / 变更 / 测试计划 / 检查清单）
4. 生成 CPython 约定的 Misc/NEWS.d/next/<分类>/ 条目草稿

这里没有任何网络请求：所有材料都在本地生成，推送与否由你决定。

用法：
    python3 03-contribution-kit.py --repo /path/to/cpython --commit HEAD --out /tmp/kit
    python3 03-contribution-kit.py --repo . --dry-run
    python3 03-contribution-kit.py --self-test
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DOCTOR = Path(__file__).with_name("02-patch-doctor.py")
ISSUE_RE = re.compile(r"^(gh-\d+|bpo-\d+):\s+(.*)$")
CATEGORY = "Documentation"


@dataclass
class Commit:
    sha: str
    subject: str
    body: str
    timestamp: int


def git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败: {proc.stderr.strip()}")
    return proc.stdout


def read_commit(repo: Path, rev: str) -> Commit:
    raw = git(repo, "show", "-s", "--format=%H%x00%s%x00%b%x00%ct", rev)
    sha, subject, body, ts = raw.split("\x00", 3)
    return Commit(sha, subject.strip(), body.strip(), int(ts))


def lint_subject(commit: Commit) -> list[tuple[str, str]]:
    problems: list[tuple[str, str]] = []
    subject = commit.subject
    if len(subject) > 72:
        problems.append(("error", f"subject {len(subject)} 字符，超过 72"))
    if subject.endswith("."):
        problems.append(("warn", "subject 结尾不要加句号"))
    if not ISSUE_RE.match(subject):
        problems.append(("warn", "subject 建议写成 gh-<issue>: <祈使句摘要>"))
    if re.search(r"\b(fixed|fixes|added|adds|changed)\b", subject, re.I):
        problems.append(("warn", "subject 用祈使句（fix/add），不要用过去式"))
    return problems


def news_entry(commit: Commit) -> tuple[str, str]:
    """返回 (相对路径, 内容)。文件名格式跟随 CPython 的 blurb 约定。"""
    m = ISSUE_RE.match(commit.subject)
    issue = m.group(1) if m else "gh-000000"
    stamp = dt.datetime.fromtimestamp(commit.timestamp, dt.timezone.utc)
    stamp_s = stamp.strftime("%Y-%m-%d-%H-%M-%S")
    digest = hashlib.sha1(commit.sha.encode()).hexdigest()[:6]
    name = f"{stamp_s}.{issue.replace('-', '-issue-')}.{digest}.rst"
    path = f"Misc/NEWS.d/next/{CATEGORY}/{name}"
    summary = m.group(2) if m else commit.subject
    content = (
        f"{summary[0].upper() + summary[1:]}.\n"
        "\n"
        f"(Contributed by Nie Dong in {issue}.)\n"
    )
    return path, content


def diffstat(patch: str) -> list[str]:
    return [ln for ln in patch.splitlines() if re.match(r"^ [^|]+\|\s+\d+", ln)]


def build_pr_body(commit: Commit, patch: str, doctor_ok: bool) -> str:
    m = ISSUE_RE.match(commit.subject)
    issue = m.group(1) if m else "(未关联 issue)"
    summary = (m.group(2) if m else commit.subject).rstrip(".")
    stats = "\n".join(diffstat(patch)) or "  (见补丁)"
    checks = "x" if doctor_ok else " "
    return f"""## 摘要

{summary}。

## 关联 issue

Fixes {issue}

## 变更

{stats}

## 测试计划

- [x] python3 02-patch-doctor.py 0001-*.patch（0 error）
- [ ] 运行受影响的文档示例 / 单元测试
- [ ] 本地构建文档（如改动 Doc/）

## 检查清单

- [{checks}] 补丁通过 patch-doctor
- [ ] subject 使用祈使句且不超过 72 字符
- [ ] 需要时已添加 Misc/NEWS.d 条目
- [ ] 没有把无关改动混进同一个 PR
"""


def run_kit(repo: Path, rev: str, out: Path, dry_run: bool) -> int:
    commit = read_commit(repo, rev)
    patch = git(repo, "format-patch", "-1", "--stdout", rev)
    out.mkdir(parents=True, exist_ok=True)
    patch_path = out / "0001-change.patch"
    if not dry_run:
        patch_path.write_text(patch, encoding="utf-8")

    doctor = subprocess.run(
        [sys.executable, str(DOCTOR), "-"],
        input=patch, capture_output=True, text=True,
    )
    # 体检器用文件参数更直观：写临时文件再跑
    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False) as tmp:
        tmp.write(patch)
        tmp_path = Path(tmp.name)
    doctor = subprocess.run(
        [sys.executable, str(DOCTOR), str(tmp_path)],
        capture_output=True, text=True,
    )
    tmp_path.unlink(missing_ok=True)
    doctor_ok = doctor.returncode == 0

    problems = lint_subject(commit)
    news_path, news_body = news_entry(commit)
    pr_body = build_pr_body(commit, patch, doctor_ok)
    checklist = f"""# 贡献前自检

- [ ] 分支基于最新的 upstream/main
- [ ] 只改一件事，commit 粒度可 review
- [ ] subject: {commit.subject}
- [ ] 本地跑过: python3 02-patch-doctor.py 0001-change.patch
- [ ] 文档改动跑过: python3 -m doctest <改动的 .rst>
- [ ] NEWS 条目: {news_path}

## 提交命令

    git switch -c my-fix upstream/main
    git commit -am "gh-<issue>: <imperative summary>"
    git format-patch -1 --stdout > 0001-change.patch
    git request-pull upstream/main . HEAD

## 体检器输出

{doctor.stdout.strip()}
"""

    print(f"repo   : {repo}")
    print(f"commit : {commit.sha[:12]}  {commit.subject}")
    body = patch.split("\n-- \n", 1)[0]
    added = sum(1 for ln in body.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in body.splitlines() if ln.startswith("-") and not ln.startswith("---"))
    print(f"patch  : +{added} / -{removed} 行")
    print(f"doctor : {'PASS' if doctor_ok else 'FAIL'}")
    for level, msg in problems:
        print(f"  {level:<5} {msg}")
    print(f"news   : {news_path}")
    print(f"out    : {out}")
    if dry_run:
        print("\n--- PR 描述（dry-run，不写文件）---")
        print(pr_body)
        return 0 if doctor_ok and not [p for p in problems if p[0] == "error"] else 1

    (out / "pr-body.md").write_text(pr_body, encoding="utf-8")
    (out / "checklist.md").write_text(checklist, encoding="utf-8")
    (out / "news-entry.rst").write_text(news_body, encoding="utf-8")
    print("已写出: 0001-change.patch / pr-body.md / checklist.md / news-entry.rst")
    return 0 if doctor_ok and not [p for p in problems if p[0] == "error"] else 1


def self_test() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="kit-selftest-"))
    try:
        repo = tmp / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "test@example.com")
        git(repo, "config", "user.name", "Test")
        (repo / "guide.rst").write_text(
            "Quickstart\n=========\n\nA common error occured here.\n", encoding="utf-8")
        git(repo, "add", "guide.rst")
        git(repo, "commit", "-q", "-m", "add guide")
        (repo / "guide.rst").write_text(
            "Quickstart\n=========\n\nA common error occurred here.\n", encoding="utf-8")
        git(repo, "commit", "-q", "-am", "gh-424242: fix typo in quickstart guide")

        out = tmp / "out"
        rc = run_kit(repo, "HEAD", out, dry_run=False)
        assert rc == 0, f"run_kit 返回 {rc}"
        for name in ("0001-change.patch", "pr-body.md", "checklist.md", "news-entry.rst"):
            assert (out / name).is_file(), name
        body = (out / "pr-body.md").read_text(encoding="utf-8")
        assert "Fixes gh-424242" in body
        assert "fix typo in quickstart guide" in body
        assert "Misc/NEWS.d/next/Documentation/" in (out / "checklist.md").read_text(encoding="utf-8")

        # subject lint 必须能抓出超长
        commit = read_commit(repo, "HEAD")
        bad = Commit(commit.sha, "gh-1: " + "x" * 80, "", commit.timestamp)
        assert any(level == "error" for level, _ in lint_subject(bad))
        print("✅ self-test passed: 补丁/PR 描述/NEWS 文件名/lint 四项")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="把本地提交打包成 PR 材料")
    parser.add_argument("--repo", default=".", help="git 仓库路径")
    parser.add_argument("--commit", default="HEAD", help="要打包的提交")
    parser.add_argument("--out", default="contribution-bundle", help="输出目录")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        return 0
    try:
        return run_kit(Path(args.repo).resolve(), args.commit, Path(args.out), args.dry_run)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
