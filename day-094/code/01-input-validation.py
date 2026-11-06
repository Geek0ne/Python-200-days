"""
Day 094 - 安全编程
01-input-validation.py: 输入验证与注入防护

知识点:
  - SQL 注入原理与防护
  - 命令注入防护
  - 路径遍历防护
  - XSS 防护
  - 输入验证最佳实践
"""

import re
import os
import html
import sqlite3
import subprocess
import tempfile
from typing import Optional

# ============================================================
# 第一部分：输入验证工具
# ============================================================

class InputValidator:
    """通用输入验证器"""
    
    @staticmethod
    def validate_email(email: str) -> tuple[bool, str]:
        """验证邮箱格式"""
        if not email or not isinstance(email, str):
            return False, "邮箱不能为空"
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "邮箱格式不正确"
        
        if len(email) > 254:
            return False, "邮箱太长"
        
        return True, ""
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """
        验证用户名
        规则：3-20位，只能包含字母、数字、下划线
        """
        if not username or not isinstance(username, str):
            return False, "用户名不能为空"
        
        if len(username) < 3:
            return False, "用户名至少3个字符"
        
        if len(username) > 20:
            return False, "用户名最多20个字符"
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "用户名只能包含字母、数字和下划线"
        
        # 不能以数字开头
        if username[0].isdigit():
            return False, "用户名不能以数字开头"
        
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """
        验证密码强度
        规则：最少8位，包含大小写字母、数字、特殊字符中的至少3类
        """
        if not password or not isinstance(password, str):
            return False, "密码不能为空"
        
        if len(password) < 8:
            return False, "密码至少8位"
        
        if len(password) > 128:
            return False, "密码最多128位"
        
        # 检查字符类别
        categories = 0
        if re.search(r'[a-z]', password):
            categories += 1
        if re.search(r'[A-Z]', password):
            categories += 1
        if re.search(r'[0-9]', password):
            categories += 1
        if re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
            categories += 1
        
        if categories < 3:
            return False, "密码需要包含大小写字母、数字、特殊字符中的至少3类"
        
        return True, ""
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """HTML 转义，防止 XSS"""
        if not text:
            return ""
        return html.escape(text, quote=True)
    
    @staticmethod
    def validate_integer(value: str, min_val: int = None, 
                         max_val: int = None) -> tuple[bool, int]:
        """验证并转换整数"""
        try:
            num = int(value)
            if min_val is not None and num < min_val:
                return False, 0
            if max_val is not None and num > max_val:
                return False, 0
            return True, num
        except (ValueError, TypeError):
            return False, 0
    
    @staticmethod
    def validate_json_field(data: dict, schema: dict) -> tuple[bool, str]:
        """
        验证 JSON 数据字段
        schema: {"field_name": {"type": str, "required": True, "max_length": 100}}
        """
        for field_name, rules in schema.items():
            # 检查必填字段
            if rules.get('required', False) and field_name not in data:
                return False, f"缺少必填字段: {field_name}"
            
            if field_name in data:
                value = data[field_name]
                
                # 检查类型
                expected_type = rules.get('type')
                if expected_type and not isinstance(value, expected_type):
                    return False, f"字段 {field_name} 类型错误"
                
                # 检查长度
                max_length = rules.get('max_length')
                if max_length and isinstance(value, str) and len(value) > max_length:
                    return False, f"字段 {field_name} 超过最大长度 {max_length}"
        
        return True, ""


# ============================================================
# 第二部分：安全的数据库查询
# ============================================================

