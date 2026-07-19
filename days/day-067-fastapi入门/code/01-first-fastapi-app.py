"""
Day 067 — 第一个 FastAPI 应用
运行方式：uvicorn 01-first-fastapi-app:app --reload
访问：http://127.0.0.1:8000
文档：http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI

# 创建 FastAPI 实例——可以传入 title、description 等用于文档
app = FastAPI(
    title="我的第一个 FastAPI 应用",
    description="学习 FastAPI 的入门示例",
    version="0.1.0",
)

# ========== 路由定义 ==========

@app.get("/")
def read_root():
    """
    根路径处理函数
    
    返回一个字典，FastAPI 会自动转为 JSON 响应。
    同时设置 Content-Type: application/json
    """
    return {"message": "Hello, FastAPI! 🚀"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    """
    路径参数 + 查询参数示例
    
    参数说明：
    - item_id (int): 路径参数，FastAPI 自动验证类型
      如果传入非整数（如 /items/abc），会返回 422 错误
    - q (str | None): 查询参数，可选
      访问 /items/42?q=hello 才会有值
    
    类型注解的作用：
    1. 运行时数据验证
    2. 自动生成 API 文档
    3. IDE 自动补全
    """
    result = {"item_id": item_id}
    if q:
        result["q"] = q
    return result


@app.get("/users/{user_id}")
def read_user(user_id: int, role: str = "guest"):
    """
    带默认值的查询参数
    
    访问 /users/1         → {"user_id": 1, "role": "guest"}
    访问 /users/1?role=admin → {"user_id": 1, "role": "admin"}
    """
    return {"user_id": user_id, "role": role}


# ========== 启动方式 ==========
# 在终端运行：
# uvicorn 01-first-fastapi-app:app --reload
#
# --reload: 代码修改后自动重启（开发模式）
# --host 0.0.0.0: 允许外部访问
# --port 8080: 指定端口
#
# 生产环境建议：
# uvicorn 01-first-fastapi-app:app --host 0.0.0.0 --port 8000 --workers 4
