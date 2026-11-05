#!/usr/bin/env python3
"""
03 - TODO API 实战：完整 RESTful 服务

本示例构建一个生产级的 TODO API 服务，涵盖：
1. RESTful 资源设计（遵循最佳实践）
2. 完整的 CRUD + 认证 + 错误处理
3. 高级功能：搜索、排序、分页、过滤
4. 请求验证与数据校验
5. 详细的错误码体系
6. 完整的 curl 测试脚本

运行方式：
    python3 03-todo-api-complete.py

需要先安装依赖：
    pip install flask flask-sqlalchemy pyjwt
"""

from flask import Flask, jsonify, request, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta, timezone
import jwt
import re
import sys

# ============================================================
# 应用配置
# ============================================================

app = Flask(__name__)

# ⚠️ 安全配置：生产环境通过环境变量注入
app.config['SECRET_KEY'] = 'dev-secret-key-do-not-use-in-production-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo_api.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False  # 支持中文 JSON

# API 配置
app.config['PAGINATION_PER_PAGE'] = 20   # 默认每页条数
app.config['MAX_TITLE_LENGTH'] = 200     # 标题最大长度
app.config['MAX_DESC_LENGTH'] = 2000     # 描述最大长度
app.config['TOKEN_EXPIRY_HOURS'] = 24    # Token 过期时间

db = SQLAlchemy(app)


# ============================================================
# 数据模型
# ============================================================

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    todos = db.relationship('Todo', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Todo(db.Model):
    """待办事项模型"""
    __tablename__ = 'todos'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    done = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=0)  # 0=低, 1=中, 2=高, 3=紧急
    due_date = db.Column(db.DateTime, nullable=True)  # 截止日期

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'done': self.done,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        status = '✅' if self.done else '⬜'
        return f'{status} Todo({self.id}): {self.title}'


# ============================================================
# JWT 认证工具
# ============================================================

def create_token(user_id):
    """生成 JWT Token"""
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user_id,
        'iat': now,
        'exp': now + timedelta(hours=app.config['TOKEN_EXPIRY_HOURS']),
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def decode_token(token):
    """解码 Token"""
    try:
        return jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']), None
    except jwt.ExpiredSignatureError:
        return None, 'Token 已过期，请重新登录'
    except jwt.InvalidTokenError:
        return None, 'Token 无效'


