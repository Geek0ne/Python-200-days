# Day 067 练习题清单

## 练习 1：Todo API ⭐⭐
创建一个 Todo API，包含以下功能：
- POST /todos/ —— 创建待办事项（title, description, priority: low/medium/high）
- GET /todos/ —— 获取所有待办（支持按 priority 过滤）
- GET /todos/{id} —— 获取单个待办
- PUT /todos/{id} —— 更新待办（支持标记完成 done=True）
- DELETE /todos/{id} —— 删除待办

**要求：**
- 使用 Pydantic 模型进行数据验证
- priority 使用枚举类型
- 支持分页

## 练习 2：用户认证 ⭐⭐⭐
为练习 1 的 Todo API 添加用户认证：
- POST /auth/register —— 注册（username, password）
- POST /auth/login —— 登录（返回 token）
- 所有 Todo 路由需要 token 认证
- 每个用户只能看到自己的待办

**要求：**
- 使用依赖注入实现认证
- Token 放在 X-Token 请求头中
- 密码使用 Pydantic 验证（最少 8 位）

## 练习 3：文件上传 API ⭐⭐⭐
创建一个文件上传 API：
- POST /upload/ —— 上传文件（支持图片、文档）
- GET /files/ —— 列出所有上传的文件
- GET /files/{id}/download —— 下载文件
- 限制文件大小（最大 10MB）和类型

**要求：**
- 使用 FastAPI 的 UploadFile
- 保存文件到本地 uploads/ 目录
- 记录文件元数据（名称、大小、上传时间）

## 练习 4：WebSocket 聊天室 ⭐⭐⭐⭐
创建一个实时聊天室 API：
- WebSocket /ws/{room_id} —— 连接到聊天室
- 支持加入/离开房间
- 广播消息给房间内所有用户
- 显示在线用户列表

**要求：**
- 使用 FastAPI 的 WebSocket
- 维护房间和用户状态
- 处理断开连接

## 练习 5：中间件开发 ⭐⭐⭐⭐
为 API 添加以下中间件：
- 请求日志（记录每个请求的方法、路径、耗时）
- CORS 支持（允许跨域请求）
- 限流（每分钟最多 100 次请求）
- 错误处理（统一错误响应格式）

**要求：**
- 使用 FastAPI 的 middleware
- 限流使用内存计数器
- 错误响应格式：{"error": {"code": 404, "message": "..."}}

## 提交要求
- 所有练习的代码文件放在 exercises/ 目录
- 每个文件可以独立运行
- 添加必要的注释和文档字符串
