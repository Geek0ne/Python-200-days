#!/usr/bin/env python3
"""
Markdown → HTML 渲染器（Python-200-days 静态站专用）

为什么不手写解析器：150k 行的真实教材文档里有嵌套列表、表格、`<details>` 原始 HTML、
以及 183 张 mermaid 图，手写必然漏。`markdown` + `pygments` 是成熟方案。

本模块负责三件"通用库不管"的事：
  ① mermaid 代码块 → 可渲染的 <div class="mermaid">
  ② ASCII 图（```text / ```）原样保留，绝不高亮、绝不换行
  ③ 每页注入 TOC 侧边栏、上下页导航、代码复制按钮

用法：
    from md2html import render_lesson
    html = render_lesson(md_text, day=day_obj, prev=prev_obj, next=next_obj, all_days=days)
"""

from __future__ import annotations

import html as htmllib
import re
from dataclasses import dataclass

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer

_FMT = HtmlFormatter(nowrap=True, cssclass="hl")


# ---------------------------------------------------------------------------
# 预处理：把 mermaid / ASCII 块换成占位符，渲染后再放回
# ---------------------------------------------------------------------------
# 围栏行（行首允许引用块前缀 "> "，反引号允许被反斜杠转义，支持 3+ 个反引号）。
# 支持转义形式：源文件里出现过 `\`\`\`text` 这种被整体转义的围栏（day-192）。
QPREFIX = r"(?:[ \t]*>[ \t]?)*"
FENCE_OPEN = re.compile(
    rf"^(?P<pre>{QPREFIX})(?P<indent>[ \t]*)(?P<ticks>(?:\\`|`){{3,}})(?P<lang>[\w+.#-]*)[ \t]*$"
)
FENCE_CLOSE = re.compile(
    rf"^(?P<pre>{QPREFIX})(?P<indent>[ \t]*)(?P<ticks>(?:\\`|`){{3,}})[ \t]*$"
)

# 这些语言的块是"图"不是"代码"：不套等宽、不高亮、必须原样
PLAIN_LANGS = {"", "text", "txt", "ascii", "plain", "console", "output", "log", "none"}


@dataclass
class Block:
    lang: str
    body: str
    is_mermaid: bool = False
    is_plain: bool = False


def _ticklen(ticks: str) -> int:
    return ticks.count("`")


def extract_blocks(md: str) -> tuple[str, list[Block]]:
    r"""把围栏代码块抠出来，换成占位符。返回 (带占位符的 md, 块列表)。

    比旧版正则多修三类真实踩坑：
      ① 被转义的围栏（反引号前带反斜杠）——day-192 整课反引号被转义，旧版完全识别不出；
      ② 引用块里的围栏（> ```bash）——旧版要求行首直接是反引号；
      ③ N>3 个反引号的围栏——嵌套场景（```markdown 里包 ```bash）必须靠
         "闭合反引号数 ≥ 开启数" 配对，否则整段正文会被吞进代码块。
    """
    lines = md.split("\n")
    out: list[str] = []
    blocks: list[Block] = []
    i, n = 0, len(lines)

    while i < n:
        m = FENCE_OPEN.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue

        pre, indent = m.group("pre"), m.group("indent")
        ticklen = _ticklen(m.group("ticks"))
        escaped = "\\`" in m.group("ticks")
        lang = (m.group("lang") or "").strip().lower()
        body_lines: list[str] = []
        i += 1

        while i < n:
            line = lines[i]
            cm = FENCE_CLOSE.match(line)
            if cm and _ticklen(cm.group("ticks")) >= ticklen:
                i += 1
                break
            s = line
            if pre and s.startswith(pre):
                s = s[len(pre):]
            s = re.sub(rf"^[ \t]{{0,{len(indent)}}}", "", s, count=1)
            if escaped:
                s = s.replace("\\`", "`")
            body_lines.append(s)
            i += 1
        # 未闭合的围栏按 CommonMark 处理：吞到文件末尾（旧版直接当纯文本展示）

        body = "\n".join(body_lines)
        idx = len(blocks)
        blocks.append(Block(
            lang=lang,
            body=body,
            is_mermaid=(lang == "mermaid"),
            is_plain=(lang in PLAIN_LANGS),
        ))
        out.append(f"{pre}{indent}@@BLOCK{idx}@@")

    return "\n".join(out), blocks


# ---------------------------------------------------------------------------
# <details> 内嵌 markdown / 表格前缺空行：python-markdown 不管，这里兜底
# ---------------------------------------------------------------------------
DETAILS_RE = re.compile(
    r"<details[^>]*>(?:(?!<details)[\s\S]*?)</details>[ \t]*", re.I
)
SUMMARY_RE = re.compile(r"<summary[^>]*>[\s\S]*?</summary>", re.I)
TABLE_ROW = re.compile(r"^[ \t]{0,3}\|")


