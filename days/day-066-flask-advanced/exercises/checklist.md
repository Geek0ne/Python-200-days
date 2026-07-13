# Day 066 — Flask 进阶：练习与检查表

## ✅ 今日完成清单

- [ ] 理解 ORM 的概念和为什么需要 ORM
- [ ] 掌握 SQLAlchemy 的架构设计（ORM + Core 两层）
- [ ] 掌握 Flask-SQLAlchemy 的配置和初始化
- [ ] 理解模型定义：列类型、约束、默认值
- [ ] 掌握一对多关系设置（`db.relationship` + `backref`）
- [ ] 理解多对多关系实现（中间表 `db.Table` + `secondary`）
- [ ] 掌握 CRUD 操作：增删改查、过滤、排序、分页
- [ ] 理解 `lazy` 加载模式的区别（select/joined/dynamic）
- [ ] 理解密码安全原则：加盐哈希 vs 加密
- [ ] 掌握 Werkzeug 的 `generate_password_hash` / `check_password_hash`
- [ ] 理解 Flask-Login 的会话管理机制
- [ ] 理解 JWT 的原理：Header.Payload.Signature
- [ ] 掌握 JWT 的签发、验证、刷新
- [ ] 理解 Access Token vs Refresh Token 分离设计
- [ ] 理解 RESTful API 设计原则
- [ ] 掌握 HTTP 方法（GET/POST/PUT/PATCH/DELETE）的正确使用
- [ ] 掌握合理使用 HTTP 状态码（200/201/204/400/401/404/409/422）
- [ ] 掌握请求参数验证和错误响应规范化
- [ ] 完成 TODO API 实战

---

## 📝 练习题

### 基础题

#### 题 1：SQLAlchemy 基础模型

定义以下数据模型：

```
作者（Author）：
  - id: 整数，主键
  - name: 字符串(50)，非空
  - email: 字符串(120)，唯一

文章（Article）：
  - id: 整数，主键
  - title: 字符串(200)，非空
  - content: 文本
  - published: 布尔值，默认 False
  - author_id: 外键 → author.id
  - created_at: 日期时间，默认当前时间

标签（Tag）：
  - id: 整数，主键
  - name: 字符串(30)，唯一

一篇文章可以有多个标签，一个标签可以被多篇文章使用。
```

**要求：**
1. 用 Flask-SQLAlchemy 定义这三个模型
2. 设置 Author ↔ Article 的一对多关系
3. 设置 Article ↔ Tag 的多对多关系
4. 每个模型添加 `to_dict()` 序列化方法

#### 题 2：认证系统实现

基于现有框架实现以下功能：

```python
# 补全以下代码
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import jwt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # TODO: 添加 set_password 和 check_password 方法

# TODO: 实现 token_required 装饰器
# TODO: 实现 login 路由
# TODO: 实现 register 路由
# TODO: 实现一个受保护的路由 /api/protected

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
```

**要求：**
- `set_password()` 使用 `generate_password_hash`
- `check_password()` 使用 `check_password_hash`
- `token_required` 装饰器从 `Authorization: Bearer <token>` 提取并验证 JWT
- `/api/register` 接收 `username` 和 `password`，返回 token
- `/api/login` 验证凭据，返回 token
- `/api/protected` 返回 `{"message": "Hello, {username}!"}`

#### 题 3：RESTful 接口设计

为以下资源设计 RESTful API 端点：

**资源：图书（Book）**

字段：`id`, `title`, `author`, `isbn`, `published_year`, `available` (是否可借)

**要求：**
1. 列出所有图书（支持按作者过滤、分页、排序）
2. 获取单本图书详情
3. 添加新图书
4. 更新图书信息
5. 借出/归还图书（PATCH 局部更新 available 字段）
6. 删除图书

**请写出：**
- 每个端点的 HTTP 方法 + URL 路径
- 请求体/参数格式
- 成功和错误状态的预期响应
- 适当的 HTTP 状态码

---

### 进阶题

#### 题 4：带分页和过滤的 TODO API

扩展 TODO API，实现一个"智能列表"端点：

`GET /api/v1/todos/smart-list`

**查询参数：**
- `today`: 如果为 `true`，只返回今天的任务（包括过期未完成的）
- `overdue`: 如果为 `true`，只返回超过截止日期但未完成的任务
- `week`: 如果为 `true`，返回本周（周一到周日）的任务

