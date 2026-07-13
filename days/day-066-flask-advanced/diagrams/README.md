# Day 066 — 图解：Flask 进阶核心概念

> 本目录包含 Flask 进阶话题的图解说明：ORM 原理、JWT 认证、RESTful API 架构。

---

## 1. SQLAlchemy 架构总览

```mermaid
graph TB
    subgraph "应用代码 (Python)"
        A["class User(db.Model):<br/>id = Column(Integer)<br/>name = Column(String)"]
        B["user = User(name='Alice')<br/>db.session.add(user)<br/>db.session.commit()"]
        C["User.query.filter_by(name='Alice')<br/>.order_by(User.id.desc())<br/>.all()"]
    end
    
    subgraph "SQLAlchemy ORM"
        D["ORM 层<br/>对象 ↔ 关系映射<br/>会话管理<br/>变更跟踪"]
    end
    
    subgraph "SQLAlchemy Core"
        E["SQL 表达式语言<br/>schema/types/sql<br/>engine/connection"]
    end
    
    subgraph "数据库驱动 (Dialect)"
        F["SQLite<br/>Dialect"]
        G["PostgreSQL<br/>Dialect"]
        H["MySQL<br/>Dialect"]
    end
    
    subgraph "数据库"
        I["📁 SQLite<br/>app.db"]
        J["🐘 PostgreSQL"]
        K["🐬 MySQL"]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    E --> G
    E --> H
    F --> I
    G --> J
    H --> K
    
    style D fill:#4A90D9,color:#fff
    style E fill:#7B68EE,color:#fff
```

### 各层职责

```
应用层 (你的 Python 代码)
    │
    ▼ 定义模型、CRUD 操作、业务逻辑
    │
ORM 层 (对象关系映射)
    │
    │  • 模型 ↔ 表的映射
    │  • 关系管理 (一对多/多对多)
    │  • 变更追踪 (unit of work)
    │  • 会话管理 (session)
    │  • 惰性加载/预加载
    │
    ▼ 翻译成 SQL 表达式
    │
Core 层 (SQL 表达式语言)
    │
    │  • SQL 抽象语法树
    │  • 类型系统与类型转换
    │  • 连接池与事务管理
    │  • 结果集处理
    │
    ▼ 发送到具体数据库
    │
Dialect (数据库方言)
    │
    │  • SQL 语法适配 (不同数据库 SQL 略有差异)
    │  • 驱动封装 (sqlite3/psycopg2/mysql-connector)
    │
    ▼
Database (数据库)
```

---

## 2. SQLAlchemy 对象状态生命周期

```mermaid
stateDiagram-v2
    [*] --> Transient: User()
    
    Transient --> Pending: db.session.add(user)
    
    Pending --> Flushed: db.session.flush()
    Pending --> Detached: db.session.expunge(user)
    
    Flushed --> Committed: db.session.commit()
    Flushed --> Pending: 事务回滚
    
    Committed --> Loaded: user.todos
    
    Loaded --> Expired: db.session.expire(user)
    Expired --> Loaded: user.name (触发重新查询)
    
    Loaded --> Deleted: db.session.delete(user)
    Deleted --> Detached: db.session.commit()
    
    Loaded --> Detached: 会话关闭
    Detached --> Loaded: db.session.merge(user)
```

| 状态 | 说明 | 是否在 session 中 | 数据库中是否存在 |
|------|------|-------------------|----------------|
| **Transient** | 刚创建的 Python 对象 | ❌ | ❌ |
| **Pending** | 已添加到 session，未刷新 | ✅ | ❌ |
| **Flushed** | SQL 已发送到数据库，未提交 | ✅ | ✅（事务中） |
| **Committed** | 已提交到数据库 | ✅ | ✅ |
| **Detached** | 与 session 分离 | ❌ | ✅ |
| **Deleted** | 标记为删除 | ✅ | ✅（等待提交删除） |

---

## 3. JWT 结构详解

```mermaid
graph LR
    subgraph "JWT = Header.Payload.Signature"
        H["Header<br/>{<br/>&nbsp;"alg": "HS256",<br/>&nbsp;"typ": "JWT"<br/>}"]
        P["Payload<br/>{<br/>&nbsp;"sub": 1,<br/>&nbsp;"iat": 1700000000,<br/>&nbsp;"exp": 1700086400<br/>}"]
        S["Signature<br/>HMACSHA256(<br/>&nbsp;base64(Header) + '.' +<br/>&nbsp;base64(Payload),<br/>&nbsp;SECRET_KEY<br/>)"]
    end
    
    H -->|Base64URL| H64["eyJhbGciOiJIUzI1NiIs..."]
    P -->|Base64URL| P64["eyJzdWIiOjEsImlhdCI6MTcw..."]
    S --> S64["dGhpcyBpcyB0aGUgc2lnbmF0..."]
    
    H64 --> Token["eyJhbGciOiJIUzI1NiIs...<br/>.<br/>eyJzdWIiOjEsImlhdCI6MTcw...<br/>.<br/>dGhpcyBpcyB0aGUgc2lnbmF0..."]
    P64 --> Token
    S64 --> Token
    
    style Token fill:#f0f0f0,stroke:#333,stroke-width:2px
```