def token_required(f):
    """JWT 认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')

        if not auth.startswith('Bearer '):
            return jsonify({
                'error': '认证失败',
                'code': 'AUTH_REQUIRED',
                'message': '请求头需要包含 Authorization: Bearer <token>'
            }), 401

        token = auth.split(' ')[1]
        payload, error = decode_token(token)

        if error:
            return jsonify({
                'error': '认证失败',
                'code': 'TOKEN_INVALID' if '无效' in error else 'TOKEN_EXPIRED',
                'message': error
            }), 401

        user = User.query.get(payload['sub'])
        if not user:
            return jsonify({'error': '用户不存在', 'code': 'USER_NOT_FOUND'}), 401

        return f(user, *args, **kwargs)
    return decorated


# ============================================================
# 认证路由
# ============================================================

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空', 'code': 'EMPTY_BODY'}), 400

    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password', '')

    # 验证
    errors = {}
    if not username or len(username) < 3:
        errors['username'] = '用户名至少 3 个字符'
    if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        errors['email'] = '邮箱格式不正确'
    if not password or len(password) < 6:
        errors['password'] = '密码至少 6 个字符'
    if errors:
        return jsonify({'error': '参数校验失败', 'code': 'VALIDATION_ERROR', 'details': errors}), 422

    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已被注册', 'code': 'USERNAME_TAKEN'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': '邮箱已被注册', 'code': 'EMAIL_TAKEN'}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_token(user.id)
    return jsonify({
        'message': '注册成功',
        'data': {
            'user': user.to_dict(),
            'token': token,
        }
    }), 201


@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '用户名和密码是必填的', 'code': 'MISSING_CREDENTIALS'}), 400

    login_id = data['username'].strip()
    user = User.query.filter(
        (User.username == login_id) | (User.email == login_id)
    ).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': '用户名或密码错误', 'code': 'INVALID_CREDENTIALS'}), 401

    token = create_token(user.id)
    return jsonify({
        'message': '登录成功',
        'data': {'user': user.to_dict(), 'token': token}
    })


@app.route('/api/v1/auth/me', methods=['GET'])
@token_required
def get_me(current_user):
    """获取当前用户信息"""
    return jsonify({'data': current_user.to_dict()})


# ============================================================
# TODO CRUD 路由
# ============================================================

def validate_todo_data(data, partial=False):
    """
    验证 TODO 数据
    
    Args:
        data: 请求数据字典
        partial: 是否为部分更新
    
    Returns:
        (cleaned_data, errors) 元组
    """
    errors = {}
    cleaned = {}

    # 标题验证
    if 'title' in data or not partial:
        title = (data.get('title') or '').strip()
        if not title:
            errors['title'] = '标题不能为空'
        elif len(title) > app.config['MAX_TITLE_LENGTH']:
            errors['title'] = f'标题不能超过 {app.config["MAX_TITLE_LENGTH"]} 个字符'
        else:
            cleaned['title'] = title

    # 描述验证
    if 'description' in data:
        desc = data['description']
        if desc and len(desc) > app.config['MAX_DESC_LENGTH']:
            errors['description'] = f'描述不能超过 {app.config["MAX_DESC_LENGTH"]} 个字符'
        else:
            cleaned['description'] = desc

    # 完成状态验证
    if 'done' in data:
        if not isinstance(data['done'], bool):
            errors['done'] = 'done 必须是布尔值'
        else:
            cleaned['done'] = data['done']

    # 优先级验证
    if 'priority' in data:
        priority = data['priority']
        if not isinstance(priority, int) or priority < 0 or priority > 3:
            errors['priority'] = 'priority 必须在 0-3 之间'
        else:
            cleaned['priority'] = priority

    # 截止日期验证
    if 'due_date' in data:
        due = data['due_date']
        if due:
            try:
                cleaned['due_date'] = datetime.fromisoformat(due.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                errors['due_date'] = 'due_date 格式无效，请使用 ISO 8601 格式'
        else:
            cleaned['due_date'] = None

    return cleaned, errors


# ─── 获取 TODO 列表 ───

@app.route('/api/v1/todos', methods=['GET'])
@token_required
def list_todos(current_user):
    """
    获取 TODO 列表
    
    查询参数：
        status: all / active / done（默认 all）
        priority: 可选，按优先级过滤
        search: 可选，搜索标题或描述
        sort_by: created_at / priority / due_date（默认 created_at）
        sort_order: asc / desc（默认 desc）
        page: 页码（默认 1）
        per_page: 每页条数（默认 20）
    """
    # 构建查询
    query = Todo.query.filter_by(user_id=current_user.id)

    # 过滤
    status = request.args.get('status', 'all')
    if status == 'active':
        query = query.filter_by(done=False)
    elif status == 'done':
        query = query.filter_by(done=True)

    priority = request.args.get('priority', type=int)
    if priority is not None and 0 <= priority <= 3:
        query = query.filter_by(priority=priority)

    # 搜索
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(
            Todo.title.contains(search) | Todo.description.contains(search)
        )

    # 排序
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')

    if sort_order == 'asc':
        order_func = lambda col: col.asc()
    else:
        order_func = lambda col: col.desc()

    sort_map = {
        'created_at': order_func(Todo.created_at),
        'priority': order_func(Todo.priority),
        'due_date': order_func(Todo.due_date),
        'title': order_func(Todo.title),
    }
    query = query.order_by(sort_map.get(sort_by, Todo.created_at.desc()))

    # 分页
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', app.config['PAGINATION_PER_PAGE'], type=int)
    per_page = min(per_page, 100)  # 限制最大每页 100 条

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'data': [todo.to_dict() for todo in pagination.items],
        'meta': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
        }
    })


# ─── 获取单个 TODO ───

@app.route('/api/v1/todos/<int:todo_id>', methods=['GET'])
@token_required
def get_todo(current_user, todo_id):
    """获取单个 TODO"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()
    if not todo:
        return jsonify({'error': '任务不存在', 'code': 'NOT_FOUND'}), 404
    return jsonify({'data': todo.to_dict()})


# ─── 创建 TODO ───

