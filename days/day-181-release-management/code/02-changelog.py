#!/usr/bin/env python3
"""
Day 181 — 发布管理
02 · Changelog 规范：Conventional Commits -> Keep a Changelog

两个规范各管一半，合起来才是「自动化发布」的前提：

  Conventional Commits  管**提交怎么命名**：  type(scope)!: subject
  Keep a Changelog      管**变更怎么归类**：  Added / Changed / Fixed / ...

它们能对接，是因为两边的信息是同源的：**提交里已经写明了这次改动是
新增、修复还是破坏性变更**。所以 CHANGELOG 不用人写，可以从提交推导出来——
前提是提交本身守规矩（这就是为什么本仓库 CONTRIBUTING.md 要求 Conventional Commits）。

本脚本不调任何第三方库：
  --from FILE   读一份 git log 风格的提交记录（提交之间空行分隔），生成条目
  --lint        体检一份已有 CHANGELOG.md 是否符合 Keep a Changelog
  --self-test   离线自检：用内嵌的样例提交记录跑通全流程

用法：
    python3 02-changelog.py --self-test
    python3 02-changelog.py --from commits.txt --current 1.1.4 --repo-url https://github.com/me/proj --dry-run
    python3 02-changelog.py --lint ../CHANGELOG.md
"""

import argparse
import datetime as dt
import re
import sys

# --- Conventional Commits 解析 ---------------------------------------------
COMMIT_RE = re.compile(r"^(?P<sha>[0-9a-f]{7,40})\s+(?P<subject>\S.*)$")
SUBJECT_RE = re.compile(
    r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^()]*)\))?(?P<bang>!)?:\s*(?P<desc>.+)$"
)

# type -> Keep a Changelog 分类。None = 内部改动，默认不进 CHANGELOG。
TYPE_TO_SECTION = {
    "feat": "Added",
    "fix": "Fixed",
    "perf": "Changed",
    "refactor": "Changed",
    "revert": "Removed",
    "style": None,
    "docs": None,
    "test": None,
    "chore": None,
    "ci": None,
    "build": None,
}
SECTIONS = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]


def parse_commits(text):
    """把 git log 风格的文本切成提交列表。

    约定：一个提交 = 一行「sha subject」，紧跟其后的非提交行属于正文（body）。
    「是不是新提交」靠**行首模式**判断（7-40 位十六进制 sha + 空格 + 主题），
    不靠空行——因为 git log --pretty=format:'%h %s%n%b' 在提交之间并不加空行，
    靠空行切会把一批提交全吸进第一个提交的 body（下面翻车复盘里的真 bug）。
    正文里的 BREAKING CHANGE: 是危害最大的那种改动，必须能被识别。
    """
    commits, cur = [], None
    for line in text.splitlines():
        if not line.strip():
            continue
        m = COMMIT_RE.match(line)
        if m:
            cur = {"sha": m.group("sha"), "subject": m.group("subject"), "body": []}
            commits.append(cur)
        elif cur is not None:
            cur["body"].append(line.strip())
    for c in commits:
        m = SUBJECT_RE.match(c["subject"])
        if m:
            c["conventional"] = True
            c["type"] = m.group("type")
            c["scope"] = m.group("scope") or ""
            c["desc"] = m.group("desc").strip()
            c["breaking"] = bool(m.group("bang"))
        else:
            c["conventional"] = False
            c["type"] = c["scope"] = ""
            c["desc"] = c["subject"]
            c["breaking"] = False
        body = "\n".join(c["body"])
        if re.search(r"^BREAKING[ -]CHANGE:", body, re.M):
            c["breaking"] = True
            note = re.search(r"^BREAKING[ -]CHANGE:\s*(.+)$", body, re.M)
            c["breaking_note"] = note.group(1).strip() if note else ""
        else:
            c["breaking_note"] = ""
    return commits


def classify(commit, include_internal=False):
    """返回 Keep a Changelog 分类名，或 None 表示不进 CHANGELOG。"""
    if commit["breaking"]:
        return "Changed"          # 破坏性变更也归 Changed，但会额外列进 BREAKING 区
    sec = TYPE_TO_SECTION.get(commit["type"].lower() if commit["conventional"] else None)
    if sec is None and include_internal and commit["conventional"]:
        return "Changed"
    return sec