### JWT 三个部分的含义

```
第一部分 ─ Header（头部）
    {"alg": "HS256"}    → 签名算法：HMAC-SHA256
    {"typ": "JWT"}      → Token 类型

第二部分 ─ Payload（载荷）
    "sub"  (Subject)   → 用户 ID
    "iat"  (Issued At) → 签发时间
    "exp"  (Expiration)→ 过期时间
    "type"             → access / refresh

第三部分 ─ Signature（签名）
    防止 Token 被篡改
    用 SECRET_KEY + Header + Payload 计算
    服务器端唯一能验证（因为只有服务器知道 SECRET_KEY）
```

---

## 4. 认证流程：注册 → 登录 → 受保护请求

```mermaid
sequenceDiagram
    participant C as 客户端
    participant API as Flask API
    participant JWT as JWT 模块
    participant DB as SQLAlchemy
    
    Note over C,DB: ─── 注册流程 ───
    
    C->>API: POST /api/auth/register<br/>{username, password}
    API->>API: 参数校验
    API->>DB: 检查用户名是否已存在
    DB-->>API: 不存在
    API->>API: generate_password_hash(password)
    API->>DB: INSERT user
    DB-->>API: 用户已创建
    API->>JWT: create_token(user_id)
    JWT-->>API: "eyJhbGciOiJIUzI1NiIs..."
    API-->>C: 201 Created<br/>{token, user}
    
    Note over C,DB: ─── 登录流程 ───
    
    C->>API: POST /api/auth/login<br/>{username, password}
    API->>DB: SELECT user WHERE username=?
    DB-->>API: User 对象
    API->>API: check_password_hash(hash, password)
    Note over API: 验证通过 ✅
    API->>JWT: create_token(user_id)
    JWT-->>API: "eyJhbGciOiJIUzI1NiIs..."
    API-->>C: 200 OK<br/>{token, user}
    
    Note over C,DB: ─── 受保护请求 ───
    
    C->>API: GET /api/todos<br/>Authorization: Bearer xxx
    API->>JWT: decode_token(token)
    JWT-->>API: {sub: 1, exp: ...}
    API->>DB: SELECT user WHERE id=1
    DB-->>API: User 对象
    API->>DB: SELECT todos WHERE user_id=1
    DB-->>API: [Todo, Todo, Todo]
    API-->>C: 200 OK<br/>{data: [...]}
```

---

## 5. RESTful API 资源映射

```mermaid
graph LR
    subgraph "HTTP 方法"
        GET[GET<br/>读取]
        POST[POST<br/>创建]
        PUT[PUT<br/>全量更新]
        PATCH[PATCH<br/>局部更新]
        DELETE[DELETE<br/>删除]
    end
    
    subgraph "URL 路径"
        COLL["/todos<br/>资源集合"]
        ITEM["/todos/:id<br/>单个资源"]
        ACT["/todos/:id/toggle<br/>动作"]
    end
    
    GET --> COLL
    POST --> COLL
    GET --> ITEM
    PUT --> ITEM
    PATCH --> ITEM
    DELETE --> ITEM
    POST --> ACT
    
    COLL -->|返回列表| R1["200 + 数组"]
    COLL -->|创建| R2["201 + 新资源"]
    ITEM -->|读取| R3["200 + 资源"]
    ITEM -->|更新| R4["200 + 资源"]
    ITEM -->|删除| R5["204 无内容"]
    ACT -->|操作| R6["200 + 结果"]
```

### RESTful URL 设计原则

```
集合 (Collection):              /resources
单个资源:                       /resources/:id
子资源:                        /resources/:id/sub-resources
动作 (非 CRUD):                /resources/:id/action
搜索/过滤:                     /resources?q=keyword&status=active
分页:                          /resources?page=1&per_page=20
```

---

## 6. 完整请求处理流程（TODO API）

