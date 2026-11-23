#!/usr/bin/env python3
"""
02 - Cookie 持久化与轮换（进阶 + 避坑）
======================================
演示：
1. Cookie 持久化到磁盘（pickle 方式），程序重启后恢复会话
2. Cookie 池核心：状态管理（fresh/active/dead）+ 失效检测

常见坑：
- 坑1：每请求换 UA 但复用同一 Session -> 会话内 UA 漂移，更可疑
- 坑2：Cookie 失效不剔除 -> 后续请求全部浪费
- 坑3：pickle 只存 Cookie，不存绑定信息（UA/IP）-> 恢复后身份不一致

运行：python3 02-cookie-pool.py
"""
import os
import pickle
import random
import requests

COOKIE_FILE = "cookie_session.pkl"


# ---------------------------------------------------------------
# 1. Cookie 持久化：把身份(UA)和 CookieJar 一起存
# 原理：恢复会话时身份必须一致，否则"换浏览器还是同一批 Cookie"
# ---------------------------------------------------------------
def save_session(s: requests.Session):
    payload = {
        "ua": s.headers.get("User-Agent"),
        "cookies": requests.utils.dict_from_cookiejar(s.cookies),
    }
    with open(COOKIE_FILE, "wb") as f:
        pickle.dump(payload, f)
    print(f"💾 会话已持久化: {len(payload['cookies'])} 个 Cookie")


def load_session() -> requests.Session:
    """从磁盘恢复会话；文件不存在则创建新会话。"""
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "rb") as f:
            payload = pickle.load(f)
        s = requests.Session()
        s.headers.update({
            "User-Agent": payload["ua"],
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        requests.utils.add_dict_to_cookiejar(s.cookies, payload["cookies"])
        print(f"♻️  恢复会话: UA={payload['ua'][:40]}..., "
              f"Cookies={list(payload['cookies'])}")
        return s
    print("🆕 创建新会话")
    s = requests.Session()
    s.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/126.0.0.0 Safari/537.36"),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    return s


# ---------------------------------------------------------------
# 2. Cookie 池：状态机管理
# ---------------------------------------------------------------
class CookiePool:
    """
    极简 Cookie 池。
    状态: fresh(未用) -> active(使用中) -> dead(剔除)
    每个条目绑定一个 UA（身份一致性），并记录连续失败次数。
    """

    def __init__(self):
        self._items = []       # [{"cookie": str, "ua": str, "state": str, "fails": int}]
        self._cursor = 0       # 轮询游标

    def add(self, cookie: str, ua: str):
        self._items.append({"cookie": cookie, "ua": ua,
                            "state": "fresh", "fails": 0})

    def get(self):
        """轮询取一个可用 Cookie（fresh/active），并返回其绑定的 UA。"""
        usable = [i for i, it in enumerate(self._items)
                  if it["state"] in ("fresh", "active")]
        if not usable:
            return None
        idx = usable[self._cursor % len(usable)]
        self._cursor += 1
        item = self._items[idx]
        item["state"] = "active"
        return item

    def report(self, item, ok: bool):
        """使用结果反馈：失败累计 3 次判死。"""
        if ok:
            item["fails"] = 0
        else:
            item["fails"] += 1
            if item["fails"] >= 3:
                item["state"] = "dead"
                print(f"💀 Cookie 已失效剔除: {item['cookie'][:20]}...")

    def stats(self):
        from collections import Counter
        return dict(Counter(it["state"] for it in self._items))


def fetch(url, item):
    """用池中的身份发请求，返回是否成功（演示用 httpbin）。"""
    s = requests.Session()
    s.headers.update({"User-Agent": item["ua"]})
    s.headers.update({"Cookie": item["cookie"]})
    try:
        r = s.get(url, timeout=15)
        return r.status_code == 200
    except requests.RequestException:
        return False


if __name__ == "__main__":
    # --- 演示 1: 持久化与恢复 ---
    s = load_session()
    s.get("https://httpbin.org/cookies/set/session_token/demo123", timeout=15)
    save_session(s)
    s2 = load_session()   # 模拟"程序重启"
    print(f"恢复后的 Cookie: {requests.utils.dict_from_cookiejar(s2.cookies)}\n")

    # --- 演示 2: Cookie 池轮换 ---
    pool = CookiePool()
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    for cid in ["sid=aaa111", "sid=bbb222", "sid=ccc333"]:
        pool.add(cid, UA)
    # 模拟 5 次请求轮换（其中随机注入一次失败）
    random.seed(42)
    for i in range(5):
        item = pool.get()
        ok = fetch("https://httpbin.org/get", item)
        if i == 1:                      # 模拟某次失效
            ok = False
        pool.report(item, ok)
        print(f"请求{i + 1}: cookie={item['cookie']} -> "
              f"{'✅' if ok else '❌'} 池状态={pool.stats()}")
