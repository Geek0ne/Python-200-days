"""
Day 045 - REST API 客户端封装
面向对象实战项目：通过类封装 HTTP 请求，实现业务 API
"""

import json
import time
from typing import Any, Dict, List, Optional
from functools import wraps


def retry(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        print(f"Attempt {attempt + 1} failed: {e}")
                        print(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


def log_calls(func):
    """日志装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[LOG] Calling {func.__name__} with args={args[1:]}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"[LOG] {func.__name__} returned: {type(result).__name__}")
        return result
    return wrapper


class APIClient:
    """REST API 客户端基类"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if api_key:
            self.session_headers['Authorization'] = f'Bearer {api_key}'

    def _build_url(self, endpoint: str) -> str:
        """构建完整 URL"""
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _simulate_request(self, method: str, url: str, **kwargs) -> dict:
        """模拟 HTTP 请求（实际项目中使用 requests）"""
        print(f"[HTTP] {method} {url}")
        if 'data' in kwargs:
            print(f"[HTTP] Body: {json.dumps(kwargs['data'], ensure_ascii=False)}")
        # 模拟响应
        return {"status": "success", "data": kwargs.get('data', {}), "url": url}

    @log_calls
    @retry(max_retries=3, delay=0.5)
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """GET 请求"""
        url = self._build_url(endpoint)
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query_string}"
        return self._simulate_request("GET", url)

    @log_calls
    @retry(max_retries=3, delay=0.5)
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Any:
        """POST 请求"""
        url = self._build_url(endpoint)
        return self._simulate_request("POST", url, data=data)

    @log_calls
    @retry(max_retries=3, delay=0.5)
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Any:
        """PUT 请求"""
        url = self._build_url(endpoint)
        return self._simulate_request("PUT", url, data=data)

    @log_calls
    @retry(max_retries=3, delay=0.5)
    def delete(self, endpoint: str) -> bool:
        """DELETE 请求"""
        url = self._build_url(endpoint)
        self._simulate_request("DELETE", url)
        return True


class UserAPI(APIClient):
    """用户 API 封装"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        super().__init__(base_url, api_key)

    def get_users(self, page: int = 1, limit: int = 10) -> list:
        """获取用户列表"""
        return self.get('/users', params={'page': page, 'limit': limit})

    def get_user(self, user_id: int) -> dict:
        """获取单个用户"""
        return self.get(f'/users/{user_id}')

    def create_user(self, name: str, email: str, age: int) -> dict:
        """创建用户"""
        return self.post('/users', data={
            'name': name,
            'email': email,
            'age': age
        })

    def update_user(self, user_id: int, **kwargs) -> dict:
        """更新用户"""
        return self.put(f'/users/{user_id}', data=kwargs)

    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        return self.delete(f'/users/{user_id}')


class ArticleAPI(APIClient):
    """文章 API 封装"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        super().__init__(base_url, api_key)

    def get_articles(self, author_id: Optional[int] = None, page: int = 1) -> list:
        """获取文章列表"""
        params = {'page': page}
        if author_id:
            params['author_id'] = author_id
        return self.get('/articles', params=params)

    def get_article(self, article_id: int) -> dict:
        """获取单篇文章"""
        return self.get(f'/articles/{article_id}')

    def create_article(self, title: str, content: str, author_id: int) -> dict:
        """创建文章"""
        return self.post('/articles', data={
            'title': title,
            'content': content,
            'author_id': author_id
        })

    def update_article(self, article_id: int, **kwargs) -> dict:
        """更新文章"""
        return self.put(f'/articles/{article_id}', data=kwargs)

    def delete_article(self, article_id: int) -> bool:
        """删除文章"""
        return self.delete(f'/articles/{article_id}')


class CommentAPI(APIClient):
    """评论 API 封装"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        super().__init__(base_url, api_key)

    def get_comments(self, article_id: int) -> list:
        """获取文章评论"""
        return self.get(f'/articles/{article_id}/comments')

    def create_comment(self, article_id: int, user_id: int, content: str) -> dict:
        """创建评论"""
        return self.post(f'/articles/{article_id}/comments', data={
            'user_id': user_id,
            'content': content
        })

    def delete_comment(self, article_id: int, comment_id: int) -> bool:
        """删除评论"""
        return self.delete(f'/articles/{article_id}/comments/{comment_id}')


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 045 - REST API 客户端封装演示")
    print("=" * 60)

    # 初始化 API 客户端
    base_url = "https://api.example.com/v1"
    api_key = "test-api-key-12345"

    user_api = UserAPI(base_url, api_key)
    article_api = ArticleAPI(base_url, api_key)
    comment_api = CommentAPI(base_url, api_key)

    print("\n1. 用户管理")
    print("-" * 40)

    # 创建用户
    print("\n创建用户:")
    new_user = user_api.create_user("李四", "lisi@example.com", 28)
    print(f"结果: {new_user}")

    # 获取用户列表
    print("\n获取用户列表:")
    users = user_api.get_users(page=1, limit=10)
    print(f"结果: {users}")

    # 获取单个用户
    print("\n获取单个用户:")
    user = user_api.get_user(1)
    print(f"结果: {user}")

    # 更新用户
    print("\n更新用户:")
    updated = user_api.update_user(1, name="李四（已更新）", age=29)
    print(f"结果: {updated}")

    # 删除用户
    print("\n删除用户:")
    deleted = user_api.delete_user(1)
    print(f"结果: {deleted}")

    print("\n2. 文章管理")
    print("-" * 40)

    # 创建文章
    print("\n创建文章:")
    new_article = article_api.create_article(
        "Python 学习笔记",
        "今天学习了面向对象编程...",
        author_id=1
    )
    print(f"结果: {new_article}")

    # 获取文章列表
    print("\n获取文章列表:")
    articles = article_api.get_articles(author_id=1)
    print(f"结果: {articles}")

    # 获取单篇文章
    print("\n获取单篇文章:")
    article = article_api.get_article(1)
    print(f"结果: {article}")

    # 更新文章
    print("\n更新文章:")
    updated_article = article_api.update_article(1, title="Python 学习笔记（更新版）")
    print(f"结果: {updated_article}")

    # 删除文章
    print("\n删除文章:")
    deleted_article = article_api.delete_article(1)
    print(f"结果: {deleted_article}")

    print("\n3. 评论管理")
    print("-" * 40)

    # 获取文章评论
    print("\n获取文章评论:")
    comments = comment_api.get_comments(article_id=1)
    print(f"结果: {comments}")

    # 创建评论
    print("\n创建评论:")
    new_comment = comment_api.create_comment(
        article_id=1,
        user_id=2,
        content="写得很好，继续加油！"
    )
    print(f"结果: {new_comment}")

    # 删除评论
    print("\n删除评论:")
    deleted_comment = comment_api.delete_comment(article_id=1, comment_id=1)
    print(f"结果: {deleted_comment}")

    print("\n4. 错误处理演示")
    print("-" * 40)

    # 模拟 API 错误
    print("\n模拟 API 错误（测试重试机制）:")
    try:
        # 这里可以模拟一个会失败的请求
        result = user_api.get_user(999)
        print(f"结果: {result}")
    except Exception as e:
        print(f"错误: {e}")

    print("\n" + "=" * 60)
    print("REST API 客户端封装演示完成！")
    print("=" * 60)
