#!/usr/bin/env python3
"""
02 - 用户认证与 JWT 实战

本示例演示完整用户认证系统：
1. Werkzeug 密码哈希（不可逆存储）
2. 用户注册与登录
3. JWT Token 签发与验证
4. @token_required 保护路由
5. Token 刷新机制
6. 常见安全陷阱与避坑

运行方式：
    python3 02-user-auth-jwt.py

测试 API（使用 curl 或 Postman）：
    见末尾的测试命令

需要先安装依赖：
    pip install flask flask-sqlalchemy pyjwt
"""

from flask import Flask, jsonify, request, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta, timezone
import jwt
import re
import sys

# ============================================================
# 应用初始化
# ============================================================

app = Flask(__name__)

# ⚠️ 生产环境中 SECRET_KEY 应通过环境变量注入，不要写在代码里
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production!@#$%'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auth_demo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Token 配置
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 30          # 30 分钟
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 7           # 7 天

db = SQLAlchemy(app)


# ============================================================
# 用户模型
# ============================================================

class User(db.Model):
    """用户模型"""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # user / admin
    is_active = db.Column(db.Boolean, default=True)   # 账号是否启用
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    last_login_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        """
        设置密码哈希
        
        Werkzeug 使用 PBKDF2-SHA256 算法：
        - 自动生成随机盐值（salt）
        - 默认 600000 次迭代
        - 输出格式：method$salt$hash
        """
        if len(password) < 6:
            raise ValueError('密码长度不能少于 6 个字符')
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_sensitive=False):
        """序列化为字典（敏感信息默认不返回）"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_sensitive:
            data['last_login_at'] = (
                self.last_login_at.isoformat()
                if self.last_login_at
                else None
            )
            data['is_active'] = self.is_active
        return data

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


# ============================================================
# JWT Token 工具函数
# ============================================================

def create_access_token(user_id):
    """生成访问 Token（短期）"""
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user_id,                                                 # subject：用户 ID
        'iat': now,                                                     # 签发时间
        'exp': now + timedelta(minutes=app.config['JWT_ACCESS_TOKEN_EXPIRES']),  # 过期时间
        'type': 'access',                                               # Token 类型
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def create_refresh_token(user_id):
    """生成刷新 Token（长期，用于获取新的 access token）"""
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user_id,
        'iat': now,
        'exp': now + timedelta(days=app.config['JWT_REFRESH_TOKEN_EXPIRES']),
        'type': 'refresh',
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def decode_token(token):
    """解码并验证 JWT Token"""
    try:
        payload = jwt.decode(
            token,
            app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, 'Token 已过期'
    except jwt.InvalidTokenError:
        return None, '无效的 Token'


# ============================================================
# JWT 认证装饰器
# ============================================================

def token_required(f):
    """
    JWT 认证装饰器
    
    使用方式：
        @app.route('/protected')
        @token_required
        def protected_route(current_user):
            return jsonify({'user': current_user.to_dict()})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        # 检查 Authorization 头
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': '认证失败',
                'message': '请提供有效的 Bearer Token（格式：Authorization: Bearer <token>）',
                'code': 'MISSING_TOKEN'
            }), 401

        token = auth_header.split(' ')[1]

        # 解码 Token
        payload, error = decode_token(token)
        if error:
            return jsonify({
                'error': '认证失败',
                'message': error,
                'code': 'TOKEN_EXPIRED' if '过期' in error else 'INVALID_TOKEN'
            }), 401

        # 验证 Token 类型
        if payload.get('type') != 'access':
            return jsonify({
                'error': '认证失败',
                'message': '请使用 access token，不要使用 refresh token',
                'code': 'WRONG_TOKEN_TYPE'
            }), 401

        # 查找用户
        user = User.query.get(payload['sub'])
        if not user:
            return jsonify({
                'error': '认证失败',
                'message': '用户不存在',
                'code': 'USER_NOT_FOUND'
            }), 401

        if not user.is_active:
            return jsonify({
                'error': '账号已停用',
                'message': '请联系管理员',
                'code': 'ACCOUNT_DISABLED'
            }), 403

        # 将当前用户注入函数参数
        return f(user, *args, **kwargs)

    return decorated


def admin_required(f):
    """管理员权限装饰器（在 token_required 基础上再检查角色）"""
    @wraps(f)
    @token_required
    def decorated(current_user, *args, **kwargs):
        if current_user.role != 'admin':
            return jsonify({
                'error': '权限不足',
                'message': '需要管理员权限',
                'code': 'FORBIDDEN'
            }), 403
        return f(current_user, *args, **kwargs)
    return decorated


# ============================================================
# 辅助函数
# ============================================================

def validate_email(email):
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username):
    """验证用户名格式（3-20 位字母数字下划线）"""
    if len(username) < 3 or len(username) > 20:
        return False
    pattern = r'^[a-zA-Z0-9_\u4e00-\u9fa5]+$'  # 支持中文
    return re.match(pattern, username) is not None


