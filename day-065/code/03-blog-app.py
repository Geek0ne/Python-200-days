#!/usr/bin/env python3
"""
03 - Flask 实战：个人博客系统

一个完整的个人博客应用，包含：
1. 文章列表展示（按时间倒序）
2. 文章详情查看（Markdown 风格内容）
3. 发布新文章（表单提交）
4. 删除文章
5. 文章搜索
6. 用户友好的界面

运行方式：
    python3 03-blog-app.py
    
然后在浏览器访问：
    - http://localhost:5000/          —— 首页文章列表
    - http://localhost:5000/create    —— 发布新文章
    - http://localhost:5000/post/1    —— 查看文章详情

技术要点：
    - 用列表模拟数据库（后续会用真正数据库替代）
    - 模板继承实现统一布局
    - GET/POST 双方法处理表单
    - 动态路由捕获文章 ID
    - 查询参数实现搜索功能
"""

from flask import (
    Flask, render_template_string, request, redirect,
    url_for, abort, flash
)
from datetime import datetime
import html  # HTML 转义，防止 XSS 攻击

# ============================================================
# 数据层（模拟数据库）
# ============================================================
# 用 Python 列表存储文章数据
# 后续会替换为 SQLAlchemy + 数据库
POSTS = [
    {
        'id': 1,
        'title': 'Flask 入门指南',
        'content': '''
<p>Flask 是一个轻量级的 Python Web 框架，适合快速开发 Web 应用。</p>
<p>它的核心设计哲学是：<strong>微框架</strong>——只提供最基本的功能，
其他功能通过扩展来添加。</p>
<h3>为什么选择 Flask？</h3>
<ul>
    <li><strong>轻量</strong>：核心代码只有几千行</li>
    <li><strong>灵活</strong>：不受框架约束，你可以自由选择组件</li>
    <li><strong>易学</strong>：半小时就能上手</li>
    <li><strong>文档优秀</strong>：官方文档清晰详细</li>
</ul>
<p>如果你刚开始学习 Python Web 开发，Flask 是绝佳的起点！</p>
<p>通过 Flask，你可以快速理解 HTTP 请求-响应模型、模板引擎、
路由系统等 Web 开发的核心概念。</p>
        ''',
        'author': '学习官',
        'created_at': '2026-07-13 08:00:00',
    },
    {
        'id': 2,
        'title': 'Python 3.13 新特性一览',
        'content': '''
<p>Python 3.13 带来了许多激动人心的新特性，让我们一探究竟：</p>
<h3>主要新特性</h3>
<ul>
    <li><strong>改进的交互式解释器</strong>：支持多行编辑、语法高亮</li>
    <li><strong>JIT 编译器的实验性支持</strong>：性能提升</li>
    <li><strong>类型系统增强</strong>：TypeVar 默认行为改进</li>
    <li><strong>错误信息优化</strong>：更友好的错误提示</li>
</ul>
<p>这些改进让 Python 在保持易用性的同时，性能和开发体验不断提升。</p>
        ''',
        'author': '技术小编',
        'created_at': '2026-07-12 16:30:00',
    },
    {
        'id': 3,
        'title': '理解 HTTP 协议',
        'content': '''
<p>HTTP（超文本传输协议）是 Web 的基石。无论你使用什么框架，
理解 HTTP 都是 Web 开发的基本功。</p>
<h3>核心概念</h3>
<ol>
    <li><strong>请求-响应模型</strong>：客户端发请求，服务器回响应</li>
    <li><strong>无状态</strong>：每次请求都是独立的</li>
    <li><strong>方法</strong>：GET（获取）、POST（创建）、PUT（更新）、DELETE（删除）</li>
    <li><strong>状态码</strong>：200（成功）、404（未找到）、500（服务器错误）</li>
</ol>
<p>掌握 HTTP 后，你再学任何 Web 框架都会事半功倍！</p>
        ''',
        'author': '网络专家',
        'created_at': '2026-07-11 10:15:00',
    },
]

# 自增 ID 计数器
_next_id = len(POSTS) + 1


# ============================================================
# 模板定义
# ============================================================

