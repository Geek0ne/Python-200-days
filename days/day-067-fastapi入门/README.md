# Day 067 — FastAPI 入门：现代 Python Web API 框架

## 概述

Day 065-066 我们学习了 Flask —— Python 最经典的 Web 框架之一。今天进入一个**新时代**：**FastAPI**。

FastAPI 是 2018 年发布的现代 Python Web 框架，它凭借**极致的性能**、**自动文档**和**类型驱动开发**迅速成为 Python Web API 开发的首选。

**今天你将学到：**
1. FastAPI 的核心特性与优势（对比 Flask）
2. Pydantic 模型 —— 强大的数据验证与序列化
3. 自动文档生成 —— Swagger UI / ReDoc
4. 依赖注入系统 —— 优雅的代码复用
5. **实战：图书管理 API** —— 一个完整的 CRUD RESTful API

> 💡 **为什么学 FastAPI？** 如果你未来要做后端开发、微服务、机器学习模型部署，FastAPI 几乎是目前 Python 生态中**最佳选择**。

---

## 1. FastAPI 特性与优势

### 1.1 什么是 FastAPI？

FastAPI 是一个用于构建 API 的**现代、高性能** Python Web 框架。它基于：

- **Starlette**（底层 Web 框架）
- **Pydantic**（数据验证）
- **Python 类型提示**（type hints）

### 1.2 核心优势对比：FastAPI vs Flask

| 特性 | FastAPI | Flask |
|------|---------|-------|
| 性能 | ⚡ 极快（接近 Go/Rust） | 中等 |
| 数据验证 | ✅ 内置 Pydantic | ❌ 需要额外库 |
| 自动文档 | ✅ Swagger + ReDoc | ❌ 需要插件 |
| 类型提示 | ✅ 原生支持 | ❌ 不依赖 |
| 异步支持 | ✅ 原生 async/await | ⚠️ 需要额外配置 |
| 学习曲线 | 中等 | 简单 |
| 生态成熟度 | 快速增长 | 非常成熟 |

### 1.3 性能对比

FastAPI 的性能来自 Python 的**类型提示**——框架在启动时就能"预编译"路由处理逻辑，而不是运行时动态解析。

```bash
# 安装 FastAPI
pip install fastapi uvicorn

# uvicorn 是 ASGI 服务器，类似 Flask 用的 Flask-CLI
# ASGI = Asynchronous Server Gateway Interface（异步服务器网关接口）
```

### 1.4 第一个 FastAPI 应用

```python
# code/01-first-fastapi-app.py
from fastapi import FastAPI

# 创建 FastAPI 实例
app = FastAPI()

# 定义路由——和 Flask 类似，但更简洁
@app.get("/")
def read_root():
    """根路径，返回欢迎信息"""
    return {"message": "Hello, FastAPI!"}  # 自动转换为 JSON

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    """
    路径参数 + 查询参数
    
    - item_id: 路径参数，类型为 int（FastAPI 自动验证）
    - q: 查询参数，可选（默认 None）
    """
    result = {"item_id": item_id}
    if q:
        result["q"] = q
    return result

# 运行方式（在终端执行）：
# uvicorn 01-first-fastapi-app:app --reload
# --reload 表示代码修改后自动重启（开发模式）
```

**启动后访问：**
- http://127.0.0.1:8000 —— 看到 `{"message": "Hello, FastAPI!"}`
- http://127.0.0.1:8000/items/42?q=test —— 看到 `{"item_id": 42, "q": "test"}`
- http://127.0.0.1:8000/docs —— 看到 Swagger 交互式文档 🎉

### 1.5 路由方式对比

```python
# Flask 的写法
@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    return jsonify({"user_id": user_id})

# FastAPI 的写法——更直观
@app.get("/users/{user_id}")
def get_user(user_id: int):  # 类型注解 = 自动验证 + 自动文档
    return {"user_id": user_id}

# FastAPI 还支持更高级的路由
@app.post("/users/")          # POST 请求
@app.put("/users/{id}")       # 更新
@app.delete("/users/{id}")    # 删除
@app.patch("/users/{id}")     # 部分更新
```

> ⚠️ **避坑指南**：FastAPI 中路由函数的参数名**必须**和路径参数名一致！`/users/{user_id}` 对应函数参数 `user_id`，不是 `id`。

---

## 2. Pydantic 模型：数据验证

