#!/usr/bin/env python3
"""
生成 Learn-Python 静态站（B 版：首页 + 索引目录 + 进度）

用法：
    python3 site/build.py                  # 生成到 site/dist/
    python3 site/build.py --out /tmp/x    # 指定输出目录

设计原则：
  · 一切数据来自仓库真实文件，不写死任何数字
    - 天数/标题：扫描 days/ 目录 + 各日 README 的 H1
    - 阶段划分：解析根 README.md 的路线表格
    - 进度百分比：progress.json（缺失时回退为 days/ 目录数）
  · 零第三方依赖，标准库即可跑
  · 可重复执行（幂等），每天学习内容生成后重跑即可刷新站点
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DEFAULT = REPO / "site" / "dist"


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class Day:
    num: int
    slug: str                       # 目录名，如 day-166-系统监控-psutil
    title: str                      # 来自 README 的 H1
    url_slug: str                   # 站内链接用的安全 slug
    has_code: bool = False
    has_exercises: bool = False
    has_diagrams: bool = False
    readme_lines: int = 0
    code_files: int = 0
    phase: int = 0
    phase_name: str = ""


@dataclass
class Phase:
    num: int
    name: str
    start: int
    end: int
    status: str                     # done | doing | todo
    days: list[Day] = field(default_factory=list)

    @property
    def count(self) -> int:
        return self.end - self.start + 1


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------
ROADMAP_ROW = re.compile(
    r"^\|\s*\*\*Phase\s+(\d+)\*\*\s*\|\s*([^|]+?)\s*\|\s*Day\s*(\d+)\s*[–\-]\s*(\d+)\s*\|\s*([^|]+?)\s*\|"
)


def parse_phases(readme: Path) -> list[Phase]:
    """从根 README 的「🗺️ 学习路线」表格里解析出 12 个阶段。"""
    if not readme.exists():
        return []
    phases: list[Phase] = []
    for line in readme.read_text(encoding="utf-8").splitlines():
        m = ROADMAP_ROW.match(line.strip())
        if not m:
            continue
        num, name, start, end, status_raw = m.groups()
        name = name.strip()
        # 去掉名字里的 emoji 与装饰性符号
        name = re.sub(r"[🔥📦⏳✅\s]+", "", name).strip()
        s = status_raw.strip()
        if "已完成" in s:
            status = "done"
        elif "进行中" in s:
            status = "doing"
        else:
            status = "todo"
        phases.append(Phase(int(num), name, int(start), int(end), status))
    return phases


H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)


def parse_day(day_dir: Path) -> Day | None:
    """从一个日期目录里抽出标题与内容完整度。"""
    m = re.match(r"day-(\d+)-(.*)$", day_dir.name)
    if not m:
        return None
    num = int(m.group(1))

    title = m.group(2).replace("-", " ").strip()
    readme = day_dir / "README.md"
    if readme.exists():
        h1 = H1.search(readme.read_text(encoding="utf-8"))
        if h1:
            # 去掉 "Day 166 — " 前缀，只留主题名
            t = h1.group(1).strip()
            t = re.sub(r"^Day\s*\d+\s*[—–\-:：]\s*", "", t)
            title = t.strip()

    code_dir = day_dir / "code"
    return Day(
        num=num,
        slug=day_dir.name,
        title=title,
        url_slug=re.sub(r"[^a-z0-9\-]", "", day_dir.name.lower()) or f"day-{num}",
        has_code=code_dir.is_dir(),
        has_exercises=(day_dir / "exercises" / "checklist.md").exists(),
        has_diagrams=(day_dir / "diagrams" / "README.md").exists(),
        readme_lines=len(readme.read_text(encoding="utf-8").splitlines()) if readme.exists() else 0,
        code_files=len([p for p in code_dir.glob("*.py")]) if code_dir.is_dir() else 0,
    )


def load_days(days_root: Path) -> list[Day]:
    if not days_root.is_dir():
        return []
    out = [d for d in (parse_day(p) for p in sorted(days_root.iterdir()) if p.is_dir()) if d]
    out.sort(key=lambda d: d.num)
    return out


def load_progress(repo: Path, days: list[Day]) -> dict:
    p = repo / "progress.json"
    data: dict = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    current = int(data.get("current_day") or (days[-1].num if days else 0))
    total = int(data.get("total_days") or 200)
    return {
        "current_day": current,
        "total_days": total,
        "phase": data.get("phase", ""),
        "last_updated": data.get("last_updated", ""),
        "total_commits": data.get("total_commits"),
        "total_files": data.get("total_files"),
        "total_lines": data.get("total_code_lines"),
    }


def git_info(repo: Path) -> dict:
    def run(args: list[str]) -> str:
        try:
            return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                                  text=True, timeout=30).stdout.strip()
        except Exception:
            return ""
    remote = run(["remote", "get-url", "origin"])
    m = re.search(r"github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?$", remote)
    return {
        "owner": m.group(1) if m else "",
        "repo": m.group(2) if m else "",
        "head": run(["rev-parse", "--short", "HEAD"]),
    }


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------
def assign_phases(days: list[Day], phases: list[Phase]) -> None:
    for d in days:
        for p in phases:
            if p.start <= d.num <= p.end:
                d.phase = p.num
                d.phase_name = p.name
                p.days.append(d)
                break


CSS = """
:root {
  --bg: #0d1117; --panel: #161b22; --border: #30363d;
  --fg: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
  --done: #3fb950; --doing: #d29922; --todo: #484f58;
  --radius: 10px;
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #ffffff; --panel: #f6f8fa; --border: #d0d7de;
    --fg: #1f2328; --muted: #656d76; --accent: #0969da;
    --done: #1a7f37; --doing: #9a6700; --todo: #8c959f;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 15px/1.65 -apple-system, "Segoe UI", "Noto Sans SC", "PingFang SC",
        "Microsoft YaHei", Roboto, Helvetica, Arial, sans-serif;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.wrap { max-width: 1100px; margin: 0 auto; padding: 0 20px 64px; }

header.hero { padding: 56px 0 32px; border-bottom: 1px solid var(--border); margin-bottom: 32px; }
.hero h1 { font-size: 2.3rem; margin: 0 0 8px; letter-spacing: -.02em; }
.hero .sub { color: var(--muted); font-size: 1.05rem; margin: 0 0 24px; }
.badges { display: flex; flex-wrap: wrap; gap: 8px; }
.badge {
  font-size: .8rem; padding: 3px 10px; border-radius: 999px;
  border: 1px solid var(--border); color: var(--muted);
}
.badge.on { border-color: var(--done); color: var(--done); }

.bar { height: 10px; background: var(--todo); border-radius: 999px; overflow: hidden; margin: 20px 0 8px; }
.bar > i { display: block; height: 100%; background: linear-gradient(90deg, var(--accent), var(--done)); }

.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 28px 0 40px; }
.stat { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px; }
.stat b { display: block; font-size: 1.5rem; line-height: 1.3; }
.stat span { color: var(--muted); font-size: .82rem; }

