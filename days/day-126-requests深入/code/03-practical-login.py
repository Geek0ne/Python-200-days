"""
Day 126 - Requests 深入：实战案例 — 模拟登录
03-practical-login.py

演示完整的模拟登录流程：获取 Token → 提交登录 → 保持会话 → 访问受保护资源

注意：本示例使用 httpbin.org 模拟，实际使用时替换为真实网站
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import time
import re
from urllib.parse import urljoin, urlparse


# ============================================================
# 1. 基础爬虫框架
# ============================================================

class WebCrawler:
    """基础爬虫框架"""

    def __init__(self, base_url, headers=None):
        self.base_url = base_url
        self.session = self._create_session(headers)

    def _create_session(self, headers=None):
        """创建带重试和伪装的 Session"""
        session = requests.Session()

        # 默认请求头
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        }
        if headers:
            default_headers.update(headers)
        session.headers.update(default_headers)

        # 重试策略
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def get(self, url, **kwargs):
        """GET 请求"""
        full_url = urljoin(self.base_url, url)
        resp = self.session.get(full_url, timeout=10, **kwargs)
        resp.raise_for_status()
        return resp

    def post(self, url, **kwargs):
        """POST 请求"""
        full_url = urljoin(self.base_url, url)
        resp = self.session.post(full_url, timeout=10, **kwargs)
        resp.raise_for_status()
        return resp


# ============================================================
# 2. CSRF Token 处理
# ============================================================

def extract_csrf_token(html):
    """
    从 HTML 中提取 CSRF Token

    常见的 CSRF Token 位置：
    1. <input type="hidden" name="csrf_token" value="xxx">
    2. <meta name="csrf-token" content="xxx">
    3. JavaScript 变量: var csrfToken = "xxx";
    """
    # 方法一：从 input 标签提取
    pattern = r'<input[^>]*name=["\']csrf[_-]?token["\'][^>]*value=["\']([^"\']+)["\']'
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        return match.group(1)

    # 方法二：从 meta 标签提取
    pattern = r'<meta[^>]*name=["\']csrf-token["\'][^>]*content=["\']([^"\']+)["\']'
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        return match.group(1)

    # 方法三：从 JavaScript 变量提取
    pattern = r'var\s+csrf[_-]?[Tt]oken\s*=\s*["\']([^"\']+)["\']'
    match = re.search(pattern, html)
    if match:
        return match.group(1)

    return None


# ============================================================
# 3. 模拟登录示例
# ============================================================

class LoginDemo:
    """模拟登录示例"""

    def __init__(self):
        self.crawler = WebCrawler("https://httpbin.org")
        self.logged_in = False

    def step1_get_login_page(self):
        """步骤 1: 获取登录页面"""
        print("\n📋 步骤 1: 获取登录页面")
        resp = self.crawler.get("/forms/post")
        print(f"  状态码: {resp.status_code}")
        print(f"  Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
        print(f"  Cookies: {dict(self.crawler.session.cookies)}")
        return resp.text

    def step2_submit_login(self, username, password):
        """步骤 2: 提交登录表单"""
        print(f"\n📋 步骤 2: 提交登录表单")
        print(f"  用户名: {username}")
        print(f"  密码: {'*' * len(password)}")

        # 模拟表单提交
        form_data = {
            "username": username,
            "password": password,
            "submit": "Login",
        }

        resp = self.crawler.post("/post", data=form_data)
        print(f"  状态码: {resp.status_code}")
        print(f"  响应大小: {len(resp.text)} 字节")
        return resp.json()

    def step3_access_protected(self):
        """步骤 3: 访问受保护资源"""
        print(f"\n📋 步骤 3: 访问受保护资源 (使用已保存的 Cookie)")
        resp = self.crawler.get("/cookies")
        cookies = resp.json().get("cookies", {})
        print(f"  服务器收到的 Cookies: {cookies}")
        return cookies

    def step4_logout(self):
        """步骤 4: 登出"""
        print(f"\n📋 步骤 4: 登出")
        self.crawler.session.cookies.clear()
        print(f"  Cookies 已清除: {dict(self.crawler.session.cookies)}")

    def run(self, username="testuser", password="testpass"):
        """执行完整登录流程"""
        print("=" * 60)
        print("🔐 模拟登录流程演示")
        print("=" * 60)

        try:
            self.step1_get_login_page()
            result = self.step2_submit_login(username, password)
            self.step3_access_protected()
            self.step4_logout()
            print("\n✅ 登录流程完成")
            return result
        except Exception as e:
            print(f"\n❌ 登录失败: {e}")
            return None


# ============================================================
# 4. 请求头伪装实战
# ============================================================

def demo_realistic_headers():
    """演示真实浏览器请求头"""
    print("\n" + "=" * 60)
    print("🎭 真实浏览器请求头对比")
    print("=" * 60)

    # 简单请求头
    simple_headers = {
        "User-Agent": "python-requests/2.31.0",
    }

    # 真实浏览器请求头
    realistic_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }

    # 对比发送
    session = requests.Session()

    print("\n--- 简单请求头 ---")
    session.headers.clear()
    session.headers.update(simple_headers)
    try:
        resp = session.get("https://httpbin.org/headers", timeout=5)
        server_headers = resp.json().get("headers", {})
        print(f"  服务器收到的 Headers 数量: {len(server_headers)}")
        print(f"  User-Agent: {server_headers.get('User-Agent', 'N/A')}")
    except Exception as e:
        print(f"  ⚠️ 请求失败: {e}")

    print("\n--- 真实浏览器请求头 ---")
    session.headers.clear()
    session.headers.update(realistic_headers)
    try:
        resp = session.get("https://httpbin.org/headers", timeout=5)
        server_headers = resp.json().get("headers", {})
        print(f"  服务器收到的 Headers 数量: {len(server_headers)}")
        print(f"  User-Agent: {server_headers.get('User-Agent', 'N/A')[:60]}...")
        print(f"  Sec-Fetch-*: {[k for k in server_headers if k.startswith('Sec-')]}")
    except Exception as e:
        print(f"  ⚠️ 请求失败: {e}")


# ============================================================
# 5. 主流程
# ============================================================

def main():
    print("🚀 Day 126 - Requests 深入：实战案例 — 模拟登录\n")

    # 模拟登录
    demo = LoginDemo()
    demo.run()

    # 请求头伪装
    demo_realistic_headers()

    print("\n" + "=" * 60)
    print("✅ 实战案例演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