### 2.1 为什么需要 Pydantic？

在 Flask 中，验证请求数据通常需要手动检查：

```python
# Flask 的痛苦写法
data = request.get_json()
if not data:
    return jsonify({"error": "No data"}), 400
if "name" not in data:
    return jsonify({"error": "Name required"}), 400
if not isinstance(data.get("age"), int):
    return jsonify({"error": "Age must be int"}), 400
# 还要继续检查... 😩
```

**Pydantic 的优雅写法：**

```python
# 定义数据模型
from pydantic import BaseModel, Field, field_validator

class UserCreate(BaseModel):
    name: str                           # 必填，字符串
    age: int = Field(gt=0, lt=150)      # 必填，0-150 之间的整数
    email: str                           # 必填，字符串
    bio: str = ""                        # 可选，默认空字符串

# 使用：FastAPI 自动验证
@app.post("/users/")
def create_user(user: UserCreate):
    # 到这里，user 已经是验证过的对象
    # 不合法的数据会被自动拒绝（返回 422 错误）
    return {"message": f"Created {user.name}", "user": user.model_dump()}
```

### 2.2 Pydantic 核心用法

```python
# code/02-pydantic-basics.py
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime

# ========== 基础模型 ==========
class Book(BaseModel):
    """图书模型——所有字段都有类型约束"""
    title: str = Field(..., min_length=1, max_length=200)
    # ... 表示必填
    author: str = Field(..., min_length=1)
    isbn: str = Field(..., pattern=r"^\d{10,13}$")
    # pattern：正则表达式验证
    price: float = Field(gt=0)
    # gt=0 表示大于 0
    published_year: int = Field(ge=1000, le=2100)
    # ge=greater than or equal, le=less than or equal
    description: str = ""
    tags: list[str] = []  # 默认空列表

# ========== 带验证器的模型 ==========
class UserRegister(BaseModel):
    """用户注册模型——包含自定义验证"""
    username: str = Field(..., min_length=3, max_length=20)
    email: str
    password: str = Field(..., min_length=8)
    confirm_password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """自定义邮箱验证"""
        if "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v.lower()  # 自动转小写

    @model_validator(mode="after")
    def check_passwords_match(self):
        """模型级验证：两次密码必须一致"""
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self

# ========== 模型嵌套 ==========
class Address(BaseModel):
    city: str
    street: str
    zip_code: str = Field(pattern=r"^\d{6}$")

class UserWithAddress(BaseModel):
    name: str
    address: Address  # 嵌套模型

# ========== 测试验证 ==========
if __name__ == "__main__":
    # ✅ 正确数据
    book = Book(
        title="Python编程",
        author="张三",
        isbn="9787111636663",
        price=59.9,
        published_year=2023,
        tags=["Python", "编程"]
    )
    print("✅ 图书创建成功:", book.model_dump())

    # ❌ 错误数据——会报 ValidationError
    try:
        bad_book = Book(
            title="",           # 空标题——违反 min_length
            author="李四",
            isbn="123",         # ISBN 格式错误
            price=-10,          # 负价格——违反 gt=0
            published_year=3000  # 超出范围
        )
    except Exception as e:
        print("❌ 验证失败:")
        print(e)

    # ✅ 正确注册
    user = UserRegister(
        username="alice",
        email="Alice@Example.com",  # 会自动转小写
        password="secure123",
        confirm_password="secure123"
    )
    print("\n✅ 用户注册:", user.model_dump())

    # ❌ 密码不匹配
    try:
        bad_user = UserRegister(
            username="bob",
            email="bob@test.com",
            password="pass1234",
            confirm_password="different"  # 不匹配！
        )
    except Exception as e:
        print("\n❌ 注册失败:", e)
```

**预期输出：**
```
✅ 图书创建成功: {'title': 'Python编程', 'author': '张三', 'isbn': '9787111636663', ...}

❌ 验证失败:
3 validation errors for Book
  title
    String should have at least 1 character [type=string_too_short, ...]
  isbn
    String should match pattern '^\d{10,13}$' [type=string_pattern_mismatch, ...]
  price
    Input should be greater than 0 [type=greater_than, ...]

✅ 用户注册: {'username': 'alice', 'email': 'alice@example.com', ...}

❌ 注册失败: 1 validation error for UserRegister
  confirm_password
    Value error, 两次输入的密码不一致
```

