#!/usr/bin/env python3
"""
Day 064 - 网络请求
示例 1: urllib vs requests 对比与基础用法

本示例演示：
1. urllib.request 基础用法
2. requests 基础用法
3. 两者的详细对比（代码量 vs 功能）
4. GET/POST 请求实战
5. JSON 数据交互
6. 文件上传与下载
7. 代理与 SSL 设置

安装依赖: pip install requests
运行方式: python3 01-urllib-vs-requests.py
"""

import json
import sys
from pathlib import Path

print("=" * 60)
print("📡 urllib vs requests — 对比与基础用法")
print("=" * 60)

# ════════════════════════════════════════════
# 1. urllib 基础
# ════════════════════════════════════════════

print("\n" + "=" * 40)
print("1️⃣  urllib 基础用法")
print("=" * 40)

from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote
from urllib.error import HTTPError, URLError


def urllib_get_example():
    """urllib GET 请求示例"""
    print("\n--- GET 请求 ---")

    try:
        # 简单 GET
        response = urlopen("https://httpbin.org/get?name=alice&age=30",
                          timeout=10)
        data = json.loads(response.read().decode("utf-8"))
        print(f"状态码: {response.status}")
        print(f"请求参数: {data.get('args', {})}")
        print(f"User-Agent: {data.get('headers', {}).get('User-Agent', 'N/A')}")
    except HTTPError as e:
        print(f"HTTP 错误: {e.code} {e.reason}")
    except URLError as e:
        print(f"网络错误: {e.reason}")


def urllib_post_example():
    """urllib POST 请求示例"""
    print("\n--- POST 请求 ---")

    # POST JSON 数据
    post_data = json.dumps({
        "name": "Alice",
        "age": 30,
        "skills": ["Python", "Data Analysis"]
    }).encode("utf-8")

    req = Request(
        "https://httpbin.org/post",
        data=post_data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Python urllib/3.12",
        }
    )

    try:
        response = urlopen(req, timeout=10)
        result = json.loads(response.read().decode("utf-8"))
        print(f"状态码: {response.status}")
        print(f"发送的 JSON: {result.get('json', {})}")
        print(f"Content-Type 头: {result.get('headers', {}).get('Content-Type', 'N/A')}")
    except HTTPError as e:
        print(f"HTTP 错误: {e.code} {e.reason}")


def urllib_headers_example():
    """urllib 自定义请求头"""
    print("\n--- 自定义请求头 ---")

    req = Request(
        "https://httpbin.org/headers",
        headers={
            "User-Agent": "MyCustomBot/1.0",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,en;q=0.9",
            "Authorization": "Bearer test_token_123",
            "X-Custom-Header": "custom_value",
        }
    )

    try:
        response = urlopen(req, timeout=10)
        result = json.loads(response.read().decode("utf-8"))
        print("收到的请求头:")
        for key, value in result.get("headers", {}).items():
            print(f"  {key}: {value}")
    except HTTPError as e:
        print(f"HTTP 错误: {e.code}")


def urllib_url_encoding():
    """URL 编码和解码"""
    print("\n--- URL 编码 ---")

    # 中文编码
    chinese = "北京天气"
    encoded = quote(chinese)
    print(f"中文 '{chinese}' → URL 编码: {encoded}")

    # 参数字典编码
    params = {
        "q": "Python 教程",
        "page": 1,
        "lang": "zh-CN"
    }
    query_string = urlencode(params)
    print(f"参数字典 → 查询字符串: {query_string}")

    # 完整 URL
    full_url = f"https://api.example.com/search?{query_string}"
    print(f"完整 URL: {full_url}")


# ════════════════════════════════════════════
# 2. requests 基础
# ════════════════════════════════════════════

print("\n" + "=" * 40)
print("2️⃣  requests 基础用法")
print("=" * 40)

HAS_REQUESTS = False
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    print("⚠️  requests 未安装。安装: pip install requests")
    print("   跳过 requests 演示。")

