#!/usr/bin/env python3
"""
01 - 逆向第一步：请求对比侦察（基础用法）
=========================================
模拟 DevTools Network 分析的 Python 版：
用 "Copy as cURL" 的思路，对比浏览器请求与脚本请求的差异，
定位哪些参数是动态生成的（需要逆向）。

为什么这样做：
- 逆向第一问永远是"哪些参数是动态的"
- 对比法：固定请求两次，变化的参数 = 动态参数；不变的 = 静态参数

运行：python3 01-request-recon.py
"""
import hashlib
import time
import requests

BASE = "https://httpbin.org/get"

def fetch_with_params(params: dict) -> dict:
    r = requests.get(BASE, params=params, timeout=10,
                     headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    return r.json()["args"]

def detect_dynamic_params() -> None:
    """
    连续请求同一接口两次，对比参数：
    - 不变的 -> 静态参数（直接抄）
    - 变化的 -> 动态参数（需要逆向生成逻辑）
    """
    def make_call():
        t = int(time.time() * 1000)
        return {
            "page": 1,                          # 静态：翻页逻辑，可控
            "app_id": "10086",                  # 静态：常量
            "timestamp": str(t),                # 动态：时间戳
            "sign": hashlib.md5(f"{t}salt".encode()).hexdigest(),  # 动态：疑似加密
        }

    first = fetch_with_params(make_call())
    time.sleep(1.1)  # 保证 timestamp 不同
    second = fetch_with_params(make_call())

    print(f"{'参数':<12}{'第一次':<36}{'第二次':<36}{'类型'}")
    print("-" * 100)
    for k in first:
        v1, v2 = first[k], second[k]
        kind = "静态 ✅" if v1 == v2 else "动态 ⚠️ 需逆向"
        print(f"{k:<12}{str(v1)[:34]:<36}{str(v2)[:34]:<36}{kind}")

    # 启发式判断动态参数的性质
    print("\n启发式分析:")
    for k in ("sign", "token", "signature", "sig"):
        if k in first:
            v = first[k]
            print(f"  - {k} 长度 {len(v)} 位", end=" ")
            if len(v) == 32:
                print("-> 疑似 MD5 / AES 中间值")
            elif len(v) in (40, 64):
                print("-> 疑似 SHA1 / SHA256")
            else:
                print("-> 疑似自定义加密 / base64 变体")

if __name__ == "__main__":
    print("== 模拟 DevTools 请求侦察 ==\n")
    detect_dynamic_params()
    print("\n结论：timestamp 与 sign 为动态参数 -> 去 DevTools 加 XHR 断点定位 sign 生成逻辑")