### 2.3 常用 Field 约束速查表

```python
from pydantic import Field

# 字符串
Field(min_length=1)          # 最小长度
Field(max_length=100)        # 最大长度
Field(pattern=r"^\d+$")      # 正则匹配
Field(to_lower=True)         # 自动转小写

# 数字
Field(gt=0)                  # 大于 0（> 0）
Field(ge=0)                  # 大于等于 0（>= 0）
Field(lt=100)                # 小于 100（< 100）
Field(le=100)                # 小于等于 100（<= 100）
Field(multiple_of=5)         # 必须是 5 的倍数

# 列表
Field(min_length=1)          # 列表至少 1 个元素
Field(max_length=10)         # 列表最多 10 个元素

# 通用
Field(default_factory=list)  # 默认值用工厂函数（可变对象）
Field(description="说明")    # 用于自动文档
Field(examples=["示例"])     # 文档中的示例值
```

> ⚠️ **避坑指南**：`default_factory` 用于可变默认值（list, dict），不能直接用 `default=[]`！Python 的可变默认参数陷阱在 Pydantic 中同样存在。

---

## 3. 请求体、响应与自动文档

### 3.1 请求体（Request Body）

```python
# code/03-request-response.py
from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field
from enum import Enum

app = FastAPI(title="图书管理 API", version="1.0.0")

# ========== 枚举类型 ==========
class BookCategory(str, Enum):
    """图书分类——枚举类型，限制可选值"""
    FICTION = "fiction"           # 小说
    NON_FICTION = "non-fiction"  # 非虚构
    SCIENCE = "science"          # 科学
    TECH = "tech"                # 技术
    HISTORY = "history"          # 历史

# ========== 请求模型 ==========
class BookCreate(BaseModel):
    """创建图书的请求体"""
    title: str = Field(..., min_length=1, max_length=200, examples=["Python编程"])
    author: str = Field(..., examples=["张三"])
    category: BookCategory
    price: float = Field(gt=0, examples=[59.9])
    description: str = ""

class BookUpdate(BaseModel):
    """更新图书的请求体——所有字段可选"""
    title: str | None = None
    author: str | None = None
    category: BookCategory | None = None
    price: float | None = Field(default=None, gt=0)
    description: str | None = None

# ========== 响应模型 ==========
class BookResponse(BaseModel):
    """返回给客户端的图书数据"""
    id: int
    title: str
    author: str
    category: BookCategory
    price: float
    description: str

# ========== 模拟数据库 ==========
books_db: dict[int, dict] = {}
next_id = 1

# ========== 路由 ==========
@app.post("/books/", response_model=BookResponse, status_code=201)
def create_book(book: BookCreate):
    """
    创建新图书
    
    - **title**: 图书标题（必填）
    - **author**: 作者（必填）
    - **category**: 分类（必填，可选值见枚举）
    - **price**: 价格（必须大于 0）
    """
    global next_id
    book_data = book.model_dump()
    book_data["id"] = next_id
    books_db[next_id] = book_data
    next_id += 1
    return book_data

@app.get("/books/", response_model=list[BookResponse])
def list_books(
    category: BookCategory | None = Query(default=None, description="按分类过滤"),
    min_price: float | None = Query(default=None, ge=0, description="最低价格"),
    max_price: float | None = Query(default=None, ge=0, description="最高价格"),
):
    """获取所有图书（支持过滤）"""
    results = list(books_db.values())
    if category:
        results = [b for b in results if b["category"] == category]
    if min_price is not None:
        results = [b for b in results if b["price"] >= min_price]
    if max_price is not None:
        results = [b for b in results if b["price"] <= max_price]
    return results

@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int = Path(..., gt=0, description="图书 ID")):
    """根据 ID 获取单本图书"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="图书不存在")
    return books_db[book_id]

@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, book: BookUpdate):
    """更新图书信息"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="图书不存在")
    stored = books_db[book_id]
    update_data = book.model_dump(exclude_unset=True)
    # exclude_unset=True: 只更新传入的字段，未传入的保持原值
    stored.update(update_data)
    return stored

@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    """删除图书"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="图书不存在")
    del books_db[book_id]
    return None  # 204 无内容

# 运行：uvicorn 03-request-response:app --reload
```

### 3.2 HTTPException：优雅的错误处理

