# Day 012 — 函数进阶：图解

> 本章图的 ASCII 示意图和 Mermaid 流程图，帮助理解函数进阶的核心概念。

---

## 目录

1. [默认参数陷阱内存示意图](#1-默认参数陷阱内存示意图-ascii)
2. [*args/**kwargs 数据流向图](#2-args-kwargs-数据流向图-mermaid)
3. [函数注解存储机制图解](#3-函数注解存储机制图解-ascii)
4. [通用数据处理器流程图](#4-通用数据处理器流程图-mermaid)

---

## 1. 默认参数陷阱内存示意图 (ASCII)

### 1.1 陷阱版本：共享同一个可变对象

```
                      ┌─────────────────────┐
                      │   函数对象 (add_item) │
                      │                     │
                      │  __defaults__ = ([]) │
                      │         │           │
                      │         ▼           │
                      │    ┌─────────────────┐
                      │    │ 空列表 []       │ ← 唯一的列表对象
                      │    └─────────────────┘
                      └─────────────────────┘


第一次调用: add_item("a")
  参数: item = "a"
  items ──── 指向默认列表 ────→ ┌─┬─┬─┐
                                │a│ │ │   ← 在默认列表上 .append("a")
                                └─┴─┴─┘
  调用后默认列表永久变为 ['a']


第二次调用: add_item("b")
  参数: item = "b"
  items ──── 仍然指向同一个 ──→ ┌─┬─┬─┐
                                │a│b│ │   ← 继续在同一个列表上 .append("b")
                                └─┴─┴─┘
  调用后默认列表变为 ['a', 'b'] ← 上个调用的结果还在！


第三次调用: add_item("c")
  参数: item = "c"
  items ──── 还是同一个 ──────→ ┌─┬─┬─┐
                                │a│b│c│   ← 越积越多
                                └─┴─┴─┘
  调用后默认列表变为 ['a', 'b', 'c']
```

### 1.2 正确版本：None 模式 + 每次创建新对象

```
                      ┌─────────────────────┐
                      │   函数对象            │
                      │  (add_item_correct)  │
                      │                     │
                      │  __defaults__ = (None)│ ← None 是不可变对象
                      │                    │
                      ＋─────────────────────＋


第一次调用: add_item_correct("a")
  参数: item = "a"
  items ──── 指向 None ──────────────────────→ None (单例)
  if items is None: items = []
  
  创建新的独立列表: ┌─┬─┬─┐
                    │a│ │ │
                    └─┴─┴─┘
  调用结束后，这个列表被返回，默认参数不受影响。


第二次调用: add_item_correct("b")
  参数: item = "b"
  items ──── 仍然指向 None ──────────────────→ None (还是那个单例)
  if items is None: items = []

  创建另一个新的独立列表: ┌─┬─┬─┐
                          │b│ │ │  ← 干净的新列表！
                          └─┴─┴─┘
  调用结束后，这个列表被返回，默认参数不受影响。
```

### 1.3 对比：陷阱 vs 正确

```
陷阱版本 (共享):
                                            
  ┌────────┐   ┌────────┐   ┌────────┐     
  │ 第1次   │   │ 第2次   │   │ 第3次   │     
  │ 调用    │   │ 调用    │   │ 调用    │     
  └───┬────┘   └───┬────┘   └───┬────┘     
      │            │            │           
      └──────┬─────┴─────┬──────┘           
             │           │                  
             ▼           ▼                  
        ┌─────────────────────┐             
        │   同一个列表         │             
        │   ['a', 'b', 'c']   │  ← 被累加修改
        └─────────────────────┘             

正确版本 (独立):

  ┌────────┐     ┌────────┐     ┌────────┐  
  │ 第1次   │     │ 第2次   │     │ 第3次   │  
  │ 调用    │     │ 调用    │     │ 调用    │  
  └───┬────┘     └───┬────┘     └───┬────┘  
      │              │              │       
      ▼              ▼              ▼       
  ┌────────┐    ┌────────┐    ┌────────┐    
  │ ['a']  │    │ ['b']  │    │ ['c']  │  ← 每次独立
  └────────┘    └────────┘    └────────┘    
```

---

## 2. *args/**kwargs 数据流向图 (Mermaid)

```mermaid
flowchart TD
    subgraph 定义时_打包
        A1["def func(*args):"] --> B1["*args 收集所有位置参数"]
        B1 --> C1["打包成 tuple"]
        C1 --> D1["args = (1, 2, 3, 4, 5)"]
        
        A2["def func(**kwargs):"] --> B2["**kwargs 收集所有关键字参数"]
        B2 --> C2["打包成 dict"]
        C2 --> D2["kwargs = {'a': 1, 'b': 2}"]
    end
    
    subgraph 调用时_解包
        E1["func(*[1, 2, 3])"] --> F1["* 解包列表"]
        F1 --> G1["相当于 func(1, 2, 3)"]
        
        E2["func(**{'x': 10, 'y': 20})"] --> F2["** 解包字典"]
        F2 --> G2["相当于 func(x=10, y=20)"]
    end

    subgraph 参数顺序
        H1["def f(pos1, pos2, *args, kw_only, **kwargs):"]
        H2["     ↑定位参数↑  ↑*args打包↑   ↑仅限关键字↑  ↑**kwargs打包↑"]
    end
```

### *args 数据流详细图

```mermaid
sequenceDiagram
    participant Caller as 调用者
    participant Func as 函数 f(a, b, *args)
    participant Args as args 元组
    
    Caller->>Func: f(1, 2, 3, 4, 5)
    Note over Func: 参数解析开始
    Func->>Func: a = 1 (第一个位置参数)
    Func->>Func: b = 2 (第二个位置参数)
    Func->>Args: 剩余参数 (3, 4, 5) 打包
    Note over Args: args = (3, 4, 5)<br/>类型: tuple
    Args-->>Func: 函数体内可使用 args[0], args[1], ...
    Func-->>Caller: 返回结果
```

### **kwargs 数据流详细图

```mermaid
sequenceDiagram
    participant Caller as 调用者
    participant Func as 函数 g(**kwargs)
    participant KWArgs as kwargs 字典
    
    Caller->>Func: g(name="张三", age=25, city="北京")
    Note over Func: 参数解析开始
    Func->>KWArgs: 打包所有关键字参数
    Note over KWArgs: kwargs = {"name": "张三", <br/>            "age": 25, <br/>            "city": "北京"}<br/>类型: dict
    KWArgs-->>Func: 函数体内可用<br/>kwargs["name"],<br/>kwargs.get("age")
    Func-->>Caller: 返回结果
```

### 参数传递完整流程

```mermaid
flowchart LR
    subgraph 传入参数
        P1["1"] 
        P2["2"]
        P3["3"]
        P4["c=100"]
        P5["x='hello'"]
    end

    subgraph 参数解析
        direction TB
        R1["普通位置参数<br/>a=1, b=2"]
        R2["*args (打包)<br/>args=(3, )"]
        R3["默认关键字参数<br/>c=10 -> 被 100 覆盖"]
        R4["**kwargs (打包)<br/>kwargs={'x':'hello'}"]
    end

    P1 --> R1
    P2 --> R1
    P3 --> R2
    P4 --> R3
    P5 --> R4
```

---

## 3. 函数注解存储机制图解 (ASCII)

### __annotations__ 字典结构

```
def add(x: int, y: int) -> float:
    return x + y

                    ┌─────────────────────────────────┐
                    │      add.__annotations__          │
                    │  (函数对象的 __annotations__ 属性)  │
                    ├─────────────────────────────────┤
                    │  ┌─────────────────────────────┐ │
                    │  │  "x"      →  <class 'int'>  │ │
                    │  │  "y"      →  <class 'int'>  │ │
                    │  │  "return" →  <class 'float'>│ │
                    │  └─────────────────────────────┘ │
                    │                                   │
                    │  字典的键: 参数名 (字符串)          │
                    │           "return" 代表返回值      │
                    │  字典的值: 类型对象 (任何表达式)     │
                    └─────────────────────────────────┘

Python 运行时不检查类型:
    add("hello", "world")  → 不会报错！
    TypeError 只在执行时出现（字符串不支持 + 操作）

静态检查工具 (mypy):
    mypy 在运行前分析 __annotations__ 
    → 发现 "hello" 不是 int → 报类型错误
```

### Python 为什么不强制检查？

```
动态类型 (Duck Typing):

    def double(x):
        return x * 2

    print(double(5))     → 10      (int * 2)
    print(double("Hi"))  → "HiHi"  (str * 2)
    print(double([1]))   → [1, 1]  (list * 2)

    同一个函数、无类型约束 — 三种不同类型都能正确工作！
    这就是「鸭子类型」的灵活性。

Type Hints + mypy 的平衡:

    灵活性                              安全性
    ┌─────────────────────────────────────┐
    │                                     │
    │  纯 Duck    有 Type     有 Type     │
    │  Typing    Hints       Hints       │
    │            无 mypy      + mypy     │
    │                                     │
    │  灵活      ⬆ 更可读    ⬆ 安全     │
    │  但易错    仍易错      CI 捕获错误  │
    │                                     │
    └─────────────────────────────────────┘
```

---

## 4. 通用数据处理器流程图 (Mermaid)

```mermaid
flowchart TD
    Start(["用户调用 processor.process()"]) --> Input["传入 *data 数据"]
    Input --> Preprocess{"有 preprocess 回调?"}
    
    Preprocess -->|"有"| ApplyPreprocess["对每个元素执行预处理<br/>square / cube / normalize / clip..."]
    Preprocess -->|"无"| RawData["直接使用原始数据"]
    
    ApplyPreprocess --> Cache
    RawData --> Cache
    
    Cache{"use_cache=True?<br/>且缓存中有结果?"}
    Cache -->|"是"| Hit["✅ 从 cache 字典中直接返回<br/>(性能优化, 避免重复计算)"]
    Cache -->|"否"| Aggregate["选择聚合方法:<br/>sum / mean / max / min / product / std"]
    
    Aggregate --> Calc["执行聚合计算"]
    Calc --> SaveCache{"use_cache=True?"}
    SaveCache -->|"是"| Store["将结果存入 cache<br/>key: hash(数据+方法)"]
    SaveCache -->|"否"| Options
    
    Store --> Options["处理 **options 配置<br/>verbose → 打印日志<br/>format_result → 格式化"]
    Options --> Result["返回结果字典"]
```

### 处理器类架构

```mermaid
classDiagram
    class DataProcessor {
        -name: str
        -_cache: Dict[str, Any]
        -_call_count: int
        +process(*data, preprocess, agg_method, use_cache, **options) Dict
        +batch_process(datasets, *, preprocess, agg_methods, verbose) Dict
        +clear_cache() None
        +get_stats() Dict
        -_make_cache_key(data, method) str
        -_aggregate(data, method) Union[int, float]
        -_format_result(value, fmt) str
    }
    
    class PreprocessFunctions {
        +square(x) int
        +cube(x) int
        +normalize(x) float
        +clip(min_val, max_val) Callable
        +log_transform(x) float
    }
    
    DataProcessor --> PreprocessFunctions : 使用回调
```

---

## 快速参考

| 概念 | 图解位置 | 核心要点 |
|------|---------|---------|
| 默认参数陷阱 | 第 1 节 | def 执行时创建默认参数，所有调用共享同一可变对象 |
| None 模式 | 第 1 节 | 用 None 代替可变默认值，函数体内创建新对象 |
| *args 打包 | 第 2 节 Mermaid | 位置参数 → 元组 |
| **kwargs 打包 | 第 2 节 Mermaid | 关键字参数 → 字典 |
| 函数注解 | 第 3 节 | 存储在 `__annotations__`，不强制检查 |
| 数据处理器 | 第 4 节 Mermaid | 综合运用所有概念 |
