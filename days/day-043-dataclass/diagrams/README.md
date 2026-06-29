# dataclass 底层实现原理图解

## 1. dataclass 装饰器做了什么？

```mermaid
flowchart TB
    subgraph 开发时
        A["你写的代码：
        @dataclass
        class Point:
            x: float
            y: float"] --> B["Python 解释器
        读取 @dataclass 装饰器"]
    end

    subgraph 装饰器执行
        B --> C["遍历类注解中的字段
        → 提取 (x, float), (y, float)"]
        C --> D{"装饰器参数判断"}
        D -->|init=True| E["生成 __init__ 方法"]
        D -->|repr=True| F["生成 __repr__ 方法"]
        D -->|eq=True| G["生成 __eq__ 方法"]
        D -->|order=True| H["生成 __lt__/__le__/__gt__/__ge__"]
        D -->|frozen=True| I["生成 __setattr__ 抛出异常"]
        D -->|slots=True| J["创建 __slots__"]
    end

    subgraph 运行时
        E --> K["p = Point(1.0, 2.0)
        → 自动调用生成的 __init__"]
        F --> L["print(p)
        → Point(x=1.0, y=2.0)"]
        G --> M["p1 == p2
        → 自动比较所有字段"]
    end

    style A fill:#e1f5fe
    style B fill:#fff3e0
    style C fill:#fff3e0
    style K fill:#e8f5e9
    style L fill:#e8f5e9
    style M fill:#e8f5e9
```

## 2. field() 参数解析

```mermaid
flowchart LR
    subgraph field 参数体系
        A["field()"] --> B["default\n简单默认值"]
        A --> C["default_factory\n⚡默认可变类型工厂"]
        A --> D["init\n是否出现在 __init__"]
        A --> E["repr\n是否出现在 __repr__"]
        A --> F["compare\n是否参与比较"]
        A --> G["hash\n是否参与哈希"]
        A --> H["metadata\n自定义元数据字典"]
    end

    B --> B1["str, int, float, bool...
    name: str = 'unknown'"]

    C --> C1["list → field(default_factory=list)"]
    C --> C2["dict → field(default_factory=dict)"]
    C --> C3["set → field(default_factory=set)"]
    C --> C4["复杂对象 → field(default_factory=lambda: [])"]

    D --> D1["init=False → 计算字段"]
    E --> E1["repr=False → 隐藏密码/密钥"]
    F --> F1["compare=False → 排除 UUID/时间戳"]
    G --> G1["hash=False → 排除非关键哈希字段"]

    style A fill:#ce93d8
    style C fill:#ffcc02
```

## 3. __post_init__ 执行流程

```mermaid
sequenceDiagram
    participant 调用方
    participant dataclass
    participant __post_init__

    调用方->>dataclass: Order("笔记本", 2, 4999)
    activate dataclass
    dataclass->>dataclass: 分配字段 self.product="笔记本"
    dataclass->>dataclass: 分配字段 self.quantity=2
    dataclass->>dataclass: 分配字段 self.unit_price=4999
    dataclass->>dataclass: 调用 __post_init__()
    deactivate dataclass
    activate __post_init__
    __post_init__->>__post_init__: 生成 order_id = UUID
    __post_init__->>__post_init__: 计算 total_price = 2 * 4999
    __post_init__->>__post_init__: 验证 quantity > 0
    __post_init__->>__post_init__: 验证 unit_price > 0
    deactivate __post_init__
    调用方->>调用方: 得到完整的 Order 实例 ✅
```

## 4. dataclass vs namedtuple vs 普通类

```mermaid
flowchart TD
    subgraph 选择决策
        A["我需要一个类来装数据"] --> B{需要可变?}
    end

    B -->|是| C{需要类型注解?}
    B -->|否| D{需要方法/继承?}

    C -->|是| E["✅ dataclass\n(日常首选)"]
    C -->|否| F["普通 class\n(少量数据)"]

    D -->|是| G["✅ dataclass(frozen=True)\n或 NamedTuple"]
    D -->|否| H["✅ NamedTuple\n或 namedtuple"]

    E --> I["field() / __post_init__\n继承 / 序列化"]
    G --> I

    H --> J["元组拆包\n可哈希 / 性能极佳"]

    style E fill:#a5d6a7
    style G fill:#81c784
    style H fill:#81c784
```

## 5. 可变默认值陷阱图解

```mermaid
flowchart LR
    subgraph ❌ 错误：共享引用
        A1["@dataclass
        class Bad:
            items: list = []

        b1 = Bad()
        b2 = Bad()"] --> A2["b1.items is b2.items
        → True (同一对象!)"]
        A2 --> A3["b1.items.append('x')
        → b2.items 也被修改了！😱"]
    end

    subgraph ✅ 正确：独立副本
        B1["@dataclass
        class Good:
            items: list = field(default_factory=list)

        g1 = Good()
        g2 = Good()"] --> B2["g1.items is g2.items
        → False (独立对象)"]
        B2 --> B3["g1.items.append('x')
        → g2.items 不受影响 ✅"]
    end

    style A3 fill:#ffcdd2
    style B3 fill:#c8e6c9
```

## 6. 配置管理架构图

```mermaid
flowchart TB
    subgraph 配置来源
        A["默认值\n(dataclass defaults)"] -->|优先级 1 低| M[配置合并器]
        B["JSON 配置文件"] -->|优先级 2| M
        C["环境变量\nAPP_*"] -->|优先级 3| M
        D["命令行参数"] -->|优先级 4 高| M
    end

    subgraph 配置处理
        M --> V[__post_init__ 验证]
        V --> Cfg["AppConfig\n(frozen=True 保护)"]
    end

    subgraph 配置消费者
        Cfg --> S1["应用层"]
        Cfg --> S2["数据库层"]
        Cfg --> S3["缓存层"]
        Cfg --> S4["日志层"]
    end

    Cfg --> E["配置导出\nasdict() → JSON"]

    style Cfg fill:#ce93d8,color:#fff
    style V fill:#fff176
```

## 7. ASCII 速查：dataclass 核心概念关系

```
                    ┌─────────────────────────────────┐
                    │         @dataclass               │
                    │  自动生成模板方法               │
                    └──────────┬──────────────────────┘
                               │
              ┌────────────────┼──────────────────┐
              │                │                  │
        ┌─────▼─────┐   ┌─────▼─────┐    ┌───────▼───────┐
        │   field()  │   │__post_init│    │ 装饰器参数    │
        │ 精细字段控制│   │  后处理   │    │ 全局行为控制  │
        └─────┬─────┘   └─────┬─────┘    └───────┬───────┘
              │               │                   │
    ┌─────────┼─────────┐     │              ┌────┴────┐
    │         │         │     │              │         │
  default_factory  compare    │            frozen    order
  (可变默认值)  (排除比较)  验证/转换      (不可变)  (自排序)
    │         │         │     │              │         │
  repr=False  hash=False│     │            slots    unsafe_hash
  (隐藏字段)  (控制哈希) │     │           (内存优化) (强制哈希)
                        │     │
                        ▼     ▼
                   ┌──────────────────┐
                   │ 最终生成的方法集 │
                   │ __init__, __repr__│
                   │ __eq__, __hash__  │
                   │ __lt__~__ge__     │
                   │ __setattr__ (frozen)│
                   └──────────────────┘
```