```python
from fastapi import HTTPException

# 简单错误
raise HTTPException(status_code=404, detail="用户不存在")

# 带 headers 的错误（比如需要重新认证）
raise HTTPException(
    status_code=401,
    detail="Token 已过期",
    headers={"WWW-Authenticate": "Bearer"}
)
```

### 3.3 自动文档生成

FastAPI **最大的卖点之一**：你写的代码就是文档！

```python
# 访问以下 URL 即可看到交互式文档：
# http://127.0.0.1:8000/docs    → Swagger UI（可直接测试 API）
# http://127.0.0.1:8000/redoc   → ReDoc（更美观的只读文档）
# http://127.0.0.1:8000/openapi.json → OpenAPI 规范（JSON）

# 文档内容来自：
# 1. 路由的 docstring / 注释
# 2. Pydantic 模型的字段定义和 Field 描述
# 3. Query/Path 参数的 description
# 4. response_model 的定义
```

---

## 4. 依赖注入系统

### 4.1 什么是依赖注入？

依赖注入（Dependency Injection，DI）是一种设计模式：**函数不自己创建依赖，而是从外部"注入"进来**。

```python
# ❌ 没有依赖注入——函数自己创建依赖
def get_current_user():
    db = create_db_connection()  # 硬编码
    user = db.query("SELECT * FROM users LIMIT 1")
    return user

# ✅ 有依赖注入——依赖作为参数传入
def get_current_user(db: Database = Depends(get_db)):
    user = db.query("SELECT * FROM users LIMIT 1")
    return user
# get_db 是"依赖"，FastAPI 会自动调用并注入
```

### 4.2 FastAPI 依赖注入

```python
# code/04-dependency-injection.py
from fastapi import FastAPI, Depends, Header, HTTPException

app = FastAPI()

# ========== 模拟依赖 ==========
def get_db():
    """模拟数据库连接"""
    db = {"connected": True, "data": ["record1", "record2"]}
    print("📦 数据库连接已建立")
    try:
        yield db  # 用 yield 实现资源管理（类似 with 语句）
    finally:
        print("🔒 数据库连接已关闭")

def get_current_user(x_token: str = Header(...)):
    """模拟用户认证——从 Header 获取 token"""
    if x_token != "secret-token":
        raise HTTPException(status_code=401, detail="Token 无效")
    return {"username": "alice", "role": "admin"}

def require_admin(user: dict = Depends(get_current_user)):
    """在认证基础上增加角色检查"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user

# ========== 使用依赖 ==========
@app.get("/data/")
def read_data(db: dict = Depends(get_db)):
    """需要数据库连接"""
    return {"data": db["data"]}

@app.get("/profile/")
def read_profile(user: dict = Depends(get_current_user)):
    """需要用户认证"""
    return {"user": user}

@app.get("/admin/dashboard/")
def admin_dashboard(admin: dict = Depends(require_admin)):
    """需要管理员权限（依赖链：认证 → 角色检查）"""
    return {"message": f"欢迎管理员 {admin['username']}"}

# ========== 依赖覆盖（测试用） ==========
def fake_get_current_user():
    return {"username": "testuser", "role": "admin"}

# 在测试中可以覆盖依赖
# app.dependency_overrides[get_current_user] = fake_get_current_user
```

### 4.3 依赖注入的优势

```python
# 1. 代码复用——多个路由共享同一个依赖
@app.get("/orders/")
def list_orders(user=Depends(get_current_user)):
    ...

@app.post("/orders/")
def create_order(user=Depends(get_current_user)):
    ...

# 2. 易于测试——替换依赖即可
# app.dependency_overrides[get_db] = fake_get_db

# 3. 职责分离——路由只关心业务逻辑
# 认证、数据库等横切关注点由依赖处理
```

---

## 5. 异步支持

### 5.1 async/await

FastAPI 原生支持异步，适合 I/O 密集型操作：

```python
# code/05-async-fastapi.py
import asyncio
from fastapi import FastAPI

app = FastAPI()

@app.get("/sync/")
def sync_handler():
    """同步路由——默认运行在线程池"""
    import time
    time.sleep(1)  # 模拟阻塞操作
    return {"message": "同步完成"}

@app.get("/async/")
async def async_handler():
    """异步路由——不阻塞事件循环"""
    await asyncio.sleep(1)  # 模拟异步 I/O
    return {"message": "异步完成"}

@app.get("/concurrent/")
async def concurrent_handler():
    """并发执行多个异步任务"""
    # 同时发起 3 个请求，总耗时约 1 秒而不是 3 秒
    results = await asyncio.gather(
        fetch_data("api1"),
        fetch_data("api2"),
        fetch_data("api3"),
    )
    return {"results": results}

async def fetch_data(url: str) -> dict:
    await asyncio.sleep(1)
    return {"url": url, "status": "ok"}
```

