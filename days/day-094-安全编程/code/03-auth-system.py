"""
Day 094 - 安全编程
03-auth-system.py: 安全认证系统实战

知识点:
  - 密码哈希与验证（bcrypt）
  - JWT Token 生成与验证
  - 登录速率限制（防暴力破解）
  - 安全的密码重置流程
  - 完整的认证系统架构
"""

import hashlib
import hmac
import json
import os
import secrets
import time
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict
from dataclasses import dataclass, field

# ============================================================
# JWT 实现（无依赖版本）
# ============================================================

class SimpleJWT:
    """
    简化的 JWT 实现（用于演示）
    生产环境请使用 PyJWT 或其他成熟库
    """
    
    def __init__(self, secret_key: str, algorithm: str = 'HS256'):
        self.secret_key = secret_key.encode()
        self.algorithm = algorithm
    
    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        """Base64 URL 安全编码"""
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode()
    
    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        """Base64 URL 安全解码"""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)
    
    def encode(self, payload: dict, expires_delta: timedelta = None) -> str:
        """创建 JWT Token"""
        header = {
            "alg": self.algorithm,
            "typ": "JWT"
        }
        
        # 添加过期时间
        if expires_delta:
            payload['exp'] = int((datetime.utcnow() + expires_delta).timestamp())
        
        payload['iat'] = int(datetime.utcnow().timestamp())
        
        # 编码 header 和 payload
        header_encoded = self._base64url_encode(json.dumps(header).encode())
        payload_encoded = self._base64url_encode(json.dumps(payload).encode())
        
        # 创建签名
        message = f"{header_encoded}.{payload_encoded}"
        signature = hmac.new(
            self.secret_key,
            message.encode(),
            hashlib.sha256
        ).digest()
        signature_encoded = self._base64url_encode(signature)
        
        return f"{header_encoded}.{payload_encoded}.{signature_encoded}"
    
    def decode(self, token: str) -> dict:
        """验证并解码 JWT Token"""
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("无效的 Token 格式")
        
        header_encoded, payload_encoded, signature_encoded = parts
        
        # 验证签名
        message = f"{header_encoded}.{payload_encoded}"
        expected_sig = hmac.new(
            self.secret_key,
            message.encode(),
            hashlib.sha256
        ).digest()
        actual_sig = self._base64url_decode(signature_encoded)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("签名验证失败")
        
        # 解码 payload
        payload = json.loads(self._base64url_decode(payload_encoded))
        
        # 检查过期时间
        if 'exp' in payload:
            if datetime.utcnow().timestamp() > payload['exp']:
                raise ValueError("Token 已过期")
        
        return payload


# ============================================================
# 密码哈希（简化版，模拟 bcrypt）
# ============================================================

