#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 155 · 示例 03 —— 实战：自动化流量处理工具（拦截 + 脱敏落盘 + HTML 报表）
==============================================================================

四个使用姿势
------------
  1) 作为 mitmproxy Addon 运行（实时抓包落盘）：
     pip install mitmproxy
     mitmdump -s 03-traffic-tool.py -p 8080 \
              --set traffic_out_dir=./traffic-out --set capture_domains=127.0.0.1

  2) 本地实验台运行（不需要 mitmproxy；仓库自带，纯标准库）：
     python3 00-local-lab.py --addon 03-traffic-tool.py \
              --set traffic_out_dir=/tmp/traffic-out --set capture_domains=127.0.0.1

  3) 离线分析已有的 JSONL（不需要 mitmproxy）：
     python3 03-traffic-tool.py --report ./traffic-out/flows.jsonl

  4) 离线自检（不联网、不装第三方库；产物全在临时目录）：
     python3 03-traffic-tool.py --self-test

产出：
  <out_dir>/flows.jsonl        ← 一行一条流量（已脱敏）
  <out_dir>/report.html        ← 可视化报表（内联 CSS，双击可看）
  <out_dir>/report.md          ← 纯文本摘要

设计要点（也是和安全工程的一致性）：
  · 白名单：默认只抓 127.0.0.1 / localhost / example.com / httpbin.org
  · 脱敏：Authorization / Cookie / password / token 一律 ***
  · 上限：单条 body 最多存 8KB，防止 jsonl 爆炸
  · 只读不写上游：本工具默认不改任何请求/响应（要改请用示例 02）
  · 默认输出目录是**系统临时目录**（`<tmp>/day155-traffic-out`），
    不指定 `traffic_out_dir` 时不会在你当前工作目录里创建 `./traffic-out`——
    演示产物不应该污染 git 工作树。
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import tempfile
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
    """把文本里的凭据替换成 ***。顺序很重要：先具体模式，再兜底。

    ⚠️ 为什么"脱敏"这种事必须做成函数并写测试？
    → 脱敏失败（漏打码）是不可见的：日志"看着正常"，但凭据已经落盘。
      只有测试能锁住"某几种已知形态必须被打码"。
    ⚠️ 边界：这里只处理**已知形态**（Bearer / key=value / JWT）。
      手机号、身份证、自定义 token 形式需要按业务补充正则。
    """
    for rx in SENSITIVE_VALUE_RE:
        s = rx.sub(lambda m: (m.group(1) if m.lastindex else "") + "***", s)
    return s


def redact_headers(headers) -> dict:
    """按头名脱敏，得到普通 dict（可 JSON 序列化）。"""
    out = {}
    for k, v in headers.items():
        out[k] = "***" if SENSITIVE_KEY_RE.search(k) else redact_text(str(v))
    return out


def clip_body(data: bytes | None, limit: int = MAX_BODY_STORE):
    """截断 body，返回 (文本, 是否被截断)。

    ⚠️ 解码用 errors="replace"：二进制内容（图片、protobuf）不会抛异常，
       只会出现替换字符。落盘工具**不能**因为一条畸形响应就崩掉。
    """
    if not data:
        return "", False
    if len(data) > limit:
        return redact_text(data[:limit].decode("utf-8", "replace")), True
    return redact_text(data.decode("utf-8", "replace")), False


# ═══════════════════════════════════════════════════════════════
class TrafficTool:
    def __init__(self):
        self.allowed = set(DEFAULT_ALLOWED)
        # 默认写到系统临时目录：即使忘了指定 traffic_out_dir，也不会污染工作树
        self.out_dir = Path(tempfile.gettempdir()) / "day155-traffic-out"
        self.jsonl = None
        self.fh = None
        self.n = 0
        self.t0 = time.time()
        self.pending = {}                     # flow.id → 起始时间

    # ── mitmproxy 选项 ──
    def load(self, loader):
        loader.add_option("traffic_out_dir", str, str(self.out_dir),
                          "JSONL 与报表输出目录（默认在系统临时目录）")
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
        # ⚠️ 用 "a" 追加：mitmdump 重启不应丢掉上一次的流量；
        #    代价是文件会越来越大 → 生产环境要加轮转（RotatingFileHandler）。
        self.fh = open(self.out_dir / "flows.jsonl", "a", encoding="utf-8")
        ctx.log.info(f"[traffic] 开始捕获，白名单={sorted(self.allowed)}，"
                     f"输出={self.out_dir / 'flows.jsonl'}")

    # ── 请求 ──
    def request(self, flow: "http.HTTPFlow"):
        host = (flow.request.host or "").lower().split(":")[0]
        if host not in self.allowed:
            return
        # 记开始时间：response 事件里算 duration（mitmproxy 不直接给耗时）
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
            self.fh.flush()                   # 崩溃时也不丢已抓到的流量
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
                         f"运行 {time.time() - self.t0:.1f}s")


