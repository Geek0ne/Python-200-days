"""
Day 036 — 封装与数据隐藏：实战案例
====================================

实战：安全的 API 封装 — 一个完整的 API 客户端框架

功能：
- 安全的 API Key 管理（名称改写保护）
- 速率限制控制（@property 验证）
- 自动重试与错误处理
- 请求签名生成
- 上下文管理器支持
- 可配置的日志记录
"""

import time
import hashlib
import hmac
import json
from datetime import datetime
from collections import deque
from typing import Optional, Dict, Any, Callable


# ====================================
# 公开异常
# ====================================

class APIError(Exception):
    """API 请求错误"""
    pass


class RateLimitError(APIError):
    """速率限制错误"""
    pass


class AuthenticationError(APIError):
    """认证错误"""
    pass


# ====================================
# 日志回调类型
# ====================================

LogCallback = Callable[[str, Dict[str, Any]], None]


def default_logger(level: str, data: Dict[str, Any]) -> None:
    """默认日志回调"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"  [{timestamp}] [{level.upper()}] {data.get('message', '')}")


# ====================================
# 安全的 API 客户端
# ====================================

class APIClient:
    """
    安全的 API 客户端封装

    封装设计：
    - __api_key: 名称改写保护的 API 密钥
    - __base_url: 名称改写保护的基础 URL
    - _rate_limit: 受保护的速率限制
    - 公开接口: get(), post(), put(), delete()
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        api_secret: str = "",
        rate_limit: int = 10,
        timeout: int = 30,
        max_retries: int = 3,
        logger: Optional[LogCallback] = None,
    ):
        # ── 私有属性（名称改写） ──
        self.__api_key = api_key        # → _APIClient__api_key
        self.__api_secret = api_secret  # → _APIClient__api_secret
        self.__base_url = base_url.rstrip('/')
        self.__session = None
        self.__call_count = 0
        self.__failed_count = 0
        self.__last_request_time = 0.0

        # ── 受保护的属性 ──
        self._rate_limit = rate_limit
        self._timeout = timeout
        self._max_retries = max_retries
        self._request_times = deque()
        self._base_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'SecureAPIClient/2.0',
        }

        # ── 公开属性 ──
        self.logger = logger or default_logger

    # ═══════════════════════════════════════
    # Property 控制
    # ═══════════════════════════════════════

    @property
    def base_url(self) -> str:
        """基础 URL（只读）"""
        return self.__base_url

    @property
    def api_key(self) -> str:
        """API Key（只读，对日志屏蔽）"""
        return self.__api_key[:4] + "..." + self.__api_key[-4:]

    @property
    def call_count(self) -> int:
        """API 调用次数（只读）"""
        return self.__call_count

    @property
    def failed_count(self) -> int:
        """失败次数（只读）"""
        return self.__failed_count

    @property
    def success_rate(self) -> float:
        """成功率（只读计算属性）"""
        total = self.__call_count
        if total == 0:
            return 1.0
        return (total - self.__failed_count) / total

    @property
    def rate_limit(self) -> int:
        """每秒最大请求数"""
        return self._rate_limit

    @rate_limit.setter
    def rate_limit(self, value: int):
        """设置速率限制（带验证）"""
        if not isinstance(value, int) or value < 1:
            raise ValueError("速率限制必须是正整数")
        self._rate_limit = value
        self._log("info", {"message": f"速率限制设置为 {value} req/s"})

    @property
    def timeout(self) -> int:
        """请求超时（秒）"""
        return self._timeout

    @timeout.setter
    def timeout(self, value: int):
        if not isinstance(value, int) or value < 1:
            raise ValueError("超时必须为正整数")
        self._timeout = value

    # ═══════════════════════════════════════
    # 内部方法（_ 前缀 — 内部使用）
    # ═══════════════════════════════════════

    def _log(self, level: str, data: Dict[str, Any]) -> None:
        """内部日志方法"""
        if self.logger:
            self.logger(level, data)

    def _get_session(self):
        """获取或创建 session（懒初始化）"""
        if self.__session is None:
            try:
                import requests
            except ImportError:
                raise ImportError("需要安装 requests 库: pip install requests")

            self.__session = requests.Session()
            self.__session.headers.update(self._base_headers)
            self.__session.headers['Authorization'] = \
                f'Bearer {self.__api_key}'
            self._log("info", {"message": "Session 已创建"})
        return self.__session

    def _check_rate_limit(self) -> None:
        """检查速率限制，必要时等待"""
        now = time.time()

        # 清理超过 1 秒的旧记录
        while self._request_times and \
                self._request_times[0] < now - 1:
            self._request_times.popleft()

        if len(self._request_times) >= self._rate_limit:
            wait_time = self._request_times[0] + 1 - now
            if wait_time > 0:
                self._log("warning", {
                    "message": f"速率限制触发，等待 {wait_time:.2f}s"
                })
                time.sleep(wait_time)

    def _make_signature(self, method: str, path: str,
                        timestamp: str, body: str = "") -> str:
        """生成请求签名（内部实现细节）"""
        if not self.__api_secret:
            return ""
        message = f"{method}{path}{timestamp}{body}"
        return hmac.new(
            self.__api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def _build_url(self, path: str) -> str:
        """构建完整 URL"""
        path = path.lstrip('/')
        return f"{self.__base_url}/{path}"

    def _should_retry(self, status_code: int) -> bool:
        """判断是否应该重试"""
        return status_code in {429, 500, 502, 503, 504}

    def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """统一请求处理（内部方法）"""
        self._check_rate_limit()

        session = self._get_session()
        url = self._build_url(path)
        self.__call_count += 1

        # 添加时间戳和签名
        timestamp = str(int(time.time()))
        body = kwargs.get('json')
        body_str = json.dumps(body) if body else ""

        session.headers['X-Timestamp'] = timestamp
        signature = self._make_signature(method, path, timestamp, body_str)
        if signature:
            session.headers['X-Signature'] = signature

        # 重试逻辑
        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                self._request_times.append(time.time())
                self.__last_request_time = time.time()

                self._log("info", {
                    "message": f"{method} {path} (尝试 {attempt + 1})"
                })

                response = session.request(
                    method, url,
                    timeout=self._timeout,
                    **kwargs
                )

                # 检查是否需要重试
                if response.status_code == 429 and attempt < self._max_retries:
                    retry_after = int(response.headers.get(
                        'Retry-After', 1
                    ))
                    self._log("warning", {
                        "message": f"429 限流，等待 {retry_after}s 后重试"
                    })
                    time.sleep(retry_after)
                    continue

                if response.status_code == 401:
                    raise AuthenticationError(
                        f"认证失败: {response.text}"
                    )

                response.raise_for_status()

                self._log("info", {
                    "message": f"{method} {path} → {response.status_code}"
                })

                return response.json()

            except AuthenticationError:
                self.__failed_count += 1
                raise

            except Exception as e:
                last_error = e
                if attempt < self._max_retries:
                    wait = 2 ** attempt  # 指数退避
                    self._log("warning", {
                        "message": f"请求失败，{wait}s 后重试: {e}"
                    })
                    time.sleep(wait)
                else:
                    self.__failed_count += 1

        self._log("error", {
            "message": f"请求失败（已重试 {self._max_retries} 次）: {last_error}"
        })
        return {"error": str(last_error)}

    # ═══════════════════════════════════════
    # 公开 API 方法
    # ═══════════════════════════════════════

    def get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """发送 GET 请求"""
        return self._request('GET', path, params=params)

    def post(self, path: str, data: Optional[Dict] = None) -> Dict:
        """发送 POST 请求"""
        return self._request('POST', path, json=data)

    def put(self, path: str, data: Optional[Dict] = None) -> Dict:
        """发送 PUT 请求"""
        return self._request('PUT', path, json=data)

    def patch(self, path: str, data: Optional[Dict] = None) -> Dict:
        """发送 PATCH 请求"""
        return self._request('PATCH', path, json=data)

    def delete(self, path: str) -> Dict:
        """发送 DELETE 请求"""
        return self._request('DELETE', path)

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "ok",
            "call_count": self.__call_count,
            "failed_count": self.__failed_count,
            "success_rate": f"{self.success_rate:.1%}",
            "rate_limit": self._rate_limit,
            "session_active": self.__session is not None,
        }

    def close(self) -> None:
        """关闭会话，释放资源"""
        if self.__session:
            self.__session.close()
            self.__session = None
            self._log("info", {"message": "Session 已关闭"})

    # ═══════════════════════════════════════
    # 上下文管理器
    # ═══════════════════════════════════════

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ═══════════════════════════════════════
    # 字符串表示
    # ═══════════════════════════════════════

    def __repr__(self):
        return (f"APIClient(base_url={self.__base_url!r}, "
                f"rate_limit={self._rate_limit})")

    def __str__(self):
        return (f"APIClient({self.__base_url}) "
                f"[calls={self.__call_count}, "
                f"success={self.success_rate:.0%}]")


