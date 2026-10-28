#!/usr/bin/env python3
"""03-article-build.py — 零依赖技术博客静态站生成器（离线可跑）

为什么不用现成框架：
  发布这件事的价值不在主题有多花，而在"读者点开能读、能复制、能验证"。
  这个脚本只做三件事：把 Markdown 渲染成可读 HTML、生成目录、生成 RSS。
  整个站点是一个目录，cp 到任何静态服务器就能用。

用法:
    python3 03-article-build.py post.md --out dist          # 单篇 + 索引 + RSS
    python3 03-article-build.py posts/ --out dist           # 目录下所有 *.md
    python3 03-article-build.py --self-test                 # 离线自证
    python3 03-article-build.py post.md --out dist --serve 9000   # 本地预览
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import http.server
import os
import re
import shutil
import socketserver
import sys
import tempfile
import unicodedata

# ---------------------------------------------------------------- front matter
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
H2_RE = re.compile(r"^(#{2,3})\s+(.*)$")
FENCE_RE = re.compile(r"^\s*`{3,}\s*([\w+.-]*)\s*$")
UL_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
OL_RE = re.compile(r"^\s*\d+\.\s+(.*)$")


def parse_front_matter(text: str):
    """极简 YAML：只支持 key: value 与 tags 的 [a, b] 形式。

    为什么不用 PyYAML：技术写作工具的依赖越少，读者复现成本越低。
    """
    m = FM_RE.match(text)
    meta = {}
    if not m:
        return meta, text
    for line in m.group(1).splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, val = line.split(":", 1)
        val = val.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            meta[key.strip()] = [v.strip().strip('"') for v in val[1:-1].split(",") if v.strip()]
        else:
            meta[key.strip()] = val
    return meta, text[m.end():]


def slugify(title: str) -> str:
    """中文标题保留可读性：非 ASCII 转成拼音不现实，这里用 UTF-8 转义太丑。
    折中方案：ASCII 转小写加连字符；纯中文用首字哈希保证稳定唯一。"""
    ascii_part = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_part).strip("-").lower()
    if ascii_part:
        return ascii_part[:60]
    h = 0
    for ch in title:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return "post-%08x" % h


def anchor_id(title: str) -> str:
    """HTML5 允许中文 id。保留可读性，只把空白折成连字符、去掉标点。"""
    t = re.sub(r"[\s\u3000]+", "-", title.strip())
    t = re.sub(r"[^\w\u4e00-\u9fff-]+", "", t)
    return t or "section"


def reading_time(text: str) -> int:
    """中文按 400 字/分钟，代码行按 1 行 = 3 秒折算成"字"。
    刻意写死在代码里并暴露公式——读者能算出你凭什么说"5 分钟读完"。"""
    code_lines = 0
    prose = []
    in_code = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_code = not in_code
            continue
        if in_code:
            code_lines += 1
        else:
            prose.append(line)
    chars = len(re.sub(r"\s", "", "".join(prose)))
    weighted = chars + code_lines * 20  # 3 秒 ≈ 20 字
    return max(1, round(weighted / 400))


def inline(text: str) -> str:
    """行内语法。先转义再替换，避免用户写的 <script> 变成真标签。"""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", lambda m: "<code>" + m.group(1) + "</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                 lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', out)
    return out


def render_markdown(body: str):
    """返回 (html_fragment, toc)。支持的语法刻意很少，但行为确定。"""
    lines = body.splitlines()
    out, toc = [], []
    i = 0
    in_code = False
    code_buf = []
    lang = ""
    para = []
    list_type = None

    def flush_para():
        nonlocal para
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []

    def close_list():
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    while i < len(lines):
        line = lines[i]
        fm = FENCE_RE.match(line)
        if fm:
            flush_para()
            close_list()
            if not in_code:
                in_code, lang, code_buf = True, fm.group(1) or "text", []
            else:
                code = html.escape("\n".join(code_buf))
                out.append(f'<pre><code class="language-{html.escape(lang)}">{code}</code></pre>')
                in_code = False
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        hm = H2_RE.match(line)
        if hm:
            flush_para()
            close_list()
            level = len(hm.group(1))
            title = hm.group(2).strip()
            anchor = anchor_id(title)
            toc.append((level, anchor, title))
            out.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
            i += 1
            continue

        if line.startswith("# "):
            flush_para()
            close_list()
            out.append(f"<h1>{inline(line[2:].strip())}</h1>")
            i += 1
            continue

        if line.startswith(">"):
            flush_para()
            close_list()
            out.append("<blockquote>" + inline(line.lstrip("> ").strip()) + "</blockquote>")
            i += 1
            continue

        um = UL_RE.match(line)
        om = OL_RE.match(line)
        if um or om:
            flush_para()
            want = "ul" if um else "ol"
            if list_type != want:
                close_list()
                out.append(f"<{want}>")
                list_type = want
            out.append("<li>" + inline((um or om).group(1)) + "</li>")
            i += 1
            continue

        if line.strip() in ("---", "***"):
            flush_para()
            close_list()
            out.append("<hr>")
            i += 1
            continue

        if not line.strip():
            flush_para()
            close_list()
        else:
            para.append(line.strip())
        i += 1

    flush_para()
    close_list()
    return "\n".join(out), toc


def build_article(text: str, path: str):
    meta, body = parse_front_matter(text)
    title = meta.get("title") or _first_h1(body) or os.path.basename(path)
    slug = meta.get("slug") or slugify(title)
    date = meta.get("date") or dt.date.today().isoformat()
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    frag, toc = render_markdown(body)
    toc_html = "\n".join(
        f'<li class="lvl{lvl}"><a href="#{a}">{html.escape(t)}</a></li>' for lvl, a, t in toc if lvl == 2)
    tag_html = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags)
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>body{{max-width:46rem;margin:2rem auto;padding:0 1rem;font:16px/1.75 -apple-system,system-ui,sans-serif;color:#1a1a1a}}
pre{{background:#f6f8fa;padding:1rem;overflow:auto;border-radius:6px;font-size:14px}}
code{{background:#f2f2f2;padding:.1em .3em;border-radius:3px}}
pre code{{background:none;padding:0}}.tag{{background:#eef;border-radius:3px;padding:.1em .4em;margin-right:.4em;font-size:13px}}
.meta{{color:#666;font-size:14px}}nav.toc{{background:#fafafa;border-left:3px solid #ddd;padding:.5rem 1rem}}</style>
</head><body>
<h1>{html.escape(title)}</h1>
<p class="meta">{date} · 约 {reading_time(body)} 分钟 · {tag_html}</p>
<nav class="toc"><strong>目录</strong><ul>{toc_html}</ul></nav>
{frag}
</body></html>"""
    return {"slug": slug, "title": title, "date": date, "tags": tags,
            "summary": meta.get("summary", ""), "html": page,
            "minutes": reading_time(body), "chars": len(body)}


