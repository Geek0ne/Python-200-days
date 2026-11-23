#!/usr/bin/env python3
"""01-article-lint.py — Markdown 技术文章结构体检器（零依赖，离线可跑）

为什么需要它：
  技术文章最常见的失败不是"写错了"，而是"读者读完不知道你到底验证了什么"。
  结构问题（标题层级、代码块语言、无证据断言）可以在发布前机械地查出来。

用法:
    python3 01-article-lint.py post.md
    cat post.md | python3 01-article-lint.py -      # 从 stdin 读
    python3 01-article-lint.py post.md --json       # 机器可读
    python3 01-article-lint.py --self-test          # 离线自证

退出码: 0 = 无 error；1 = 至少一条 error；2 = 用法错误
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# ---------------------------------------------------------------- 规则定义
# E = error（会误导读者/结构坏了）；W = warning（读者体验受损）
VAGUE_WORDS = ("显然", "众所周知", "大家都知道", "不用多说", "不言而喻", "自然就")
PERF_WORDS = ("倍", "×", "快了", "慢了", "提升", "下降")
CONDITION_WORDS = ("样本", "测试", "环境", "次", "median", "中位", "均值", "平均",
                   "warmup", "预热", "重复", "benchmark", "基准")

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*([\w+.-]*)\s*$")
LINK_RE = re.compile(r"(?<![!\]])\[([^\]]+)\]\(([^)]+)\)")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
TODO_RE = re.compile(r"\b(TODO|FIXME|TBD|XXX)\s*[:：]")


def lint(text: str) -> dict:
    """把 Markdown 拆成块，逐块检查。返回 {"findings": [...], "stats": {...}}"""
    lines = text.splitlines()
    findings = []
    h1_count = 0
    prev_level = 0
    in_fence = False
    fence_count = 0
    para = []
    para_start = 0

    def add(code, level, line_no, msg):
        findings.append({"code": code, "level": level, "line": line_no, "message": msg})

    def flush_para():
        nonlocal para_start
        if not para:
            para_start = 0
            return
        body = "".join(p.strip() for p in para)
        # 去掉行内代码与「引用」的短语，只对真正的陈述做措辞检查
        prose = re.sub(r"`[^`]+`", "", body)
        prose = re.sub(r'["「“][^"」”]{1,40}["」”]', '', prose)
        para.clear()
        if not body:
            para_start = 0
            return
        for w in VAGUE_WORDS:
            if w in prose:
                add("W102", "warning", para_start, f"模糊断言「{w}」：给出证据或删掉")
        if any(w in prose for w in PERF_WORDS) and not any(c in body for c in CONDITION_WORDS):
            add("W103", "warning", para_start,
                "性能/数量断言缺少测量条件（样本量、环境、重复次数）")
        if len(body) > 400:
            add("W101", "warning", para_start, f"段落 {len(body)} 字，建议拆成 2-3 段")
        para_start = 0

    for i, raw in enumerate(lines, 1):
        line = raw.rstrip()

        m = FENCE_RE.match(line)
        if m:
            if not in_fence:
                in_fence = True
                fence_count += 1
                if not m.group(2):
                    add("E003", "error", i, "代码块没有标注语言（读者失去语法高亮）")
            else:
                in_fence = False
            continue
        if in_fence:
            continue  # 代码内容不参与结构检查——这是最容易误报的地方

        hm = HEADING_RE.match(line)
        if hm:
            flush_para()
            level = len(hm.group(1))
            if level == 1:
                h1_count += 1
                if h1_count > 1:
                    add("E001", "error", i, "出现第二个 H1：一篇文章只能有一个标题")
            if prev_level and level > prev_level + 1:
                add("E002", "error", i, f"标题从 H{prev_level} 跳到 H{level}")
            if not hm.group(2).strip():
                add("E004", "error", i, "空标题")
            prev_level = level
            continue

        if line.startswith("|"):
            cells = line.strip().strip("|").split("|")
            if len(cells) < 2:
                add("W106", "warning", i, "表格行只有一列，可能是分隔符写错")
            continue

        line_checks = re.sub(r"`[^`]+`", "", line)
        if TODO_RE.search(line_checks):
            add("W104", "warning", i, "遗留 TODO/TBD：发布前处理掉或明确标注为邀请协作")

        for alt, url in IMAGE_RE.findall(line_checks):
            if not alt.strip():
                add("W105", "warning", i, f"图片缺少 alt 文本: {url}")

        for label, url in LINK_RE.findall(line_checks):
            if url.startswith("http") and not label.strip():
                add("W107", "warning", i, f"链接没有可读文字: {url}")

        if not line.strip():
            flush_para()
        else:
            if not para:
                para_start = i
            para.append(line)
    flush_para()

    if h1_count == 0:
        add("E005", "error", 1, "缺少 H1 标题")
    if fence_count == 0:
        add("W108", "warning", 1, "全文没有代码块：技术文章至少应给一段可复制的命令")

    errors = sum(1 for f in findings if f["level"] == "error")
    warnings = sum(1 for f in findings if f["level"] == "warning")
    score = max(0, 100 - 10 * errors - 3 * warnings)
    stats = {
        "lines": len(lines),
        "chars": len(text),
        "headings": sum(1 for l in lines if HEADING_RE.match(l)),
        "code_blocks": fence_count,
        "errors": errors,
        "warnings": warnings,
        "score": score,
    }
    findings.sort(key=lambda f: (f["line"], f["code"]))
    return {"findings": findings, "stats": stats}


def render(result, path):
    s = result["stats"]
    out = [f"📝 {path}",
           f"   行数 {s['lines']} / 字符 {s['chars']} / 标题 {s['headings']} / 代码块 {s['code_blocks']}",
           f"   评分 {s['score']}/100   错误 {s['errors']}   警告 {s['warnings']}"]
    if result["findings"]:
        out.append("")
        for f in result["findings"]:
            icon = "❌" if f["level"] == "error" else "⚠️"
            out.append(f"  {icon} L{f['line']:<4} {f['code']}  {f['message']}")
    else:
        out.append("   ✅ 没有发现问题")
    return "\n".join(out)


# ---------------------------------------------------------------- 自测
FIXTURE_BAD = """# 标题

