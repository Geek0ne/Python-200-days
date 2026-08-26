"""01-代理基础用法.py — requests 使用代理的完整演示

运行: python3 01-代理基础用法.py
依赖: pip install requests
"""

import requests

# ============================================================
# 1. 最基本的代理使用
# ============================================================
# 代理格式: 协议://[用户名:密码@]IP:端口
# 注意: proxies 字典的 key 是「你要访问的目标协议」，
#       而不是代理服务器本身的协议！

PROXY = "http://182.92.1.2:8080"  # 换成一个可用的代理再运行

proxies = {
    "http": PROXY,
    "https": PROXY,  # https 站点也可以走 http 代理（CONNECT 隧道）
}


def check_direct_ip():
    """不用代理，查看本机出口 IP"""
    resp = requests.get("https://httpbin.org/ip", timeout=10)
    print(f"[直连] 出口 IP: {resp.json()['origin']}")


def check_proxy_ip():
    """通过代理访问，验证 IP 是否变化"""
    try:
        resp = requests.get(
            "https://httpbin.org/ip",
            proxies=proxies,
            timeout=(3, 8),  # (连接超时3s, 读取超时8s) —— 用代理必设短超时!
        )
        print(f"[代理] 出口 IP: {resp.json()['origin']}")
    except requests.exceptions.ConnectTimeout:
        print("[代理] 连接超时 —— 代理已失效（免费代理常态）")
    except requests.exceptions.ProxyError:
        print("[代理] 代理拒绝连接 —— 代理不可用")


def check_anonymity():
    """检测代理匿名级别：观察响应头里是否泄露真实 IP"""
    try:
        resp = requests.get(
            "https://httpbin.org/headers",
            proxies=proxies,
            timeout=(3, 8),
        )
        headers = resp.json()["headers"]
        xff = headers.get("X-Forwarded-For", "")
        via = headers.get("Via", "")

        if xff and "." in xff:
            level = "透明代理 ❌（暴露真实 IP）"
        elif via or xff:
            level = "普通匿名 ⚠️（对方知道你用了代理）"
        else:
            level = "高匿名 ✅（完全隐藏）"
        print(f"[匿名度] {level}  XFF={xff!r} Via={via!r}")
    except Exception as e:
        print(f"[匿名度] 检测失败: {e}")


if __name__ == "__main__":
    check_direct_ip()
    check_proxy_ip()
    check_anonymity()
