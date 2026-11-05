# Day 023 — 装饰器入门 图解

## 1. 装饰器执行流程

```mermaid
flowchart TD
    subgraph Def["① 定义阶段 (定义时执行)"]
        A["@decorator<br/>def func():"] --> B["decorator(func)"]
        B --> C["创建 wrapper 函数<br/>(闭包捕获 func)"]
        C --> D["返回 wrapper<br/>替换原 func"]
    end

    subgraph Call["② 调用阶段 (调用时执行)"]
        E["func() 被调用"] --> F["调用 wrapper()"]
        F --> G["前置操作<br/>(before)"]
        G --> H["调用原始 func()"]
        H --> I["后置操作<br/>(after)"]
        I --> J["返回结果"]
    end

    D -.-> E

    style A fill:#e3f2fd
    style B fill:#bbdefb
    style C fill:#90caf9
    style D fill:#64b5f6
    style E fill:#e8f5e9
    style F fill:#c8e6c9
    style G fill:#fff9c4
    style H fill:#ffe0b2
    style I fill:#fff9c4
    style J fill:#a5d6a7
```

---

## 2. 闭包与作用域链

```mermaid
flowchart TD
    subgraph Outer["外层作用域<br/>decorator(func)"]
        direction LR
        FUNC["参数 func<br/>= 原始函数"]
    end

    subgraph Closure["闭包"]
        W["wrapper(*args, **kwargs)"]
        CAP["📎 捕获变量<br/>func → 原始函数"]
    end

    subgraph Execute["调用 wrapper()"]
        PRE["前置逻辑"]
        INVOKE["调用 func()"]
        POST["后置逻辑"]
    end

    Outer -->|返回| Closure
    Closure -->|执行| Execute
    CAP -.->|引用| INVOKE

    style Outer fill:#e8eaf6
    style Closure fill:#fff9c4
    style Execute fill:#c8e6c9
```

---

## 3. 语法糖 @ 等价还原

```mermaid
sequenceDiagram
    participant C as 代码
    participant P as Python 解释器
    participant M as 内存
    
    Note over C: @decorator<br/>def func(): ...
    
    C->>P: 解析 def func()
    P->>M: 创建函数对象 func
    C->>P: 遇到 @decorator
    P->>P: func = decorator(func)
    P->>M: func 指向 wrapper
    M-->>C: func 已被替换
    
    Note over C: 现在 func = wrapper<br/>wrapper 闭包捕获了原始 func
```

---

## 4. functools.wraps 工作原理

```mermaid
flowchart LR
    subgraph Before["使用 @wraps 前"]
        ORIG["原始函数<br/>__name__='greet'<br/>__doc__='问候'"]
        W1["wrapper<br/>__name__='wrapper'<br/>__doc__=None"]
        ORIG -->|装饰后| W1
    end

    subgraph After["使用 @wraps(func) 后"]
        ORIG2["原始函数<br/>__name__='greet'<br/>__doc__='问候'"]
        W2["wrapper<br/>__name__='greet' ← 复制<br/>__doc__='问候' ← 复制"]
        ORIG2 -->|装饰后| W2
        W2 -.->|__wrapped__| ORIG2
    end

    style Before fill:#ffcdd2
    style After fill:#c8e6c9
```

---

## 5. 装饰器顺序：洋葱模型

```mermaid
flowchart TD
    subgraph Decoration["装饰阶段（从下到上）"]
        DEF["@A<br/>@B<br/>@C<br/>def func()"]
        EQUIV["等价于<br/>func = A(B(C(func)))"]
    end

    subgraph Execution["调用阶段（从上到下）"]
        CALL["调用 func()"] --> A_PRE["A 前置操作"]
        A_PRE --> B_PRE["B 前置操作"]
        B_PRE --> C_PRE["C 前置操作"]
        C_PRE --> ORIG["原始函数执行"]
        ORIG --> C_POST["C 后置操作"]
        C_POST --> B_POST["B 后置操作"]
        B_POST --> A_POST["A 后置操作"]
        A_POST --> RESULT["返回结果"]
    end

    Decoration -.-> Execution

    style DEF fill:#e3f2fd
    style EQUIV fill:#f3e5f5
    style A_PRE fill:#ffcc80
    style B_PRE fill:#ffcc80
    style C_PRE fill:#ffcc80
    style ORIG fill:#81c784
    style A_POST fill:#90caf9
    style B_POST fill:#90caf9
    style C_POST fill:#90caf9
    style RESULT fill:#a5d6a7
```

---

## 6. 装饰器应用场景概览

```mermaid
graph LR
    subgraph Common["常见装饰器应用"]
        L1["日志 📝"]
        L2["计时 ⏱️"]
        L3["缓存 💾"]
        L4["权限 🔐"]
        L5["重试 🔄"]
        L6["限流 🚦"]
    end

    subgraph Core["核心概念"]
        C1["函数是一等公民"]
        C2["闭包"]
        C3["@ 语法糖"]
        C4["wraps"]
    end

    subgraph Today["今日所学"]
        D1["基础装饰器 ✅"]
        D2["@语法糖 ✅"]
        D3["wraps ✅"]
        D4["洋葱模型 ✅"]
        D5["日志装饰器 ✅"]
        D6["计时装饰器 ✅"]
    end

    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> D1
    D1 --> D2
    D2 --> D3
    D3 --> D4
    D4 --> D5
    D5 --> D6

    L1 -.->|Day 23| D5
    L2 -.->|Day 23| D6
    L3 -.->|Day 24| 缓存
    L4 -.->|Day 24| 权限
    L5 -.->|Day 24| 重试

    style Core fill:#f3e5f5
    style Today fill:#e8f5e9
    style Common fill:#e3f2fd
```

---

## 7. 装饰器 API 对比图

```mermaid
mindmap
  root((装饰器))
    基础概念
      函数是一等公民
      闭包
      @ 语法糖
      functools.wraps
    创建方式
      函数装饰器
        def decorator(func):
        def wrapper():
     类装饰器
        __call__
        __init__
    执行机制
      定义时执行
      洋葱模型
      自下而上装饰
      自上而下执行
    陷阱
      忘记 wraps
      返回值假设
      类方法装饰
      带参数 vs 不带参数
    实战应用
      日志
      计时
      缓存
      权限检查
      重试机制
      输入验证
      单例模式
```
