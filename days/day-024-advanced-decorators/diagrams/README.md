# Day 024 — 装饰器进阶 图解

## 1. 带参数装饰器执行流程

```mermaid
flowchart TD
    subgraph Code["代码"]
        C1["@repeat(3)"]
        C2["def greet(name):"]
    end

    subgraph Step1["Step 1: repeat(3)"]
        S1["repeat(3) 被调用"]
        S2["返回 decorator<br/>(闭包捕获 n=3)"]
    end

    subgraph Step2["Step 2: @decorator"]
        S3["decorator(greet) 被调用"]
        S4["创建 wrapper<br/>(闭包捕获 func=greet)"]
        S5["返回 wrapper<br/>greet = wrapper"]
    end

    subgraph Step3["Step 3: greet('Alice')"]
        S6["调用 wrapper('Alice')"]
        S7["循环 3 次调用<br/>原始 greet('Alice')"]
    end

    C1 --> S1
    C2 --> S3
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S5
    S5 -.-> S6
    S6 --> S7

    style C1 fill:#e3f2fd
    style C2 fill:#e3f2fd
    style Step1 fill:#fff3e0
    style Step2 fill:#f3e5f5
    style Step3 fill:#e8f5e9
```

---

## 2. 三层嵌套结构详解

```mermaid
graph TD
    subgraph L1["第一层：参数层"]
        P1["def repeat(n):"]
        P2["n = 3<br/>(闭包变量)"]
    end

    subgraph L2["第二层：装饰器层"]
        D1["def decorator(func):"]
        D2["func = greet<br/>(闭包变量)"]
    end

    subgraph L3["第三层：包装器层"]
        W1["def wrapper(*args, **kwargs):"]
        W2["执行循环 n 次<br/>调用 func()"]
    end

    P1 -->|返回 decorator| P2
    P2 -.->|"n 被捕获"| D1
    D1 -->|返回 wrapper| D2
    D2 -.->|"func 被捕获"| W1
    W1 --> W2

    style L1 fill:#ffcdd2
    style L2 fill:#c8e6c9
    style L3 fill:#bbdefb
```

---

## 3. 多层装饰器链执行顺序

```mermaid
sequenceDiagram
    participant A as @A 外层
    participant B as @B 中间
    participant C as @C 内层
    participant F as 原始函数

    Note over A,F: 装饰阶段（定义时，从下到上）
    C->>C: 装饰 C
    B->>B: 装饰 B
    A->>A: 装饰 A

    Note over A,F: 调用阶段（从上到下，洋葱模型）
    A->>B: A 前置操作
    B->>C: B 前置操作
    C->>F: C 前置操作
    F->>F: ★ 原始函数执行 ★
    F-->>C: 返回结果
    C-->>B: C 后置操作
    B-->>A: B 后置操作
    A-->>A: A 后置操作

    Note over A: 最终结果
```

---

## 4. 类装饰器工作机制

```mermaid
flowchart TD
    subgraph Def["定义阶段"]
        DEF["@CallCounter<br/>def hello():"]
        INST["CallCounter(hello)<br/>→ 创建实例"]
        INST2["实例替换 hello<br/>hello 现在是 ClassCounter 实例"]
    end

    subgraph State["实例状态"]
        S1["self.func = hello"]
        S2["self.count = 0"]
    end

    subgraph Call["调用阶段"]
        C1["hello() 被调用"]
        C2["调用 __call__()"]
        C3["self.count += 1"]
        C4["调用 self.func()"]
    end

    DEF --> INST
    INST --> INST2
    INST2 --> State
    State -.->|__call__| C2
    C1 --> C2
    C2 --> C3
    C3 --> C4

    style Def fill:#e3f2fd
    style State fill:#fff9c4
    style Call fill:#e8f5e9
```

---

## 5. 缓存装饰器工作原理

```mermaid
flowchart TD
    subgraph Input["输入"]
        ARGS["fibonacci(10)"]
    end

    subgraph Cache["缓存层 (memoize)"]
        CHECK{缓存中有<br/> (10) 吗?}
        HIT["✅ 命中<br/>返回缓存值"]
        MISS["❌ 未命中<br/>调用原始函数"]
        STORE["存储结果到缓存<br/>cache[(10)] = 55"]
    end

    subgraph Func["原始函数"]
        EXEC["执行 fibonacci(10)"]
        RESULT["返回 55"]
    end

    ARGS --> CHECK
    CHECK -->|有| HIT
    CHECK -->|没有| MISS
    MISS --> EXEC
    EXEC --> RESULT
    RESULT --> STORE
    STORE --> HIT
    HIT --> Output["输出: 55"]

    style Cache fill:#fff9c4
    style Func fill:#c8e6c9
    style HIT fill:#a5d6a7
    style MISS fill:#ffcdd2
```

---

## 6. 重试装饰器工作流

```mermaid
flowchart TD
    START["调用 func()"] --> TRY["尝试执行"]
    TRY --> SUCCESS{成功?}
    SUCCESS -->|是| RETURN["返回结果 ✅"]
    SUCCESS -->|否| CHECK_ATTEMPT{已达<br/>最大重试次数?}
    CHECK_ATTEMPT -->|是| RAISE["抛出异常 ❌"]
    CHECK_ATTEMPT -->|否| WAIT["等待 delay 秒"]
    WAIT --> ADJUST["delay × backoff<br/>(指数退避)"]
    ADJUST --> TRY

    style START fill:#e3f2fd
    style TRY fill:#fff3e0
    style RETURN fill:#c8e6c9
    style RAISE fill:#ffcdd2
    style WAIT fill:#f3e5f5
```

---

## 7. 权限装饰器架构

```mermaid
flowchart TD
    subgraph Request["请求"]
        USER["用户对象<br/>{name, role, permissions}"]
        ACTION["要执行的操作"]
    end

    subgraph Auth["权限链"]
        AUTH_CHECK{已认证?}
        ROLE_CHECK{角色匹配?}
        PERM_CHECK{有权限?}
    end

    subgraph Execute["执行"]
        FUNC["执行操作"]
        LOG["记录审计日志"]
    end

    USER --> AUTH_CHECK
    AUTH_CHECK -->|否| DENY1["拒绝: 未认证"]
    AUTH_CHECK -->|是| ROLE_CHECK
    ROLE_CHECK -->|否| DENY2["拒绝: 角色不足"]
    ROLE_CHECK -->|是| PERM_CHECK
    PERM_CHECK -->|否| DENY3["拒绝: 权限不足"]
    PERM_CHECK -->|是| FUNC
    FUNC --> LOG

    style Request fill:#e3f2fd
    style Auth fill:#fff9c4
    style Execute fill:#c8e6c9
    style DENY1 fill:#ffcdd2
    style DENY2 fill:#ffcdd2
    style DENY3 fill:#ffcdd2
```

---

## 8. 装饰器链组合全景

```mermaid
mindmap
  root((装饰器进阶))
    带参数装饰器
      三层嵌套
      可选参数
      默认参数技巧
    类装饰器
      __call__ 方法
      类状态管理
      方法扩展
      继承支持
    实战
      缓存 memoize
      LRU 缓存
      TTL 缓存
      重试
      基础重试
      指数退避
      异常白名单
      权限检查
      角色检查
      权限检查
      认证授权
    链式组合
      洋葱模型
      顺序依赖
      关注点分离
      装饰器工厂
    陷阱
      顺序依赖
      返回值假设
      副作用
      性能影响
```