# 父模板：全局布局
BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}我的博客{% endblock %}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.8;
            color: #333;
            background: #f5f5f5;
        }
        nav {
            background: #2c3e50;
            color: white;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        nav .brand { font-size: 1.3rem; font-weight: bold; }
        nav a { color: white; text-decoration: none; margin-left: 1.5rem; }
        nav a:hover { text-decoration: underline; }
        .container { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
        .flash {
            padding: 0.75rem 1rem;
            border-radius: 6px;
            margin-bottom: 1rem;
        }
        .flash-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .flash-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .post-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .post-card h2 { margin-bottom: 0.5rem; }
        .post-card h2 a { color: #2c3e50; text-decoration: none; }
        .post-card h2 a:hover { color: #3498db; }
        .post-meta {
            color: #888;
            font-size: 0.875rem;
            margin-bottom: 0.75rem;
        }
        .post-meta span { margin-right: 1rem; }
        .post-summary { color: #666; }
        .btn {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            text-decoration: none;
            border: none;
            cursor: pointer;
            font-size: 0.9rem;
        }
        .btn-primary { background: #3498db; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-secondary { background: #95a5a6; color: white; }
        .btn:hover { opacity: 0.9; }
        .search-box { 
            display: flex; gap: 0.5rem; margin-bottom: 1.5rem; 
        }
        .search-box input {
            flex: 1; padding: 0.5rem; border: 1px solid #ddd;
            border-radius: 4px; font-size: 1rem;
        }
        .search-box button { padding: 0.5rem 1rem; }
        .post-content { 
            background: white; padding: 2rem; border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .post-content h3 { margin-top: 1.5rem; margin-bottom: 0.5rem; }
        .post-content ul, .post-content ol { margin-left: 1.5rem; }
        .post-content li { margin-bottom: 0.25rem; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.25rem; font-weight: bold; }
        .form-group input, .form-group textarea {
            width: 100%; padding: 0.5rem; border: 1px solid #ddd;
            border-radius: 4px; font-size: 1rem;
        }
        .form-group textarea { min-height: 200px; font-family: monospace; }
        .empty-state { text-align: center; padding: 3rem; color: #888; }
        .empty-state h2 { margin-bottom: 1rem; }
        footer {
            text-align: center; padding: 2rem; color: #888;
            margin-top: 3rem;
        }
    </style>
</head>
<body>
    <nav>
        <span class="brand">📝 我的博客</span>
        <div>
            <a href="{{ url_for('index') }}">首页</a>
            <a href="{{ url_for('create') }}">发布文章</a>
        </div>
    </nav>

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash flash-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <footer>
        <p>Flask 个人博客 &copy; 2026 | 用 ❤️ 和 Python 构建</p>
    </footer>
</body>
</html>'''


# ============================================================
# Flask 应用
# ============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'blog-secret-key-dev'
app.config['JSON_AS_ASCII'] = False


# ============================================================
# 路由：首页 — 文章列表
# ============================================================
@app.route('/')
def index():
    """
    首页：显示所有文章（支持搜索过滤）
    
    搜索功能：?q=关键词
    - 按标题和作者搜索
    - 不区分大小写
    - 没有结果时显示友好的空状态
    """
    query = request.args.get('q', '').strip()
    
    # 按创建时间倒序排列
    posts = sorted(POSTS, key=lambda p: p['created_at'], reverse=True)
    
    # 如果有搜索关键词，过滤文章
    if query:
        query_lower = query.lower()
        posts = [
            p for p in posts
            if query_lower in p['title'].lower()
            or query_lower in p['author'].lower()
            or query_lower in p['content'].lower()
        ]
    
    return render_template_string('''{% extends "base" %}
{% block title %}{{ "搜索: " + query if query else "首页" }} - 我的博客{% endblock %}
{% block content %}
<h1 style="margin-bottom: 1.5rem;">
    {% if query %}
        搜索结果：{{ query }}（{{ posts|length }} 篇）
    {% else %}
        最新文章
    {% endif %}
</h1>

<!-- 搜索框 -->
<form class="search-box" method="GET" action="{{ url_for('index') }}">
    <input type="text" name="q" placeholder="搜索文章标题/作者..." 
           value="{{ query }}">
    <button type="submit" class="btn btn-primary">搜索</button>
    {% if query %}
        <a href="{{ url_for('index') }}" class="btn btn-secondary">清除</a>
    {% endif %}
</form>

{% if posts %}
    {% for post in posts %}
    <div class="post-card">
        <h2><a href="{{ url_for('show_post', post_id=post.id) }}">
            {{ post.title }}
        </a></h2>
        <div class="post-meta">
            <span>✍️ {{ post.author }}</span>
            <span>📅 {{ post.created_at }}</span>
        </div>
        <div class="post-summary">
            {{ post.content|striptags|truncate(150) }}
        </div>
        <div style="margin-top: 0.75rem;">
            <a href="{{ url_for('show_post', post_id=post.id) }}" 
               class="btn btn-primary">阅读全文 →</a>
        </div>
    </div>
    {% endfor %}
{% else %}
    <div class="empty-state">
        <h2>😕 没有找到文章</h2>
        {% if query %}
            <p>没有匹配 "{{ query }}" 的文章，试试其他关键词？</p>
        {% else %}
            <p>还没有文章，成为第一位作者吧！</p>
            <a href="{{ url_for('create') }}" class="btn btn-primary"
               style="margin-top: 1rem;">发布第一篇文章</a>
        {% endif %}
    </div>
{% endif %}
{% endblock %}''', 
        posts=posts,
        query=query,
    )


# ============================================================
# 路由：文章详情
# ============================================================
@app.route('/post/<int:post_id>')
def show_post(post_id):
    """
    文章详情页面
    - 根据 ID 查找文章
    - 不存在则返回 404
    """
    # 查找文章
    post = None
    for p in POSTS:
        if p['id'] == post_id:
            post = p
            break
    
    if post is None:
        abort(404)
    
    return render_template_string('''{% extends "base" %}
{% block title %}{{ post.title }} - 我的博客{% endblock %}
{% block content %}
<div class="post-content">
    <h1>{{ post.title }}</h1>
    <div class="post-meta" style="margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #eee;">
        <span>✍️ {{ post.author }}</span>
        <span>📅 {{ post.created_at }}</span>
    </div>
    <div>
        {{ post.content|safe }}
    </div>
    <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #eee;">
        <a href="{{ url_for('index') }}" class="btn btn-secondary">← 返回首页</a>
        <form method="POST" action="{{ url_for('delete_post', post_id=post.id) }}"
              style="display: inline;"
              onsubmit="return confirm('确定要删除这篇文章吗？');">
            <button type="submit" class="btn btn-danger">🗑️ 删除</button>
        </form>
    </div>
</div>
{% endblock %}''', 
        post=post,
    )


# ============================================================
# 路由：发布文章
# ============================================================
@app.route('/create', methods=['GET', 'POST'])
def create():
    """
    发布新文章
    - GET：显示发布表单
    - POST：处理表单提交，创建新文章
    """
    global _next_id
    
    if request.method == 'POST':
        # 获取表单数据
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        author = request.form.get('author', '').strip()
        
        # 验证数据
        errors = []
        if not title:
            errors.append('标题不能为空')
        if not content:
            errors.append('内容不能为空')
        if not author:
            errors.append('作者不能为空')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template_string(CREATE_TEMPLATE, 
                title=title, content=content, author=author)
        
        # 创建新文章
        new_post = {
            'id': _next_id,
            'title': title,
            'content': content,
            'author': author,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        POSTS.append(new_post)
        _next_id += 1
        
        flash('文章发布成功！', 'success')
        return redirect(url_for('show_post', post_id=new_post['id']))
    
    # GET 请求：显示表单
    return render_template_string(CREATE_TEMPLATE, 
        title='', content='', author='')


CREATE_TEMPLATE = '''{% extends "base" %}
{% block title %}发布文章 - 我的博客{% endblock %}
{% block content %}
<h1 style="margin-bottom: 1.5rem;">📝 发布新文章</h1>

<form method="POST">
    <div class="form-group">
        <label for="title">文章标题 *</label>
        <input type="text" id="title" name="title" 
               placeholder="给你的文章起个名字" 
               value="{{ title }}" required>
    </div>
    
    <div class="form-group">
        <label for="author">作者 *</label>
        <input type="text" id="author" name="author" 
               placeholder="你的名字" 
               value="{{ author }}" required>
    </div>
    
    <div class="form-group">
        <label for="content">文章内容 *（支持 HTML 格式）</label>
        <textarea id="content" name="content" 
                  placeholder="写点什么吧..." required>{{ content }}</textarea>
    </div>
    
    <div style="display: flex; gap: 0.5rem;">
        <button type="submit" class="btn btn-primary">发布文章</button>
        <a href="{{ url_for('index') }}" class="btn btn-secondary">取消</a>
    </div>
</form>
{% endblock %}'''


# ============================================================
# 路由：删除文章
# ============================================================
@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    """
    删除文章（POST 请求）
    - 使用 POST 而不是 GET，防止 CSRF 和误操作
    - 删除后重定向到首页
    """
    global POSTS
    
    post_to_delete = None
    for p in POSTS:
        if p['id'] == post_id:
            post_to_delete = p
            break
    
    if post_to_delete is None:
        abort(404)
    
    POSTS.remove(post_to_delete)
    flash(f'文章 "{post_to_delete["title"]}" 已删除', 'success')
    return redirect(url_for('index'))


# ============================================================
# 错误处理
# ============================================================
@app.errorhandler(404)
def not_found(error):
    return render_template_string('''{% extends "base" %}
{% block title %}404 - 页面未找到{% endblock %}
{% block content %}
<div style="text-align: center; padding: 3rem;">
    <h1 style="font-size: 4rem; color: #e74c3c;">404</h1>
    <h2>页面未找到</h2>
    <p style="color: #666; margin: 1rem 0;">您访问的页面不存在</p>
    <a href="{{ url_for('index') }}" class="btn btn-primary">← 返回首页</a>
</div>
{% endblock %}'''), 404


# ============================================================
# 🚀 启动应用
# ============================================================
if __name__ == '__main__':
    print("=" * 50)
    print("📝 个人博客启动...")
    print("   访问: http://127.0.0.1:5000/")
    print("   发布: http://127.0.0.1:5000/create")
    print("=" * 50)
    print(f"\n当前共有 {len(POSTS)} 篇示例文章")
    print("按 Ctrl+C 停止服务器\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
