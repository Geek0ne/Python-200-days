# Day 097 — DSL 进阶挑战

## 🚀 挑战 1：表达式 DSL

设计一个可以解析简单数学表达式的 DSL：

```python
# DSL 语法：
expr = (Expr()
    .number(5)
    .plus(3)
    .times(2)
    .minus(1))
# 计算: (5 + 3) * 2 - 1 = 15

result = expr.evaluate()
print(result)  # 15
```

**提示**：需要实现表达式树，支持链式调用构建表达式。

## 🚀 挑战 2：路由 DSL

设计一个 HTTP 路由 DSL，类似 Flask 但更简洁：

```python
# DSL 语法：
app = Router("myapp")

@app.get("/users")
def list_users():
    return "user list"

@app.post("/users")
def create_user():
    return "created"

@app.get("/users/<int:id>")
def get_user(id):
    return f"user {id}"

# 路由匹配
print(app.match("GET", "/users"))      # → list_users
print(app.match("POST", "/users"))     # → create_user
print(app.match("GET", "/users/42"))   # → get_user(42)
```

**要求**：
1. 支持 GET/POST/PUT/DELETE 方法
2. 支持路径参数 `<int:id>` 类型转换
3. 支持 404 处理

## 🚀 挑战 3：日志 DSL

设计一个日志 DSL，让日志代码读起来像自然语言：

```python
# DSL 语法：
log = Logger("app")

(log.info("用户 {name} 登录成功")
   .with_fields(name="Alice", ip="127.0.0.1")
   .tag("auth")
   .write())

(log.error("数据库连接失败")
   .with_fields(host="localhost", port=5432)
   .tag("db", "critical")
   .alert(email="admin@example.com")
   .write())
```

**要求**：
1. 支持 info/warning/error 级别
2. 支持字段注入
3. 支持标签过滤
4. 支持告警通知

## 🚀 挑战 4：数据管道 DSL

设计一个数据处理管道 DSL：

```python
# DSL 语法：
pipeline = (Pipeline("用户数据处理")
    .read_from("users.csv")
    .filter(lambda row: row["age"] > 18)
    .transform(lambda row: {**row, "name": row["name"].upper()})
    .validate(schema)
    .write_to("output.json"))

result = pipeline.execute()
print(f"处理了 {result.count} 条记录")
```

**要求**：
1. 支持多种数据源（CSV、JSON、数据库）
2. 支持 filter/transform/validate 操作
3. 支持错误处理和跳过策略
4. 支持执行统计

---

> 💡 **挑战提示**：设计 DSL 时，先想清楚「用户怎么用」，再想「内部怎么实现」。好的 DSL 让使用者不需要关心实现细节。
