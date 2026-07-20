"""
Day 074 — 异步测试
运行方式：python 04-async-test.py
注意：需要安装 pytest-asyncio: pip install pytest-asyncio
"""
import pytest
import asyncio
from unittest.mock import AsyncMock


# ========== 1. 异步函数 ==========


async def async_add(a, b):
    """异步加法"""
    await asyncio.sleep(0.1)  # 模拟异步操作
    return a + b


async def async_fetch_data(url):
    """模拟异步数据获取"""
    await asyncio.sleep(0.1)
    return {"status": "ok", "url": url}


# ========== 2. 异步测试 ==========


@pytest.mark.asyncio
async def test_async_add():
    """测试异步加法"""
    result = await async_add(2, 3)
    assert result == 5


@pytest.mark.asyncio
async def test_async_fetch():
    """测试异步数据获取"""
    result = await async_fetch_data("https://api.example.com")
    assert result["status"] == "ok"
    assert result["url"] == "https://api.example.com"


# ========== 3. 异步 Fixture ==========


@pytest.fixture
async def async_data():
    """异步 fixture"""
    await asyncio.sleep(0.1)
    return {"key": "value", "numbers": [1, 2, 3]}


@pytest.mark.asyncio
async def test_with_async_fixture(async_data):
    """使用异步 fixture"""
    assert async_data["key"] == "value"
    assert len(async_data["numbers"]) == 3


# ========== 4. 异步类 ==========


class AsyncAPIClient:
    """异步 API 客户端"""

    def __init__(self, base_url):
        self.base_url = base_url
        self.session = None

    async def connect(self):
        """连接到服务器"""
        await asyncio.sleep(0.1)  # 模拟连接
        self.session = True

    async def disconnect(self):
        """断开连接"""
        await asyncio.sleep(0.1)
        self.session = None

    async def get(self, path):
        """发送 GET 请求"""
        if not self.session:
            raise RuntimeError("未连接")
        await asyncio.sleep(0.1)
        return {"status": "ok", "path": path}


@pytest.fixture
async def api_client():
    """异步 API 客户端 fixture"""
    client = AsyncAPIClient("https://api.example.com")
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_api_connect(api_client):
    """测试 API 连接"""
    assert api_client.session is True


@pytest.mark.asyncio
async def test_api_get(api_client):
    """测试 API GET 请求"""
    result = await api_client.get("/users")
    assert result["status"] == "ok"
    assert result["path"] == "/users"


# ========== 5. AsyncMock ==========


@pytest.mark.asyncio
async def test_with_async_mock():
    """使用异步 mock"""
    mock_func = AsyncMock(return_value=42)

    result = await mock_func()

    assert result == 42
    mock_func.assert_called_once()


# ========== 6. 异步生成器 ==========


@pytest.mark.asyncio
async def test_async_generator():
    """测试异步生成器"""

    async def async_range(n):
        for i in range(n):
            await asyncio.sleep(0.01)
            yield i

    results = []
    async for num in async_range(5):
        results.append(num)

    assert results == [0, 1, 2, 3, 4]


# ========== 7. 超时测试 ==========


@pytest.mark.asyncio
async def test_with_timeout():
    """测试异步操作超时"""
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            asyncio.sleep(10),
            timeout=0.1
        )


# ========== 运行测试 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 异步测试演示")
    print("=" * 60)
    print()
    print("注意：需要安装 pytest-asyncio")
    print("pip install pytest-asyncio")
    print()
    pytest.main([__file__, "-v"])