class SecureDatabase:
    """安全的数据库操作封装"""
    
    def __init__(self, db_path: str = ':memory:'):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def add_user(self, username: str, email: str) -> tuple[bool, str]:
        """安全地添加用户"""
        # 先验证输入
        validator = InputValidator()
        
        valid, msg = validator.validate_username(username)
        if not valid:
            return False, msg
        
        valid, msg = validator.validate_email(email)
        if not valid:
            return False, msg
        
        try:
            # ✅ 使用参数化查询，防止 SQL 注入
            self.conn.execute(
                "INSERT INTO users (username, email) VALUES (?, ?)",
                (username, email)
            )
            self.conn.commit()
            return True, "添加成功"
        except sqlite3.IntegrityError:
            return False, "用户名已存在"
    
    def find_user(self, username: str) -> Optional[dict]:
        """
        安全地查询用户
        
        ❌ 危险的写法:
        sql = f"SELECT * FROM users WHERE username='{username}'"
        # 如果 username = "'; DROP TABLE users; --"
        # 就会导致 SQL 注入
        
        ✅ 安全的写法（参数化查询）:
        """
        # 验证输入
        valid, _ = InputValidator.validate_username(username)
        if not valid:
            return None
        
        cursor = self.conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def search_users(self, keyword: str) -> list:
        """安全的模糊搜索"""
        if not keyword or not isinstance(keyword, str):
            return []
        
        # 验证并清理输入
        keyword = keyword.strip()
        if len(keyword) > 50:
            keyword = keyword[:50]
        
        # 使用参数化查询
        cursor = self.conn.execute(
            "SELECT * FROM users WHERE username LIKE ? OR email LIKE ?",
            (f"%{keyword}%", f"%{keyword}%")
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        self.conn.close()


# ============================================================
# 第三部分：命令注入防护
# ============================================================

class SafeCommandExecutor:
    """安全的命令执行器"""
    
    @staticmethod
    def list_files_safe(directory: str) -> tuple[bool, str]:
        """
        安全地列出目录文件
        
        ❌ 危险：
        subprocess.run(f"ls {directory}", shell=True)
        # 如果 directory = "; rm -rf /" 就完了
        
        ✅ 安全：
        """
        # 验证目录路径
        directory = os.path.normpath(directory)
        
        # 检查路径遍历
        if '..' in directory:
            return False, "路径不能包含 .."
        
        if not os.path.isdir(directory):
            return False, "目录不存在"
        
        # 使用列表形式，不使用 shell=True
        try:
            result = subprocess.run(
                ["ls", "-la", directory],
                capture_output=True,
                text=True,
                timeout=5,  # 5秒超时
                shell=False  # 关键：不使用 shell
            )
            return True, result.stdout
        except subprocess.TimeoutExpired:
            return False, "命令执行超时"
        except Exception as e:
            return False, f"执行失败: {e}"
    
    @staticmethod
    def safe_system_info() -> dict:
        """安全地获取系统信息"""
        info = {}
        
        # 使用 subprocess 安全获取信息
        try:
            result = subprocess.run(
                ["uname", "-a"],
                capture_output=True,
                text=True,
                timeout=5
            )
            info['system'] = result.stdout.strip()
        except Exception:
            info['system'] = "获取失败"
        
        try:
            import platform
            info['python'] = platform.python_version()
            info['platform'] = platform.platform()
        except Exception:
            pass
        
        return info


# ============================================================
# 第四部分：路径遍历防护
# ============================================================

class SafeFileHandler:
    """安全的文件操作"""
    
    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)
    
    def safe_read(self, filename: str) -> tuple[bool, str]:
        """
        安全地读取文件
        
        ❌ 危险：
        with open(os.path.join(base_dir, filename)) as f:
            return f.read()
        # 如果 filename = "../../etc/passwd" 就泄露了
        
        ✅ 安全：
        """
        # 规范化路径
        target_path = os.path.normpath(
            os.path.join(self.base_dir, filename)
        )
        
        # 验证路径没有逃出 base_dir
        if not target_path.startswith(self.base_dir):
            return False, "禁止访问 base 目录之外的文件"
        
        if not os.path.isfile(target_path):
            return False, "文件不存在"
        
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return True, content
        except Exception as e:
            return False, f"读取失败: {e}"
    
    def safe_write(self, filename: str, content: str) -> tuple[bool, str]:
        """安全地写入文件"""
        # 清理文件名
        filename = os.path.basename(filename)  # 去掉路径部分
        
        if not filename or filename.startswith('.'):
            return False, "无效的文件名"
        
        target_path = os.path.normpath(
            os.path.join(self.base_dir, filename)
        )
        
        if not target_path.startswith(self.base_dir):
            return False, "路径越界"
        
        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, f"写入成功: {filename}"
        except Exception as e:
            return False, f"写入失败: {e}"


# ============================================================
# 主程序演示
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Day 094 - 输入验证与注入防护演示")
    print("=" * 60)
    
    # 1. 输入验证
    print("\n--- 1. 输入验证 ---")
    v = InputValidator()
    
    test_emails = [
        "user@example.com",
        "invalid-email",
        "@no-local.com",
        "a" * 255 + "@long.com",
    ]
    for email in test_emails:
        valid, msg = v.validate_email(email)
        print(f"  {email:30s} → {'✅' if valid else '❌'} {msg}")
    
    test_usernames = ["alice", "ab", "a" * 21, "1admin", "user-name"]
    for name in test_usernames:
        valid, msg = v.validate_username(name)
        print(f"  {name:20s} → {'✅' if valid else '❌'} {msg}")
    
    # 2. HTML 转义
    print("\n--- 2. XSS 防护 ---")
    xss_input = '<script>alert("XSS")</script>'
    safe = v.sanitize_html(xss_input)
    print(f"  输入: {xss_input}")
    print(f"  转义: {safe}")
    
    # 3. 数据库安全查询
    print("\n--- 3. SQL 注入防护 ---")
    db = SecureDatabase()
    
    # 添加测试用户
    db.add_user("alice", "alice@example.com")
    db.add_user("bob", "bob@example.com")
    
    # 正常查询
    user = db.find_user("alice")
    print(f"  正常查询 alice: {user}")
    
    # SQL 注入尝试
    malicious_input = "'; DROP TABLE users; --"
    user = db.find_user(malicious_input)
    print(f"  SQL 注入尝试: {user} (被拦截)")
    
    # 验证数据库仍然正常
    user = db.find_user("bob")
    print(f"  数据库正常: {user}")
    
    db.close()
    
    # 4. 路径遍历防护
    print("\n--- 4. 路径遍历防护 ---")
    handler = SafeFileHandler("/tmp/test_safe_files")
    
    # 正常写入
    handler.safe_write("test.txt", "Hello, Security!")
    
    # 正常读取
    success, content = handler.safe_read("test.txt")
    print(f"  正常读取: {success}, 内容: {content[:30]}")
    
    # 路径遍历尝试
    success, content = handler.safe_read("../../etc/passwd")
    print(f"  路径遍历: {success}, {content}")
    
    # 5. 命令注入防护
    print("\n--- 5. 命令注入防护 ---")
    executor = SafeCommandExecutor()
    
    # 正常执行
    success, output = executor.list_files_safe("/tmp")
    print(f"  列出文件: {success}, 行数: {len(output.splitlines())}")
    
    # 命令注入尝试
    success, output = executor.list_files_safe("; echo hacked")
    print(f"  命令注入: {success}, {output}")
    
    print("\n✅ 安全编程演示完成")