**返回格式：**
```json
{
    "data": [...],
    "meta": {
        "total": 42,
        "sections": {
            "overdue": 2,
            "today": 5,
            "upcoming": 35
        }
    }
}
```

**要求：**
- 实现日期范围的正确计算（注意时区）
- `overdue` 的任务即使在 `today` 列表中也要标记出来
- 按紧急程度排序：过期 > 今天到期 > 优先级高 > 创建时间新

#### 题 5：Flask-Login 集成

将 Flask-Login 集成到已有的 TODO API 中，替换 JWT 认证：

```python
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

login_manager = LoginManager()
login_manager.init_app(app)

# TODO: 实现 UserMixin 用户模型
# TODO: 实现 user_loader 回调
# TODO: 实现基于 session 的登录/登出
# TODO: 将 @token_required 替换为 @login_required
```

**要求：**
- 使用 `UserMixin` 混入类
- 实现 `login_manager.user_loader`
- 登录路由调用 `login_user()`
- 登出路由调用 `logout_user()`
- 保护路由使用 `@login_required`
- 对比 JWT 和 Session 两种方案的优劣

---

## 💡 挑战题

### 挑战 1：完整 Blog API

设计并实现一个完整的博客 API 系统：

**功能需求：**

1. **用户系统**
   - 注册（支持用户名、邮箱、密码）
   - 登录（返回 JWT）
   - 个人资料查看/修改

2. **文章系统**
   - CRUD（用户只能操作自己的文章）
   - 文章有标题、内容、摘要、封面图 URL
   - 文章可以发布/草稿两种状态
   - 支持按标签分类
   - 支持搜索（标题和内容全文搜索）

3. **评论系统**
   - 用户可以对已发布的文章评论
   - 评论支持回复（嵌套评论）
   - 文章作者可以删除评论

4. **交互功能**
   - 点赞/取消点赞文章
   - 统计文章阅读量（每次 GET 详情 +1）
   - 热门文章排行（按阅读量或点赞数排序）

**技术要求：**
- 至少 5 个数据库模型
- RESTful 风格设计
- 完整的错误码体系
- 分页、过滤、排序支持
- 请求参数校验

**示例数据模型：**
```python
class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.String(500))
    cover_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='draft')  # draft / published
    view_count = db.Column(db.Integer, default=0)
    
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = ...
    updated_at = ...
    published_at = db.Column(db.DateTime, nullable=True)
```

### 挑战 2：生产级错误处理中间件

实现一个完善的错误处理系统：

```python
# 自定义异常类
class APIException(Exception):
    """API 异常基类"""
    def __init__(self, message, code, status_code=400):
        self.message = message
        self.code = code
        self.status_code = status_code

class NotFound(APIException):
    def __init__(self, message='资源不存在'):
        super().__init__(message, 'NOT_FOUND', 404)

class ValidationError(APIException):
    def __init__(self, message, details=None):
        super().__init__(message, 'VALIDATION_ERROR', 422)
        self.details = details or {}

class Unauthorized(APIException):
    def __init__(self, message='请先登录'):
        super().__init__(message, 'UNAUTHORIZED', 401)

class Forbidden(APIException):
    def __init__(self, message='权限不足'):
        super().__init__(message, 'FORBIDDEN', 403)

# TODO: 实现全局错误处理函数
# @app.errorhandler(APIException)
# def handle_api_exception(error):
#     ...

# @app.errorhandler(404)
# def handle_404(error):
#     ...

# @app.errorhandler(500)
# def handle_500(error):
#     ...

# @app.before_request
# def validate_content_type():
#     # 对 POST/PUT/PATCH 请求，检查 Content-Type
#     ...
```

**要求：**
- 所有 API 错误通过 `raise APIException` 统一抛出
- 全局 `errorhandler` 捕获并返回统一格式的 JSON 错误
- 500 错误要记录日志并回滚数据库事务
- `before_request` 检查 JSON API 的 Content-Type

---

## 📚 参考资料

- [SQLAlchemy 官方文档](https://docs.sqlalchemy.org/en/20/)
- [Flask-SQLAlchemy 文档](https://flask-sqlalchemy.palletsprojects.com/)
- [Flask-Migrate 文档](https://flask-migrate.readthedocs.io/)
- [Werkzeug 密码哈希](https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security)
- [JWT 官方文档](https://pyjwt.readthedocs.io/)
- [RESTful API 设计规范（Microsoft）](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [HTTP 状态码规范（RFC 7231）](https://datatracker.ietf.org/doc/html/rfc7231#section-6)
