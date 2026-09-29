#!/usr/bin/env python3
"""
04 - Flask 进阶 API 速查与对比表

本文件不是可运行脚本，而是 Flask 进阶开发中常用 API 的集中速查参考。

目录：
    1. SQLAlchemy ORM API 速查
    2. 数据库关系配置
    3. 查询 API
    4. JWT 认证 API
    5. RESTful API 设计模式
    6. 状态码速查
"""

# ============================================================
# 1. SQLAlchemy ORM API 速查
# ============================================================

# ─── 配置 ───
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

"""
app = Flask(__name__)

# 常用数据库 URI
# SQLite:   sqlite:///app.db
# PostgreSQL: postgresql://user:pass@host:5432/dbname
# MySQL:     mysql+pymysql://user:pass@host:3306/dbname

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True  # 打印 SQL（调试用）

db = SQLAlchemy(app)
"""

# ─── 列类型 ───
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, Date, JSON, PickleType, BigInteger
)

"""
column = Column(Integer, primary_key=True)          # 主键
column = Column(String(80), unique=True)            # 唯一约束
column = Column(String(80), nullable=False)         # 非空
column = Column(String(80), default='default_val')  # 默认值
column = Column(Integer, index=True)                # 索引
column = Column(DateTime, default=func.now())       # 默认当前时间
column = Column(DateTime, onupdate=func.now())      # 更新时自动修改
column = Column(Integer, ForeignKey('users.id'))    # 外键
"""

# ─── 关系配置 ───
"""
# 一对多
class User(db.Model):
    id = Column(Integer, primary_key=True)
    posts = db.relationship('Post', backref='author', lazy='select')
    # backref='author' → Post 模型自动获得 .author 属性

class Post(db.Model):
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))

# 多对多（需中间表）
post_tag = db.Table('post_tag',
    Column('post_id', Integer, ForeignKey('post.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tag.id'), primary_key=True),
)

class Post(db.Model):
    tags = db.relationship('Tag', secondary=post_tag, backref='posts')

class Tag(db.Model):
    id = Column(Integer, primary_key=True)
"""

# ─── lazy 加载模式对比 ───
"""
lazy='select'     # 默认。访问时查询（N+1 问题）
lazy='joined'     # LEFT JOIN 预加载（1 次查询）
lazy='subquery'   # 子查询预加载
lazy='dynamic'    # 返回 Query 对象（支持链式过滤）
"""


# ============================================================
# 2. 查询 API
# ============================================================

# ─── 基本查询 ───
"""
# 获取全部
Model.query.all()

# 按主键
Model.query.get(1)

# 条件过滤
Model.query.filter_by(name='Alice').all()          # 等值
Model.query.filter(Model.name == 'Alice').all()    # 通用
Model.query.filter(Model.age > 18).all()           # 大于
Model.query.filter(Model.name.like('%alice%')).all()  # LIKE

# 多条件
Model.query.filter_by(name='Alice', active=True)
Model.query.filter(Model.name == 'Alice', Model.age > 18)

# IN 查询
Model.query.filter(Model.id.in_([1, 2, 3])).all()

# 排序
Model.query.order_by(Model.created_at.desc()).all()
Model.query.order_by(Model.priority.desc(), Model.created_at).all()

# 限制与偏移
Model.query.limit(10).offset(20).all()

# 聚合
from sqlalchemy import func
db.session.query(func.count(Model.id)).scalar()
db.session.query(func.avg(Model.price)).scalar()

# 分组
db.session.query(Model.category, func.count(Model.id)) \\
    .group_by(Model.category).all()

# 分页
page = Model.query.order_by(Model.id).paginate(
    page=1, per_page=20, error_out=False
)
page.items      # 当前页数据
page.total      # 总条数
page.pages      # 总页数
page.has_next   # 是否有下一页
page.has_prev   # 是否有上一页
"""

# ─── 事务管理 ───
"""
# 自动事务（推荐）
try:
    db.session.add(obj)
    db.session.commit()
except Exception:
    db.session.rollback()
    raise

# 嵌套事务（保存点）
with db.session.begin_nested():
    db.session.add(obj1)
    db.session.add(obj2)
# 内部失败会自动回滚到保存点，外部可继续
"""


# ============================================================
# 3. JWT 认证 API
# ============================================================

# ─── 密码哈希 ───
from werkzeug.security import generate_password_hash, check_password_hash

"""
# 注册时：存哈希，不存明文
password_hash = generate_password_hash('user_password')
# ➜ 'pbkdf2:sha256:600000$r4nd0msalt$hash....'

# 登录时：验证哈希
is_valid = check_password_hash(stored_hash, input_password)

# 参数调整（默认 600000 次迭代）
password_hash = generate_password_hash('pw', method='pbkdf2:sha256:300000')
"""

# ─── JWT ───
import jwt
from datetime import datetime, timedelta, timezone

"""
# 生成 Token
SECRET_KEY = 'your-secret-key'
payload = {
    'sub': user_id,
    'iat': datetime.now(timezone.utc),
    'exp': datetime.now(timezone.utc) + timedelta(hours=24),
}
token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

# 验证 Token
try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    user_id = payload['sub']
except jwt.ExpiredSignatureError:
    # Token 过期
    pass
except jwt.InvalidTokenError:
    # Token 无效
    pass
"""

