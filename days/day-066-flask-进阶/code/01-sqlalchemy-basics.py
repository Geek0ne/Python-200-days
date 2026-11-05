#!/usr/bin/env python3
"""
01 - SQLAlchemy 数据库基础操作

本示例演示 Flask-SQLAlchemy 的核心用法：
1. Flask 应用与数据库配置
2. 定义数据模型（User、Todo、Category）
3. 一对多、多对多关系
4. CRUD 完整操作
5. 高级查询（排序、分页、过滤链）

运行方式：
    python3 01-sqlalchemy-basics.py

注意：需要先安装依赖
    pip install flask flask-sqlalchemy
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import sys

# ============================================================
# 第一部分：应用初始化与配置
# ============================================================

app = Flask(__name__)

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///example.db'  # SQLite 数据库
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False             # 关闭事件系统（节省 40% 内存）
app.config['SQLALCHEMY_ECHO'] = True                             # 打印 SQL 语句（调试用）

db = SQLAlchemy(app)


# ============================================================
# 第二部分：数据模型定义
# ============================================================

# 多对多的中间表：Todo 和 Tag 的关系
todo_tag = db.Table(
    'todo_tag',
    db.Column('todo_id', db.Integer, db.ForeignKey('todo.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)


class User(db.Model):
    """用户模型"""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    # 一对多：一个用户有多个 Todo
    # backref 给 Todo 模型添加 .user 属性
    # lazy='dynamic' 返回 Query 对象，支持链式过滤
    todos = db.relationship('Todo', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    """分类模型"""
    __tablename__ = 'category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, default='')

    # 一对多：一个分类有多个 Todo
    todos = db.relationship('Todo', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


class Tag(db.Model):
    """标签模型（多对多关系）"""
    __tablename__ = 'tag'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)

    def __repr__(self):
        return f'<Tag {self.name}>'


class Todo(db.Model):
    """待办事项模型"""
    __tablename__ = 'todo'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    done = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=0)  # 优先级：0=普通，1=重要，2=紧急

    # 外键
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    # 时间戳
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)  # 更新时自动修改
    )

    # 多对多关系
    tags = db.relationship('Tag', secondary=todo_tag, backref='todos', lazy='select')

    def to_dict(self):
        """将模型转为字典（方便 JSON 序列化）"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'done': self.done,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'tags': [t.name for t in self.tags],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        status = '✅' if self.done else '⬜'
        return f'{status} <Todo {self.id}: {self.title}>'


# ============================================================
# 第三部分：CRUD 操作示例
# ============================================================

