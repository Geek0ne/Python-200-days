#!/usr/bin/env python3
"""
01 - Flask 基础入门：路由、模板、请求与响应

本示例演示 Flask 的核心概念：
1. 创建应用实例与基本路由
2. 动态路由（URL 变量）
3. Jinja2 模板渲染
4. 请求对象的使用
5. 多种响应方式

运行方式：
    python3 01-flask-basics.py
    
然后在浏览器访问：
    - http://localhost:5000/
    - http://localhost:5000/user/张三
    - http://localhost:5000/search?q=python&page=2
    - http://localhost:5000/api/info
"""

from flask import Flask, request, jsonify, make_response, redirect, url_for
from datetime import datetime

# ============================================================
# 第一步：创建 Flask 应用实例
# ============================================================
# __name__ 告诉 Flask 从当前文件所在的目录寻找模板和静态文件
app = Flask(__name__)

# ============================================================
# 第二步：定义路由和视图函数
# ============================================================

# --- 2.1 基本路由 ---
@app.route('/')
def index():
    """首页：返回 HTML 字符串"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Flask 基础教程</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; }
            a { display: block; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>🚀 Flask 基础教程</h1>
        <p>当前时间：''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
        <hr>
        <h2>试试以下链接：</h2>
        <a href="/user/张三">🔗 动态路由：/user/张三</a>
        <a href="/user/admin">🔗 动态路由：/user/admin</a>
        <a href="/post/42">🔗 文章详情：/post/42</a>
        <a href="/search?q=Flask教程&page=1">🔗 搜索：/search?q=Flask教程&page=1</a>
        <a href="/api/info">🔗 JSON API：/api/info</a>
        <a href="/custom-header">🔗 自定义响应头：/custom-header</a>
        <a href="/redirect-demo">🔗 重定向示例：/redirect-demo</a>
        <a href="/greet/小明">🔗 模板渲染：/greet/小明</a>
    </body>
    </html>
    '''


# --- 2.2 动态路由（URL 变量）---
@app.route('/user/<username>')
def show_user(username):
    """使用 URL 变量 username，显示用户信息"""
    # 变量会作为参数传入视图函数
    return f'''
    <h1>👤 用户: {username}</h1>
    <p>用户名称: {username}</p>
    <p>字符数: {len(username)}</p>
    <p><a href="/">← 返回首页</a></p>
    '''


@app.route('/post/<int:post_id>')
def show_post(post_id):
    """使用 int 转换器：只匹配整数"""
    # 如果访问 /post/abc，会返回 404
    return f'''
    <h1>📄 文章详情</h1>
    <p>文章 ID: {post_id}</p>
    <p>模拟内容：这是第 {post_id} 号文章的详细内容。</p>
    <p><a href="/">← 返回首页</a></p>
    '''


@app.route('/download/<path:filepath>')
def download_file(filepath):
    """使用 path 转换器：匹配含斜杠的路径"""
    return f'下载文件路径: {filepath}'


# --- 2.3 HTTP 方法限制 ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    GET 和 POST 双方法路由
    - GET：显示登录页面
    - POST：处理登录表单
    """
    if request.method == 'POST':
        # 从表单获取数据
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # 简单的验证逻辑
        if username == 'admin' and password == '123456':
            return f'<h1>✅ 登录成功！欢迎 {username}</h1>'
        else:
            return f'''
            <h1>❌ 登录失败</h1>
            <p>用户名或密码错误</p>
            <a href="/login">重新登录</a>
            '''
    
    # GET 请求：显示登录表单
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>登录</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>登录</h1>
        <form method="POST">
            <div>
                <label>用户名：</label>
                <input type="text" name="username" required>
            </div>
            <div style="margin-top:10px">
                <label>密码：</label>
                <input type="password" name="password" required>
            </div>
            <div style="margin-top:10px">
                <button type="submit">登录</button>
            </div>
        </form>
        <p>提示：admin / 123456</p>
        <p><a href="/">← 返回首页</a></p>
    </body>
    </html>
    '''


# --- 2.4 请求对象的使用 ---
@app.route('/search')
def search():
    """
    演示 request.args：获取 URL 查询参数
    访问：/search?q=python&page=2&lang=zh
    """
    query = request.args.get('q', '')               # ?q=xxx，默认空字符串
    page = request.args.get('page', 1, type=int)     # ?page=xxx，默认1，转为int
    
    # 获取所有参数
    all_params = dict(request.args)
    
    # 获取请求头信息
    user_agent = request.headers.get('User-Agent', '未知')
    accept_language = request.headers.get('Accept-Language', '未知')
    
    return f'''
    <h1>🔍 搜索演示</h1>
    <h2>查询参数</h2>
    <ul>
        <li>搜索词: {query}</li>
        <li>页码: {page}</li>
        <li>所有参数: {all_params}</li>
    </ul>
    <h2>请求信息</h2>
    <ul>
        <li>请求方法: {request.method}</li>
        <li>请求路径: {request.path}</li>
        <li>完整 URL: {request.url}</li>
        <li>客户端 IP: {request.remote_addr}</li>
        <li>User-Agent: {user_agent[:60]}...</li>
        <li>Accept-Language: {accept_language}</li>
    </ul>
    <p><a href="/">← 返回首页</a></p>
    '''


# --- 2.5 返回 JSON ---
@app.route('/api/info')
def api_info():
    """使用 jsonify() 返回 JSON 响应"""
    data = {
        'app_name': 'Flask 基础教程',
        'version': '1.0.0',
        'endpoints': [
            '/',
            '/user/<username>',
            '/post/<int:post_id>',
            '/search',
            '/api/info',
            '/custom-header',
            '/redirect-demo',
            '/greet/<name>',
            '/login',
        ],
        'timestamp': datetime.now().isoformat(),
        'server': 'Flask Development Server',
    }
    return jsonify(data)


# --- 2.6 自定义响应头 ---
@app.route('/custom-header')
def custom_header():
    """使用 make_response() 构建自定义响应"""
    resp = make_response(f'''
    <h1>📋 自定义响应头</h1>
    <p>请在浏览器开发者工具中查看响应头</p>
    <ul>
        <li>X-Custom-Header: hello-flask</li>
        <li>X-API-Version: 2.0</li>
        <li>X-Server-Time: {datetime.now().isoformat()}</li>
    </ul>
    <p><a href="/">← 返回首页</a></p>
    ''')
    
    # 添加自定义响应头
    resp.headers['X-Custom-Header'] = 'hello-flask'
    resp.headers['X-API-Version'] = '2.0'
    resp.headers['X-Server-Time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 设置 Cookie
    resp.set_cookie('visited_at', datetime.now().isoformat(), max_age=3600)
    
    return resp


# --- 2.7 重定向 ---
@app.route('/redirect-demo')
def redirect_demo():
    """演示重定向：访问此路由会被重定向到首页"""
    # 302 临时重定向到首页
    return redirect(url_for('index'))


# ============================================================
# 第三步：启动应用
# ============================================================
if __name__ == '__main__':
    """
    使用 debug=True 开启调试模式：
    - 代码修改后自动重启（热重载）
    - 出错时显示交互式调试页面
    - 提供更详细的错误信息
    
    ⚠️ 生产环境绝不用 debug=True！
    """
    print("🚀 Flask 应用启动...")
    print("   访问 http://127.0.0.1:5000/")
    print("   按 Ctrl+C 停止服务器")
    app.run(debug=True, host='127.0.0.1', port=5000)