> ⚠️ **避坑指南**：不要在 `async def` 路由中使用 `time.sleep()`，要用 `await asyncio.sleep()`！否则会阻塞整个事件循环。

---

## 实战项目：图书管理 API

### 项目说明

构建一个完整的图书管理 RESTful API，包含：
- 图书的 CRUD（增删改查）
- 分类与搜索
- 数据验证
- 错误处理
- 依赖注入（认证）

### 完整代码

```python
# code/06-book-api-complete.py
"""
📚 图书管理 API —— 完整实战项目
功能：CRUD、分类、搜索、认证、分页
"""
from fastapi import FastAPI, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field
from datetime import datetime

# ========== 应用配置 ==========
app = FastAPI(
    title="📚 图书管理 API",
    description="一个完整的图书管理系统 API，支持增删改查、分类、搜索",
    version="1.0.0",
)

# ========== 数据模型 ==========
class BookCreate(BaseModel):
    """创建图书"""
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    isbn: str = Field(..., pattern=r"^\d{10,13}$")
    price: float = Field(gt=0, le=9999)
    category: str = Field(default="未分类")
    description: str = ""

class BookUpdate(BaseModel):
    """更新图书（所有字段可选）"""
    title: str | None = Field(default=None, min_length=1)
    author: str | None = Field(default=None, min_length=1)
    isbn: str | None = Field(default=None, pattern=r"^\d{10,13}$")
    price: float | None = Field(default=None, gt=0)
    category: str | None = None
    description: str | None = None

class BookResponse(BaseModel):
    """图书响应"""
    id: int
    title: str
    author: str
    isbn: str
    price: float
    category: str
    description: str
    created_at: str
    updated_at: str

class PaginatedResponse(BaseModel):
    """分页响应"""
    total: int
    page: int
    page_size: int
    items: list[BookResponse]

# ========== 模拟数据库 ==========
books_db: dict[int, dict] = {}
next_id = 1

# ========== 依赖注入 ==========
def get_current_user(x_token: str = Header(..., description="认证 Token")):
    """模拟用户认证"""
    valid_tokens = {"admin-token": "admin", "user-token": "user"}
    if x_token not in valid_tokens:
        raise HTTPException(status_code=401, detail="无效的 Token")
    return {"token": x_token, "role": valid_tokens[x_token]}

# ========== CRUD 路由 ==========
@app.post("/books/", response_model=BookResponse, status_code=201,
          summary="创建图书", tags=["图书管理"])
def create_book(book: BookCreate):
    """创建一本新图书"""
    global next_id
    now = datetime.now().isoformat()
    book_data = {
        "id": next_id,
        **book.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    books_db[next_id] = book_data
    next_id += 1
    return book_data

@app.get("/books/", response_model=PaginatedResponse, summary="图书列表",
         tags=["图书管理"])
def list_books(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
    category: str | None = Query(None, description="按分类过滤"),
    search: str | None = Query(None, description="搜索标题或作者"),
    min_price: float | None = Query(None, ge=0, description="最低价格"),
    max_price: float | None = Query(None, ge=0, description="最高价格"),
):
    """
    获取图书列表，支持分页、分类过滤、关键词搜索
    """
    results = list(books_db.values())

    # 过滤
    if category:
        results = [b for b in results if b["category"] == category]
    if search:
        search_lower = search.lower()
        results = [b for b in results
                   if search_lower in b["title"].lower()
                   or search_lower in b["author"].lower()]
    if min_price is not None:
        results = [b for b in results if b["price"] >= min_price]
    if max_price is not None:
        results = [b for b in results if b["price"] <= max_price]

    # 分页
    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size
    items = results[start:end]

    return PaginatedResponse(
        total=total, page=page, page_size=page_size, items=items
    )

@app.get("/books/{book_id}", response_model=BookResponse, summary="获取图书详情",
         tags=["图书管理"])
def get_book(book_id: int = Path(..., gt=0)):
    """根据 ID 获取图书详情"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail=f"图书 {book_id} 不存在")
    return books_db[book_id]

@app.put("/books/{book_id}", response_model=BookResponse, summary="更新图书",
         tags=["图书管理"])
def update_book(book_id: int, book: BookUpdate):
    """更新图书信息（仅更新传入的字段）"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail=f"图书 {book_id} 不存在")

    stored = books_db[book_id]
    update_data = book.model_dump(exclude_unset=True)
    if update_data:
        stored.update(update_data)
        stored["updated_at"] = datetime.now().isoformat()
    return stored

@app.delete("/books/{book_id}", status_code=204, summary="删除图书",
            tags=["图书管理"])
def delete_book(book_id: int):
    """删除图书"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail=f"图书 {book_id} 不存在")
    del books_db[book_id]

@app.get("/stats/", summary="图书统计", tags=["统计"])
def get_stats():
    """获取图书统计信息"""
    books = list(books_db.values())
    categories = {}
    for book in books:
        cat = book["category"]
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_books": len(books),
        "categories": categories,
        "avg_price": round(
            sum(b["price"] for b in books) / len(books), 2
        ) if books else 0,
    }

@app.get("/health/", summary="健康检查", tags=["系统"])
def health_check():
    """API 健康检查"""
    return {"status": "healthy", "books_count": len(books_db)}

# ========== 启动事件 ==========
@app.on_event("startup")
def startup_event():
    """应用启动时执行"""
    print("📚 图书管理 API 启动成功！")
    print("📖 访问 http://127.0.0.1:8000/docs 查看交互式文档")

# 运行：uvicorn 06-book-api-complete:app --reload
```