# ─── 认证装饰器模板 ───
from functools import wraps
from flask import request, jsonify

"""
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': '未认证'}), 401
        token = auth.split(' ')[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(payload['sub'])
        except:
            return jsonify({'error': 'Token 无效或已过期'}), 401
        return f(current_user, *args, **kwargs)
    return decorated
"""


# ============================================================
# 4. RESTful API 设计模式
# ============================================================

# ─── 资源路由映射 ───
"""
HTTP 方法 | URL            | 操作   | 状态码
----------|----------------|--------|--------
GET       | /todos         | 列表   | 200
POST      | /todos         | 创建   | 201
GET       | /todos/1       | 详情   | 200
PUT       | /todos/1       | 全量更新 | 200
PATCH     | /todos/1       | 局部更新 | 200
DELETE    | /todos/1       | 删除   | 204

# 搜索/过滤
GET /todos?status=active&priority=2&page=1&per_page=20

# 动作
POST /todos/1/toggle     # 快捷操作
POST /todos/batch        # 批量操作
"""

# ─── 统一响应格式 ───
"""
# 成功
{
    "data": [...],          # 主体数据
    "meta": {               # 元信息
        "page": 1,
        "total": 42,
        "pages": 3
    },
    "message": "操作成功"
}

# 错误
{
    "error": "人类可读错误",
    "code": "MACHINE_READABLE_CODE",
    "details": {"field": "字段级错误"}
}

# 创建成功
return jsonify({'data': ..., 'message': '创建成功'}), 201

# 删除成功（无内容）
return '', 204

# 认证失败
return jsonify({'error': '未登录', 'code': 'AUTH_REQUIRED'}), 401

# 权限不足
return jsonify({'error': '权限不足', 'code': 'FORBIDDEN'}), 403

# 资源不存在
return jsonify({'error': '资源不存在', 'code': 'NOT_FOUND'}), 404

# 参数错误
return jsonify({'error': '参数校验失败', 'code': 'VALIDATION_ERROR',
                'details': {...}}), 422
"""

# ─── 错误处理中间件模板 ───
"""
class APIException(Exception):
    def __init__(self, message, code, status_code=400):
        self.message = message
        self.code = code
        self.status_code = status_code

@app.errorhandler(APIException)
def handle_api_error(error):
    return jsonify({
        'error': error.message,
        'code': error.code,
    }), error.status_code

@app.errorhandler(404)
def handle_404(e):
    return jsonify({'error': '接口不存在', 'code': 'NOT_FOUND'}), 404

@app.errorhandler(500)
def handle_500(e):
    db.session.rollback()
    return jsonify({'error': '服务器内部错误', 'code': 'SERVER_ERROR'}), 500
"""


# ============================================================
# 5. 状态码速查
# ============================================================

# ─── 2xx 成功 ───
"""
200 OK          # 请求成功（GET）
201 Created     # 创建成功（POST）
204 No Content  # 删除成功（DELETE），无响应体
"""

# ─── 4xx 客户端错误 ───
"""
400 Bad Request       # 请求格式错误
401 Unauthorized      # 未认证/Token 无效
403 Forbidden         # 已认证但无权限
404 Not Found         # 资源不存在
405 Method Not Allowed # HTTP 方法不支持
409 Conflict          # 资源冲突（如用户名已存在）
422 Unprocessable     # 请求体校验失败
429 Too Many Requests # 请求频率限制
"""

# ─── 5xx 服务器错误 ───
"""
500 Internal Server Error   # 服务器内部错误
502 Bad Gateway             # 网关错误
503 Service Unavailable     # 服务暂时不可用
"""


# ============================================================
# 6. 最佳实践备忘录
# ============================================================

# 安全
"""
1. SECRET_KEY 通过环境变量注入，不写死在代码里
2. 密码永远用 generate_password_hash 处理
3. JWT Token 不要放在 URL 参数中
4. API 使用 HTTPS
5. 不要暴露详细的服务器错误信息给客户端
"""

# 性能
"""
1. 合理设置 lazy 加载模式，避免 N+1 查询
2. 添加数据库索引（index=True）
3. 查询 SQL 用 SQLALCHEMY_ECHO 调试
4. 分页限制最大 per_page
"""

# 可维护性
"""
1. 统一错误码体系
2. 所有路由有类型提示
3. 使用蓝图模块化组织
4. 配置文件和业务逻辑分离
5. 使用 Flask-Migrate 管理数据库版本
"""

if __name__ == '__main__':
    print('=' * 60)
    print('📖 Flask 进阶 API 速查参考')
    print('=' * 60)
    print('\n本文件不是可运行脚本，而是作为代码注释形式的 API 参考手册。')
    print('\n打开本文件查看以下内容的速查表：')
    print('  1. SQLAlchemy ORM API 速查')
    print('  2. 查询 API（过滤、排序、分页、聚合）')
    print('  3. JWT 认证 API')
    print('  4. RESTful API 设计模式')
    print('  5. HTTP 状态码速查')
    print('  6. 最佳实践备忘录')
    print()