class PasswordHasher:
    """
    密码哈希器
    注意：这里使用 PBKDF2 模拟 bcrypt 的慢哈希特性
    生产环境请直接使用 bcrypt 或 argon2
    """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码"""
        # 生成随机盐
        salt = secrets.token_hex(16)
        
        # 使用 PBKDF2-SHA256（100000 次迭代）
        dk = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            iterations=100000
        )
        
        # 格式: iterations:salt:hash
        return f"100000:{salt}:{dk.hex()}"
    
    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """验证密码"""
        try:
            iterations, salt, hash_hex = stored_hash.split(':')
            dk = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt.encode(),
                iterations=int(iterations)
            )
            return hmac.compare_digest(dk.hex(), hash_hex)
        except Exception:
            return False


# ============================================================
# 速率限制器
# ============================================================

class RateLimiter:
    """简单的内存速率限制器"""
    
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, list] = {}
    
    def is_allowed(self, key: str) -> tuple[bool, int]:
        """
        检查是否允许请求
        返回 (是否允许, 剩余等待秒数)
        """
        now = time.time()
        
        if key not in self.attempts:
            self.attempts[key] = []
        
        # 清理过期记录
        self.attempts[key] = [
            t for t in self.attempts[key]
            if now - t < self.window_seconds
        ]
        
        if len(self.attempts[key]) >= self.max_attempts:
            # 计算需要等待的时间
            oldest = self.attempts[key][0]
            wait_seconds = int(self.window_seconds - (now - oldest))
            return False, max(wait_seconds, 1)
        
        return True, 0
    
    def record_attempt(self, key: str):
        """记录一次尝试"""
        if key not in self.attempts:
            self.attempts[key] = []
        self.attempts[key].append(time.time())
    
    def reset(self, key: str):
        """重置计数器（登录成功后调用）"""
        self.attempts.pop(key, None)


# ============================================================
# 用户数据库（内存模拟）
# ============================================================

@dataclass
class User:
    user_id: str
    username: str
    email: str
    password_hash: str
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_login: Optional[str] = None


class UserDatabase:
    """用户数据库（内存模拟）"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.reset_tokens: Dict[str, dict] = {}  # token -> {user_id, expires}
        self.hasher = PasswordHasher()
    
    def create_user(self, username: str, email: str, password: str) -> tuple[bool, str]:
        """创建用户"""
        # 检查用户名是否已存在
        for user in self.users.values():
            if user.username == username:
                return False, "用户名已存在"
            if user.email == email:
                return False, "邮箱已被注册"
        
        # 验证密码强度
        if len(password) < 8:
            return False, "密码至少8位"
        
        # 创建用户
        user_id = secrets.token_hex(8)
        password_hash = self.hasher.hash_password(password)
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash
        )
        
        self.users[user_id] = user
        return True, "注册成功"
    
    def authenticate(self, username: str, password: str) -> tuple[bool, Optional[User]]:
        """验证用户名密码"""
        for user in self.users.values():
            if user.username == username and user.is_active:
                if self.hasher.verify_password(password, user.password_hash):
                    user.last_login = datetime.now().isoformat()
                    return True, user
        return False, None
    
    def generate_reset_token(self, email: str) -> Optional[str]:
        """生成密码重置 Token"""
        for user in self.users.values():
            if user.email == email and user.is_active:
                token = secrets.token_urlsafe(32)
                self.reset_tokens[token] = {
                    'user_id': user.user_id,
                    'expires': time.time() + 3600  # 1小时有效
                }
                return token
        return None
    
    def reset_password(self, token: str, new_password: str) -> tuple[bool, str]:
        """使用 Token 重置密码"""
        if token not in self.reset_tokens:
            return False, "无效的重置 Token"
        
        token_data = self.reset_tokens[token]
        
        if time.time() > token_data['expires']:
            del self.reset_tokens[token]
            return False, "Token 已过期"
        
        user_id = token_data['user_id']
        user = self.users.get(user_id)
        
        if not user:
            return False, "用户不存在"
        
        # 更新密码
        user.password_hash = self.hasher.hash_password(new_password)
        
        # 删除已使用的 Token
        del self.reset_tokens[token]
        
        return True, "密码重置成功"


# ============================================================
# 认证服务
# ============================================================