if HAS_REQUESTS:
    def requests_get_example():
        """requests GET 请求示例"""
        print("\n--- GET 请求 ---")

        try:
            response = requests.get(
                "https://httpbin.org/get",
                params={"name": "alice", "age": 30},
                timeout=10
            )
            data = response.json()
            print(f"状态码: {response.status_code}")
            print(f"请求参数: {data.get('args', {})}")
            print(f"URL: {response.url}")  # 可以看到编码后的完整 URL
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")

    def requests_post_example():
        """requests POST 请求示例"""
        print("\n--- POST 请求 ---")

        # POST JSON (requests 自动处理 Content-Type)
        response = requests.post(
            "https://httpbin.org/post",
            json={
                "name": "Alice",
                "age": 30,
                "skills": ["Python", "Data Analysis"],
            },
            timeout=10
        )
        result = response.json()
        print(f"状态码: {response.status_code}")
        print(f"发送的 JSON: {result.get('json', {})}")

        # POST 表单
        form_response = requests.post(
            "https://httpbin.org/post",
            data={"username": "admin", "password": "secret"},
            timeout=10
        )
        form_result = form_response.json()
        print(f"\n表单数据: {form_result.get('form', {})}")

    def requests_headers_example():
        """requests 自定义请求头"""
        print("\n--- 自定义请求头 ---")

        headers = {
            "User-Agent": "MyCustomBot/1.0",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,en;q=0.9",
            "Authorization": "Bearer test_token_123",
        }

        response = requests.get(
            "https://httpbin.org/headers",
            headers=headers,
            timeout=10
        )
        result = response.json()
        print("收到的请求头:")
        for key, value in result.get("headers", {}).items():
            print(f"  {key}: {value}")

    def requests_binary_example():
        """requests 二进制数据 (下载图片等)"""
        print("\n--- 二进制数据 (文件下载) ---")

        response = requests.get("https://httpbin.org/image/png", timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"内容大小: {len(response.content)} bytes")

        # 流式下载（大文件时使用）
        # with open('large_file.zip', 'wb') as f:
        #     response = requests.get(url, stream=True)
        #     for chunk in response.iter_content(chunk_size=8192):
        #         f.write(chunk)

    def requests_file_upload():
        """requests 文件上传"""
        print("\n--- 文件上传 ---")

        # 创建一个临时文件
        test_file = Path("/tmp/day064_upload_test.txt")
        test_file.write_text("Hello, this is a test file!", encoding="utf-8")

        # 上传文件
        with open(test_file, "rb") as f:
            response = requests.post(
                "https://httpbin.org/post",
                files={"file": ("test.txt", f, "text/plain")},
                timeout=10
            )
        result = response.json()
        print(f"上传结果: {result.get('files', {}).get('file', '...')[:50]}...")

        test_file.unlink()

# ════════════════════════════════════════════
# 3. 代码量对比
# ════════════════════════════════════════════

print("\n" + "=" * 40)
print("3️⃣  代码量对比: urllib vs requests")
print("=" * 40)

print("\n相同的功能: POST JSON 数据并解析响应")
print()

# urllib 版本
urllib_code = """
from urllib.request import Request, urlopen
import json

data = json.dumps({"name": "Alice"}).encode()
req = Request("https://httpbin.org/post",
              data=data,
              headers={"Content-Type": "application/json"})
resp = urlopen(req, timeout=10)
result = json.loads(resp.read().decode())
"""
print(f"📦 urllib ({len(urllib_code)} 字符):")
for line in urllib_code.strip().split("\n"):
    print(f"  {line}")

# requests 版本
requests_code = """
import requests

result = requests.post("https://httpbin.org/post",
                       json={"name": "Alice"},
                       timeout=10).json()
"""
print(f"\n🚀 requests ({len(requests_code)} 字符):")
for line in requests_code.strip().split("\n"):
    print(f"  {line}")

# ════════════════════════════════════════════
# 4. 综合对比测试
# ════════════════════════════════════════════

print("\n" + "=" * 40)
print("4️⃣  综合 HTTP 测试")
print("=" * 40)

if HAS_REQUESTS:
    # 运行示例
    requests_get_example()
    requests_post_example()
    requests_headers_example()
    requests_binary_example()
    requests_file_upload()
else:
    # 仅 urllib
    urllib_get_example()
    urllib_post_example()
    urllib_headers_example()
    urllib_url_encoding()

# ─── 超时与异常处理 ───

print("\n\n--- 超时与异常处理对比 ---")

# urllib
print("\nurllib 超时处理:")
try:
    urlopen("https://httpbin.org/delay/5", timeout=2)
except Exception as e:
    print(f"  ⚠️  {type(e).__name__}: {e}")

if HAS_REQUESTS:
    # requests
    print("\nrequests 超时处理:")
    try:
        requests.get("https://httpbin.org/delay/5", timeout=2)
    except Exception as e:
        print(f"  ⚠️  {type(e).__name__}: {e}")

    # requests 的连接/读取分离超时
    print("\nrequests 连接/读取分离超时:")
    try:
        requests.get("https://httpbin.org/delay/5", timeout=(2, 3))
    except Exception as e:
        print(f"  ⚠️  {type(e).__name__}: {e}")

print("\n✅ 示例完成！")
