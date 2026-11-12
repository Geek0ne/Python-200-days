"""
Day 067 — 📚 图书管理 API 完整实战项目
功能：CRUD、分类、搜索、认证、分页、统计

运行方式：uvicorn 06-book-api-complete:app --reload
文档访问：http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI, Depends, HTTPException, Query, Path, Header
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
    """创建图书请求体"""
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    isbn: str = Field(..., pattern=r"^\d{10,13}$")
    price: float = Field(gt=0, le=9999)
    category: str = Field(default="未分类", description="图书分类")
    description: str = Field(default="", max_length=1000)


class BookUpdate(BaseModel):
    """更新图书请求体（所有字段可选）"""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=100)
    isbn: str | None = Field(default=None, pattern=r"^\d{10,13}$")
    price: float | None = Field(default=None, gt=0, le=9999)
    category: str | None = None
    description: str | None = Field(default=None, max_length=1000)


class BookResponse(BaseModel):
    """图书响应体"""
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
    """分页响应体"""
    total: int
    page: int
    page_size: int
    items: list[BookResponse]


class StatsResponse(BaseModel):
    """统计响应体"""
    total_books: int
    categories: dict[str, int]
    avg_price: float


# ========== 模拟数据库 ==========
books_db: dict[int, dict] = {}
next_id = 1


# ========== 依赖注入 ==========

def get_current_user(x_token: str = Header(..., description="认证 Token")):
    """
    模拟用户认证
    
    测试用 Token：
    - admin-token → 管理员
    - user-token → 普通用户
    """
    valid_tokens = {
        "admin-token": {"username": "admin", "role": "admin"},
        "user-token": {"username": "user", "role": "user"},
    }
    if x_token not in valid_tokens:
        raise HTTPException(
            status_code=401,
            detail="无效的 Token，请先登录",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return valid_tokens[x_token]


# ========== CRUD 路由 ==========

@app.post("/books/",
          response_model=BookResponse,
          status_code=201,
          summary="创建图书",
          tags=["图书管理"])
def create_book(book: BookCreate):
    """
    创建一本新图书
    
    请求体字段：
    - title: 图书标题（必填，1-200 字符）
    - author: 作者（必填）
    - isbn: ISBN 号（必填，10-13 位数字）
    - price: 价格（必填，大于 0）
    - category: 分类（可选，默认"未分类"）
    - description: 简介（可选）
    """
    global next_id

    # 检查 ISBN 是否已存在
    for existing_book in books_db.values():
        if existing_book["isbn"] == book.isbn:
            raise HTTPException(
                status_code=409,
                detail=f"ISBN {book.isbn} 已被使用"
            )

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


@app.get("/books/",
         response_model=PaginatedResponse,
         summary="图书列表",
         tags=["图书管理"])
def list_books(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
    category: str | None = Query(None, description="按分类过滤"),
    search: str | None = Query(None, description="搜索标题或作者（不区分大小写）"),
    min_price: float | None = Query(None, ge=0, description="最低价格"),
    max_price: float | None = Query(None, ge=0, description="最高价格"),
):
    """
    获取图书列表，支持分页、分类过滤、关键词搜索
    
    分页参数：
    - page: 页码（默认 1）
    - page_size: 每页数量（默认 10，最大 50）
    
    过滤参数：
    - category: 精确匹配分类
    - search: 模糊搜索标题和作者
    - min_price / max_price: 价格范围
    """
    results = list(books_db.values())

    # 分类过滤
    if category:
        results = [b for b in results if b["category"] == category]

    # 关键词搜索（不区分大小写）
    if search:
        search_lower = search.lower()
        results = [
            b for b in results
            if search_lower in b["title"].lower()
            or search_lower in b["author"].lower()
        ]

    # 价格过滤
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
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@app.get("/books/{book_id}",
         response_model=BookResponse,
         summary="获取图书详情",
         tags=["图书管理"])
def get_book(book_id: int = Path(..., gt=0, description="图书 ID")):
    """根据 ID 获取图书详细信息"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail=f"图书 {book_id} 不存在")
    return books_db[book_id]


@app.put("/books/{book_id}",
         response_model=BookResponse,
         summary="更新图书",
         tags=["图书管理"])
def update_book(book_id: int, book: BookUpdate):
    """
    更新图书信息
    
    只更新请求体中显式传入的字段，未传入的字段保持原值。
    这是 PATCH 语义的 PUT 实现。
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail=f"图书 {book_id} 不存在")

    stored = books_db[book_id]
    update_data = book.model_dump(exclude_unset=True)
    # exclude_unset=True 只包含用户显式传入的字段

    if update_data:
        stored.update(update_data)
        stored["updated_at"] = datetime.now().isoformat()

    return stored


@app.delete("/books/{book_id}",
            status_code=204,
            summary="删除图书",
            tags=["图书管理"])
def delete_book(book_id: int):
    """删除图书（无响应体）"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail=f"图书 {book_id} 不存在")
    del books_db[book_id]
    return None


# ========== 统计路由 ==========

@app.get("/stats/",
         response_model=StatsResponse,
         summary="图书统计",
         tags=["统计"])
def get_stats():
    """获取图书统计信息（分类统计、平均价格）"""
    books = list(books_db.values())

    if not books:
        return StatsResponse(
            total_books=0,
            categories={},
            avg_price=0.0,
        )

    categories: dict[str, int] = {}
    for book in books:
        cat = book["category"]
        categories[cat] = categories.get(cat, 0) + 1

    avg_price = round(
        sum(b["price"] for b in books) / len(books), 2
    )

    return StatsResponse(
        total_books=len(books),
        categories=categories,
        avg_price=avg_price,
    )


# ========== 系统路由 ==========

@app.get("/health/", summary="健康检查", tags=["系统"])
def health_check():
    """API 健康检查"""
    return {
        "status": "healthy",
        "books_count": len(books_db),
        "timestamp": datetime.now().isoformat(),
    }


# ========== 启动事件 ==========

@app.on_event("startup")
def startup_event():
    """应用启动时执行"""
    print("📚 图书管理 API 启动成功！")
    print("📖 Swagger 文档: http://127.0.0.1:8000/docs")
    print("📖 ReDoc 文档: http://127.0.0.1:8000/redoc")


# ========== 运行 ==========
# uvicorn 06-book-api-complete:app --reload
#
# 测试命令：
#
# 1. 创建图书
# curl -X POST http://127.0.0.1:8000/books/ \
#   -H "Content-Type: application/json" \
#   -d '{"title":"Python编程","author":"张三","isbn":"9787111636663","price":59.9,"category":"tech"}'
#
# 2. 获取列表
# curl http://127.0.0.1:8000/books/?category=tech&search=Python
#
# 3. 获取详情
# curl http://127.0.0.1:8000/books/1
#
# 4. 更新图书
# curl -X PUT http://127.0.0.1:8000/books/1 \
#   -H "Content-Type: application/json" \
#   -d '{"price":49.9}'
#
# 5. 删除图书
# curl -X DELETE http://127.0.0.1:8000/books/1
#
# 6. 统计信息
# curl http://127.0.0.1:8000/stats/
#
# 7. 健康检查
# curl http://127.0.0.1:8000/health/
