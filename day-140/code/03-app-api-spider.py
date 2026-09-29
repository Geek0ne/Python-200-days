"""
03 - 完整 App 协议模拟爬虫（实战案例）
========================================
把 抓包分析 + 签名复现 组装成一个可翻页的 App API 爬虫。
目标接口为教学模拟（httpbin 风格），换成真实授权接口即可复用框架。

核心结构:
    SignClient  -> 负责签名与请求（协议层）
    AppSpider   -> 负责翻页/重试/限速/存储（业务层）
"""

import hashlib
import json
import time
import random
from pathlib import Path

import requests

SALT = "a1b2c3d4e5"
BASE_URL = "https://httpbin.org"  # 教学用，替换为授权的目标 API
OUT_FILE = Path(__file__).parent / "app_spider_result.jsonl"


class SignClient:
    """协议层：复现 App 的签名逻辑并发请求"""

    def __init__(self, username: str, password: str, device_id: str):
        self.username = username
        self.password = password
        self.device_id = device_id
        self.session = requests.Session()  # 复用 TCP 连接，模拟真实 App

    @staticmethod
    def _md5_upper(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest().upper()

    def _sign(self, timestamp: int) -> str:
        return self._md5_upper(self._md5_upper(self.password) + str(timestamp) + SALT)

    def get(self, path: str, params: dict | None = None) -> dict:
        ts = int(time.time())
        headers = {
            "User-Agent": "okhttp/4.9.3",
            "X-Username": self.username,
            "X-Timestamp": str(ts),
            "X-Sign": self._sign(ts),
            "X-Device-Id": self.device_id,
        }
        resp = self.session.get(BASE_URL + path, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()


class AppSpider:
    """业务层：翻页 + 重试 + 限速 + 存储"""

    def __init__(self, client: SignClient, max_pages: int = 3):
        self.client = client
        self.max_pages = max_pages

    def crawl(self, path: str, page_size: int = 10) -> list[dict]:
        results = []
        for page in range(1, self.max_pages + 1):
            params = {"page": page, "size": page_size}
            data = self._request_with_retry(path, params)
            items = data.get("args", {}) if isinstance(data, dict) else {}
            results.append({"page": page, "echo": items})
            print(f"[第{page}页] 请求成功, 返回键: {list(data.keys())[:6]}")
            # 随机延迟 0.8~1.5s，模拟真人操作节奏
            time.sleep(random.uniform(0.8, 1.5))
        return results

    def _request_with_retry(self, path: str, params: dict, retries: int = 3) -> dict:
        """简单重试：网络错误/5xx 指数退避重试"""
        for attempt in range(1, retries + 1):
            try:
                return self.client.get(path, params)
            except requests.RequestException as e:
                wait = 2 ** attempt
                print(f"  [重试 {attempt}/{retries}] {e}, {wait}s 后重试")
                time.sleep(wait)
        raise RuntimeError(f"请求 {path} 连续 {retries} 次失败")

    @staticmethod
    def save(records: list[dict]) -> None:
        with open(OUT_FILE, "a", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"✅ 已保存 {len(records)} 条到 {OUT_FILE}")


if __name__ == "__main__":
    client = SignClient(username="nie", password="demo123",
                        device_id="8f3a2b1c-device-fake-id-0001")
    spider = AppSpider(client, max_pages=3)
    data = spider.crawl("/get")
    spider.save(data)