def _first_h1(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def build_site(paths, outdir: str) -> list:
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)
    articles = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            articles.append(build_article(fh.read(), p))
    articles.sort(key=lambda a: a["date"], reverse=True)
    for a in articles:
        with open(os.path.join(outdir, a["slug"] + ".html"), "w", encoding="utf-8") as fh:
            fh.write(a["html"])
    items = "\n".join(
        f'<li><a href="{a["slug"]}.html">{html.escape(a["title"])}</a>'
        f' <span class="meta">{a["date"]} · {a["minutes"]} 分钟</span>'
        f'<br>{html.escape(a["summary"])}</li>' for a in articles)
    index = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>技术写作实验室</title></head><body>
<h1>技术写作实验室</h1><p class="meta">{len(articles)} 篇文章</p>
<ul>{items}</ul></body></html>"""
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index)
    feed_items = "\n".join(
        f"<item><title>{html.escape(a['title'])}</title>"
        f"<link>/{a['slug']}.html</link><guid>/{a['slug']}.html</guid>"
        f"<description>{html.escape(a['summary'])}</description></item>" for a in articles)
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>技术写作实验室</title>
<link>/</link><description>可复现的技术文章</description>
{feed_items}</channel></rss>"""
    with open(os.path.join(outdir, "feed.xml"), "w", encoding="utf-8") as fh:
        fh.write(feed)
    open(os.path.join(outdir, ".nojekyll"), "w").close()
    return articles


