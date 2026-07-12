# Day 065 — Web 框架入门

## 概述

Web 框架是构建 Web 应用的基石。对于 Python 开发者来说，Flask 是最受欢迎的微框架之一——它**轻量、灵活、易上手**，非常适合初学者理解 Web 开发的本质。

本日将从零开始，掌握 Flask 的核心概念：**路由、模板、请求与响应处理**，最后通过一个**个人博客**实战项目把所学串联起来。

---

## 1. 为什么需要 Web 框架？

### 1.1 从裸 WSGI 说起

在 Web 框架诞生之前，Python Web 开发直接使用 WSGI（Web Server Gateway Interface）：

```python
# 纯 WSGI 应用——没有框架
def app(environ, start_response):
    path = environ.get('PATH_INFO', '')
    if path == '/':
        body = b'<h1>Hello, World!</h1>'
    elif path == '/about':
        body = b'<h1>About</h1>'
    else:
        body = b'<h1>404 Not Found</h1>'
    
    status = '200 OK'
    headers = [('Content-Type', 'text/html; charset=utf-8')]
    start_response(status, headers)
    return [body]
```

**问题**：手动解析路径、处理请求头、构建响应……代码很快变得臃肿、难以维护。

### 1.2 Web 框架解决的核心问题

| 问题 | 框架解决方案 |
|------|-------------|
| URL 分发 | **路由系统**——把 URL 映射到函数 |
| 响应生成 | **模板引擎**——动态生成 HTML |
| 请求解析 | **请求对象**——方便的 API 读参数、cookie、headers |
| 响应封装 | **响应对象**——快速构造 JSON/HTML/重定向 |
| 中间处理 | **中间件/钩子**——认证、日志、跨域等 |
| 开发效率 | **调试模式/热重载**——改代码自动刷新 |

---

## 2. Flask 基础概念

### 2.1 什么是 Flask？

Flask 是一个 **微框架（Microframework）**，核心设计哲学：

- **微**：核心只包含路由、模板、请求/响应处理，其他功能通过扩展组装
- **可扩展**：数据库（Flask-SQLAlchemy）、登录（Flask-Login）、表单（WTForms）等
- **约定优于配置**：默认模板在 `templates/`，静态文件在 `static/`

> 💡 **设计原理**："微"不代表功能弱，而是指核心精简。像乐高积木，需要什么就加什么扩展，不会塞一堆用不上的功能。

### 2.2 最小的 Flask 应用

```python
from flask import Flask

# 创建应用实例
app = Flask(__name__)

# 定义路由和视图函数
@app.route('/')
def hello():
    return '<h1>Hello, Flask!</h1>'
```

**运行方式**：
```bash
# 方式一：直接用 python 运行
python app.py

# 方式二：flask 命令
export FLASK_APP=app.py
flask run

# 指定端口
flask run --port=8080 --host=0.0.0.0
```

**关键点**：
- `__name__` 告诉 Flask 从哪里寻找模板和静态文件
- `@app.route()` 是**装饰器**，把 URL 和函数绑定
- 函数返回值就是 HTTP 响应的正文

### 2.3 完整的 Flask 应用入口模板

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return '<h1>首页</h1>'

@app.route('/about')
def about():
    return '<h1>关于我们</h1>'

if __name__ == '__main__':
    app.run(debug=True)   # debug=True 开启调试模式
```

> 💡 `debug=True` 的作用：代码修改后自动重启服务器、出错时显示交互式调试页面（**生产环境务必关闭！**）。

---

## 3. 路由系统

### 3.1 什么是路由？

路由是把 **URL 路径** 映射到 **视图函数** 的机制。当用户访问某个 URL 时，Flask 根据路由表找到对应的函数并执行。

```
用户请求 /posts/123
      │
      ▼
Flask 查找路由表
      │
      ├── /              → index()
      ├── /about         → about()
      ├── /posts/<id>    → show_post(id)  ← 命中
      │
      ▼
执行 show_post(123) → 返回响应
```

### 3.2 基本路由

```python
@app.route('/')
def index():
    return '首页'

@app.route('/blog')
def blog():
    return '博客列表'
```

### 3.3 动态路由（变量规则）

用 `<变量名>` 捕获 URL 中的动态部分：

```python
@app.route('/post/<int:post_id>')
def show_post(post_id):
    return f'文章 ID: {post_id}'

@app.route('/user/<username>')
def show_user(username):
    return f'用户: {username}'