def next_version(commits, current, zero_major=False):
    """从提交推导下一个版本号（这就是 release 自动化的「版本决策」那一步）。

    基本规则：BREAKING -> major，feat -> minor，其余 -> patch。
    0.x 特殊：SemVer 规范说 0.y.z 是「随时可能变」的，社区惯例是
    BREAKING -> minor、其余 -> patch（用 --zero-major 打开）。
    """
    breaking = any(c["breaking"] for c in commits)
    feature = any(c["type"].lower() == "feat" for c in commits if c["conventional"])
    maj, mi, pa = (int(x) for x in current.split("."))
    if zero_major and maj == 0:
        if breaking:
            mi, pa = mi + 1, 0
        else:
            pa += 1
    elif breaking:
        maj, mi, pa = maj + 1, 0, 0
    elif feature:
        mi, pa = mi + 1, 0
    else:
        pa += 1
    reason = "BREAKING CHANGE" if breaking else ("feat" if feature else "仅 fix/内部改动")
    return f"{maj}.{mi}.{pa}", reason


def render(commits, version, current, repo_url="", date=None, include_internal=False):
    """生成一段 Keep a Changelog 条目。返回 (文本, 被跳过的提交数)。"""
    date = date or dt.date.today().isoformat()
    buckets = {s: [] for s in SECTIONS}
    breaking = []
    skipped = 0
    for c in commits:
        if not c["conventional"]:
            skipped += 1
            continue
        if c["breaking"]:
            breaking.append(f"- {c['desc']} ({c['sha'][:7]})")
        sec = classify(c, include_internal)
        if sec is None:
            skipped += 1
            continue
        prefix = f"**{c['scope']}**: " if c["scope"] else ""
        buckets[sec].append(f"- {prefix}{c['desc']} ({c['sha'][:7]})")

    lines = [f"## [{version}] - {date}", ""]
    if breaking:
        lines += ["### BREAKING CHANGES", ""] + breaking + [""]
    for sec in SECTIONS:
        if buckets[sec]:
            lines += [f"### {sec}", ""] + buckets[sec] + [""]
    if not breaking and not any(buckets.values()):
        lines += ["### Changed", "", "- 无对外可见变更（仅内部改动）", ""]
    if repo_url and current:
        lines.append(f"[{version}]: {repo_url}/compare/v{current}...v{version}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", skipped


def lint(text):
    """体检 CHANGELOG.md 是否符合 Keep a Changelog。返回 (问题列表, 统计)。"""
    problems = []
    if not re.search(r"^#\s+Changelog", text, re.M):
        problems.append("缺少 # Changelog 标题")
    if "## [Unreleased]" not in text:
        problems.append("缺少 ## [Unreleased] 段（新提交应该先进这里）")
    versions = re.findall(r"^## \[([^\]]+)\](?:\s*-\s*(\S+))?", text, re.M)
    released = [(v, d) for v, d in versions if v.lower() != "unreleased"]
    for v, d in released:
        if not re.fullmatch(r"\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?", v):
            problems.append(f"版本号 {v} 不是 SemVer 形式")
        if not d or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d or ""):
            problems.append(f"{v} 缺少 - YYYY-MM-DD 日期")
    dates = [d for _, d in released if d]
    if dates != sorted(dates, reverse=True):
        problems.append("版本段落不是按时间倒序（最新应在最上面）")
    for cat in re.findall(r"^###\s+(.+)$", text, re.M):
        if cat not in SECTIONS and cat != "BREAKING CHANGES":
            problems.append(f"分类 ### {cat} 不在 Keep a Changelog 的六类里")
    stats = {"版本段": len(released), "分类段": len(re.findall(r"^###\s+", text, re.M))}
    return problems, stats


# --- 样例提交记录（自检用；真实项目中来自 git log） --------------------------
SAMPLE_LOG = """\
a1b2c3d feat(api): 新增分页参数 page/page_size
9f8e7d6 fix(api): 修正 page=0 时的越界读取
4c3b2a1 perf(db): 用批量查询替换 N+1 查询
7d6c5b4 docs(readme): 补充分页用法示例
2e1d0c9 chore(ci): 升级 actions/setup-python 到 v5
8b7a6f5 feat(cli)!: 把 --output 参数改名为 --format

BREAKING CHANGE: --output 已移除，请改用 --format
3a2b1c0 fix(cli): 修正 --format json 时的缩进
"""


