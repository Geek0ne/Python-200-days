"""
Day 126 - Requests 深入：Session 会话与 Cookie 管理
01-session-cookies.py

演示 Session 的核心功能和 Cookie 管理
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from http.cookiejar import MozillaCookieJar
from requests.cookies import RequestsCookieJar
import json
import time
from datetime import datetime


# ============================================================
# 1. Session 基础用法
# ============================================================

def demo_basic_session():
    """演示 Session 与独立请求的区别"""
    print("=" * 60)
    print("🔧 1. Session 基础用法")
    print("=" * 60)

    # ❌ 独立请求：无法保持会话
    print("\n--- 独立请求 (无法保持 Cookie) ---")
    resp1 = requests.get("https://httpbin.org/cookies/set/token/abc123")
    print(f"第一次请求状态: {resp1.status_code}")

    resp2 = requests.get("https://httpbin.org/cookies")
    cookies = resp2.json().get("cookies", {})
    print(f"第二次请求携带的 Cookie: {cookies}")
    print("结论: 没有 Cookie！独立请求不共享状态")

    # ✅ Session：自动管理 Cookie
    print("\n--- Session (自动保持 Cookie) ---")
    session = requests.Session()
    resp1 = session.get("https://httpbin.org/cookies/set/token/abc123")
    print(f"第一次请求状态: {resp1.status_code}")

    resp2 = session.get("https://httpbin.org/cookies")
    cookies = resp2.json().get("cookies", {})
    print(f"第二次请求携带的 Cookie: {cookies}")
    print("结论: Cookie 自动携带！Session 保持了会话状态")


# ============================================================
# 2. Session 高级配置
# ============================================================

def demo_session_config():
    """演示 Session 的高级配置"""
    print("\n" + "=" * 60)
    print("🔧 2. Session 高级配置")
    print("=" * 60)

    session = requests.Session()

    # 设置公共请求头
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "X-Custom-Header": "my-value",
    })

    # 设置认证信息
    session.auth = ("user", "pass")

    # 查看配置
    print(f"\n公共 Headers: {dict(session.headers)}")
    print(f"认证信息: {session.auth}")

    # 发送请求，公共 headers 会自动附加
    resp = session.get("https://httpbin.org/headers")
    server_headers = resp.json().get("headers", {})
    print(f"\n服务器收到的 Headers:")
    for key, value in server_headers.items():
        print(f"  {key}: {value}")


# ============================================================
# 3. Cookie 持久化
# ============================================================

def demo_cookie_persistence():
    """演示 Cookie 的保存和加载"""
    print("\n" + "=" * 60)
    print("🔧 3. Cookie 持久化")
    print("=" * 60)

    # 创建 Session 并使用 MozillaCookieJar
    session = requests.Session()
    session.cookies = MozillaCookieJar("demo_cookies.txt")

    # 发送请求获取 Cookie
    resp = session.get("https://httpbin.org/cookies/set/persistence/test123")
    print(f"获取 Cookie: {dict(session.cookies)}")

    # 保存 Cookie 到文件
    session.cookies.save(ignore_discard=True, ignore_expires=True)
    print("✅ Cookie 已保存到 demo_cookies.txt")

    # 重新加载 Cookie
    new_session = requests.Session()
    new_session.cookies = MozillaCookieJar("demo_cookies.txt")
    new_session.cookies.load(ignore_discard=True, ignore_expires=True)
    print(f"重新加载的 Cookie: {dict(new_session.cookies)}")

    # 验证 Cookie 可用
    resp = new_session.get("https://httpbin.org/cookies")
    print(f"验证 Cookie: {resp.json().get('cookies', {})}")


# ============================================================
# 4. Cookie 手动操作
# ============================================================

def demo_manual_cookies():
    """演示手动管理 Cookie"""
    print("\n" + "=" * 60)
    print("🔧 4. Cookie 手动操作")
    print("=" * 60)

    session = requests.Session()

    # 手动设置 Cookie
    session.cookies.set(
        "user_id",
        "12345",
        domain=".httpbin.org",
        path="/",
    )
    session.cookies.set(
        "session_token",
        "xyz789",
        domain=".httpbin.org",
        path="/",
    )

    # 查看所有 Cookie
    print(f"\n手动设置的 Cookie:")
    for cookie in session.cookies:
        print(f"  {cookie.name}={cookie.value} (domain={cookie.domain})")

    # 发送请求验证
    resp = session.get("https://httpbin.org/cookies")
    print(f"\n服务器收到的 Cookie: {resp.json().get('cookies', {})}")

    # 删除 Cookie
    del session.cookies["user_id"]
    print(f"\n删除 user_id 后: {[c.name for c in session.cookies]}")


# ============================================================
# 5. 主流程
# ============================================================

def main():
    print("🚀 Day 126 - Requests 深入：Session 会话与 Cookie 管理\n")

    try:
        demo_basic_session()
    except Exception as e:
        print(f"⚠️ 网络请求失败: {e}")

    try:
        demo_session_config()
    except Exception as e:
        print(f"⚠️ 网络请求失败: {e}")

    try:
        demo_cookie_persistence()
    except Exception as e:
        print(f"⚠️ 网络请求失败: {e}")

    try:
        demo_manual_cookies()
    except Exception as e:
        print(f"⚠️ 网络请求失败: {e}")

    # 清理临时文件
    import os
    if os.path.exists("demo_cookies.txt"):
        os.remove("demo_cookies.txt")

    print("\n" + "=" * 60)
    print("✅ Session 与 Cookie 演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