# ====================================
# 子 API 封装
# ====================================

class UsersAPI:
    """用户相关 API 的子封装"""

    def __init__(self, client: APIClient):
        self._client = client  # 受保护的引用

    def list(self, page: int = 1, per_page: int = 20) -> Dict:
        return self._client.get("/users", params={
            "page": page, "per_page": per_page
        })

    def get(self, user_id: int) -> Dict:
        return self._client.get(f"/users/{user_id}")

    def create(self, name: str, email: str) -> Dict:
        return self._client.post("/users", data={
            "name": name, "email": email
        })

    def update(self, user_id: int, **kwargs) -> Dict:
        return self._client.patch(f"/users/{user_id}", data=kwargs)

    def delete(self, user_id: int) -> Dict:
        return self._client.delete(f"/users/{user_id}")


class SecureAPIClient(APIClient):
    """
    增强版 API 客户端 — 带子 API 模块

    展示继承中的封装控制：
    - _users: 受保护的用户 API 子模块
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初始化子 API 模块
        self._users = UsersAPI(self)

    @property
    def users(self) -> UsersAPI:
        """用户 API（只读）"""
        return self._users


# ====================================
# 演示
# ====================================

def demo():
    print("=" * 60)
    print("🔐 安全的 API 客户端 — 演示")
    print("=" * 60)

    # 创建客户端
    client = SecureAPIClient(
        api_key="sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        api_secret="ss-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        base_url="https://api.example.com/v1",
        rate_limit=5,
        timeout=10,
        max_retries=2,
    )

    # 展示封装控制
    print(f"\n📦 客户端信息:")
    print(f"  {client}")
    print(f"  API Key: {client.api_key}")  # 显示掩码后的 key
    print(f"  Base URL: {client.base_url}")
    print(f"  健康检查: {client.health_check()}")

    # 验证封装
    print(f"\n🔒 封装验证:")
    print(f"  公开属性: base_url, call_count, rate_limit, success_rate")
    try:
        print(f"  client.__api_key → ", end="")
        _ = client.__api_key
    except AttributeError:
        print("❌ (名称改写保护)")
    try:
        print(f"  client.__api_secret → ", end="")
        _ = client.__api_secret
    except AttributeError:
        print("❌ (名称改写保护)")

    # 通过名称改写仍然可以访问（展示 Python 的哲学）
    print(f"\n  名称改写后（展示 Python 开放哲学）:")
    print(f"  client._APIClient__api_key 前半部分: "
          f"{client._APIClient__api_key[:8]}...")

    # 子 API 模块
    print(f"\n📂 子 API 模块:")
    print(f"  client.users → UsersAPI (通过 client.users.list() 访问)")

    # 模拟请求
    print(f"\n🌐 模拟请求:")
    result = client.get("/health")
    print(f"  GET /health → {result}")

    # 使用上下文管理器
    print(f"\n📋 使用 with 语句:")
    with SecureAPIClient("test-key", "https://api.test.com/v1") as c:
        print(f"  在 with 块内: {c}")
    print(f"  离开 with 块后 session 已关闭")

    # 使用 property 修改配置
    print(f"\n⚙️  修改配置:")
    print(f"  原速率限制: {client.rate_limit}")
    client.rate_limit = 10
    print(f"  新速率限制: {client.rate_limit}")
    try:
        client.rate_limit = 0
    except ValueError as e:
        print(f"  ❌ 设置 0: {e}")

    # 最终统计
    print(f"\n📊 最终统计:")
    stats = client.health_check()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    client.close()
    print("\n" + "=" * 60)
    print("✅ 安全 API 封装演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