def fix_tables(md: str) -> str:
    """表格行直接跟在段落/标题后面时 python-markdown 不认（day-109），补空行。"""
    lines = md.split("\n")
    out: list[str] = []
    for ln in lines:
        if (TABLE_ROW.match(ln) and out and out[-1].strip()
                and not TABLE_ROW.match(out[-1])
                and not out[-1].lstrip().startswith(">")
                and "@@BLOCK" not in out[-1]):
            out.append("")
        out.append(ln)
    return "\n".join(out)


def extract_details(md: str) -> tuple[str, list[str]]:
    """把 <details>...</details> 段落抠出（最内层优先），返回 (md, 段落列表)。"""
    parts: list[str] = []
    while DETAILS_RE.search(md):
        def repl(m: re.Match) -> str:
            parts.append(m.group(0).rstrip())
            return f"@@DETAILS{len(parts) - 1}@@"
        md = DETAILS_RE.sub(repl, md)
    return md, parts


def _make_md(nl2br: bool) -> "markdown.Markdown":
    exts = ["extra", "tables", "fenced_code", "sane_lists", "toc", "attr_list"]
    if nl2br:
        exts.append("nl2br")
    return markdown.Markdown(extensions=exts, output_format="html")


def render_body(md_text: str, *, nl2br: bool) -> tuple[str, list[Block]]:
    """markdown 文本 → 正文 HTML（代码块已放回、details 内 markdown 已渲染）。"""
    md_text, blocks = extract_blocks(md_text)
    md_text, detail_parts = extract_details(md_text)
    body = _make_md(nl2br).convert(fix_tables(md_text))

    # details 段落：内层占位符先组装，再注入外层（extract_details 保证内层序号更小）
    assembled: dict[int, str] = {}
    for idx, seg in enumerate(detail_parts):
        dm = re.match(r"(?is)(<details[^>]*>)([\s\S]*?)(</details>)\s*$", seg)
        if not dm:
            assembled[idx] = htmllib.escape(seg)
            continue
        open_tag, content, close_tag = dm.groups()
        sm = SUMMARY_RE.search(content)
        summary_html, rest = (sm.group(0), content[sm.end():]) if sm else ("", content)
        inner = _make_md(nl2br).convert(fix_tables(rest))
        html_seg = f"{open_tag}\n{summary_html}\n{inner}\n{close_tag}"
        for k in range(idx):
            html_seg = (html_seg
                        .replace(f"<p>@@DETAILS{k}@@</p>", assembled[k])
                        .replace(f"@@DETAILS{k}@@", assembled[k]))
        assembled[idx] = html_seg
        body = (body
                .replace(f"<p>@@DETAILS{idx}@@</p>", html_seg)
                .replace(f"@@DETAILS{idx}@@", html_seg))

    for idx, html_block in render_blocks_html(blocks).items():
        body = body.replace(f"<p>@@BLOCK{idx}@@</p>", html_block)
        body = body.replace(f"@@BLOCK{idx}@@", html_block)
    return body, blocks


def highlight_code(lang: str, body: str) -> str:
    """用 pygments 高亮；未知语言或非代码语言退回纯文本。"""
    if not lang or lang in PLAIN_LANGS:
        return htmllib.escape(body)
    try:
        lexer = get_lexer_by_name(lang, stripall=False)
    except Exception:
        return htmllib.escape(body)
    return highlight(body, lexer, _FMT)


def render_blocks_html(blocks: list[Block]) -> dict[int, str]:
    out: dict[int, str] = {}
    for i, b in enumerate(blocks):
        if b.is_mermaid:
            # mermaid 文本里不能有会破坏解析的裸 < > &，交给 mermaid.js 自己处理
            out[i] = (
                f'<div class="mermaid-wrap">'
                f'<div class="mermaid">{htmllib.escape(b.body)}</div>'
                f'<button class="mermaid-raw" type="button" '
                f"onclick=\"this.parentNode.classList.toggle('show-raw')\">查看源码</button>"
                f'<pre class="mermaid-src"><code>{htmllib.escape(b.body)}</code></pre>'
                f"</div>"
            )
        elif b.is_plain:
            out[i] = f'<pre class="plain"><code>{htmllib.escape(b.body)}</code></pre>'
        else:
            label = htmllib.escape(b.lang)
            out[i] = (
                f'<div class="codeblock">'
                f'<div class="cb-head"><span class="cb-lang">{label}</span>'
                f'<button class="copy" type="button" onclick="copyCode(this)">复制</button></div>'
                f'<pre class="hl-pre"><code class="hl">{highlight_code(b.lang, b.body)}</code></pre>'
                f"</div>"
            )
    return out