h2 { font-size: 1.35rem; margin: 40px 0 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
h2 .muted { font-weight: 400; color: var(--muted); font-size: .9rem; }

.phase { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 18px; margin-bottom: 10px; }
.phase > summary { cursor: pointer; list-style: none; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.phase > summary::-webkit-details-marker { display: none; }
.phase .pname { font-weight: 600; flex: 1; min-width: 180px; }
.phase .prange { color: var(--muted); font-size: .85rem; font-variant-numeric: tabular-nums; }
.pill { font-size: .74rem; padding: 2px 9px; border-radius: 999px; border: 1px solid currentColor; }
.pill.done { color: var(--done); } .pill.doing { color: var(--doing); } .pill.todo { color: var(--todo); }

.days { list-style: none; margin: 14px 0 0; padding: 0; display: grid; gap: 1px;
        background: var(--border); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.days li { background: var(--panel); padding: 9px 14px; display: flex; align-items: center; gap: 12px; }
.days .dnum { color: var(--muted); font-variant-numeric: tabular-nums; min-width: 62px; font-size: .86rem; }
.days .dtitle { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.days .tags { display: flex; gap: 5px; }
.tag { font-size: .68rem; color: var(--muted); border: 1px solid var(--border); border-radius: 4px; padding: 1px 5px; }

#q { width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border);
     background: var(--panel); color: var(--fg); font-size: .95rem; margin-bottom: 14px; }
#count { color: var(--muted); font-size: .85rem; margin: -6px 0 14px; }

footer { margin-top: 56px; padding-top: 20px; border-top: 1px solid var(--border);
         color: var(--muted); font-size: .85rem; display: flex; gap: 16px; flex-wrap: wrap; }
code { background: var(--panel); border: 1px solid var(--border); border-radius: 4px; padding: 1px 5px; font-size: .88em; }
"""


def render_index_html(days: list[Day], phases: list[Phase], prog: dict, info: dict) -> str:
    done = prog["current_day"]
    total = prog["total_days"]
    pct = (done / total * 100) if total else 0
    e = html.escape

    badges = [f'<span class="badge on">已更新 Day {done}</span>']
    if info.get("owner") and info.get("repo"):
        badges.append(f'<span class="badge">{e(info["owner"])}/{e(info["repo"])}</span>')
    if info.get("head"):
        badges.append(f'<span class="badge">commit {e(info["head"])}</span>')
    if prog.get("last_updated"):
        badges.append(f'<span class="badge">{e(prog["last_updated"])}</span>')

    stats = [
        (f"{done} / {total}", "已学天数"),
        (f"{pct:.1f}%", "完成度"),
        (len(days), "已生成课程目录"),
        (sum(1 for d in days if d.has_code), "含可运行代码"),
        (sum(d.code_files for d in days), "代码文件总数"),
    ]
    if prog.get("total_commits"):
        stats.append((f"{prog['total_commits']:,}", "累计提交"))
    stat_html = "".join(
        f'<div class="stat"><b>{e(str(v))}</b><span>{e(lbl)}</span></div>' for v, lbl in stats
    )

    # 阶段折叠块
    ph_html = []
    for p in phases:
        cls = {"done": "done", "doing": "doing", "todo": "todo"}[p.status]
        label = {"done": "已完成", "doing": "进行中", "todo": "未开始"}[p.status]
        open_attr = " open" if p.status == "doing" else ""
        if p.days:
            lis = "".join(
                f'<li data-t="{e((d.title + " " + d.slug).lower())}">'
                f'<span class="dnum">Day {d.num}</span>'
                f'<span class="dtitle">{e(d.title)}</span>'
                f'<span class="tags">'
                + ('<span class="tag">code</span>' if d.has_code else "")
                + ('<span class="tag">ex</span>' if d.has_exercises else "")
                + ('<span class="tag">diag</span>' if d.has_diagrams else "")
                + '</span></li>'
                for d in p.days
            )
        else:
            lis = '<li><span class="dnum">—</span><span class="dtitle muted">尚未生成</span><span></span></li>'
        ph_html.append(
            f'<details class="phase"{open_attr}>'
            f'<summary><span class="pname">Phase {p.num} · {e(p.name)}</span>'
            f'<span class="prange">Day {p.start:03d}–{p.end:03d} · {len(p.days)}/{p.count}</span>'
            f'<span class="pill {cls}">{label}</span></summary>'
            f'<ul class="days">{lis}</ul></details>'
        )

    repo_url = f"https://github.com/{info['owner']}/{info['repo']}" if info.get("owner") else "#"
    phase_name = prog.get("phase") or "—"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Python 200 天 · {e(prog.get('phase') or '学习教程')}</title>
<meta name="description" content="200 天 Python 从入门到生产实践的完整教程，{done} 天已完成，含可运行代码、图解与练习。">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="wrap">

<header class="hero">
  <h1>Python 200 天</h1>
  <p class="sub">从语法基础到生产级实战 —— 每天一课，每课都有真机跑过的代码、图解与练习。</p>
  <div class="badges">{''.join(badges)}</div>
  <div class="bar"><i style="width:{pct:.2f}%"></i></div>
  <p class="sub" style="margin:0">已完成 <b>{done}</b> / {total} 天（{pct:.1f}%）· 当前阶段：{e(phase_name)}</p>
</header>

<div class="stats">{stat_html}</div>

<h2>全部课程 <span class="muted">按阶段分组</span></h2>
<input id="q" type="search" placeholder="输入天数或主题过滤，例如 170、监控、fabric…" autocomplete="off">
<p id="count"></p>
{''.join(ph_html)}

<footer>
  <span>本站由 <code>site/build.py</code> 依据仓库真实数据生成</span>
  <span>·</span>
  <a href="{repo_url}" rel="noopener">GitHub 源码仓库</a>
  <span>·</span>
  <span>课程正文见各日 README（本版暂为索引页）</span>
</footer>

</div>
<script>
(function () {{
  var q = document.getElementById('q');
  var count = document.getElementById('count');
  var items = [].slice.call(document.querySelectorAll('.days li[data-t]'));
  function apply() {{
    var v = q.value.trim().toLowerCase();
    var hit = 0;
    items.forEach(function (li) {{
      var show = !v || li.dataset.t.indexOf(v) !== -1;
      li.style.display = show ? '' : 'none';
      if (show) hit++;
    }});
    // 命中为 0 的阶段自动折叠，避免大片空白
    [].slice.call(document.querySelectorAll('details.phase')).forEach(function (d) {{
      var vis = [].slice.call(d.querySelectorAll('.days li[data-t]'))
        .some(function (li) {{ return li.style.display !== 'none'; }});
      d.style.display = (v && !vis) ? 'none' : '';
    }});
    count.textContent = v ? ('匹配 ' + hit + ' 门课程') : ('共 ' + items.length + ' 门课程');
  }}
  q.addEventListener('input', apply);
  apply();
}})();
</script>
</body>
</html>
"""


def build(repo: Path, out: Path) -> dict:
    days = load_days(repo / "days")
    phases = parse_phases(repo / "README.md")
    assign_phases(days, phases)
    prog = load_progress(repo, days)
    info = git_info(repo)

    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "assets" / "style.css").write_text(CSS, encoding="utf-8")
    (out / "index.html").write_text(render_index_html(days, phases, prog, info), encoding="utf-8")

    # 便于机器读取的清单
    manifest = {
        "generated_for_day": prog["current_day"],
        "total_days": prog["total_days"],
        "phase": prog.get("phase", ""),
        "days": [
            {"num": d.num, "title": d.title, "slug": d.slug,
             "code": d.has_code, "exercises": d.has_exercises, "diagrams": d.has_diagrams}
            for d in days
        ],
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 404 页
    (out / "404.html").write_text(
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>404</title><style>body{font-family:sans-serif;background:#0d1117;color:#e6edf3;"
        "display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}"
        "a{color:#58a6ff}</style></head><body><div><h1>404</h1>"
        "<p>这一课还没写，或者地址不对。</p><p><a href='/'>回到首页</a></p></div></body></html>",
        encoding="utf-8",
    )
    return prog


def main() -> int:
    ap = argparse.ArgumentParser(description="生成 Learn-Python 静态站")
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    prog = build(REPO, out)
    print(f"✅ 站点已生成：{out}")
    print(f"   Day {prog['current_day']}/{prog['total_days']} · {prog.get('phase','')}")
    for f in sorted(out.rglob("*")):
        if f.is_file():
            print(f"   {f.relative_to(out)}  ({f.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