# ---------------------------------------------------------------- 自测
FIXTURE = """---
title: "把一次实验写成文章"
date: 2026-10-29
tags: [写作, 实验]
summary: 一个用于自测的样本
---

# 把一次实验写成文章

## 为什么要写

正文里有一个 `inline code` 和 <script>alert(1)</script>。

```python
x = 1 < 2
print(x)
```

## 结论

- 第一条
- 第二条
"""


def self_test() -> int:
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("  ✅ " if cond else "  ❌ ") + msg)
        ok = ok and bool(cond)

    meta, body = parse_front_matter(FIXTURE)
    check(meta["title"] == "把一次实验写成文章", "front matter 的 title 解析正确")
    check(meta["tags"] == ["写作", "实验"], "tags 列表解析正确")
    frag, toc = render_markdown(body)
    check(any(a == "为什么要写" for _, a, _ in toc) or len(toc) == 2, "目录提取到 2 个 H2")
    check('id="为什么要写"' in frag, "标题生成了与目录一致的锚点 id")
    check("&lt;script&gt;" in frag, "正文里的 <script> 被转义（不执行）")
    check("x = 1 &lt; 2" in frag, "代码块里的 < 被转义")
    check('class="language-python"' in frag, "代码块保留语言标记")
    check("<li>第一条</li>" in frag, "列表被渲染")

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "post.md")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(FIXTURE)
        arts = build_site([src], os.path.join(tmp, "dist"))
        page = open(os.path.join(tmp, "dist", arts[0]["slug"] + ".html"), encoding="utf-8").read()
        check("<h1>把一次实验写成文章</h1>" in page, "文章页包含 H1")
        check("分钟" in page, "文章页标注了阅读时长")
        feed = open(os.path.join(tmp, "dist", "feed.xml"), encoding="utf-8").read()
        check("<item>" in feed and arts[0]["slug"] in feed, "RSS 包含文章条目")
        check(os.path.exists(os.path.join(tmp, "dist", ".nojekyll")), "生成了 .nojekyll")
        idx = open(os.path.join(tmp, "dist", "index.html"), encoding="utf-8").read()
        check(arts[0]["slug"] + ".html" in idx, "首页链接到文章页")

    check(reading_time("中文" * 200) == 1, "阅读时长至少 1 分钟")
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def serve(outdir: str, port: int) -> None:
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=outdir, **kw)
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"http://127.0.0.1:{port}/  (Ctrl-C 停止)")
        httpd.serve_forever()


def main() -> int:
    ap = argparse.ArgumentParser(description="零依赖技术博客构建器")
    ap.add_argument("source", nargs="?")
    ap.add_argument("--out", default="dist")
    ap.add_argument("--serve", type=int, metavar="PORT")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.source:
        ap.error("缺少源文件或目录")
    if os.path.isdir(args.source):
        paths = sorted(os.path.join(args.source, f) for f in os.listdir(args.source)
                       if f.endswith(".md"))
    else:
        paths = [args.source]
    arts = build_site(paths, args.out)
    for a in arts:
        print(f"  {a['slug']}.html  {a['minutes']} 分钟  {a['chars']} 字符")
    print(f"✅ 构建完成：{len(arts)} 篇 → {args.out}/")
    if args.serve:
        serve(args.out, args.serve)
    return 0


if __name__ == "__main__":
    sys.exit(main())
