"""
Day 067 — FastAPI 依赖注入系统
运行方式：uvicorn 04-dependency-injection:app --reload
"""
from fastapi import FastAPI, Depends, Header, HTTPException

app = FastAPI(title="依赖注入示例")


# ========== 模拟依赖 ==========

def get_db():
    """
    模拟数据库连接——使用 yield 实现资源管理
    
    yield 的作用：
    - yield 之前的代码 = 连接建立（类似 __enter__）
    - yield 之后的代码 = 连接关闭（类似 __exit__）
    - 即使请求处理中发生异常，finally 块也会执行
    """
    db = {"connected": True, "data": ["record1", "record2"]}
    print("📦 数据库连接已建立")
    try:
        yield db  #  yield 把 db 传递给依赖它的路由函数
    finally:
        print("🔒 数据库连接已关闭")


def get_current_user(x_token: str = Header(..., description="认证 Token")):
    """
    模拟用户认证——从请求 Header 获取 token
    
    Header(...) 表示 x_token 是必填的请求头。
    如果客户端没传 X-Token 头，会返回 422 错误。
    """
    valid_tokens = {
        "secret-token-alice": {"username": "alice", "role": "admin"},
        "secret-token-bob": {"username": "bob", "role": "user"},
    }
    if x_token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    return valid_tokens[x_token]


def require_admin(user: dict = Depends(get_current_user)):
    """
    角色检查依赖——依赖链的第二层
    
    依赖链：请求 → get_current_user（认证）→ require_admin（权限检查）
    
    Depends(get_current_user) 表示：
    1. 先调用 get_current_user 获取用户
    2. 把用户传给 require_admin
    3. require_admin 检查角色
    """
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


# ========== 使用依赖的路由 ==========

@app.get("/data/")
def read_data(db: dict = Depends(get_db)):
    """
    需要数据库连接的路由
    
    Depends(get_db) 的工作流程：
    1. FastAPI 调用 get_db() 得到 db 对象
    2. 把 db 作为参数传给 read_data
    3. 请求结束后自动关闭连接
    """
    return {"data": db["data"]}


@app.get("/profile/")
def read_profile(user: dict = Depends(get_current_user)):
    """
    需要用户认证的路由
    
    客户端需要在请求头中传递 X-Token
    """
    return {"message": f"欢迎, {user['username']}!", "role": user["role"]}


@app.get("/admin/dashboard/")
def admin_dashboard(admin: dict = Depends(require_admin)):
    """
    需要管理员权限的路由
    
    依赖链：认证 → 权限检查
    """
    return {
        "message": f"管理员 {admin['username']} 的控制台",
        "admin_features": ["用户管理", "系统配置", "数据分析"]
    }


@app.get("/items/")
def list_items(
    db: dict = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    多个依赖——同时需要数据库和认证
    
    Depends 可以叠加使用，FastAPI 会依次调用。
    """
    return {
        "items": db["data"],
        "requested_by": user["username"]
    }


# ========== 依赖覆盖（测试用） ==========

# 在测试中可以轻松替换依赖
def fake_get_current_user():
    """假的用户认证——用于测试"""
    return {"username": "testuser", "role": "admin"}

# app.dependency_overrides[get_current_user] = fake_get_current_user
# 取消注释后，所有依赖 get_current_user 的路由都会用假数据


# ========== 运行 ==========
# uvicorn 04-dependency-injection:app --reload
#
# 测试命令（需要传 Header）：
# curl http://127.0.0.1:8000/data/ -H "X-Token: any-token"
# curl http://127.0.0.1:8000/profile/ -H "X-Token: secret-token-alice"
# curl http://127.0.0.1:8000/admin/dashboard/ -H "X-Token: secret-token-alice"
# curl http://127.0.0.1:8000/admin/dashboard/ -H "X-Token: secret-token-bob"
#   → 403 需要管理员权限
