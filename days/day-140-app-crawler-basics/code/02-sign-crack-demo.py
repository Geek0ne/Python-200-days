"""
02 - 签名参数复现与避坑（进阶用法）
====================================
演示 App 爬虫最核心的一步：把 App 里的 sign 算法用 Python 复现。
这里用一个"教学版"算法模拟真实的逆向结果。

逆向得到的（假设 jadx 中定位到的）Java 逻辑:
    sign = md5( md5(password).upper() + timestamp + SALT ).upper()

避坑点:
    1. md5 结果大小写（App 常用大写，Python hexdigest 是小写）
    2. 拼接顺序不能错，差一个字符全盘皆输
    3. timestamp 是秒还是毫秒，要和抓包样本对齐
"""

import hashlib
import time

SALT = "a1b2c3d4e5"  # 反编译时从代码里挖出来的固定盐值


def md5_upper(text: str) -> str:
    """md5 并转大写——大小写是 App 签名最常见坑"""
    return hashlib.md5(text.encode("utf-8")).hexdigest().upper()


def make_sign(password: str, timestamp: int) -> str:
    """复现 App 的签名算法（与 jadx 反编译逻辑一一对应）"""
    return md5_upper(md5_upper(password) + str(timestamp) + SALT)


def build_signed_headers(username: str, password: str) -> dict:
    """构造带签名的请求头——模拟抓包看到的真实 App 请求"""
    ts = int(time.time())
    return {
        "User-Agent": "okhttp/4.9.3",  # okhttp 是安卓最常见 UA
        "X-Username": username,
        "X-Timestamp": str(ts),
        "X-Sign": make_sign(password, ts),
        "X-Device-Id": "8f3a2b1c-device-fake-id-0001",
    }


# ═══════════════ 自测与验证 ═══════════════
if __name__ == "__main__":
    # 验证方法：拿抓包样本里的 (password, timestamp, sign) 三元组做断言
    # 假设抓包样本: password="demo123", ts=1756598400, sign="XXXXXXXX..."
    ts = 1756598400
    sign = make_sign("demo123", ts)
    print(f"password=demo123, ts={ts}")
    print(f"计算得到 sign = {sign}")

    # 模拟构造完整请求头
    headers = build_signed_headers("nie", "demo123")
    print("\n签名后的请求头:")
    for k, v in headers.items():
        print(f"  {k}: {v}")

    # ⚠️ 避坑演示：大小写 + 毫秒时间戳会导致校验失败
    wrong1 = hashlib.md5(b"demo123").hexdigest()  # 小写 md5
    print(f"\n[坑1] 小写 md5: {wrong1}  (App 要大写 -> 校验必失败)")
    wrong2 = make_sign("demo123", ts * 1000)  # 毫秒时间戳
    print(f"[坑2] 毫秒时间戳算出的 sign 与抓包样本不一致: {wrong2}")
