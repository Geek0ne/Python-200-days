#!/usr/bin/env python3
"""
02 - Flask 进阶：模板继承、错误处理、请求钩子、蓝图

本示例演示 Flask 进阶用法：
1. Jinja2 模板继承（演示模板语法）
2. 自定义错误页面（404、500）
3. 请求钩子（before_request、after_request）
4. 蓝图（Blueprint）——模块化组织路由
5. 进阶避坑：循环导入、模板缓存、SECRET_KEY

运行方式：
    python3 02-flask-advanced.py
    
然后在浏览器访问：
    - http://localhost:5000/
    - http://localhost:5000/nonexistent   (测试 404)
    - http://localhost:5000/trigger-error (测试 500)
"""

from flask import (
    Flask, render_template_string, request, jsonify,
    abort, g, session
)
from datetime import datetime
import uuid

# ============================================================
# 第一部分：Jinja2 模板 —— 在代码中内联模板（便于演示）
# 实际项目应放在 templates/ 目录下的独立 .html 文件中
# ============================================================

# 父模板（layout）
BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Flask 进阶{% endblock %}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, sans-serif; line-height: 1.6; 
               min-height: 100vh; display: flex; flex-direction: column; }
        nav { background: #2c3e50; padding: 1rem; }
        nav a { color: white; text-decoration: none; margin-right: 1.5rem; }
        nav a:hover { text-decoration: underline; }
        .container { max-width: 900px; margin: 2rem auto; padding: 0 1rem; flex: 1; }
        footer { background: #ecf0f1; text-align: center; padding: 1rem; 
                 margin-top: auto; }
        .flash { background: #d4edda; color: #155724; padding: 0.75rem; 
                 border-radius: 4px; margin-bottom: 1rem; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; 
                margin-bottom: 1rem; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
    </style>
    {% block extra_head %}{% endblock %}
</head>
<body>
    <nav>
        <a href="/">🏠 首页</a>
        <a href="/admin">🔧 后台</a>
        <a href="/api/status">📡 API 状态</a>
        <a href="/trigger-error">💥 触发错误</a>
    </nav>

    <div class="container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="flash">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <footer>
        <p>Flask 进阶教程 &copy; 2026 | 
           请求处理时间: {{ "%.2f"|format(g.get("process_time", 0)) }}ms</p>
    </footer>
</body>
</html>'''

# 首页模板
INDEX_TEMPLATE = '''{% extends "base" %}
{% block title %}首页 - Flask 进阶{% endblock %}
{% block content %}
<h1>🚀 Flask 进阶功能演示</h1>

<div class="card">
    <h2>📌 请求钩子</h2>
    <p>访问任何页面时，<code>before_request</code> 和 <code>after_request</code> 
       会自动执行。查看页脚的处理时间。</p>
</div>

<div class="card">
    <h2>📌 模板过滤器</h2>
    <p>当前时间（原始）: {{ now }}</p>
    <p>当前时间（格式化）: {{ now|strftime }}</p>
    <p>标题大写: {{ "hello, flask!"|capitalize }}</p>
    <p>列表连接: {{ items|join(" → ") }}</p>
    <p>截断文本: {{ long_text|truncate(30) }}</p>
</div>

<div class="card">
    <h2>📌 用户访问统计</h2>
    <ul>
        <li>会话 ID: <code>{{ session_id }}</code></li>
        <li>访问次数: {{ visit_count }}</li>
        <li>当前用户代理: <code>{{ user_agent[:50] }}...</code></li>
    </ul>
</div>

<div class="card">
    <h2>📌 模板条件与循环</h2>
    <h3>推荐的 Python Web 框架：</h3>
    <ul>
    {% for framework in frameworks %}
        <li>
            {% if framework.popular %}
                <strong>{{ framework.name }}</strong> ⭐ 热门
            {% else %}
                {{ framework.name }}
            {% endif %}
            — {{ framework.desc }}
        </li>
    {% endfor %}
    </ul>
</div>
{% endblock %}'''

# ============================================================
# 第二部分：创建应用
# ============================================================

app = Flask(__name__)

# 重要：生产环境必须设置一个复杂的 SECRET_KEY！
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['JSON_AS_ASCII'] = False  # JSON 支持中文


# ============================================================
# 第三部分：自定义 Jinja2 过滤器
# ============================================================

@app.template_filter('strftime')
def strftime_filter(dt, fmt='%Y-%m-%d %H:%M:%S'):
    """自定义模板过滤器：格式化时间"""
    if isinstance(dt, datetime):
        return dt.strftime(fmt)
    return dt


# ============================================================
# 第四部分：请求钩子（Hooks）
# ============================================================

@app.before_request
def before_request():
    """
    每次请求前执行：
    1. 记录开始时间
    2. 初始化会话数据
    3. 记录请求日志
    """
    # 在 g 对象中记录开始时间
    g.start_time = datetime.now()
    
    # 初始化访问计数器
    if 'visit_count' not in session:
        session['visit_count'] = 0
        session['session_id'] = str(uuid.uuid4())
    session['visit_count'] += 1
    
    # 记录请求日志（开发用）
    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
          f"{request.method} {request.path} - "
          f"Session: {session.get('session_id', 'new')[:8]}...")


@app.after_request
def after_request(response):
    """
    每次请求后执行（即使出错也会执行）：
    1. 计算处理时间
    2. 添加调试头
    """
    if hasattr(g, 'start_time'):
        elapsed = (datetime.now() - g.start_time).total_seconds() * 1000
        g.process_time = elapsed
        
        # 添加响应头（调试用）
        response.headers['X-Process-Time-MS'] = str(round(elapsed, 2))
    
    # 添加服务器标识
    response.headers['X-Powered-By'] = 'Flask 进阶教程'
    
    return response


# ============================================================
# 第五部分：路由与视图
# ============================================================

@app.route('/')
def index():
    """首页：演示模板语法"""
    return render_template_string(
        INDEX_TEMPLATE,
        now=datetime.now(),
        items=['Flask', 'Django', 'FastAPI'],
        long_text='这是一个很长的文本，用于演示 truncate 过滤器的截断效果。',
        frameworks=[
            {'name': 'Flask', 'desc': '轻量灵活的微框架', 'popular': True},
            {'name': 'Django', 'desc': '全功能大而全', 'popular': True},
            {'name': 'FastAPI', 'desc': '高性能异步框架', 'popular': True},
            {'name': 'Tornado', 'desc': '异步网络库', 'popular': False},
            {'name': 'Pyramid', 'desc': '可伸缩的企业框架', 'popular': False},
        ],
        session_id=session.get('session_id', 'unknown'),
        visit_count=session.get('visit_count', 0),
        user_agent=request.headers.get('User-Agent', 'unknown'),
    )


@app.route('/admin')
def admin_panel():
    """模拟后台管理页面（演示蓝图的思想）"""
    return render_template_string('''{% extends "base" %}
{% block title %}后台管理{% endblock %}
{% block content %}
<h1>🔧 后台管理面板</h1>
<div class="card">
    <h2>系统状态</h2>
    <ul>
        <li>Flask 版本: 3.x</li>
        <li>调试模式: {{ "开启" if debug else "关闭" }}</li>
        <li>服务器时间: {{ now.strftime("%Y-%m-%d %H:%M:%S") }}</li>
        <li>活跃会话: {{ session_id[:8] }}...</li>
    </ul>
</div>
<div class="card">
    <h2>⚠️ 避坑提醒</h2>
    <ul>
        <li><strong>SECRET_KEY</strong> 必须设置，否则 session 会报错！</li>
        <li><strong>debug=True</strong> 绝不能在生产环境开启</li>
        <li><strong>循环导入</strong>：大型应用要避免 app 和 views 互相导入</li>
        <li><strong>模板缓存</strong>：生产环境 Jinja2 会缓存模板，修改后需重启</li>
        <li><strong>JSON 中文</strong>：设置 JSON_AS_ASCII=False 显示中文</li>
    </ul>
</div>
{% endblock %}''', 
        debug=app.debug, 
        now=datetime.now(),
        session_id=session.get('session_id', 'unknown'),
    )


@app.route('/api/status')
def api_status():
    """JSON API 端点"""
    return jsonify({
        'status': 'ok',
        'server_time': datetime.now().isoformat(),
        'uptime_seconds': 0,
        'session_id': session.get('session_id', 'unknown'),
        'visit_count': session.get('visit_count', 0),
        'active_endpoints': 8,
    })


# ============================================================
# 第六部分：自定义错误处理
# ============================================================

ERROR_TEMPLATE = '''{% extends "base" %}
{% block title %}{{ code }} - {{ name }}{% endblock %}
{% block content %}
<div style="text-align: center; padding: 4rem 0;">
    <h1 style="font-size: 5rem; color: #e74c3c;">{{ code }}</h1>
    <h2>{{ name }}</h2>
    <p style="color: #666; margin: 1rem 0;">{{ description }}</p>
    <a href="/" style="display: inline-block; margin-top: 1rem; 
       padding: 0.75rem 1.5rem; background: #3498db; color: white; 
       text-decoration: none; border-radius: 4px;">
        ← 返回首页
    </a>
</div>
{% endblock %}'''


@app.errorhandler(404)
def not_found(error):
    """自定义 404 页面"""
    return render_template_string(
        ERROR_TEMPLATE,
        code=404,
        name='页面未找到',
        description='您访问的页面不存在，请检查 URL 是否正确。',
    ), 404


@app.errorhandler(500)
def server_error(error):
    """自定义 500 页面"""
    return render_template_string(
        ERROR_TEMPLATE,
        code=500,
        name='服务器内部错误',
        description='服务器出错了，请稍后重试或联系管理员。',
    ), 500


@app.route('/trigger-error')
def trigger_error():
    """主动触发一个 500 错误来测试错误处理器"""
    # 访问此 URL 会触发 ZeroDivisionError
    result = 1 / 0  # ZeroDivisionError
    return f'你不会看到这句话: {result}'


# ============================================================
# ⚠️ 第七部分：常见避坑
# ============================================================

"""
避坑 1：循环导入（Circular Import）

❌ 错误写法：
    # app.py
    from views import home
    
    # views.py
    from app import app
    
✅ 正确做法：延迟导入 或 使用应用工厂模式

避坑 2：模板修改不生效

    debug=False 时 Jinja2 会缓存模板文件。
    解决方法：debug=True（开发时），或重启应用（生产时）。

避坑 3：SECRET_KEY 为空

    Flask session 需要 SECRET_KEY 来签名 cookie。
    如果不设置，访问 session 会报错：
    RuntimeError: The session is unavailable because no secret key was set.

避坑 4：JSON 返回中文显示为 \\uXXXX

    默认 Flask jsonify 会对中文转义。
    解决方法：app.config['JSON_AS_ASCII'] = False

避坑 5：多线程共享变量

    每个请求在不同线程中运行，全局变量可能被多个请求同时修改。
    使用 g 对象存储请求级数据（每个请求独立），不要用全局变量存请求数据。
"""


# ============================================================
# 启动
# ============================================================
if __name__ == '__main__':
    print("🚀 Flask 进阶应用启动...")
    print("   访问 http://127.0.0.1:5000/")
    print("   测试 404: http://127.0.0.1:5000/任何不存在的路径")
    print("   测试 500: http://127.0.0.1:5000/trigger-error")
    print("   按 Ctrl+C 停止服务器")
    app.run(debug=True, host='127.0.0.1', port=5000)
