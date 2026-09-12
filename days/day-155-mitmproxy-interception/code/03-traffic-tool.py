#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 155 · 示例 03 —— 实战：自动化流量处理工具（拦截 + 脱敏落盘 + HTML 报表）
==============================================================================

三个使用姿势：

  1) 作为 mitmproxy Addon 运行（实时抓包落盘）：
     mitmdump -s 03-traffic-tool.py -p 8080 \
              --set traffic_out_dir=./traffic-out --set capture_domains=127.0.0.1

  2) 离线分析已有的 JSONL（不需要 mitmproxy）：
     python3 03-traffic-tool.py --report ./traffic-out/flows.jsonl

  3) 离线自检：
     python3 03-traffic-tool.py --self-test

产出：
  traffic-out/flows.jsonl      ← 一行一条流量（已脱敏）
  traffic-out/report.html      ← 可视化报表（内联 CSS，双击可看）
  traffic-out/report.md        ← 纯文本摘要

设计要点（也是和安全工程的一致性）：
  · 白名单：默认只抓 127.0.0.1 / localhost / example.com / httpbin.org
  · 脱敏：Authorization / Cookie / password / token 一律 ***
  · 上限：单条 body 最多存 8KB，防止 jsonl 爆炸
  · 只读不写上游：本工具默认不改任何请求/响应（要改请用示例 02）
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    from mitmproxy import ctx, http
    HAVE_MITM = True
except ImportError:
    ctx = None
    http = None
    HAVE_MITM = False

DEFAULT_ALLOWED = ["127.0.0.1", "localhost", "::1", "example.com", "httpbin.org"]
MAX_BODY_STORE = 8192                          # 单条 body 最多存 8KB

SENSITIVE_KEY_RE = re.compile(
    r"(authorization|cookie|set-cookie|password|passwd|pwd|token|secret|"
    r"api[-_]?key|session|csrf|otp|pin)", re.I)
# 文本里常见的凭据模式（防止 body 里明文泄露）
SENSITIVE_VALUE_RE = [
    re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+"),
    re.compile(r"((?:token|password|passwd|pwd|secret)\"?\s*[:=]\s*\"?)[^\"\s,&}]+", re.I),
    re.compile(r"(eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,})"),  # JWT
]


def redact_text(s: str) -> str:
    """把文本里的凭据替换成 ***。顺序很重要：先具体模式，再兜底。"""
    for rx in SENSITIVE_VALUE_RE:
        s = rx.sub(lambda m: (m.group(1) if m.lastindex else "") + "***", s)
    return s


def redact_headers(headers) -> dict:
    out = {}
    for k, v in headers.items():
        out[k] = "***" if SENSITIVE_KEY_RE.search(k) else redact_text(str(v))
    return out


def clip_body(data: bytes | None, limit: int = MAX_BODY_STORE) -> tuple:
    """截断 body，返回 (文本, 是否被截断)。"""
    if not data:
        return "", False
    if len(data) > limit:
        return redact_text(data[:limit].decode("utf-8", "replace")), True
    return redact_text(data.decode("utf-8", "replace")), False


