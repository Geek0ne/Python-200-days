#!/usr/bin/env python3
"""02-pitfall-fingerprint.py — 无头浏览器指纹：改了什么、没改什么、怎么被认出来

实验设计：同一个靶站，用 4 种浏览器配置各访问一次，把客户端自报的指纹抓回来，
再用一套"检测规则"给每份指纹打分。重点不是"如何绕过"，而是**理解哪些字段是自洽的**：
只改 UA 不改 platform，等于穿了西装但脚上还是拖鞋。

用法：
    python3 02-pitfall-fingerprint.py            # 真机跑 4 个 profile
    python3 02-pitfall-fingerprint.py --self-test
"""
from __future__ import annotations

import argparse
import glob
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_chromium() -> str | None:
    for pat in [str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux64/chrome"),
                str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux/chrome"),
                "/usr/bin/chromium", "/usr/bin/google-chrome"]:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def launch(p, **kw):
    try:
        return p.chromium.launch(**kw)
    except Exception as e:
        exe = find_chromium()
        if not exe:
            raise
        kw["executable_path"] = exe
        return p.chromium.launch(**kw)


PROFILES = {
    "A 默认无头": {},
    "B 只改 UA/时区/语言": {
        "user_agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "viewport": {"width": 1920, "height": 1080},
        "device_scale_factor": 1,
    },
    "C B + 抹掉 webdriver": {
        "user_agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "viewport": {"width": 1920, "height": 1080},
        "device_scale_factor": 1,
        "init_script": True,
    },
    "D 无 GPU 的软件渲染": {"args": ["--disable-gpu", "--use-angle=swiftshader-webgl"]},
}

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
"""


def collect(url: str) -> list[dict]:
    from playwright.sync_api import sync_playwright

    rows = []
    with sync_playwright() as p:
        browser = launch(p)
        for name, opt in PROFILES.items():
            ctx_kw = {k: v for k, v in opt.items() if k not in ("init_script", "args")}
            ctx = browser.new_context(**ctx_kw)
            if opt.get("init_script"):
                ctx.add_init_script(STEALTH_JS)
            page = ctx.new_page()
            page.goto(url, wait_until="load", timeout=20000)
            page.wait_for_function("window.__fp !== undefined", timeout=20000)
            fp = page.evaluate("window.__fp")
            fp["profile"] = name
            fp["red_flags"] = judge(fp)
            fp["risk"] = len(fp["red_flags"])
            rows.append(fp)
            ctx.close()
        browser.close()
    return rows


def judge(fp: dict) -> list[str]:
    """一致性检测。真实风控系统就是这么打分的：单看一项都不致命，
    但"UA 说 Windows、platform 说 Linux"这类矛盾几乎无法用配置文件消除。"""
    flags = []
    ua = (fp.get("ua") or "").lower()
    platform = (fp.get("platform") or "").lower()
    renderer = (fp.get("webglRenderer") or "").lower()
    if fp.get("webdriver"):
        flags.append("navigator.webdriver=true")
    if "windows" in ua and "linux" in platform:
        flags.append("UA=Windows 但 platform=Linux")
    if "swiftshader" in renderer:
        flags.append("WebGL=SwiftShader 软件渲染")
    if fp.get("fontsCount", 0) <= 3:
        flags.append(f"字体仅 {fp.get('fontsCount')} 个（真实桌面机通常 >10）")
    if fp.get("timezone") in ("UTC", "Etc/UTC") and "windows" in ua:
        flags.append("声明 Windows 桌面却是 UTC 时区")
    if fp.get("hardwareConcurrency") and fp["hardwareConcurrency"] <= 2:
        flags.append(f"CPU 核数 {fp['hardwareConcurrency']}（容器典型值）")
    if fp.get("screen") in ("800x600", "1280x720") and "windows" in ua:
        flags.append(f"屏幕 {fp['screen']} 与桌面 UA 不符")
    return flags


def run(url: str | None) -> int:
    server = None
    if url is None:
        s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
        server = subprocess.Popen([sys.executable, str(HERE / "00-lab-target.py"), "--port", str(port)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = f"http://127.0.0.1:{port}/"
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.1)
    try:
        rows = collect(url)
    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()

    keys = ["webdriver", "timezone", "platform", "screen", "hardwareConcurrency",
            "webglRenderer", "canvas", "fontsCount", "risk"]
    print(f"{'字段':<20}" + "".join(f"{r['profile'][:14]:<16}" for r in rows))
    print("-" * (20 + 16 * len(rows)))
    for k in keys:
        line = f"{k:<20}"
        for r in rows:
            v = r.get(k)
            if isinstance(v, str):
                v = v.replace("ANGLE (", "").replace("Google Inc. ", "")[:14]
            line += f"{str(v):<16}"
        print(line)
    print("\n各配置被识别出的破绽：")
    for r in rows:
        print(f"  {r['profile']:<20} risk={r['risk']}  {r['red_flags'] or '无'}")
    out = Path(tempfile.gettempdir()) / "day193-fingerprint.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"\n结果已写入 {out}")
    return 0


def self_test() -> int:
    fails = 0

    def check(name, cond):
        nonlocal fails
        print(("  ✅ " if cond else "  ❌ ") + name)
        fails += 0 if cond else 1

    clean = {"ua": "Mozilla/5.0 (X11; Linux x86_64)", "platform": "Linux x86_64",
             "webdriver": False, "webglRenderer": "ANGLE (NVIDIA RTX 3060)", "fontsCount": 42,
             "timezone": "Asia/Shanghai", "hardwareConcurrency": 16, "screen": "2560x1440"}
    bad = {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "platform": "Linux x86_64",
           "webdriver": True, "webglRenderer": "ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device))",
           "fontsCount": 1, "timezone": "UTC", "hardwareConcurrency": 2, "screen": "800x600"}
    check("干净指纹 0 破绽", judge(clean) == [])
    flags = judge(bad)
    check("伪装指纹至少 5 个破绽", len(flags) >= 5, )
    check("能识别 UA 与 platform 矛盾", any("platform" in f for f in flags))
    check("能识别 SwiftShader", any("SwiftShader" in f for f in flags))
    check("能识别 webdriver 标记", any("webdriver" in f for f in flags))
    print(f"\n自检结果：{'全部通过' if fails == 0 else f'{fails} 项失败'}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    raise SystemExit(self_test() if a.self_test else run(a.url))