# ============================================================
# 认证路由
# ============================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    用户注册
    
    请求体：
        {
            "username": "alice",
            "email": "alice@example.com",
            "password": "securePass123"
        }
    
    响应（201 Created）：
        {
            "message": "注册成功",
            "data": {
                "user": { ... },
                "access_token": "...",
                "refresh_token": "..."
            }
        }
    """
    data = request.get_json()

    # ─── 参数验证 ───
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    # 逐个字段验证，给出明确的错误信息
    if not username:
        return jsonify({'error': '用户名是必填的'}), 400
    if not validate_username(username):
        return jsonify({
            'error': '用户名格式无效',
            'message': '用户名长度 3-20 位，支持字母、数字、下划线或中文'
        }), 400

    if not email:
        return jsonify({'error': '邮箱是必填的'}), 400
    if not validate_email(email):
        return jsonify({'error': '邮箱格式不正确'}), 400

    if not password or len(password) < 6:
        return jsonify({'error': '密码长度不能少于 6 个字符'}), 400

    # ─── 检查重复 ───
    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已被注册'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': '邮箱已被注册'}), 409

    # ─── 创建用户 ───
    user = User(
        username=username,
        email=email,
        role='user'
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # ─── 生成 Token ───
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    print(f'✅ 新用户注册: {user.username}')
    return jsonify({
        'message': '注册成功',
        'data': {
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token,
        }
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    用户登录
    
    请求体：
        {
            "username": "alice",
            "password": "securePass123"
        }
    
    支持用用户名或邮箱登录
    """
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '用户名/邮箱和密码是必填的'}), 400

    login_id = data['username'].strip()
    password = data['password']

    # 支持用户名或邮箱登录
    user = User.query.filter(
        (User.username == login_id) | (User.email == login_id)
    ).first()

    if not user or not user.check_password(password):
        # ⚠️ 不要告诉用户是「用户名错误」还是「密码错误」
        # 防止攻击者通过错误信息枚举有效用户名
        return jsonify({'error': '用户名或密码错误'}), 401

    if not user.is_active:
        return jsonify({'error': '账号已被停用'}), 403

    # 更新最后登录时间
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    # 生成 Token
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    print(f'🔑 用户登录: {user.username}')
    return jsonify({
        'message': '登录成功',
        'data': {
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token,
        }
    })


@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    """
    刷新 Access Token
    
    请求头：
        Authorization: Bearer <refresh_token>
    
    响应：
        { "access_token": "new_token" }
    """
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return jsonify({'error': '请提供 Refresh Token'}), 401

    token = auth_header.split(' ')[1]
    payload, error = decode_token(token)

    if error:
        return jsonify({'error': error}), 401

    # 验证是 refresh token
    if payload.get('type') != 'refresh':
        return jsonify({'error': '请使用 Refresh Token，不要使用 Access Token'}), 401

    # 验证用户还存在
    user = User.query.get(payload['sub'])
    if not user or not user.is_active:
        return jsonify({'error': '用户不存在或已停用'}), 401

    # 签发新的 access token
    new_access_token = create_access_token(user.id)

    return jsonify({
        'message': 'Token 已刷新',
        'access_token': new_access_token,
    })


@app.route('/api/auth/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """获取当前用户信息（需要登录）"""
    return jsonify({
        'data': current_user.to_dict(include_sensitive=True)
    })


# ============================================================
# 受保护的管理员路由
# ============================================================

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def list_users(current_user):
    """获取所有用户列表（管理员专用）"""
    users = User.query.all()
    return jsonify({
        'data': [u.to_dict(include_sensitive=True) for u in users],
        'total': len(users),
    })


@app.route('/api/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(current_user, user_id):
    """启用/停用用户（管理员专用）"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    if user.id == current_user.id:
        return jsonify({'error': '不能停用自己的账号'}), 400

    user.is_active = not user.is_active
    db.session.commit()

    status = '已启用' if user.is_active else '已停用'
    print(f'⚙️ 管理员 {current_user.username} 将用户 {user.username} {status}')
    return jsonify({
        'message': f'用户 {user.username} {status}',
        'is_active': user.is_active,
    })


# ============================================================
# 避坑演示：常见错误
# ============================================================

# ❌ 错误 1：在 URL 中传递 Token
# 不要这样做——URL 会被服务器日志记录
# GET /api/resource?token=xxx ← 不安全！

# ❌ 错误 2：前端存储 Token 不当
# Web 应用：用 httpOnly Cookie 而不是 localStorage（防止 XSS 窃取）
# 移动端：使用系统安全的密钥存储

# ❌ 错误 3：不校验 Token 类型
# 始终检查 payload['type'] 确保 access/refresh 各司其职

# ❌ 错误 4：密码明文存储
# 永远使用 generate_password_hash——Werkzeug 已经做好了


# ============================================================
# 初始化数据库并启动
# ============================================================

def init_db():
    """初始化数据库并创建测试用户"""
    with app.app_context():
        db.create_all()

        # 创建测试用户
        if User.query.count() == 0:
            # 普通用户
            alice = User(
                username='alice',
                email='alice@example.com',
                role='user'
            )
            alice.set_password('alice123')
            db.session.add(alice)

            # 管理员
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)

            db.session.commit()
            print('✅ 测试用户已创建: alice / admin（密码: xxx123）')


if __name__ == '__main__':
    init_db()

    print('\n' + '=' * 60)
    print('🚀 JWT 认证演示服务已启动')
    print('=' * 60)
    print(f'\n测试命令（在另一个终端运行）：')
    print(f'\n# 1. 注册新用户')
    print('curl -X POST http://localhost:5000/api/auth/register \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"username":"test","email":"test@test.com","password":"test123"}\'')
    print(f'\n# 2. 登录')
    print('curl -X POST http://localhost:5000/api/auth/login \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"username":"alice","password":"alice123"}\'')
    print(f'\n# 3. 获取个人信息（替换 <token>）')
    print('curl http://localhost:5000/api/auth/profile \\')
    print('  -H "Authorization: Bearer <token>"')
    print(f'\n# 4. 管理员查看所有用户')
    print('curl http://localhost:5000/api/admin/users \\')
    print('  -H "Authorization: Bearer <admin_token>"')
    print(f'\n# 5. 刷新 Token')
    print('curl -X POST http://localhost:5000/api/auth/refresh \\')
    print('  -H "Authorization: Bearer <refresh_token>"')
    print()

    app.run(debug=True, host='0.0.0.0', port=5000)