addons = [TrafficTool()]


# ═══════════════════════════════════════════════════════════════
# 离线报表生成（不需要 mitmproxy）
# ═══════════════════════════════════════════════════════════════
def load_jsonl(path: Path) -> list:
    """读 JSONL：坏行跳过而不是崩溃（日志文件常有被截断的最后一行）。"""
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
# 离线自检
# ═══════════════════════════════════════════════════════════════
class _Checker:
    def __init__(self):
        self.fail = 0
        self.n = 0

    def eq(self, name, actual, expected):
        self.n += 1
        if actual == expected:
            print(f"✅ {name}: {actual!r}")
        else:
            self.fail += 1
            print(f"❌ {name}\n     实际值: {actual!r}\n     期望值: {expected!r}")

    def ok(self, name, cond, detail=""):
        self.n += 1
        if cond:
            print(f"✅ {name}{(' — ' + detail) if detail else ''}")
        else:
            self.fail += 1
            print(f"❌ {name}{(' — ' + detail) if detail else ''}")

    def done(self) -> int:
        print("-" * 70)
        if self.fail:
            print(f"❌ {self.fail}/{self.n} 项断言失败")
            return 1
        print(f"✅ 全部 {self.n} 项断言通过")
        print("SELF-TEST OK")
        return 0


class _H(dict):
    """鸭子类型 headers（够 TrafficTool 的 redact_headers 用）。"""

    def items(self):
        return dict.items(self)


class _Req:
    def __init__(self, method="GET", host="127.0.0.1", path="/api/users",
                 scheme="http", port=8080, headers=None, content=b""):
        self.method = method
        self.host = host
        self.path = path
        self.scheme = scheme
        self.port = port
        self.headers = _H(headers or {})
        self.content = content

    def json(self):
        return json.loads(self.content.decode())


class _Resp:
    def __init__(self, status_code=200, reason="OK", headers=None, content=b""):
        self.status_code = status_code
        self.reason = reason
        self.headers = _H(headers or {"Content-Type": "application/json"})
        self.content = content


class _Flow:
    def __init__(self, req=None, resp=None, fid="flow-1"):
        self.id = fid
        self.request = req or _Req()
        self.response = resp
        self.metadata = {}
        self.error = None