class AuthService:
    """认证服务"""
    
    def __init__(self, jwt_secret: str = "your-secret-key"):
        self.db = UserDatabase()
        self.jwt = SimpleJWT(jwt_secret)
        self.rate_limiter = RateLimiter(max_attempts=5, window_seconds=300)
    
    def register(self, username: str, email: str, password: str) -> dict:
        """用户注册"""
        success, message = self.db.create_user(username, email, password)
        return {"success": success, "message": message}
    
    def login(self, username: str, password: str, 
              client_ip: str = "unknown") -> dict:
        """用户登录"""
        # 检查速率限制
        allowed, wait_seconds = self.rate_limiter.is_allowed(client_ip)
        
        if not allowed:
            return {
                "success": False,
                "message": f"登录尝试过多，请 {wait_seconds} 秒后重试",
                "retry_after": wait_seconds
            }
        
        # 验证用户名密码
        success, user = self.db.authenticate(username, password)
        
        if success:
            # 重置速率限制
            self.rate_limiter.reset(client_ip)
            
            # 生成 JWT Token
            token = self.jwt.encode(
                {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email
                },
                expires_delta=timedelta(hours=24)
            )
            
            return {
                "success": True,
                "message": "登录成功",
                "token": token,
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email
                }
            }
        else:
            # 记录失败尝试
            self.rate_limiter.record_attempt(client_ip)
            return {
                "success": False,
                "message": "用户名或密码错误"
            }
    
    def verify_token(self, token: str) -> dict:
        """验证 Token"""
        try:
            payload = self.jwt.decode(token)
            return {"valid": True, "user": payload}
        except ValueError as e:
            return {"valid": False, "error": str(e)}
    
    def request_password_reset(self, email: str) -> dict:
        """请求密码重置"""
        token = self.db.generate_reset_token(email)
        
        if token:
            # 实际应用中应该发送邮件
            return {
                "success": True,
                "message": "重置链接已发送到您的邮箱",
                "reset_token": token  # 仅用于演示
            }
        else:
            return {
                "success": False,
                "message": "如果该邮箱已注册，您将收到重置链接"
            }
    
    def reset_password(self, token: str, new_password: str) -> dict:
        """重置密码"""
        success, message = self.db.reset_password(token, new_password)
        return {"success": success, "message": message}


# ============================================================
# 演示程序
# ============================================================

def demo():
    """演示完整的认证流程"""
    auth = AuthService(jwt_secret="demo-secret-key-2024")
    
    print("=" * 60)
    print("Day 094 - 安全认证系统演示")
    print("=" * 60)
    
    # 1. 注册
    print("\n--- 1. 用户注册 ---")
    result = auth.register("alice", "alice@example.com", "MyP@ssw0rd!")
    print(f"注册: {result}")
    
    result = auth.register("bob", "bob@example.com", "weak")
    print(f"弱密码注册: {result}")
    
    result = auth.register("alice", "alice2@example.com", "Another@Pass1")
    print(f"重复用户名: {result}")
    
    # 2. 登录
    print("\n--- 2. 用户登录 ---")
    result = auth.login("alice", "MyP@ssw0rd!", client_ip="192.168.1.1")
    print(f"正确登录: {result['success']} - {result['message']}")
    token = result.get('token')
    
    result = auth.login("alice", "wrong_password", client_ip="192.168.1.1")
    print(f"错误密码: {result['success']} - {result['message']}")
    
    # 3. 速率限制
    print("\n--- 3. 速率限制（暴力破解防护）---")
    for i in range(6):
        result = auth.login("alice", f"wrong{i}", client_ip="10.0.0.1")
        status = "✅" if result['success'] else "❌"
        print(f"  尝试 {i+1}: {status} {result['message']}")
    
    # 4. Token 验证
    print("\n--- 4. Token 验证 ---")
    if token:
        result = auth.verify_token(token)
        print(f"有效 Token: {result}")
        
        result = auth.verify_token("invalid.token.here")
        print(f"无效 Token: {result}")
    
    # 5. 密码重置
    print("\n--- 5. 密码重置 ---")
    result = auth.request_password_reset("alice@example.com")
    print(f"请求重置: {result['message']}")
    reset_token = result.get('reset_token')
    
    if reset_token:
        result = auth.reset_password(reset_token, "N3wP@ssw0rd!")
        print(f"重置密码: {result['message']}")
        
        # 用新密码登录
        result = auth.login("alice", "N3wP@ssw0rd!")
        print(f"新密码登录: {result['success']}")
        
        # 旧密码不能再用
        result = auth.login("alice", "MyP@ssw0rd!")
        print(f"旧密码登录: {result['success']} (应该失败)")
    
    print("\n✅ 认证系统演示完成")


if __name__ == '__main__':
    demo()