```

**转换器类型**：

| 转换器 | 说明 | 示例 |
|--------|------|------|
| 默认 (string) | 匹配任何字符串（不含斜杠） | `/<name>` |
| `int` | 匹配整数 | `/<int:id>` |
| `float` | 匹配浮点数 | `/<float:price>` |
| `path` | 匹配含斜杠的路径 | `/<path:filepath>` |
| `uuid` | 匹配 UUID | `/<uuid:token>` |

### 3.4 HTTP 方法限制

```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return '处理登录表单'
    return '显示登录页面'
```

> 💡 默认只接受 GET 请求。**设计原理**：显式声明 methods 可以避免意外的副作用——比如 GET 请求触发了本应只接收 POST 的删除操作。

### 3.5 URL 构建

使用 `url_for()` 函数根据视图函数名生成 URL，而不是硬编码：

```python
from flask import Flask, url_for

@app.route('/')
def index():
    # 生成 /post/5 这样的 URL
    post_url = url_for('show_post', post_id=5)
    return f'<a href="{post_url}">查看文章</a>'
```

> 💡 **为什么用 url_for()？** 如果以后修改了路由路径（比如把 `/post/<id>` 改成 `/article/<id>`），所有用了 url_for 的代码自动生效，不需要逐个修改。

---

## 4. 模板系统（Jinja2）

### 4.1 为什么需要模板？

视图函数直接返回 HTML 的问题：

```python
# ❌ 不推荐：HTML 和 Python 混在一起
@app.route('/user/<name>')
def user(name):
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>{name}的个人主页</title></head>
    <body>
        <h1>欢迎, {name}!</h1>
        <p>这是你的个人主页。</p>
    </body>
    </html>
    '''
```

**问题**：HTML 写死在 Python 代码里，修改页面样式需要改 Python 代码。

**解决方案**：用 **模板** 把 HTML 和 Python 逻辑分离。

### 4.2 模板目录结构

```
your_app/
├── app.py
└── templates/
    ├── index.html
    ├── about.html
    └── layout.html    # 父模板
```

Flask 默认在 `templates/` 目录下查找模板文件。

### 4.3 模板基本语法

**render_template()**：渲染模板并返回 HTML：

```python
from flask import Flask, render_template

@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)
```

**模板文件** `templates/user.html`：
```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ name }}的个人主页</title>
</head>
<body>
    <h1>欢迎, {{ name }}!</h1>
</body>
</html>
```

### 4.4 Jinja2 模板语法速查

| 语法 | 说明 | 示例 |
|------|------|------|
| `{{ var }}` | 输出变量的值 | `{{ name }}` |
| `{% if %}` ... `{% endif %}` | 条件判断 | `{% if user %} ... {% endif %}` |
| `{% for %}` ... `{% endfor %}` | 循环 | `{% for item in list %} ... {% endfor %}` |
| `{# 注释 #}` | 注释（不出现在 HTML 中） | `{# 这是注释 #}` |
| `{% extends "base.html" %}` | 模板继承 | 子模板继承父模板 |
| `{% block name %}` ... `{% endblock %}` | 块定义 | 子模板覆盖父模板的块 |
| `{{ var\|filter }}` | 过滤器 | `{{ name\|upper }}` |

**常用过滤器**：

```html
<!-- 字符串处理 -->
{{ name|upper }}           <!-- 转大写 -->
{{ name|capitalize }}      <!-- 首字母大写 -->
{{ text|truncate(50) }}    <!-- 截断到50字符 -->

<!-- 列表处理 -->
{{ items|first }}          <!-- 第一个元素 -->
{{ items|last }}           <!-- 最后一个元素 -->
{{ items|length }}         <!-- 长度 -->
{{ items|join(', ') }}     <!-- 用逗号连接 -->

<!-- 时间格式化 -->
{{ post.created_at|strftime('%Y-%m-%d') }}

<!-- 默认值 -->
{{ user.bio|default('这个人很懒，什么都没写') }}

<!-- 安全输出（不转义 HTML） -->
{{ content|safe }}
```

### 4.5 模板继承

**父模板** `templates/base.html`：
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{% block title %}我的博客{% endblock %}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav>
        <a href="/">首页</a>
        <a href="/blog">博客</a>
    </nav>
    
    <main>
        {% block content %}{% endblock %}
    </main>
    
    <footer>
        <p>&copy; 2026 我的博客</p>
    </footer>
</body>
</html>
```

**子模板** `templates/index.html`：
```html
{% extends "base.html" %}

{% block title %}首页 - 我的博客{% endblock %}

{% block content %}
<div class="posts">
    {% for post in posts %}
    <article>
        <h2>{{ post.title }}</h2>
        <p>{{ post.summary }}</p>
    </article>
    {% endfor %}
</div>
{% endblock %}
```

> 💡 **设计原理**：模板继承避免了重复写 HTML 骨架。修改导航栏或页脚时，只需要改父模板一个文件。

---

## 5. 静态文件

### 5.1 什么是静态文件？

CSS、JavaScript、图片、字体等**不需要动态生成**的文件。

### 5.2 目录结构

```
your_app/
├── app.py
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── images/
│       └── logo.png
└── templates/
```

### 5.3 在模板中引用静态文件

用 `url_for('static', filename='...')` 生成静态文件 URL：

```html
<!-- CSS -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">

<!-- JavaScript -->
<script src="{{ url_for('static', filename='js/main.js') }}"></script>

<!-- 图片 -->
<img src="{{ url_for('static', filename='images/logo.png') }}" alt="Logo">
```

**生成的 URL**示例：`/static/css/style.css`

> 💡 **为什么用 url_for？** 如果部署时静态文件放到 CDN，可以通过配置改变 static 路径，url_for 会自动更新。

---

## 6. 请求与响应

### 6.1 请求对象（request）

Flask 的 `request` 对象封装了 HTTP 请求的所有信息：

```python
from flask import Flask, request

@app.route('/search', methods=['GET'])
def search():
    # GET 参数: ?q=python&page=1
    query = request.args.get('q', '')      # args: 查询参数
    page = request.args.get('page', 1, type=int)
    return f'搜索: {query}, 第{page}页'

@app.route('/submit', methods=['POST'])
def submit():
    # 表单数据
    username = request.form.get('username')   # form: 表单数据
    password = request.form.get('password')
    
    # JSON 数据
    data = request.get_json()                 # JSON 请求体
    
    # 请求头
    user_agent = request.headers.get('User-Agent')
    content_type = request.content_type
    
    # 其他信息
    method = request.method    # GET/POST/PUT/DELETE
    path = request.path        # /submit
    url = request.url          # 完整 URL
    ip = request.remote_addr   # 客户端 IP
    cookies = request.cookies  # Cookie 字典
    
    return '提交成功'
```

### 6.2 请求对象常用属性表

| 属性 | 类型 | 说明 |
|------|------|------|
| `request.method` | str | HTTP 请求方法 |
| `request.args` | MultiDict | URL 查询参数 (`?key=value`) |
| `request.form` | MultiDict | POST 表单数据 |
| `request.json` | dict | POST JSON 数据（需调用 `get_json()`） |
| `request.files` | MultiDict | 上传的文件 |
| `request.headers` | EnvironHeaders | 请求头 |
| `request.cookies` | dict | Cookie |
| `request.path` | str | 请求路径 |
| `request.url` | str | 完整 URL |
| `request.remote_addr` | str | 客户端 IP |
| `request.user_agent` | str | User-Agent |

### 6.3 响应对象

Flask 视图函数可以返回多种形式的响应：

```python
from flask import Flask, jsonify, make_response, redirect, abort

# 方式一：直接返回字符串（自动转成 200 + text/html）
@app.route('/')
def index():
    return '<h1>Hello</h1>'

# 方式二：返回 JSON
@app.route('/api/data')
def api_data():
    return jsonify({
        'name': 'Flask',
        'version': '3.0',
        'features': ['轻量', '灵活', '扩展丰富']
    })

# 方式三：自定义状态码
@app.route('/created')
def created():
    return '创建成功', 201  # (响应体, 状态码)

# 方式四：make_response 构建完整响应
@app.route('/custom')
def custom():
    resp = make_response('<h1>自定义响应</h1>', 200)
    resp.headers['X-Custom-Header'] = 'hello'
    resp.set_cookie('username', 'admin', max_age=3600)
    return resp

# 方式五：重定向
@app.route('/old-page')
def old():
    return redirect('/new-page', 301)  # 301 永久重定向

# 方式六：404
@app.route('/page/<name>')
def page(name):
    if name not in ['about', 'contact']:
        abort(404)  # 返回 404 错误页面
    return f'{name} 页面'
```

### 6.4 响应对象方法速查

| 方法 | 说明 | 示例 |
|------|------|------|
| `make_response(data, status)` | 创建响应对象 | `make_response('OK', 200)` |
| `jsonify(data)` | 返回 JSON 响应 | `jsonify({'key': 'value'})` |
| `redirect(location, code)` | 重定向 | `redirect('/login', 302)` |
| `abort(code)` | 终止请求并返回错误 | `abort(404)` |
| `resp.set_cookie(key, value)` | 设置 Cookie | `resp.set_cookie('token', 'xxx')` |
| `resp.delete_cookie(key)` | 删除 Cookie | `resp.delete_cookie('token')` |
| `resp.headers[key] = value` | 设置响应头 | `resp.headers['X-API-Version'] = '2.0'` |

---

## 7. 实战：个人博客

### 7.1 项目结构

```
blog/
├── app.py                  # 应用入口
├── static/
│   └── css/
│       └── style.css       # 样式文件
└── templates/
    ├── base.html           # 父模板
    ├── index.html          # 首页（文章列表）
    ├── post.html           # 文章详情
    └── create.html         # 发布文章（表单）
```

### 7.2 数据模型设计

本实战用 Python 列表模拟数据库（后续学习 Day 066 会换成真正的数据库）：

```python
# posts = [
#     {
#         'id': 1,
#         'title': '标题',
#         'content': '内容',  # 支持 HTML
#         'author': '作者',
#         'created_at': '2026-07-13'
#     }
# ]
```

### 7.3 核心功能

| 功能 | 路由 | 方法 | 说明 |
|------|------|------|------|
| 文章列表 | `/` | GET | 按时间倒序显示所有文章 |
| 文章详情 | `/post/<int:id>` | GET | 查看文章完整内容 |
| 发布文章 | `/create` | GET/POST | 显示/处理发布表单 |
| 删除文章 | `/post/<int:id>/delete` | POST | 删除指定文章 |

### 7.4 各模板说明

**base.html**：全局布局模板，包含导航栏、页脚、CSS 引用

**index.html**：继承 base.html，循环显示文章列表，展示标题、摘要、作者、时间

**post.html**：继承 base.html，显示文章完整内容

**create.html**：继承 base.html，包含标题、内容、作者的输入表单

---

## 8. 调试与开发技巧

### 8.1 调试模式

```python
if __name__ == '__main__':
    app.run(debug=True)
```

**调试模式提供**：
1. **自动重载**：修改代码自动重启服务器
2. **交互式调试器**：出错时在浏览器中看到完整堆栈，可以执行任意 Python 代码
3. **更详细的错误提示**

> ⚠️ **安全警告**：生产环境永远不会 `debug=True`，因为调试器允许远程执行代码！

### 8.2 常用配置

```python
app = Flask(__name__)

# 基础配置
app.config['DEBUG'] = True              # 调试模式
app.config['SECRET_KEY'] = 'dev-key'    # 密钥（用于 session 等）
app.config['HOST'] = '0.0.0.0'          # 监听所有网络接口
app.config['PORT'] = 5000               # 端口

# 生产环境配置
# app.config['DEBUG'] = False
# app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback')
```

### 8.3 常用扩展一览

| 扩展 | 用途 |
|------|------|
| Flask-SQLAlchemy | 数据库 ORM |
| Flask-Login | 用户认证 |
| Flask-WTF | 表单验证 |
| Flask-Migrate | 数据库迁移 |
| Flask-Mail | 发送邮件 |
| Flask-CORS | 跨域支持 |
| Flask-RESTful | REST API 构建 |

---

## 9. 思考题

1. **路由设计**：Flask 的路由匹配顺序是怎样的？如果同时有 `/post/<id>` 和 `/post/create`，访问 `/post/create` 会匹配哪个？怎么保证正确匹配？

2. **模板 vs 前后端分离**：使用 Jinja2 模板渲染（服务端渲染）和前后端分离（Vue/React + REST API）各有什么优缺点？什么时候该用哪种？

3. **请求与响应**：HTTP 是无状态协议，那 Flask 如何实现"记住用户已登录"的功能？Session 和 Cookie 在这里扮演什么角色？

4. **调试模式的意义**：为什么 Flask 要把调试模式和热重载放在一起提供？这种设计对开发效率有什么影响？有什么潜在风险？

5. **微框架哲学**：Flask 作为"微框架"，和 Django 这样的"全功能框架"比，各有什么优劣？一个简单的博客应该用哪个？一个大型电商平台呢？

---

## 📚 参考资料

- [Flask 官方文档](https://flask.palletsprojects.com/)
- [Jinja2 模板引擎文档](https://jinja.palletsprojects.com/)
- [Flask 模式——大型应用](https://flask.palletsprojects.com/en/stable/patterns/packages/)
- [HTTP 状态码](https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Status)
