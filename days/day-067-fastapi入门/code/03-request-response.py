"""
Day 067 — 请求体、响应与自动文档
运行方式：uvicorn 03-request-response:app --reload
"""
from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field
from enum import Enum

app = FastAPI(title="图书管理 API", version="1.0.0")

# ========== 枚举类型 ==========
class BookCategory(str, Enum):
    """
    图书分类——枚举类型
    
    使用枚举的好处：
    1. 限制可选值，避免拼写错误
    2. 自动出现在 API 文档中
    3. 代码更可读
    """
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
    
    - **title**: 图书标题（必填，1-200 字符）
    - **author**: 作者（必填）
    - **category**: 分类（必填，可选值见枚举）
    - **price**: 价格（必须大于 0）
    - **description**: 简介（可选）
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
    """获取所有图书（支持按分类和价格过滤）"""
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
    """
    更新图书信息
    
    只更新传入的字段，未传入的字段保持原值。
    使用 model_dump(exclude_unset=True) 实现部分更新。
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="图书不存在")

    stored = books_db[book_id]
    update_data = book.model_dump(exclude_unset=True)
    # exclude_unset=True 只包含显式传入的字段
    stored.update(update_data)
    return stored


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    """删除图书（204 No Content）"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="图书不存在")
    del books_db[book_id]
    return None  # 204 无响应体


# ========== 运行 ==========
# uvicorn 03-request-response:app --reload
#
# 测试命令：
# 创建：curl -X POST http://127.0.0.1:8000/books/ -H "Content-Type: application/json" -d '{"title":"Python","author":"张三","isbn":"1234567890","price":59.9,"category":"tech"}'
# 列表：curl http://127.0.0.1:8000/books/?category=tech
# 详情：curl http://127.0.0.1:8000/books/1
# 删除：curl -X DELETE http://127.0.0.1:8000/books/1