## 小节

# 第二个 H1

```
没有语言标注的代码块
```

显然这个方案更快，提升了 3 倍。

![](/x.png)

- TODO: 补图
"""


def self_test():
    r = lint(FIXTURE_BAD)
    codes = [f["code"] for f in r["findings"]]
    expect = {"E001", "E003", "W102", "W103", "W105", "W104"}
    ok = True
    for c in sorted(expect):
        hit = c in codes
        print(("  ✅ " if hit else "  ❌ ") + f"{c} 被检出")
        ok = ok and hit
    good = """# 标题

## 方法

```python
# 这是注释，不是标题
print("hi")
```
"""
    g = lint(good)
    no_false_heading = not any(f["code"] == "E001" for f in g["findings"])
    print(("  ✅ " if no_false_heading else "  ❌ ") + "代码块内 # 不被误判为 H1")
    ok = ok and no_false_heading
    lower = r["stats"]["score"] < g["stats"]["score"]
    print(f"  {'✅' if lower else '❌'} 坏文章分数更低 ({r['stats']['score']} < {g['stats']['score']})")
    ok = ok and lower
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="Markdown 技术文章结构体检")
    ap.add_argument("path", nargs="?", help="Markdown 文件路径，- 表示 stdin")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--self-test", action="store_true", help="离线自测")
    ap.add_argument("--strict", action="store_true", help="warning 也算失败")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.path:
        ap.print_usage()
        return 2

    if args.path == "-":
        text, name = sys.stdin.read(), "<stdin>"
    else:
        with open(args.path, encoding="utf-8") as fh:
            text = fh.read()
        name = args.path

    result = lint(text)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render(result, name))
    bad = result["stats"]["errors"] > 0 or (args.strict and result["stats"]["warnings"] > 0)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