# ---------------------------------------------------------------------------
# 页面组装
# ---------------------------------------------------------------------------
def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text.lower()).strip("-") or "x"


def build_toc(body_html: str) -> str:
    """从渲染后的 h2/h3 里抽 TOC。"""
    items: list[str] = []
    for m in re.finditer(r'<h([23]) id="([^"]+)"[^>]*>(.*?)</h\1>', body_html, re.S):
        level, hid, inner = m.group(1), m.group(2), m.group(3)
        text = re.sub(r"<[^>]+>", "", inner)
        items.append(
            f'<a class="toc-l{level}" href="#{hstrip(hid)}" '
            f'title="{htmllib.escape(text, quote=True)}">{htmllib.escape(text)}</a>'
        )
    return "\n".join(items)


def hstrip(s: str) -> str:
    return s


def render_lesson(md_text: str, *, day, prev_day=None, next_day=None,
                  all_days=None, site_root: str = "..") -> str:
    """渲染一节课为完整 HTML 页面。"""
    body, _blocks = render_body(md_text, nl2br=True)
    toc = build_toc(body)
    title = f"Day {day.num} — {day.title}"
    e = htmllib.escape

    nav_items = []
    if prev_day:
        nav_items.append(
            f'<a class="nav-prev" href="../{prev_day.url_slug}/index.html">← Day {prev_day.num} {e(prev_day.title)}</a>'
        )
    else:
        nav_items.append('<span class="nav-prev disabled">已是第一课</span>')
    if next_day:
        nav_items.append(
            f'<a class="nav-next" href="../{next_day.url_slug}/index.html">Day {next_day.num} {e(next_day.title)} →</a>'
        )
    else:
        nav_items.append('<span class="nav-next disabled">已是最后一课</span>')

    extras = []
    if day.has_code:
        extras.append('<a class="pill-link" href="code/" download>📦 下载本课代码（{n} 个文件）</a>'.format(n=day.code_files))
    if day.has_exercises:
        extras.append('<a class="pill-link" href="exercises.html">✍️ 练习与清单</a>')
    if day.has_diagrams:
        extras.append('<a class="pill-link" href="diagrams.html">🗺️ 图解</a>')

    raw_link = f'<a class="pill-link" href="https://github.com/Geek0ne/Python-200-days/tree/main/days/{day.slug}" rel="noopener">📁 GitHub 源文件</a>'

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="stylesheet" href="{site_root}/assets/style.css">
<link rel="stylesheet" href="{site_root}/assets/lesson.css">
</head>
<body class="lesson">
<a class="skip" href="#content">跳到正文</a>

<header class="lhead">
  <a class="back" href="{site_root}/index.html">← 返回总目录</a>
  <h1>{e(title)}</h1>
  <div class="lmeta">
    <span class="badge">{e(day.phase_name)}</span>
    <span class="badge">{day.readme_lines} 行</span>
    {'<span class="badge">{} 个可运行脚本</span>'.format(day.code_files) if day.has_code else ''}
    {'<div class="pills">{}</div>'.format(''.join(extras) + raw_link)}
  </div>
</header>

<div class="lwrap">
  <nav class="toc" aria-label="目录">
    <div class="toc-h">本页目录</div>
    {toc}
  </nav>
  <main id="content" class="lbody">
{body}
  </main>
</div>

<nav class="pager">
  {''.join(nav_items)}
</nav>

<script src="{site_root}/assets/mermaid.min.js"></script>
<script>
if (window.mermaid) {{
  mermaid.initialize({{ startOnLoad: true, securityLevel: 'loose', theme: 'default' }});
}}
function copyCode(btn) {{
  var pre = btn.closest('.codeblock').querySelector('pre');
  navigator.clipboard.writeText(pre.innerText).then(function () {{
    var o = btn.textContent; btn.textContent = '已复制';
    setTimeout(function () {{ btn.textContent = o; }}, 1500);
  }});
}}
</script>
</body>
</html>
"""


def render_subpage(md_text: str, *, title: str, day, site_root: str = "..") -> str:
    """渲染练习 / 图解这类附属页面。"""
    body, _blocks = render_body(md_text, nl2br=False)
    e = htmllib.escape
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="stylesheet" href="{site_root}/assets/style.css">
<link rel="stylesheet" href="{site_root}/assets/lesson.css">
</head>
<body class="lesson">
<header class="lhead">
  <a class="back" href="index.html">← 返回 Day {day.num} 正文</a>
  <h1>{e(title)}</h1>
</header>
<div class="lwrap"><main class="lbody">{body}</main></div>
<script src="{site_root}/assets/mermaid.min.js"></script>
<script>if (window.mermaid) {{ mermaid.initialize({{ startOnLoad: true, securityLevel: 'loose' }}); }}</script>
</body>
</html>
"""