# ═══════════════════════════════════════════════════════════════
class TrafficTool:
    def __init__(self):
        self.allowed = set(DEFAULT_ALLOWED)
        self.out_dir = Path("./traffic-out")
        self.jsonl = None
        self.fh = None
        self.n = 0
        self.t0 = time.time()
        self.pending = {}                     # flow.id → 起始时间

    # ── mitmproxy 选项 ──
    def load(self, loader):
        loader.add_option("traffic_out_dir", str, "./traffic-out",
                          "JSONL 与报表输出目录")
        loader.add_option("capture_domains", str, ",".join(DEFAULT_ALLOWED),
                          "逗号分隔的域名白名单")

    def configure(self, updated):
        if not HAVE_MITM:
            return
        if "traffic_out_dir" in updated:
            self.out_dir = Path(ctx.options.traffic_out_dir)
        if "capture_domains" in updated:
            self.allowed = {d.strip().lower()
                            for d in ctx.options.capture_domains.split(",") if d.strip()}

    def running(self):
        if not HAVE_MITM:
            return
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.fh = open(self.out_dir / "flows.jsonl", "a", encoding="utf-8")
        ctx.log.info(f"[traffic] 开始捕获，白名单={sorted(self.allowed)}，"
                     f"输出={self.out_dir/'flows.jsonl'}")

    # ── 请求 ──
    def request(self, flow: "http.HTTPFlow"):
        host = (flow.request.host or "").lower().split(":")[0]
        if host not in self.allowed:
            return
        self.pending[flow.id] = time.time()

    # ── 响应：落盘 ──
    def response(self, flow: "http.HTTPFlow"):
        host = (flow.request.host or "").lower().split(":")[0]
        if host not in self.allowed:
            return
        started = self.pending.pop(flow.id, time.time())
        r = flow.response
        req_body, req_clip = clip_body(flow.request.content)
        resp_body, resp_clip = clip_body(r.content if r else None)

        rec = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "flow_id": flow.id,
            "duration_ms": round((time.time() - started) * 1000, 1),
            "request": {
                "method": flow.request.method,
                "scheme": flow.request.scheme,
                "host": flow.request.host,
                "port": flow.request.port,
                "path": flow.request.path,
                "headers": redact_headers(flow.request.headers),
                "body": req_body,
                "body_truncated": req_clip,
            },
            "response": {
                "status": r.status_code if r else None,
                "reason": r.reason if r else None,
                "headers": redact_headers(r.headers) if r else {},
                "body": resp_body,
                "body_truncated": resp_clip,
                "size": len(r.content) if r else 0,
                "content_type": (r.headers.get("Content-Type", "") if r else ""),
            },
        }
        if self.fh:
            self.fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.fh.flush()
        self.n += 1
        if HAVE_MITM and self.n % 50 == 0:
            ctx.log.info(f"[traffic] 已捕获 {self.n} 条")

    def error(self, flow: "http.HTTPFlow"):
        host = (flow.request.host or "").lower().split(":")[0]
        if host in self.allowed and self.fh:
            self.fh.write(json.dumps({
                "ts": datetime.now().isoformat(timespec="milliseconds"),
                "flow_id": flow.id, "error": str(flow.error),
                "request": {"method": flow.request.method,
                            "host": flow.request.host,
                            "path": flow.request.path},
            }, ensure_ascii=False) + "\n")
            self.fh.flush()

    def done(self):
        if self.fh:
            self.fh.close()
            self.fh = None
        if HAVE_MITM:
            ctx.log.info(f"[traffic] 结束，共 {self.n} 条，"
                         f"运行 {time.time()-self.t0:.1f}s")


addons = [TrafficTool()]


# ═══════════════════════════════════════════════════════════════
# 离线报表生成（不需要 mitmproxy）
# ═══════════════════════════════════════════════════════════════
def load_jsonl(path: Path) -> list:
    recs = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                recs.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return recs


def summarize(recs: list) -> dict:
    status = Counter()
    hosts = Counter()
    paths = Counter()
    methods = Counter()
    slow = []
    errors = 0
    total_bytes = 0
    for r in recs:
        if "error" in r:
            errors += 1
            continue
        resp = r.get("response", {})
        status[str(resp.get("status"))] += 1
        hosts[r["request"].get("host", "?")] += 1
        paths[r["request"].get("path", "?").split("?")[0]] += 1
        methods[r["request"].get("method", "?")] += 1
        total_bytes += resp.get("size") or 0
        if r.get("duration_ms", 0) > 500:
            slow.append(r)
    return {
        "total": len(recs), "errors": errors,
        "status": status, "hosts": hosts, "paths": paths, "methods": methods,
        "slow": sorted(slow, key=lambda x: -x.get("duration_ms", 0))[:20],
        "total_bytes": total_bytes,
    }


def build_html(recs: list, s: dict) -> str:
    def esc(x):
        return html.escape(str(x))

    def rows(counter, limit=20):
        return "\n".join(
            f"<tr><td>{esc(k)}</td><td>{v}</td></tr>"
            for k, v in counter.most_common(limit))

    detail = []
    for r in recs[:200]:                       # 报表最多展示 200 条明细
        if "error" in r:
            detail.append(f"<tr><td colspan=5 class='err'>ERROR {esc(r['error'])} "
                          f"{esc(r.get('request', {}).get('path'))}</td></tr>")
            continue
        req, resp = r["request"], r["response"]
        detail.append(
            "<tr>"
            f"<td>{esc(r['ts'][11:23])}</td>"
            f"<td>{esc(req['method'])} {esc(req['host'])}{esc(req['path'])}</td>"
            f"<td>{esc(resp['status'])}</td>"
            f"<td>{esc(r.get('duration_ms'))}ms</td>"
            f"<td>{esc(resp.get('content_type',''))[:40]}</td>"
            "</tr>")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>Day155 流量分析报表</title>
