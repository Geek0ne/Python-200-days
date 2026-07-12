# Day 065 — Web 框架入门：练习与检查表

## ✅ 今日完成清单

- [ ] 理解 Web 框架的作用和设计理念
- [ ] 理解 Flask 微框架哲学（核心精简、扩展可组装）
- [ ] 掌握 Flask 路由系统（基本路由、动态路由、HTTP 方法）
- [ ] 掌握 Jinja2 模板语法（变量输出、循环、条件、过滤器）
- [ ] 掌握模板继承（父模板/子模板、块）
- [ ] 理解静态文件的组织和使用
- [ ] 掌握 Flask 请求对象（request.args、request.form、request.headers）
- [ ] 掌握各种响应方式（字符串、JSON、重定向、自定义响应）
- [ ] 理解 URL 构建函数 url_for() 的使用
- [ ] 掌握请求钩子（before_request、after_request）
- [ ] 了解蓝图（Blueprint）模块化组织方式
- [ ] 完成实战：个人博客应用

---

## 📝 练习题

### 基础题

#### 题 1：搭建第一个 Flask 应用

创建一个 Flask 应用，包含以下路由：
1. `/` — 返回 "欢迎来到我的 Flask 应用"
2. `/about` — 返回一个包含标题、描述和联系方式的 JSON
3. `/time` — 返回当前服务器时间（格式化的字符串）
4. `/hello/<name>` — 返回 "你好, {name}!"

要求：
- 所有路由都要包含完整的类型提示
- `/time` 返回格式化的日期时间字符串
- 应用在 `127.0.0.1:5000` 运行

#### 题 2：Jinja2 模板练习

创建一个 Flask 应用，使用以下模板功能：

**模板要求（通过 render_template_string 实现）：**
1. 接收一个 `items` 列表，用 `{% for %}` 循环显示
2. 偶数项用绿色背景，奇数项用蓝色背景（用 `loop.index` 判断奇偶）
3. 如果列表为空，显示"暂无数据"
4. 显示列表长度

**访问 `/list` 路由时：**
- 传入 `items = ['Python', 'Flask', 'Jinja2', 'Web', '开发']`
- 使用模板渲染

#### 题 3：请求对象综合练习

创建以下路由，演示请求对象的各种用法：

1. `/user-info` — 显示访问者的 User-Agent、IP 地址、请求方法
2. `/add` — GET 请求，从查询参数中读取两个数字并求和（如 `/add?a=3&b=5`）
3. `/headers` — 显示所有请求头（用表格展示 key-value）
4. `/form-demo` — GET/POST 双方法，GET 显示表单，POST 处理并回显提交的数据

---

### 进阶题

#### 题 4：简易留言板

创建一个留言板应用，包含：

**功能：**
1. `/` — 显示所有留言列表
2. `/add` — GET/POST，发布新留言（昵称 + 内容）
3. `/delete/<int:id>` — POST，删除留言

**要求：**
- 用列表存储留言数据
- 使用 `flash()` 显示成功/失败消息
- 留言按时间倒序排列
- 使用模板继承（创建 base.html 结构）
- 删除需要确认弹窗

**示例数据：**
```python
messages = [
    {
        'id': 1,
        'nickname': '小明',
        'content': '今天学到了 Flask！',
        'created_at': '2026-07-13 14:30:00'
    },
]
```

#### 题 5：URL 构建与重定向

创建一个包含以下功能的应用：

1. `/go/<destination>` — 根据参数重定向到不同页面：
   - `home` → 重定向到 `/`
   - `about` → 重定向到 `/about`
   - `search` → 重定向到 `/search?q=flask`
   - 不认识的目标 → 返回 404

2. `/links` — 页面上显示 5 个链接，所有链接使用 `url_for()` 生成：
   - 首页
   - 关于页面
   - 访问 `/go/home`
   - 搜索 Flask  
   - 查看用户 "admin"

3. `/external` — 演示如何重定向到外部 URL（如 `https://flask.palletsprojects.com`）

---

## 💡 挑战题

### 挑战 1：图片画廊应用

创建一个简单的图片画廊应用：

```python
# 用字典存储图片数据
gallery = {
    1: {'title': '风景', 'filename': 'landscape.jpg', 'desc': '美丽的自然风光'},
    2: {'title': '城市', 'filename': 'city.jpg', 'desc': '繁华的城市夜景'},
}
```

**功能要求：**
1. `/gallery` — 显示所有图片缩略图（用占位图链接代替真实图片）
2. `/gallery/<int:id>` — 显示单张图片详情
3. `/gallery/tag/<tag>` — 按标签筛选（同一张图可以有多个标签）
4. 支持搜索（`/gallery?q=关键词`）

**提示：**
- 图片 URL 可以用 `https://picsum.photos/seed/{id}/300/200` 作为占位图
- 使用 Jinja2 过滤器处理文本截断

### 挑战 2：简易 URL 缩短器

实现一个 URL 缩短服务：

**功能需求：**
1. `/` — 显示表单：输入长 URL，点击缩短
2. `/shorten` — POST，生成短码并保存映射（返回短链接）
3. `/s/<short_code>` — 根据短码重定向到原始 URL
4. `/stats` — 显示所有被缩短的 URL 及其访问次数

**技术要求：**
- 短码用 6 位随机字符（字母+数字）
- 使用 `before_request` 钩子记录访问统计
- 使用 `after_request` 钩子添加响应时间头
- 使用 `session` 存储最近创建的短链接

---

## 📚 参考资料

- [Flask 官方文档（中文）](https://flask.net.cn/)
- [Flask 快速入门](https://flask.palletsprojects.com/en/stable/quickstart/)
- [Jinja2 模板设计者文档](https://jinja.palletsprojects.com/en/stable/templates/)
- [Werkzeug 文档（Flask 底层库）](https://werkzeug.palletsprojects.com/)
- [Flask 大型应用模式](https://flask.palletsprojects.com/en/stable/patterns/packages/)
