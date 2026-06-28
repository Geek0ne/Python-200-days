"""
Day 42 - 03-type-safe-api.py
实战：类型安全的 API 封装

使用类型提示构建一个类型安全的 HTTP API 客户端。
完整功能：GET 请求、JSON 解析、数据校验、错误处理。
可直接运行（需要网络连接访问 GitHub API）。
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict, List, ClassVar
import json
import urllib.request
import urllib.error
import urllib.parse
import sys


# ============================================================
# 1. 数据模型（使用 dataclass + 类型注解）
# ============================================================

@dataclass
class GitHubUser:
    """GitHub 用户数据模型"""
    login: str
    id: int
    name: Optional[str] = None
    company: Optional[str] = None
    blog: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    public_repos: int = 0
    public_gists: int = 0
    followers: int = 0
    following: int = 0
    created_at: Optional[str] = None


@dataclass
class GitHubRepo:
    """GitHub 仓库数据模型"""
    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    is_fork: bool = False
    html_url: str = ""


@dataclass
class ApiResponse:
    """
    通用 API 响应包装。
    
    使用泛型风格：可以用 ApiResponse[GitHubUser] 表示用户响应，
    但为简洁起见当前使用 Optional[Any]。
    """
    success: bool
    status_code: int = 0
    data: Optional[Any] = None
    error: Optional[str] = None
    raw_json: Optional[str] = None  # 调试用


# ============================================================
# 2. API 客户端（类型安全）
# ============================================================

class GitHubClient:
    """
    类型安全的 GitHub REST API 客户端。
    
    所有公开方法都有完整的类型注解，
    返回 ApiResponse 包装后的结果，错误处理统一。
    """
    
    BASE_URL: ClassVar[str] = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None) -> None:
        """
        初始化客户端。
        
        Args:
            token: GitHub 个人访问令牌（可选，有令牌可提高 API 限额）
        """
        self._token: Optional[str] = token
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers: Dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Learn-Python-TypeSafe-API",
        }
        if self._token:
            headers["Authorization"] = f"token {self._token}"
        return headers
    
    def _request(self, endpoint: str) -> ApiResponse:
        """
        发送 GET 请求的通用方法。
        
        Args:
            endpoint: API 端点（如 /users/octocat）
            
        Returns:
            ApiResponse 包装的响应
        """
        url: str = f"{self.BASE_URL}{endpoint}"
        
        try:
            req = urllib.request.Request(
                url,
                headers=self._build_headers(),
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code: int = resp.status
                body: str = resp.read().decode("utf-8")
                data: Any = json.loads(body)
                return ApiResponse(
                    success=True,
                    status_code=status_code,
                    data=data,
                    raw_json=body,
                )
                
        except urllib.error.HTTPError as e:
            error_body: str = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            return ApiResponse(
                success=False,
                status_code=e.code,
                error=f"HTTP {e.code}: {e.reason}",
                raw_json=error_body,
            )
            
        except urllib.error.URLError as e:
            return ApiResponse(
                success=False,
                error=f"网络错误: {e.reason}",
            )
            
        except json.JSONDecodeError as e:
            return ApiResponse(
                success=False,
                error=f"JSON 解析错误: {e}",
            )
            
        except Exception as e:
            return ApiResponse(
                success=False,
                error=f"未知错误: {e}",
            )
    
    def get_user(self, username: str) -> ApiResponse:
        """
        获取 GitHub 用户信息。
        
        Args:
            username: GitHub 用户名
            
        Returns:
            ApiResponse，成功时 data 为原始 JSON 字典
        """
        return self._request(f"/users/{urllib.parse.quote(username)}")
    
    def get_repos(self, username: str, per_page: int = 10) -> ApiResponse:
        """
        获取用户的公开仓库列表。
        
        Args:
            username: GitHub 用户名
            per_page: 每页数量（默认 10，最多 100）
            
        Returns:
            ApiResponse，成功时 data 为仓库列表 JSON
        """
        return self._request(
            f"/users/{urllib.parse.quote(username)}/repos"
            f"?per_page={per_page}&sort=updated"
        )
    
    def get_repo(self, owner: str, repo: str) -> ApiResponse:
        """
        获取单个仓库信息。
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            
        Returns:
            ApiResponse，成功时 data 为仓库 JSON
        """
        return self._request(f"/repos/{owner}/{repo}")


# ============================================================
# 3. 数据解析器（将 JSON 转化为类型安全的数据模型）
# ============================================================

class GitHubParser:
    """
    将原始 API JSON 响应解析为类型安全的数据模型。
    所有方法都返回 Optional[数据模型]，调用方需要处理 None。
    """
    
    @staticmethod
    def parse_user(resp: ApiResponse) -> Optional[GitHubUser]:
        """
        将 ApiResponse 解析为 GitHubUser 对象。
        
        Args:
            resp: API 响应
            
        Returns:
            GitHubUser 对象，解析失败或请求失败时返回 None
        """
        if not resp.success or not isinstance(resp.data, dict):
            return None
        
        data: Dict[str, Any] = resp.data
        
        try:
            return GitHubUser(
                login=data.get("login", ""),
                id=data.get("id", 0),
                name=data.get("name"),
                company=data.get("company"),
                blog=data.get("blog"),
                location=data.get("location"),
                email=data.get("email"),
                bio=data.get("bio"),
                public_repos=data.get("public_repos", 0),
                public_gists=data.get("public_gists", 0),
                followers=data.get("followers", 0),
                following=data.get("following", 0),
                created_at=data.get("created_at"),
            )
        except (TypeError, ValueError) as e:
            print(f"  [警告] 解析用户数据失败: {e}")
            return None
    
    @staticmethod
    def parse_repos(resp: ApiResponse) -> List[GitHubRepo]:
        """
        将 ApiResponse 解析为 GitHubRepo 列表。
        
        Args:
            resp: API 响应
            
        Returns:
            GitHubRepo 列表，解析失败时返回空列表
        """
        if not resp.success or not isinstance(resp.data, list):
            return []
        
        repos: List[GitHubRepo] = []
        for item in resp.data:
            if not isinstance(item, dict):
                continue
            try:
                repo = GitHubRepo(
                    id=item.get("id", 0),
                    name=item.get("name", ""),
                    full_name=item.get("full_name", ""),
                    description=item.get("description"),
                    language=item.get("language"),
                    stars=item.get("stargazers_count", 0),
                    forks=item.get("forks_count", 0),
                    open_issues=item.get("open_issues_count", 0),
                    is_fork=item.get("fork", False),
                    html_url=item.get("html_url", ""),
                )
                repos.append(repo)
            except (TypeError, ValueError):
                continue
        
        return repos


# ============================================================
# 4. 主程序
# ============================================================

def display_user_info(user: GitHubUser) -> None:
    """显示用户信息的辅助函数"""
    print(f"  ▸ 登录名: {user.login}")
    print(f"  ▸ ID:     {user.id}")
    print(f"  ▸ 姓名:   {user.name or '(未设置)'}")
    print(f"  ▸ 公司:   {user.company or '(未设置)'}")
    print(f"  ▸ 位置:   {user.location or '(未设置)'}")
    print(f"  ▸ BIO:    {user.bio or '(无)'}")
    print(f"  ▸ 仓库数: {user.public_repos}")
    print(f"  ▸ 关注者: {user.followers}")
    print(f"  ▸ 关注中: {user.following}")
    print()


def display_repos(repos: List[GitHubRepo], limit: int = 5) -> None:
    """显示仓库列表的辅助函数"""
    if not repos:
        print("  (无仓库数据)")
        return
    
    for repo in repos[:limit]:
        star_str: str = "⭐" if repo.stars > 0 else ""
        lang: str = f" [{repo.language}]" if repo.language else ""
        desc: str = f" — {repo.description}" if repo.description else ""
        print(f"  {star_str} {repo.name}{lang}{desc}")
    
    if len(repos) > limit:
        print(f"  ... 还有 {len(repos) - limit} 个仓库")
    print()


def main() -> None:
    """
    主函数：演示类型安全 API 客户端的使用。
    
    尝试查询 GitHub 用户 "octocat"（GitHub 的吉祥物账号）。
    """
    print("=" * 65)
    print("  GitHub 类型安全 API 客户端演示")
    print("=" * 65)
    print()
    
    # 创建客户端和解析器
    client = GitHubClient()
    parser = GitHubParser()
    
    # 可以根据需要修改用户名为其他 GitHub 用户
    username: str = "octocat"
    
    # === 1. 获取用户信息 ===
    print(f"📡 正在查询用户: {username}")
    user_resp: ApiResponse = client.get_user(username)
    
    if not user_resp.success:
        print(f"❌ 请求失败: {user_resp.error}")
        if user_resp.status_code == 403:
            print("   提示: API 速率限制已触发，请稍后再试或设置 token")
        elif user_resp.status_code == 404:
            print(f"   用户 '{username}' 不存在")
        sys.exit(1)
    
    # 解析为类型安全的 GitHubUser 对象
    user: Optional[GitHubUser] = parser.parse_user(user_resp)
    
    if user is None:
        print("❌ 无法解析用户数据")
        sys.exit(1)
    
    print(f"✅ 成功获取用户信息！")
    display_user_info(user)
    
    # === 2. 获取仓库列表 ===
    print(f"📡 正在查询 {username} 的仓库...")
    repos_resp: ApiResponse = client.get_repos(username)
    
    repos: List[GitHubRepo] = parser.parse_repos(repos_resp)
    print(f"✅ 获取到 {len(repos)} 个仓库（显示前 5 个）：")
    display_repos(repos)
    
    # === 3. 详细展示一个仓库 ===
    if repos:
        first_repo: GitHubRepo = repos[0]
        print(f"📡 正在查询仓库详情: {first_repo.full_name}")
        repo_resp: ApiResponse = client.get_repo(
            username, first_repo.name
        )
        
        if repo_resp.success:
            print(f"  ▸ 仓库: {first_repo.full_name}")
            print(f"  ▸ URL:  {first_repo.html_url}")
            print(f"  ▸ ⭐ {first_repo.stars}    🍴 {first_repo.forks}")
            print(f"  ▸ 语言: {first_repo.language or '未指定'}")
        else:
            print(f"  ⚠ 详情查询失败: {repo_resp.error}")
    
    print()
    print("=" * 65)
    print("  ✅ 类型安全 API 客户端演示完成")
    print("=" * 65)


if __name__ == "__main__":
    main()