<style>
 body{{font-family:-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
      margin:0;padding:24px;background:#f6f7f9;color:#222}}
 h1{{font-size:22px;margin:0 0 4px}} .sub{{color:#666;font-size:13px;margin-bottom:20px}}
 .cards{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}}
 .card{{background:#fff;border:1px solid #e3e6ea;border-radius:10px;padding:14px 18px;
       min-width:120px}}
 .card .k{{font-size:12px;color:#777}} .card .v{{font-size:22px;font-weight:600}}
 table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e3e6ea;
       border-radius:10px;overflow:hidden;margin-bottom:20px}}
 th,td{{padding:8px 10px;border-bottom:1px solid #eef1f4;font-size:13px;text-align:left}}
 th{{background:#fafbfc;color:#555;font-weight:600}}
 tr:hover td{{background:#fcfdff}}
 .err{{color:#c0392b}}
 .grid{{display:flex;gap:20px;flex-wrap:wrap}} .grid>div{{flex:1;min-width:260px}}
 code{{background:#eef1f4;padding:1px 5px;border-radius:4px}}
</style></head><body>
<h1>🌐 流量分析报表（Day 155 · mitmproxy）</h1>
<div class="sub">生成时间 {esc(datetime.now().isoformat(timespec='seconds'))}
 · 数据来源 JSONL · 所有凭据已脱敏</div>

<div class="cards">
 <div class="card"><div class="k">总请求</div><div class="v">{s['total']}</div></div>
 <div class="card"><div class="k">错误</div><div class="v">{s['errors']}</div></div>
 <div class="card"><div class="k">传输字节</div><div class="v">{s['total_bytes']:,}</div></div>
 <div class="card"><div class="k">慢请求(>500ms)</div><div class="v">{len(s['slow'])}</div></div>
 <div class="card"><div class="k">唯一主机</div><div class="v">{len(s['hosts'])}</div></div>
</div>

<div class="grid">
 <div><h3>状态码分布</h3><table><tr><th>状态</th><th>次数</th></tr>
   {rows(s['status'])}</table></div>
 <div><h3>主机分布</h3><table><tr><th>主机</th><th>次数</th></tr>
   {rows(s['hosts'])}</table></div>
</div>

<h3>Top 路径</h3>
<table><tr><th>路径</th><th>次数</th></tr>{rows(s['paths'])}</table>

<h3>慢请求 Top 20</h3>
<table><tr><th>耗时</th><th>方法</th><th>路径</th></tr>
{chr(10).join(f"<tr><td>{esc(r.get('duration_ms'))}ms</td><td>{esc(r['request']['method'])}</td><td>{esc(r['request']['path'])}</td></tr>" for r in s['slow']) or '<tr><td colspan=3>无</td></tr>'}
</table>

<h3>请求明细（最多 200 条）</h3>
<table><tr><th>时间</th><th>请求</th><th>状态</th><th>耗时</th><th>类型</th></tr>
{chr(10).join(detail) or '<tr><td colspan=5>无数据</td></tr>'}
</table>

<p style="color:#888;font-size:12px">
⚠️ 本报表中的 Authorization / Cookie / token 等字段已自动替换为 <code>***</code>。
分享报表前请再人工检查一遍 body 内容。
</p>
</body></html>"""


def build_markdown(recs: list, s: dict) -> str:
    lines = ["# Day155 流量分析摘要", "",
             f"- 总请求: {s['total']}",
             f"- 错误: {s['errors']}",
             f"- 传输字节: {s['total_bytes']:,}",
             f"- 慢请求(>500ms): {len(s['slow'])}", "",
             "## 状态码分布", "", "| 状态 | 次数 |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in s["status"].most_common()]
    lines += ["", "## Top 路径", "", "| 路径 | 次数 |", "|---|---|"]
    lines += [f"| `{k}` | {v} |" for k, v in s["paths"].most_common(20)]
    return "\n".join(lines)


def generate_reports(jsonl_path: Path, out_dir: Path | None = None) -> tuple:
    recs = load_jsonl(jsonl_path)
    s = summarize(recs)
    out_dir = out_dir or jsonl_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    hp = out_dir / "report.html"
    mp = out_dir / "report.md"
    hp.write_text(build_html(recs, s), encoding="utf-8")
    mp.write_text(build_markdown(recs, s), encoding="utf-8")
    return hp, mp, s


# ═══════════════════════════════════════════════════════════════
def _self_test(tmp: Path) -> int:
    print("=" * 70)
    print("离线自检：脱敏 + JSONL + 报表")
    print("=" * 70)

    # 1) 头脱敏
    h = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.aaa.bbb",
         "Cookie": "session=abc", "Content-Type": "application/json",
         "X-Api-Key": "sk-1234567890"}
    rh = redact_headers(h)
    assert rh["Authorization"] == "***" and rh["Cookie"] == "***"
    assert rh["X-Api-Key"] == "***"
    assert rh["Content-Type"] == "application/json"
    print("✅ redact_headers(): 敏感头全部脱敏，正常头保留")

    # 2) body 脱敏
    body = '{"user":"nina","password":"hunter2","token":"abc.def.ghi"}'
    rb = redact_text(body)
    assert "hunter2" not in rb and "abc.def.ghi" not in rb
    print(f"✅ redact_text(): {rb}")

    # 3) JWT 检测
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    assert jwt not in redact_text(f"token={jwt}")
    print("✅ redact_text(): JWT 被识别并替换")

    # 4) body 截断
    big = b"A" * (MAX_BODY_STORE + 100)
    text, clipped = clip_body(big)
    assert clipped is True and len(text) <= MAX_BODY_STORE
    print(f"✅ clip_body(): 超长 body 被截断到 {len(text)}B（标记 truncated=True）")

    # 5) JSONL → 报表
    tmp.mkdir(parents=True, exist_ok=True)
    jf = tmp / "flows.jsonl"
    samples = [
        {"ts": "2026-09-13T10:00:00.000", "duration_ms": 12.0,
         "request": {"method": "GET", "host": "example.com", "path": "/a",
                     "headers": redact_headers({"Cookie": "x=1", "Accept": "*/*"}),
                     "body": "", "body_truncated": False},
         "response": {"status": 200, "reason": "OK", "headers": {},
                      "body": '{"ok":1}', "body_truncated": False, "size": 8,
                      "content_type": "application/json"}},
        {"ts": "2026-09-13T10:00:01.000", "duration_ms": 900.0,
         "request": {"method": "POST", "host": "example.com", "path": "/login",
                     "headers": {}, "body": "user=a&password=***",
                     "body_truncated": False},
         "response": {"status": 302, "reason": "Found", "headers": {},
                      "body": "", "body_truncated": False, "size": 0,
                      "content_type": "text/html"}},
        {"ts": "2026-09-13T10:00:02.000", "flow_id": "f3",
         "error": "ConnectionRefused"},
    ]
    with open(jf, "w", encoding="utf-8") as f:
        for r in samples:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    hp, mp, s = generate_reports(jf, tmp)
    assert s["total"] == 3 and s["errors"] == 1
    assert s["status"]["200"] == 1 and s["status"]["302"] == 1
    assert len(s["slow"]) == 1, "应识别出 1 条慢请求"
    assert hp.exists() and mp.exists()
    html_text = hp.read_text(encoding="utf-8")
    assert "hunter2" not in html_text
    print(f"✅ generate_reports(): 解析 {s['total']} 条，"
          f"状态分布={dict(s['status'])}，慢请求={len(s['slow'])}")
    print(f"   报表: {hp}")
    print(f"         {mp}")

    # 6) 主机白名单逻辑
    tool = TrafficTool()
    assert "127.0.0.1" in tool.allowed
    assert "evil.example.org" not in tool.allowed
    print("✅ TrafficTool(): 默认白名单不含任意外部域名")

    print("\n全部离线自检通过。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Day155 自动化流量处理工具")
    ap.add_argument("--report", metavar="flows.jsonl", help="离线分析已有 JSONL 并生成报表")
    ap.add_argument("--out-dir", default=None, help="报表输出目录")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--tmp", default="/tmp/day155-selftest")
    args = ap.parse_args()

    if args.self_test:
        return _self_test(Path(args.tmp))

    if args.report:
        jf = Path(args.report)
        if not jf.exists():
            print(f"文件不存在: {jf}")
            return 1
        out = Path(args.out_dir) if args.out_dir else jf.parent
        hp, mp, s = generate_reports(jf, out)
        print(f"✅ 解析 {s['total']} 条 | 错误 {s['errors']} | "
              f"字节 {s['total_bytes']:,} | 慢请求 {len(s['slow'])}")
        print(f"   HTML: {hp}\n   MD  : {mp}")
        return 0

    if HAVE_MITM:
        print("请用 mitmdump 加载：")
        print("  mitmdump -s 03-traffic-tool.py -p 8080 --set traffic_out_dir=./traffic-out")
        return 0

    print("未检测到 mitmproxy。可用离线模式：")
    print("  python3 03-traffic-tool.py --self-test")
    print("  python3 03-traffic-tool.py --report ./traffic-out/flows.jsonl")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