@app.route('/api/v1/todos', methods=['POST'])
@token_required
def create_todo(current_user):
    """创建 TODO"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空', 'code': 'EMPTY_BODY'}), 400

    cleaned, errors = validate_todo_data(data, partial=False)
    if errors:
        return jsonify({
            'error': '参数校验失败',
            'code': 'VALIDATION_ERROR',
            'details': errors
        }), 422

    todo = Todo(
        title=cleaned['title'],
        description=cleaned.get('description', ''),
        done=cleaned.get('done', False),
        priority=cleaned.get('priority', 0),
        due_date=cleaned.get('due_date'),
        user_id=current_user.id,
    )
    db.session.add(todo)
    db.session.commit()

    return jsonify({
        'message': '创建成功',
        'data': todo.to_dict(),
    }), 201


# ─── 更新 TODO（全量） ───

@app.route('/api/v1/todos/<int:todo_id>', methods=['PUT'])
@token_required
def update_todo(current_user, todo_id):
    """全量更新 TODO"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()
    if not todo:
        return jsonify({'error': '任务不存在', 'code': 'NOT_FOUND'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空', 'code': 'EMPTY_BODY'}), 400

    cleaned, errors = validate_todo_data(data, partial=False)
    if errors:
        return jsonify({
            'error': '参数校验失败',
            'code': 'VALIDATION_ERROR',
            'details': errors
        }), 422

    # 更新所有字段
    for key, value in cleaned.items():
        setattr(todo, key, value)
    db.session.commit()

    return jsonify({
        'message': '更新成功',
        'data': todo.to_dict(),
    })


# ─── 局部更新 TODO ───

@app.route('/api/v1/todos/<int:todo_id>', methods=['PATCH'])
@token_required
def patch_todo(current_user, todo_id):
    """局部更新 TODO"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()
    if not todo:
        return jsonify({'error': '任务不存在', 'code': 'NOT_FOUND'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空', 'code': 'EMPTY_BODY'}), 400

    cleaned, errors = validate_todo_data(data, partial=True)
    if errors:
        return jsonify({
            'error': '参数校验失败',
            'code': 'VALIDATION_ERROR',
            'details': errors
        }), 422

    # 只更新提供的字段
    for key, value in cleaned.items():
        setattr(todo, key, value)
    db.session.commit()

    return jsonify({
        'message': '更新成功',
        'data': todo.to_dict(),
    })


# ─── 快速切换完成状态 ───

@app.route('/api/v1/todos/<int:todo_id>/toggle', methods=['POST'])
@token_required
def toggle_todo(current_user, todo_id):
    """快捷切换 TODO 的完成状态（不需要请求体）"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()
    if not todo:
        return jsonify({'error': '任务不存在', 'code': 'NOT_FOUND'}), 404

    todo.done = not todo.done
    db.session.commit()

    return jsonify({
        'message': '已完成' if todo.done else '已标记为未完成',
        'data': todo.to_dict(),
    })


# ─── 删除 TODO ───

@app.route('/api/v1/todos/<int:todo_id>', methods=['DELETE'])
@token_required
def delete_todo(current_user, todo_id):
    """删除 TODO"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()
    if not todo:
        return jsonify({'error': '任务不存在', 'code': 'NOT_FOUND'}), 404

    db.session.delete(todo)
    db.session.commit()

    return '', 204  # No Content


# ─── 批量操作 ───

@app.route('/api/v1/todos/batch', methods=['POST'])
@token_required
def batch_todos(current_user):
    """
    批量操作 TODO
    
    请求体：
        {
            "operation": "delete" | "mark_done" | "mark_undone",
            "ids": [1, 2, 3]
        }
    """
    data = request.get_json()
    if not data or not data.get('ids'):
        return jsonify({'error': '请提供要操作的 ID 列表', 'code': 'MISSING_IDS'}), 400

    ids = data['ids']
    if not isinstance(ids, list) or not ids:
        return jsonify({'error': 'ids 必须是包含整数的列表', 'code': 'INVALID_IDS'}), 400

    # 只操作属于当前用户的 TODO
    todos = Todo.query.filter(
        Todo.id.in_(ids),
        Todo.user_id == current_user.id
    ).all()

    if not todos:
        return jsonify({'error': '没有找到可操作的任务', 'code': 'NOT_FOUND'}), 404

    operation = data.get('operation', 'delete')

    if operation == 'mark_done':
        for todo in todos:
            todo.done = True
        db.session.commit()
        return jsonify({'message': f'已标记 {len(todos)} 个任务为完成'})

    elif operation == 'mark_undone':
        for todo in todos:
            todo.done = False
        db.session.commit()
        return jsonify({'message': f'已标记 {len(todos)} 个任务为未完成'})

    else:  # delete
        for todo in todos:
            db.session.delete(todo)
        db.session.commit()
        return jsonify({'message': f'已删除 {len(todos)} 个任务'})


# ─── 统计 ───

@app.route('/api/v1/todos/stats', methods=['GET'])
@token_required
def todo_stats(current_user):
    """获取 TODO 统计信息"""
    total = Todo.query.filter_by(user_id=current_user.id).count()
    done = Todo.query.filter_by(user_id=current_user.id, done=True).count()
    active = total - done
    urgent = Todo.query.filter_by(user_id=current_user.id, priority=3, done=False).count()

    return jsonify({
        'data': {
            'total': total,
            'done': done,
            'active': active,
            'urgent': urgent,
            'completion_rate': round(done / total * 100, 1) if total > 0 else 0,
        }
    })


# ============================================================
# 错误处理
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '接口不存在', 'code': 'NOT_FOUND'}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': '不支持的请求方法', 'code': 'METHOD_NOT_ALLOWED'}), 405


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': '服务器内部错误', 'code': 'SERVER_ERROR'}), 500


# ============================================================
# 初始化与启动
# ============================================================

def init_db():
    """初始化数据库"""
    with app.app_context():
        db.drop_all()  # 每次重新建表，演示用
        db.create_all()

        # 创建测试用户
        user = User(username='demo', email='demo@example.com')
        user.set_password('demo123')
        db.session.add(user)

        # 创建测试 TODO
        for i in range(5):
            todo = Todo(
                title=f'示例任务 {i + 1}',
                description=f'这是第 {i + 1} 个示例任务，用于演示',
                done=(i == 0),
                priority=i % 4,
                user_id=1,
            )
            db.session.add(todo)

        db.session.commit()
        print('✅ 测试数据已创建')
        print(f'   用户: demo / demo123')
        print(f'   示例 TODO: 5 条')


if __name__ == '__main__':
    init_db()

    print('\n' + '=' * 60)
    print('🚀 TODO API 服务已启动')
    print('=' * 60)
    print(f'\n📋 API 端点：')
    print(f'  POST   /api/v1/auth/register   — 注册')
    print(f'  POST   /api/v1/auth/login      — 登录')
    print(f'  GET    /api/v1/auth/me         — 个人信息')
    print(f'  GET    /api/v1/todos           — TODO 列表')
    print(f'  POST   /api/v1/todos           — 创建 TODO')
    print(f'  GET    /api/v1/todos/:id       — 获取 TODO')
    print(f'  PUT    /api/v1/todos/:id       — 更新 TODO')
    print(f'  PATCH  /api/v1/todos/:id       — 局部更新')
    print(f'  POST   /api/v1/todos/:id/toggle — 切换完成')
    print(f'  DELETE /api/v1/todos/:id       — 删除 TODO')
    print(f'  POST   /api/v1/todos/batch     — 批量操作')
    print(f'  GET    /api/v1/todos/stats     — 统计信息')
    print(f'\n📝 快速测试：')
    print(f'  # 登录获取 Token')
    print(f'  TOKEN=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{"username":"demo","password":"demo123"}\' \\')
    print(f'    | python3 -c "import sys,json; print(json.load(sys.stdin)[\'data\'][\'token\'])"')
    print(f'  )')
    print(f'  echo "Token: $TOKEN"')
    print(f'\n  # 获取 TODO 列表')
    print(f'  curl http://localhost:5000/api/v1/todos?status=active \\')
    print(f'    -H "Authorization: Bearer $TOKEN"')
    print(f'\n  # 创建 TODO')
    print(f'  curl -X POST http://localhost:5000/api/v1/todos \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -H "Authorization: Bearer $TOKEN" \\')
    print(f'    -d \'{"title":"学习 RESTful API","priority":2}\'')
    print()

    app.run(debug=True, host='0.0.0.0', port=5000)