def self_test():
    commits = parse_commits(SAMPLE_LOG)
    assert len(commits) == 7, f"应该解析出 7 个提交，得到 {len(commits)}"
    by_sha = {c["sha"]: c for c in commits}

    # 1. 两类破坏性变更都要被抓到：subject 里的 ! 与 body 里的 BREAKING CHANGE:
    assert by_sha["8b7a6f5"]["breaking"] is True, "subject 里的 ! 没被识别"
    assert "已移除" in by_sha["8b7a6f5"]["breaking_note"], "BREAKING CHANGE 正文没被摘出来"
    assert by_sha["a1b2c3d"]["breaking"] is False

    # 2. 分类
    assert classify(by_sha["a1b2c3d"]) == "Added"
    assert classify(by_sha["9f8e7d6"]) == "Fixed"
    assert classify(by_sha["4c3b2a1"]) == "Changed"
    assert classify(by_sha["7d6c5b4"]) is None, "docs 默认不进 CHANGELOG"
    assert classify(by_sha["7d6c5b4"], include_internal=True) == "Changed"

    # 3. 版本决策：有 BREAKING -> major
    ver, reason = next_version(commits, "1.1.4")
    assert ver == "2.0.0" and reason == "BREAKING CHANGE", (ver, reason)

    # 4. 没有 BREAKING 时：有 feat -> minor；只有 fix -> patch；0.x 走惯例
    no_break = [c for c in commits if not c["breaking"]]
    assert next_version(no_break, "1.1.4")[0] == "1.2.0"
    only_fix = [c for c in commits if c["type"] == "fix" and not c["breaking"]]
    assert next_version(only_fix, "1.1.4")[0] == "1.1.5"
    assert next_version(commits, "0.3.1", zero_major=True)[0] == "0.4.0"

    # 5. 渲染
    text, skipped = render(commits, "2.0.0", "1.1.4",
                           repo_url="https://example.com/p", date="2026-10-16")
    assert text.startswith("## [2.0.0] - 2026-10-16")
    assert "### BREAKING CHANGES" in text
    assert "### Added" in text and "### Fixed" in text
    assert "**api**: 新增分页参数" in text, "scope 应该带进条目"
    assert skipped == 2, f"docs/chore 两条内部改动应被跳过，实际 {skipped}"
    assert "[2.0.0]: https://example.com/p/compare/v1.1.4...v2.0.0" in text

    # 6. 非规范提交不崩，且被计入 skipped
    messy = parse_commits("1a2b3c4 修了个 bug\naaaaaaa feat: 正常提交\n")
    assert len(messy) == 2, "sha 是十六进制的提交行都要被认出来"
    assert messy[0]["conventional"] is False, "手写的非规范提交不算 conventional"
    assert messy[1]["conventional"] is True
    _, sk2 = render(messy, "1.0.1", "1.0.0")
    assert sk2 == 1, "非规范提交应被跳过并计数"
    # 6b. sha 不是十六进制的行会被丢弃（这是设计限制，不是崩溃）
    assert len(parse_commits("zzzzzzz not-a-sha\n2a3b4c5 fix: ok\n")) == 1

    # 7. lint：规范文档通过，缺 Unreleased/日期的文档必须被点名
    good = "# Changelog\n\n## [Unreleased]\n\n" + text
    assert lint(good)[0] == [], lint(good)[0]
    bad = "## [2.0.0]\n\n### Added\n- x\n"
    probs = lint(bad)[0]
    assert any("Unreleased" in p for p in probs) and any("Changelog" in p for p in probs)
    assert any("日期" in p for p in probs)

    print("✅ self-test 通过：7 个提交解析（含无空行情形）/ 2 类 BREAKING 识别 / 4 条分类规则 /"
          " 4 条版本决策（含 0.x 惯例）/ 渲染 3 条断言 / lint 正反两例")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Day 181 · 02 Changelog")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--from", dest="src", help="提交记录文件（git log 风格）")
    ap.add_argument("--current", default="0.0.0", help="当前线上版本（用来算下一个版本）")
    ap.add_argument("--repo-url", default="", help="仓库地址，用来生成 compare 链接")
    ap.add_argument("--include-internal", action="store_true", help="docs/chore 也写进 Changed")
    ap.add_argument("--zero-major", action="store_true", help="0.x 项目惯例：BREAKING 只升 minor")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不落盘")
    ap.add_argument("--out", default="CHANGELOG.entry.md")
    ap.add_argument("--lint", metavar="FILE", help="体检已有 CHANGELOG")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())

    if args.lint:
        try:
            text = open(args.lint, encoding="utf-8").read()
        except OSError as e:
            print(f"❌ 读不到 {args.lint}: {e}")
            sys.exit(2)
        problems, stats = lint(text)
        print(f"# lint {args.lint} · {stats['版本段']} 个版本段 · {stats['分类段']} 个分类段")
        if problems:
            for p in problems:
                print(f"  ❌ {p}")
            sys.exit(1)
        print("  ✅ 符合 Keep a Changelog")
        return

    raw = open(args.src, encoding="utf-8").read() if args.src else SAMPLE_LOG
    commits = parse_commits(raw)
    version, reason = next_version(commits, args.current, args.zero_major)
    text, skipped = render(commits, version, args.current, args.repo_url,
                           include_internal=args.include_internal)
    print(f"# 提交 {len(commits)} 条 · 跳过 {skipped} 条（非规范或内部改动）"
          f" · 版本决策 {args.current} -> {version}（依据：{reason}）")
    print()
    print(text)
    if args.dry_run:
        print("# --dry-run：未写文件")
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"# 已写入 {args.out}")


if __name__ == "__main__":
    main()