def _self_test() -> int:
    c = _Checker()
    print("=" * 70)
    print("离线自检：脱敏 + JSONL 落盘 + 报表（不联网，产物在临时目录）")
    print("=" * 70)
    print(f"mitmproxy 可用: {HAVE_MITM}"
          f"{'' if HAVE_MITM else '（没装也能跑：本文件的事件逻辑用鸭子类型对象驱动）'}")

    # ── 1. 头脱敏 ──
    h = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.aaa.bbb",
         "Cookie": "session=abc", "Content-Type": "application/json",
         "X-Api-Key": "sk-1234567890", "Set-Cookie": "a=1"}
    rh = redact_headers(h)
    c.eq("redact_headers: Authorization", rh["Authorization"], "***")
    c.eq("redact_headers: Cookie", rh["Cookie"], "***")
    c.eq("redact_headers: X-Api-Key", rh["X-Api-Key"], "***")
    c.eq("redact_headers: Set-Cookie", rh["Set-Cookie"], "***")
    c.eq("redact_headers: 正常头保留", rh["Content-Type"], "application/json")
    c.eq("redact_headers: 返回普通 dict（可 JSON 序列化）",
         json.loads(json.dumps(rh))["Cookie"], "***")

    # ── 2. body 脱敏（三种已知形态）──
    body = '{"user":"nina","password":"hunter2","token":"abc.def.ghi"}'
    rb = redact_text(body)
    c.ok("redact_text: password 值被打码", "hunter2" not in rb, rb)
    c.ok("redact_text: token 值被打码", "abc.def.ghi" not in rb)
    c.ok("redact_text: 非敏感字段保留", "nina" in rb)
    c.eq("redact_text: Bearer 保留前缀",
         redact_text("Authorization: Bearer abc123XYZ"), "Authorization: Bearer ***")
    jwt = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
           "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
           "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")
    c.ok("redact_text: JWT 被整段替换",
         jwt not in redact_text(f"token={jwt}"), redact_text(f"token={jwt}"))
    c.eq("redact_text: 无敏感内容时原样返回", redact_text("hello world"), "hello world")

    # ── 3. body 截断边界 ──
    text, clipped = clip_body(b"A" * (MAX_BODY_STORE + 100))
    c.eq("clip_body: 超长被标记截断", clipped, True)
    c.eq("clip_body: 截断到上限", len(text), MAX_BODY_STORE)
    text2, clipped2 = clip_body(b"B" * MAX_BODY_STORE)
    c.eq("clip_body: 恰好等于上限不截断", clipped2, False)
    c.eq("clip_body: 恰好等于上限长度", len(text2), MAX_BODY_STORE)
    c.eq("clip_body: 空 body", clip_body(None), ("", False))
    c.eq("clip_body: 非法字节不抛异常（replace 兜底）",
         clip_body(b"\xff\xfe")[0], "\ufffd\ufffd")

    # ── 4. 事件回调 → JSONL 落盘（真的写文件，但写到临时目录）──
    tmp = Path(tempfile.mkdtemp(prefix="day155-selftest-"))
    tool = TrafficTool()
    tool.out_dir = tmp
    tool.allowed = {"127.0.0.1"}
    jl = tmp / "flows.jsonl"
    tool.fh = open(jl, "w", encoding="utf-8")

    f1 = _Flow(req=_Req(path="/api/users", headers={"Cookie": "sid=secret-value"}),
               resp=_Resp(200, "OK", {"Content-Type": "application/json"},
                          b'{"ok":1}'), fid="f1")
    f2 = _Flow(req=_Req(method="POST", path="/login",
                        headers={"Authorization": "Bearer abcdefgh"},
                        content=b'{"password":"hunter2"}'),
               resp=_Resp(302, "Found", {"Location": "/login?next=/admin"},
                          b""), fid="f2")
    f3 = _Flow(req=_Req(host="evil.example.org", path="/x"), fid="f3")
    tool.request(f1)
    tool.response(f1)
    tool.request(f2)
    tool.response(f2)
    tool.request(f3)          # 不在白名单 → 不记录
    tool.response(f3)
    c.eq("抓包: 只记录白名单内的流量", tool.n, 2)
    c.eq("抓包: pending 已清空", tool.pending, {})

    f_err = _Flow(req=_Req(path="/timeout"), fid="f4")
    f_err.error = "ConnectionTimeout"
    tool.error(f_err)
    tool.done()               # 关闭文件
    c.eq("done(): 文件句柄已关闭", tool.fh, None)

    lines = [json.loads(x) for x in jl.read_text(encoding="utf-8").splitlines() if x]
    c.eq("JSONL: 共 3 行（2 条流量 + 1 条错误）", len(lines), 3)
    c.eq("JSONL: 第一条路径", lines[0]["request"]["path"], "/api/users")
    c.eq("JSONL: Cookie 已脱敏", lines[0]["request"]["headers"]["Cookie"], "***")
    c.eq("JSONL: POST 方法被记录", lines[1]["request"]["method"], "POST")
    c.eq("JSONL: Authorization 已脱敏",
         lines[1]["request"]["headers"]["Authorization"], "***")
    c.ok("JSONL: body 里的明文密码已脱敏",
         "hunter2" not in lines[1]["request"]["body"], lines[1]["request"]["body"])
    c.eq("JSONL: 响应状态码", lines[1]["response"]["status"], 302)
    c.eq("JSONL: 错误记录格式", lines[2]["error"], "ConnectionTimeout")
    c.ok("JSONL: 整份文件里没有明文凭据",
         "hunter2" not in jl.read_text(encoding="utf-8")
         and "abcdefgh" not in jl.read_text(encoding="utf-8"))

    # ── 5. 报表生成 ──
    hp, mp, s = generate_reports(jl, tmp)
    c.eq("报表: 总条数", s["total"], 3)
    c.eq("报表: 错误条数", s["errors"], 1)
    c.eq("报表: 200 计数", s["status"]["200"], 1)
    c.eq("报表: 302 计数", s["status"]["302"], 1)
    c.eq("报表: 方法统计", dict(s["methods"]), {"GET": 1, "POST": 1})
    c.ok("报表: HTML 已落盘", hp.exists())
    c.ok("报表: Markdown 已落盘", mp.exists())
    html_text = hp.read_text(encoding="utf-8")
    md_text = mp.read_text(encoding="utf-8")
    c.ok("报表: HTML 里没有明文凭据", "hunter2" not in html_text)
    c.ok("报表: Markdown 里没有明文凭据", "hunter2" not in md_text)
    c.ok("报表: Markdown 含状态码分布小节", "状态码分布" in md_text)
    c.ok("报表: HTML 含脱敏提示", "已自动替换" in html_text)

    # ── 6. 报表 XSS 防护：把 `<script>` 写进路径，生成的 HTML 必须被转义 ──
    evil = [{"ts": "2026-09-19T10:00:00.000", "flow_id": "x", "duration_ms": 1.0,
             "request": {"method": "GET", "host": "127.0.0.1",
                         "path": "/<script>alert(1)</script>",
                         "headers": {}, "body": "", "body_truncated": False},
             "response": {"status": 200, "reason": "OK", "headers": {},
                          "body": "", "body_truncated": False, "size": 0,
                          "content_type": "text/html"}}]
    evil_html = build_html(evil, summarize(evil))
    c.ok("报表安全: 路径里的 <script> 被转义（不会在浏览器执行）",
         "<script>alert(1)</script>" not in evil_html
         and "&lt;script&gt;" in evil_html)

    # ── 7. 慢请求与字节统计 ──
    slow_recs = [dict(x) for x in [lines[0]]]
    slow_recs[0]["duration_ms"] = 900.0
    s2 = summarize(slow_recs)
    c.eq("报表: 慢请求阈值 (>500ms)", len(s2["slow"]), 1)
    c.eq("报表: 字节统计取 response.size", s2["total_bytes"], 8)

    # ── 8. 白名单与只读保证 ──
    t2 = TrafficTool()
    c.ok("默认白名单包含 127.0.0.1", "127.0.0.1" in t2.allowed)
    c.ok("默认输出目录是绝对路径（在系统临时目录，不污染工作树）",
         t2.out_dir.is_absolute() and "day155-traffic-out" in str(t2.out_dir),
         str(t2.out_dir))
    c.ok("默认白名单不含任意外部域名", "evil.example.org" not in t2.allowed)
    f5 = _Flow(req=_Req(), resp=_Resp(content=b'{"ok":1}'))
    snapshot = (f5.request.path, dict(f5.request.headers), f5.request.content,
                f5.response.status_code, f5.response.content, f5.response.headers)
    tool2 = TrafficTool()
    tool2.out_dir = tmp
    tool2.fh = open(tmp / "flows2.jsonl", "w", encoding="utf-8")
    tool2.request(f5)
    tool2.response(f5)
    tool2.done()
    after = (f5.request.path, dict(f5.request.headers), f5.request.content,
             f5.response.status_code, f5.response.content, f5.response.headers)
    c.eq("只读保证: 本工具不改动请求/响应", after, snapshot)

    # ── 9. 模块契约 ──
    c.eq("模块级 addons 列表", isinstance(addons, list), True)
    c.ok("addons[0] 是 TrafficTool", isinstance(addons[0], TrafficTool))
    c.ok("提供 load/configure/running/request/response/error/done 回调",
         all(hasattr(TrafficTool, mm) for mm in
             ("load", "configure", "running", "request", "response", "error", "done")))

    print(f"\n本次自检产物（临时目录，不会污染仓库）：{tmp}")
    print("  flows.jsonl / report.html / report.md")
    return c.done()


def main() -> int:
    ap = argparse.ArgumentParser(description="Day155 自动化流量处理工具")
    ap.add_argument("--report", metavar="flows.jsonl", help="离线分析已有 JSONL 并生成报表")
    ap.add_argument("--out-dir", default=None, help="报表输出目录")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        # 自检产物一律落在系统临时目录（tempfile 会自动选 /tmp 之类的位置）
        return _self_test()

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
    print("或使用仓库自带的本地实验台（纯标准库）：")
    print("  python3 00-local-lab.py --addon 03-traffic-tool.py "
          "--set traffic_out_dir=/tmp/traffic-out")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