```mermaid
flowchart TB
    Start["HTTP 请求<br/>POST /api/v1/todos"] --> Auth{"token_required<br/>检查 Authorization"}
    
    Auth -->|"无 Token"| Err401["401 Unauthorized<br/>{code: AUTH_REQUIRED}"]
    Auth -->|"Token 无效/过期"| Err401
    
    Auth -->|Token 有效| UserCheck["查找用户<br/>User.query.get(sub)"]
    
    UserCheck -->|用户不存在| Err401_2["401 Unauthorized<br/>{code: USER_NOT_FOUND}"]
    UserCheck -->|用户存在| Validate["参数校验<br/>validate_todo_data()"]
    
    Validate -->|校验失败| Err422["422 Unprocessable<br/>{code: VALIDATION_ERROR,<br/>details: {...}}"]
    
    Validate -->|校验通过| Create["创建 Todo 对象<br/>todo = Todo(**cleaned)"]
    
    Create --> Add["db.session.add(todo)"]
    Add --> Commit["db.session.commit()"]
    Commit --> Response["201 Created<br/>{message, data}"]
    
    style Err401 fill:#ff9999
    style Err401_2 fill:#ff9999
    style Err422 fill:#ffcc99
    style Response fill:#90EE90
```

---

## 7. 密码哈希原理图解

```
用户注册密码: "myPassword123"
                    │
                    ▼
    生成随机 Salt: "a1b2c3d4e5f6g7h8"
                    │
                    ▼
    组合: "myPassword123" + "a1b2c3d4e5f6g7h8"
                    │
                    ▼
    PBKDF2-HMAC-SHA256 (600000 次迭代)
                    │
                    ▼
    输出哈希: "pbkdf2:sha256:600000$a1b2c3d4e5f6g7h8$..."
                                          ↑
                                    Salt 被包含在输出中
    
    存储到数据库: password_hash 字段 ← "pbkdf2:sha256:600000$..."
    
    ──────────── 验证 ────────────
    
    用户输入密码: "myPassword123"
    
    check_password_hash() 执行:
    1. 从存储的哈希中提取 Salt: "a1b2c3d4e5f6g7h8"
    2. 用同样的 Salt + 算法重新计算哈希
    3. 比较结果是否一致
    
    如果一致 → 密码正确 ✅
    如果不一致 → 密码错误 ❌
```

---

## 8. ORM 查询中 N+1 问题

```mermaid
graph TD
    subgraph "❌ N+1 查询 (lazy='select')"
        Q1["1 次查询: SELECT * FROM users"]
        Q1 --> U1["用户 1"]
        Q1 --> U2["用户 2"]
        Q1 --> U3["用户 3"]
        
        U1 --> T1["1 次查询: SELECT * FROM todos WHERE user_id=1"]
        U2 --> T2["1 次查询: SELECT * FROM todos WHERE user_id=2"]
        U3 --> T3["1 次查询: SELECT * FROM todos WHERE user_id=3"]
        
        Total1["总共: 1 (用户) + N (用户数) 次查询"]
    end
    
    subgraph "✅ 预加载 (lazy='joined')"
        Q2["1 次查询: SELECT * FROM users<br/>LEFT JOIN todos ON user.id=todos.user_id"]
        Q2 --> R1["用户 1 + TODO 列表  ← 一次查询全部获取"]
        Q2 --> R2["用户 2 + TODO 列表"]
        Q2 --> R3["用户 3 + TODO 列表"]
        
        Total2["总共: 1 次查询！"]
    end
    
    style Total1 fill:#ff9999
    style Total2 fill:#90EE90
```

---

## 9. Flask 项目分层架构（推荐）

```
flask-todo-api/
│
├── app.py                 ← 创建 Flask 实例、配置加载
│
├── config.py              ← 不同环境的配置类
│
├── models/                ← 数据库模型
│   ├── __init__.py
│   ├── user.py
│   └── todo.py
│
├── routes/                ← 路由（蓝图）
│   ├── __init__.py
│   ├── auth.py            ← 认证相关路由
│   └── todos.py           ← TODO CRUD 路由
│
├── services/              ← 业务逻辑
│   ├── __init__.py
│   ├── auth_service.py
│   └── todo_service.py
│
├── utils/                 ← 工具函数
│   ├── __init__.py
│   ├── errors.py          ← 错误码和异常
│   ├── validators.py      ← 参数校验
│   └── jwt_utils.py       ← JWT 工具
│
├── requirements.txt
├── Dockerfile
└── .env                    ← 环境变量
```

**分层职责：**

```
路由层 (routes/)        ← 接收请求、返回响应、参数提取
    │
    ▼ 调用服务层
服务层 (services/)      ← 业务逻辑、事务管理
    │
    ▼ 调用模型层
模型层 (models/)        ← 数据定义、数据库操作
    │
    ▼
工具层 (utils/)         ← JWT、校验、错误码等通用工具
```
