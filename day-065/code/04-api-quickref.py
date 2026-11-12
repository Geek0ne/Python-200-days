#!/usr/bin/env python3
"""
04 - Flask API 速查手册（可直接运行）

本文件是 Flask 路由、请求、响应、模板等核心 API 的速查参考。
可以直接运行后在浏览器中查看所有 API 的实时演示。

运行方式：
    python3 04-api-quickref.py

访问：
    http://localhost:5000/   —— 首页（API 速查索引）
"""

from flask import Flask, request, jsonify, make_response, redirect, url_for, render_template_string
from datetime import datetime

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

INDEX_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Flask API 速查</title>
    <style>
        body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }
        h1 { border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #2c3e50; margin-top: 30px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background: #f5f5f5; font-weight: bold; }
        tr:hover { background: #f9f9f9; }
        code { background: #eee; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
        .demo-link { color: #3498db; text-decoration: none; }
        .demo-link:hover { text-decoration: underline; }
        .section { background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>🚀 Flask API 速查手册</h1>
    <p>当前时间: {now} | 服务器: Flask {version}</p>

    <div class="section">
        <h2>📌 路由系统</h2>
        <table>
            <tr><th>API</th><th>说明</th><th>示例</th></tr>
            <tr><td><code>@app.route('/')</code></td><td>基本路由</td><td><a class="demo-link" href="/demo/basic">测试 →</a></td></tr>
            <tr><td><code>@app.route('/&lt;name&gt;')</code></td><td>动态路由（字符串）</td><td><a class="demo-link" href="/demo/hello">测试 →</a></td></tr>
            <tr><td><code>@app.route('/&lt;int:id&gt;')</code></td><td>动态路由（整数）</td><td><a class="demo-link" href="/demo/42">测试 →</a></td></tr>
            <tr><td><code>methods=['GET','POST']</code></td><td>限制 HTTP 方法</td><td><a class="demo-link" href="/demo/methods">测试 →</a></td></tr>
        </table>
    </div>

    <div class="section">
        <h2>📌 请求对象</h2>
        <table>
            <tr><th>属性/方法</th><th>说明</th><th>测试</th></tr>
            <tr><td><code>request.args.get('key')</code></td><td>查询参数</td><td><a class="demo-link" href="/demo/request?a=1&b=hello">测试 →</a></td></tr>
            <tr><td><code>request.headers</code></td><td>请求头</td><td><a class="demo-link" href="/demo/headers">测试 →</a></td></tr>
            <tr><td><code>request.method</code></td><td>请求方法</td><td><a class="demo-link" href="/demo/request">测试 →</a></td></tr>
            <tr><td><code>request.remote_addr</code></td><td>客户端 IP</td><td><a class="demo-link" href="/demo/request">测试 →</a></td></tr>
        </table>
    </div>

    <div class="section">
        <h2>📌 响应方式</h2>
        <table>
            <tr><th>方式</th><th>代码</th><th>测试</th></tr>
            <tr><td>字符串</td><td><code>return 'Hello'</code></td><td><a class="demo-link" href="/demo/text">测试 →</a></td></tr>
            <tr><td>JSON</td><td><code>return jsonify(data)</code></td><td><a class="demo-link" href="/demo/json">测试 →</a></td></tr>
            <tr><td>重定向</td><td><code>return redirect(url)</code></td><td><a class="demo-link" href="/demo/redirect">测试 →</a></td></tr>
            <tr><td>自定义头</td><td><code>make_response()</code></td><td><a class="demo-link" href="/demo/custom">测试 →</a></td></tr>
            <tr><td>404</td><td><code>abort(404)</code></td><td><a class="demo-link" href="/demo/abort-404">测试 →</a></td></tr>
        </table>
    </div>

    <div class="section">
        <h2>📌 URL 构建</h2>
        <table>
            <tr><th>函数</th><th>说明</th></tr>
            <tr><td><code>url_for('index')</code></td><td>生成 '/' 的 URL</td></tr>
            <tr><td><code>url_for('show_demo', name='test')</code></td><td>生成 '/demo/test'</td></tr>
            <tr><td><code>url_for('static', filename='css/style.css')</code></td><td>生成 '/static/css/style.css'</td></tr>
        </table>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(INDEX_HTML, now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), version='3.x')

@app.route('/demo/basic')
def demo_basic():
    return '<h1>✅ 基本路由</h1><p>这是 @app.route("/") 的效果</p><a href="/">← 返回</a>'

@app.route('/demo/<name>')
def show_demo(name):
    return f'<h1>✅ 动态路由</h1><p>捕获的变量: {name}</p><p>类型: {type(name).__name__}</p><a href="/">← 返回</a>'

@app.route('/demo/<int:num>')
def show_number(num):
    return f'<h1>✅ 整数路由</h1><p>捕获的整数: {num}</p><p>运算: {num} × 2 = {num * 2}</p><a href="/">← 返回</a>'

@app.route('/demo/methods', methods=['GET', 'POST'])
def demo_methods():
    return f'<h1>✅ 多方法路由</h1><p>当前请求方法: {request.method}</p><form method="POST"><button type="submit">发送 POST 请求</button></form><a href="/">← 返回</a>'

@app.route('/demo/request')
def demo_request():
    args = dict(request.args)
    return f'''
    <h1>✅ 请求对象</h1>
    <table border="1" cellpadding="8">
        <tr><td>method</td><td>{request.method}</td></tr>
        <tr><td>path</td><td>{request.path}</td></tr>
        <tr><td>url</td><td>{request.url}</td></tr>
        <tr><td>remote_addr</td><td>{request.remote_addr}</td></tr>
        <tr><td>查询参数</td><td>{args}</td></tr>
    </table>
    <a href="/">← 返回</a>
    '''

@app.route('/demo/headers')
def demo_headers():
    headers = dict(request.headers)
    rows = ''.join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in sorted(headers.items())[:15])
    return f'<h1>✅ 请求头</h1><table border="1" cellpadding="8">{rows}</table><a href="/">← 返回</a>'

@app.route('/demo/text')
def demo_text():
    return '<h1>✅ 返回字符串</h1><p>Flask 自动包装为 text/html 响应</p><a href="/">← 返回</a>'

@app.route('/demo/json')
def demo_json():
    return jsonify({
        'status': 'ok',
        'message': '这是 JSON 响应',
        'endpoint': '/demo/json',
        'params': dict(request.args),
    })

@app.route('/demo/redirect')
def demo_redirect():
    return redirect(url_for('index'))

@app.route('/demo/custom')
def demo_custom():
    resp = make_response('<h1>✅ 自定义响应</h1><p>查看响应头的 X-Custom 字段</p><a href="/">← 返回</a>')
    resp.headers['X-Custom-Header'] = 'hello'
    resp.headers['X-API-Version'] = '3.0'
    return resp

@app.route('/demo/abort-404')
def demo_abort():
    from flask import abort
    abort(404)

if __name__ == '__main__':
    print("🚀 Flask API 速查手册启动...")
    print("   访问 http://127.0.0.1:5000/")
    app.run(debug=True, host='127.0.0.1', port=5000)