### API 测试命令

```bash
# 创建图书
curl -X POST http://127.0.0.1:8000/books/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python编程从入门到实践",
    "author": "Eric Matthes",
    "isbn": "9787111636663",
    "price": 69.8,
    "category": "tech",
    "description": "Python 入门经典教材"
  }'

# 获取图书列表
curl http://127.0.0.1:8000/books/?category=tech&search=Python

# 获取统计
curl http://127.0.0.1:8000/stats/
```

---

## 今日总结

- **FastAPI 是现代 Python API 框架**，基于类型提示实现高性能、自动文档
- **Pydantic 模型**提供强大的数据验证，替代手动 if-else 检查
- **自动文档**：代码即文档，Swagger UI + ReDoc 无需额外配置
- **依赖注入**：优雅地管理数据库连接、认证、权限等横切关注点
- **异步原生**：`async/await` 让 I/O 密集型操作更高效
- FastAPI 适合构建 REST API、微服务、机器学习模型部署接口

## 练习题

### 练习 1：基础 API
创建一个 Todo API，包含以下功能：
- POST /todos/ —— 创建待办事项（title, description, priority）
- GET /todos/ —— 获取所有待办（支持按 priority 过滤）
- GET /todos/{id} —— 获取单个待办
- PUT /todos/{id} —— 更新待办（标记完成）
- DELETE /todos/{id} —— 删除待办

### 练习 2：用户认证
为练习 1 的 Todo API 添加用户认证：
- POST /auth/register —— 注册（username, password）
- POST /auth/login —— 登录（返回 token）
- 所有 Todo 路由需要 token 认证
- 每个用户只能看到自己的待办

### 练习 3：文件上传
创建一个文件上传 API：
- POST /upload/ —— 上传文件（支持图片、文档）
- GET /files/ —— 列出所有上传的文件
- GET /files/{id}/download —— 下载文件
- 限制文件大小（最大 10MB）和类型

### 练习 4：WebSocket 聊天室
创建一个实时聊天室 API：
- WebSocket /ws/{room_id} —— 连接到聊天室
- 支持加入/离开房间
- 广播消息给房间内所有用户
- 显示在线用户列表

### 练习 5：中间件
为 API 添加以下中间件：
- 请求日志（记录每个请求的方法、路径、耗时）
- CORS 支持（允许跨域请求）
- 限流（每分钟最多 100 次请求）
- 错误处理（统一错误响应格式）

## 明天预告

Day 068 将学习**数据库基础**——SQLite3 模块、SQL 语言基础（CRUD、JOIN、索引）、连接池与事务管理。我们将构建一个完整的通讯录管理系统，打好数据库操作的基本功！