def demo_crud():
    """演示完整的增删改查操作"""
    print('=' * 60)
    print('📦 数据库 CRUD 演示')
    print('=' * 60)

    # ────────────── 创建 ──────────────

    print('\n--- 1️⃣ 创建数据 ---')

    # 创建用户
    alice = User(username='alice', email='alice@example.com')
    bob = User(username='bob', email='bob@example.com')
    db.session.add_all([alice, bob])

    # 创建分类
    study = Category(name='学习', description='学习相关任务')
    work = Category(name='工作', description='工作相关任务')
    personal = Category(name='个人', description='生活个人事项')
    db.session.add_all([study, work, personal])

    # 创建标签
    urgent = Tag(name='urgent')
    python_tag = Tag(name='python')
    important = Tag(name='important')
    db.session.add_all([urgent, python_tag, important])

    # 提交——写数据库
    db.session.commit()
    print(f'✅ 创建了用户: {alice}, {bob}')
    print(f'✅ 创建了分类: {study}, {work}, {personal}')
    print(f'✅ 创建了标签: {urgent}, {python_tag}, {important}')

    # ────────────── 创建 TODO（含关系） ──────────────

    print('\n--- 2️⃣ 创建 TODO（关联用户、分类、标签） ---')

    todo1 = Todo(
        title='学习 SQLAlchemy',
        description='完成 Day 066 的数据库部分，掌握 ORM 的所有操作',
        user=alice,             # 直接关联 User 对象（替代 user_id）
        category=study,
        priority=1,              # 重要
        tags=[python_tag, important]
    )

    todo2 = Todo(
        title='提交日报',
        description='撰写今日学习总结并提交 Git',
        user=alice,
        category=work,
        priority=2  # 紧急
    )

    todo3 = Todo(
        title='阅读 Flask 官方文档',
        user=bob,
        category=study,
        tags=[python_tag]
    )

    db.session.add_all([todo1, todo2, todo3])
    db.session.commit()
    print(f'✅ 创建了 TODO 事项')

    # ────────────── 读取 ──────────────

    print('\n--- 3️⃣ 读取数据 ---')

    # 获取所有用户
    all_users = User.query.all()
    print(f'所有用户: {[u.username for u in all_users]}')

    # 按主键获取
    user = User.query.get(1)
    print(f'ID=1 的用户: {user}')

    # 条件过滤
    study_todos = Todo.query.filter_by(category=study).all()
    print(f'学习类 TODO: {[t.title for t in study_todos]}')

    # 复杂过滤
    important_todos = Todo.query.filter(Todo.priority >= 1).all()
    print(f'重要/紧急 TODO: {[t.title for t in important_todos]}')

    # 排序
    recent_todos = Todo.query.order_by(Todo.created_at.desc()).all()
    print(f'按创建时间倒序: {[t.title for t in recent_todos]}')

    # 链式过滤
    alice_todos = (
        Todo.query
        .filter_by(user=alice)
        .filter(Todo.priority >= 1)
        .order_by(Todo.priority.desc())
        .all()
    )
    print(f'Alice 的高优先级 TODO: {[t.title for t in alice_todos]}')

    # ────────────── 跨关系查询 ──────────────

    print('\n--- 4️⃣ 跨关系查询 ---')

    # 正向查询：用户 → TODO
    alice = User.query.filter_by(username='alice').first()
    print(f'Alice 的所有 TODO:')
    for todo in alice.todos.all():
        print(f'  {todo}')

    # 反向查询：TODO → 用户
    todo = Todo.query.filter_by(title='学习 SQLAlchemy').first()
    if todo:
        print(f'TODO "{todo.title}" 属于用户: {todo.user.username}')

    # 多对多查询
    python_todo = Todo.query.filter(Todo.tags.any(name='python')).all()
    print(f'带 python 标签的 TODO: {[t.title for t in python_todo]}')

    # ────────────── 更新 ──────────────

    print('\n--- 5️⃣ 更新数据 ---')

    todo = Todo.query.filter_by(title='学习 SQLAlchemy').first()
    todo.done = True  # 修改属性
    db.session.commit()
    print(f'✅ 标记完成: {todo}')

    # ────────────── 分页查询 ──────────────

    print('\n--- 6️⃣ 分页查询 ---')

    page = Todo.query.order_by(Todo.created_at.desc()).paginate(
        page=1, per_page=2, error_out=False
    )
    print(f'第 {page.page} 页，共 {page.pages} 页，总计 {page.total} 条')
    for item in page.items:
        print(f'  {item}')

    # ────────────── 聚合查询 ──────────────

    print('\n--- 7️⃣ 聚合统计 ---')

    from sqlalchemy import func

    # 统计每个用户的 TODO 数量
    stats = (
        db.session.query(
            User.username,
            func.count(Todo.id).label('todo_count')
        )
        .join(Todo, User.id == Todo.user_id)
        .group_by(User.id)
        .all()
    )
    for username, count in stats:
        print(f'{username}: {count} 个 TODO')

    # ────────────── 删除 ──────────────

    print('\n--- 8️⃣ 删除数据 ---')

    # 删除一个 TODO
    todo_to_delete = Todo.query.filter_by(
        title='提交日报'
    ).first()
    if todo_to_delete:
        print(f'🗑️ 删除: {todo_to_delete.title}')
        db.session.delete(todo_to_delete)
        db.session.commit()


# ============================================================
# 第四部分：数据库检查与清理
# ============================================================

def check_data():
    """打印当前数据库中的所有数据"""
    print('\n' + '=' * 60)
    print('📊 当前数据库状态')
    print('=' * 60)

    print(f'\n用户数: {User.query.count()}')
    for u in User.query.all():
        print(f'  {u.username} ({u.email})')

    print(f'\n分类数: {Category.query.count()}')
    for c in Category.query.all():
        print(f'  {c.name}: {c.description}')

    print(f'\n标签数: {Tag.query.count()}')
    for t in Tag.query.all():
        print(f'  #{t.name}')

    print(f'\nTODO 总数: {Todo.query.count()}')
    for t in Todo.query.order_by(Todo.created_at.desc()).all():
        print(f'  {t} [标签: {[tag.name for tag in t.tags]}]')


# ============================================================
# 主入口
# ============================================================

if __name__ == '__main__':
    with app.app_context():
        # 删除旧的数据库，确保每次运行结果一致
        import os
        db_path = 'instance/example.db'
        if os.path.exists(db_path):
            os.remove(db_path)
            print('🗑️ 已删除旧数据库文件')

        # 创建所有表
        db.create_all()
        print('✅ 数据库表已创建')

        # 执行 CRUD 演示
        demo_crud()

        # 检查最终数据
        check_data()

        print('\n' + '=' * 60)
        print('✅ 全部操作完成！')
        print('=' * 60)
        print(f'\n数据库文件位置: {db_path}')
        print('你可以用 SQLite 工具查看: sqlite3 instance/example.db')
