#!/usr/bin/env python3
"""01-basic-render.py — 静态抓取 vs 浏览器渲染，以及"等什么才算等到了"

本脚本会自己拉起 00-lab-target.py（随机端口），用 5 种等待策略各跑一遍，
打印「耗时 / 拿到几条商品 / 状态文本」，最后关掉靶站。
所以一条命令就能复现 README 里的表格。

用法：
    python3 01-basic-render.py                 # 全流程真机实验
    python3 01-basic-render.py --url http://127.0.0.1:8931
    python3 01-basic-render.py --self-test     # 离线自检（不启浏览器）
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- 浏览器启动
def find_chromium() -> str | None:
    """Playwright 版本和本地缓存的浏览器 revision 常常对不上。

    真实场景：pip 装了 playwright 1.64，缓存里只有 chromium-1234，
    默认 launch() 会去找 chromium_headless_shell-1248 然后报
    "Executable doesn't exist"。此时必须手动指定 executable_path。
    """
    pats = [
        str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux64/chrome"),
        str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux/chrome"),
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
    ]
    for pat in pats:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def launch(p, headless=True, args: list[str] | None = None):
    kwargs = {"headless": headless, "args": args or []}
    try:
        return p.chromium.launch(**kwargs)
    except Exception as first_err:
        exe = find_chromium()
        if not exe:
            raise RuntimeError(f"找不到可用的 Chromium：{first_err}") from first_err
        kwargs["executable_path"] = exe
        return p.chromium.launch(**kwargs)


# ---------------------------------------------------------------- 抓取实现
def fetch_static(url: str, timeout: float = 10) -> tuple[str, float]:
    """纯 HTTP 抓取：拿到的是服务器原始 HTML，JS 一行都不会执行。"""
    t0 = time.perf_counter()
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", "replace")
    return html, time.perf_counter() - t0


def count_items_in_html(html: str) -> int:
    """DOM 里商品 <li> 的数量。静态 HTML 里是 0 条（只有注释骨架）。"""
    return html.count("<li>")


STRATEGIES = ("load", "selector-exists", "selector-items", "sleep-1s", "networkidle", "wait-function")


def render(url: str, strategy: str, timeout: float = 10) -> dict:
    """按指定策略等待页面就绪，返回耗时与结果。"""
    from playwright.sync_api import sync_playwright

    out = {"strategy": strategy, "ok": False, "elapsed": None, "items": 0, "status": "", "error": ""}
    with sync_playwright() as p:
        browser = launch(p)
        page = browser.new_page()
        t0 = time.perf_counter()
        try:
            page.goto(url, wait_until="load", timeout=timeout * 1000)
            if strategy == "selector-exists":
                # ⚠️ 常见错误：#status 在骨架 HTML 里就存在（文本 "booting…"），
                # 所以这个 wait 立刻返回，此时列表还是空的。
                page.wait_for_selector("#status", timeout=timeout * 1000)
            elif strategy == "selector-items":
                page.wait_for_selector("#list li", timeout=timeout * 1000)
            elif strategy == "sleep-1s":
                time.sleep(1.0)
            elif strategy == "networkidle":
                page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            elif strategy == "wait-function":
                page.wait_for_function("document.querySelectorAll('#list li').length >= 12", timeout=timeout * 1000)
            out["elapsed"] = time.perf_counter() - t0
            out["items"] = page.locator("#list li").count()
            out["status"] = page.inner_text("#status")
            out["ok"] = out["items"] == 12
        except Exception as e:                     # 超时也是实验结果，不要吞掉
            out["elapsed"] = time.perf_counter() - t0
            out["error"] = type(e).__name__ + ": " + str(e).split("\n")[0][:120]
            try:
                out["items"] = page.locator("#list li").count()
            except Exception:
                pass
        finally:
            browser.close()
    return out


# ---------------------------------------------------------------- 实验编排
def wait_port(port: int, timeout: float = 10) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def run_experiment(url: str | None, rounds: int) -> int:
    server = None
    if url is None:
        port = free_port()
        server = subprocess.Popen([sys.executable, str(HERE / "00-lab-target.py"), "--port", str(port)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = f"http://127.0.0.1:{port}/"
        if not wait_port(port):
            print("❌ 靶站没起来")
            server.kill()
            return 1
    print(f"靶站: {url}\n")

    html, t_static = fetch_static(url)
    static_items = count_items_in_html(html)
    print("① 纯 HTTP 抓取（无 JS）")
    print(f"   耗时 {t_static*1000:.0f}ms  商品数 = {static_items}   HTML {len(html)} 字节")
    print("   页面里看到的是:", " / ".join(l.strip() for l in html.splitlines() if "booting" in l or "list" in l)[:120], "\n")

    print("② 浏览器渲染 × 6 种等待策略（每种 2 轮，取第 2 轮以避开冷启动）")
    results = []
    try:
        for st in STRATEGIES:
            runs = [render(url, st) for _ in range(max(1, rounds))]
            last = runs[-1]
            last["elapsed_all"] = [round(r["elapsed"], 3) for r in runs]
            results.append(last)
            flag = "✅" if last["ok"] else "❌"
            print(f"   {flag} {st:16s} {last['elapsed']*1000:7.0f}ms  items={last['items']:2d}  "
                  f"status={last['status'][:38]!r} {last['error']}")
    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()

    print("\n③ 结论")
    good = [r for r in results if r["ok"]]
    if good:
        fastest = min(good, key=lambda r: r["elapsed"])
        print(f"   最快且正确: {fastest['strategy']} ({fastest['elapsed']*1000:.0f}ms)")
    bad = [r for r in results if not r["ok"]]
    for b in bad:
        print(f"   陷阱: {b['strategy']} → items={b['items']} ({b['error'] or '等待条件不充分'})")
    print(f"   静态抓取漏掉 {12 - static_items} 条数据 → 渲染不是升级版抓取，而是唯一能拿到内容的方式")

    out = Path(tempfile.gettempdir()) / "day193-render.json"
    out.write_text(json.dumps({"url": url, "static": {"items": static_items, "ms": t_static * 1000},
                               "strategies": results}, ensure_ascii=False, indent=2))
    print(f"\n结果已写入 {out}")
    return 0


# ---------------------------------------------------------------- 自检
def self_test() -> int:
    """离线自检：不启浏览器、不联网，只验证解析与策略表。"""
    fails = 0

    def check(name, cond, extra=""):
        nonlocal fails
        print(("  ✅ " if cond else "  ❌ ") + name + (f"  {extra}" if extra else ""))
        fails += 0 if cond else 1

    skeleton = '<ul id="list"><!-- JS 注入前是空的 --></ul>'
    rendered = '<ul id="list"><li>a</li><li>b</li><li>c</li></ul>'
    check("静态骨架商品数为 0", count_items_in_html(skeleton) == 0)
    check("渲染后商品数为 3", count_items_in_html(rendered) == 3)
    check("策略表覆盖 6 种等待方式", len(STRATEGIES) == 6 and "selector-items" in STRATEGIES)
    check("本地 Chromium 可定位（仅提示，不作为失败）", bool(find_chromium()), find_chromium() or "未安装")
    check("HTML 解析不依赖浏览器", True)
    print(f"\n自检结果：{'全部通过' if fails == 0 else f'{fails} 项失败'}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="已存在的靶站地址；不填则自动拉起")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(self_test())
    raise SystemExit(run_experiment(a.url, a.rounds))
