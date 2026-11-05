# Python 执行流程

```mermaid
flowchart TB
    subgraph Source[" 源代码 .py 文件 "]
        A["print('Hello')"]
    end
    
    subgraph Lexer[" 词法分析 (Lexer) "]
        B["Token 序列:<br/>NAME 'print'<br/>LPAR<br/>STRING 'Hello'<br/>RPAR"]
    end
    
    subgraph Parser[" 语法分析 (Parser) "]
        C["抽象语法树 (AST)"]
    end
    
    subgraph Compiler[" 编译器 (Compiler) "]
        D["字节码 (Bytecode)"]
        E["__pycache__/*.pyc<br/>缓存文件"]
    end
    
    subgraph VM[" CPython 虚拟机 "]
        F["逐条执行字节码<br/>管理栈帧、对象"]
    end
    
    subgraph Output[" 输出 "]
        G["Hello"]
    end
    
    A --> Lexer
    Lexer --> Parser
    Parser --> Compiler
    Compiler --> D
    D --> E
    E -.->|"复用缓存"| D
    D --> VM
    VM --> Output
```

---

# Python 内存模型（基础）

```
                 ┌─────────────────────┐
                 │    内存地址空间      │
                 │                     │
                 │  ┌───────────────┐  │
                 │  │    代码区      │  │
                 │  │ 字节码指令     │  │
                 │  └───────────────┘  │
                 │                     │
                 │  ┌───────────────┐  │
                 │  │    栈区        │  │
                 │  │  ┌─────────┐  │  │
                 │  │  │ 栈帧 1  │  │  │
                 │  │  │ 局部变量 │  │  │
                 │  │  │ 返回地址 │  │  │
                 │  │  └─────────┘  │  │
                 │  │  ┌─────────┐  │  │
                 │  │  │ 栈帧 2  │  │  │
                 │  │  │ ...     │  │  │
                 │  │  └─────────┘  │  │
                 │  └───────────────┘  │
                 │                     │
                 │  ┌───────────────┐  │
                 │  │    堆区        │  │
                 │  │  ┌─────────┐  │  │
                 │  │  │ 对象 A  │  │  │
                 │  │  │ "Hello" │  │  │
                 │  │  └─────────┘  │  │
                 │  │  ┌─────────┐  │  │
                 │  │  │ 对象 B  │  │  │
                 │  │  │   42    │  │  │
                 │  │  └─────────┘  │  │
                 │  │  ...          │  │
                 │  └───────────────┘  │
                 └─────────────────────┘
```

# Python 版本演变

```mermaid
timeline
    title Python 版本历史
    1991 : Python 0.9.0 发布
    1994 : Python 1.0
         : lambda, map, filter
    2000 : Python 2.0
         : Unicode, 列表推导式
    2008 : Python 3.0
         : print() 函数, 新式类
    2010 : Python 2.7 (最终 2.x)
    2020 : Python 2 正式停止支持
    2022 : Python 3.11
         : 大幅性能提升
    2023 : Python 3.12
         : 更友好的错误信息
    2024+ : Python 3.13
          : 自由线程 (nogil)
```

# Python VS 其他语言

```mermaid
quadrantChart
    title 编程语言对比
    x-axis "慢" --> "快"
    y-axis "新手友好" --> "专家导向"
    quadrant-1 "适合入门"
    quadrant-2 "高效开发"
    quadrant-3 "底层控制"
    quadrant-4 "高性能"
    Python: [0.25, 0.25]
    JavaScript: [0.35, 0.35]
    Java: [0.55, 0.50]
    C++: [0.85, 0.80]
    Rust: [0.75, 0.75]
    Go: [0.50, 0.55]
```
