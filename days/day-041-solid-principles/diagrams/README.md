# Day 41 — SOLID 原则关系图解

> 本章节包含 SOLID 五大原则之间的关系图解，帮助理解它们如何协同工作。

---

## 1. SOLID 原则关系总图

```mermaid
flowchart TB
    subgraph Foundation["基础层"]
        SRP["SRP 单一职责原则
        一个类只做一件事"]
    end

    subgraph Design["设计层"]
        OCP["OCP 开闭原则
        对扩展开放，对修改关闭"]
        ISP["ISP 接口隔离原则
        接口要小而专"]
    end

    subgraph Guarantee["保障层"]
        LSP["LSP 里氏替换原则
        子类必须可替换父类"]
    end

    subgraph Architecture["架构层"]
        DIP["DIP 依赖反转原则
        依赖抽象而非具体"]
    end

    SRP -->|"职责清晰是基础"| OCP
    SRP -->|"职责清晰才能设计好接口"| ISP
    SRP -->|"职责清晰才能正确继承"| LSP
    
    OCP -->|"通过抽象实现扩展"| DIP
    ISP -->|"通过小接口实现抽象"| DIP
    LSP -->|"保证多态正确工作"| OCP
    
    DIP -.->|"指导整体依赖流向"| OCP
    DIP -.->|"指导整体依赖流向"| ISP
```

---

## 2. 违反 SOLID 的连锁反应

```mermaid
flowchart LR
    subgraph Bad["违反 SRP"]
        A["一个类做多件事"]
        A1["修改频繁
        影响范围大"]
    end

    subgraph Bad2["连锁反应"]
        B1["❌ 违反 OCP
        改一个功能动整个类"]
        B2["❌ 违反 LSP
        继承关系混乱"]
        B3["❌ 违反 ISP
        接口臃肿"]
    end

    subgraph Bad3["最终结果"]
        C1["🛑 意大利面条代码"]
        C2["🛑 不敢重构"]
        C3["🛑 技术债爆炸"]
    end

    A -->|"导致"| A1
    A1 --> Bad2
    Bad2 --> Bad3
```

---

## 3. 遵循 SOLID 的良性循环

```mermaid
flowchart LR
    subgraph Good["遵循 SRP"]
        D["每个类
        单一职责"]
        D1["类小、专注
        易于理解和修改"]
    end

    subgraph Good2["良性循环"]
        E1["✅ OCP
        新增功能=新增类"]
        E2["✅ LSP
        子类安全替换父类"]
        E3["✅ ISP
        接口小巧又干净"]
        E4["✅ DIP
        依赖抽象可切换"]
    end

    subgraph Good3["最终结果"]
        F1["📐 整洁架构"]
        F2["🚀 容易扩展"]
        F3["💪 长期可维护"]
    end

    D -->|"带来"| D1
    D1 --> Good2
    Good2 --> Good3
```

---

## 4. SOLID 原则与对应设计模式

```mermaid
flowchart TD
    SOLID["SOLID 原则"] --> SRP
    SOLID --> OCP
    SOLID --> LSP
    SOLID --> ISP
    SOLID --> DIP

    SRP --- SRP_P["相关模式
    · 外观模式（Facade）
    · 命令模式（Command）"]
    
    OCP --- OCP_P["相关模式
    · 策略模式（Strategy）
    · 模板方法（Template Method）
    · 装饰器模式（Decorator）
    · 工厂模式（Factory）"]
    
    LSP --- LSP_P["相关模式
    · 抽象工厂（Abstract Factory）
    · 命令模式（Command）"]
    
    ISP --- ISP_P["相关模式
    · 适配器模式（Adapter）
    · 代理模式（Proxy）"]
    
    DIP --- DIP_P["相关模式
    · 工厂模式（Factory）
    · 依赖注入（DI）
    · 策略模式（Strategy）"]

    style SOLID fill:#f9f,stroke:#333,stroke-width:2px
    style SRP fill:#e1f5fe,stroke:#0277bd
    style OCP fill:#e8f5e9,stroke:#2e7d32
    style LSP fill:#fff3e0,stroke:#ef6c00
    style ISP fill:#f3e5f5,stroke:#7b1fa2
    style DIP fill:#fce4ec,stroke:#c62828
```

---

## 5. 每个原则的一句话速记

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  SRP = 一个类只做一件事，专心才能做得好                  │
│                                                      │
│  OCP = 加功能就加类，改已有的代码要慎重                   │
│                                                      │
│  LSP = 子类得能完全顶替父类，不能偷偷改契约                │
│                                                      │
│  ISP = 接口要小而专，别让用户依赖不需要的东西               │
│                                                      │
│  DIP = 依赖抽象不依赖具体，接口是模块间的桥梁               │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 6. ASCII 关系图

```
                   ╔═══════════════════════════════════╗
                   ║        DIP  依赖反转原则           ║
                   ║     决定模块间的依赖方向            ║
                   ╚═══════════╦═══════════════════╝
                               ║
              ┌────────────────╬────────────────┐
              ║                ║                ║
    ╔═════════╬═══════╗  ╔════╬════════╗  ╔═══╬═════════╗
    ║  OCP           ║  ║   ISP    ║  ║  LSP           ║
    ║ 开闭原则        ║  ║ 接口隔离  ║  ║ 里氏替换        ║
    ║ 扩展开放        ║  ║ 小而专    ║  ║ 可替换性        ║
    ╚════════════════╝  ╚══════════╝  ╚════════════════╝
                               ║
                   ╔═══════════╩═══════════════════╗
                   ║        SRP  单一职责原则       ║
                   ║    所有原则的基础和出发点       ║
                   ╚═══════════════════════════════╝

    关系解读：
    • SRP 是地基：职责清晰才谈得上扩展、替换和隔离
    • OCP 追求弹性：允许无伤新增功能
    • LSP 保证安全：多态替换不出错
    • ISP 讲究精准：接口刚好够用
    • DIP 是顶层架构：控制依赖的方向
```

---

## 7. 重构前后的代码结构对比

```mermaid
flowchart LR
    subgraph Before["重构前 🚫"]
        B1["订单系统 OrderSystem
        ┌──────────────────┐
        │ 验证逻辑          │
        │ 价格计算          │
        │ 存储逻辑          │
        │ 日志记录          │
        │ 通知发送          │
        │ 结果返回          │
        └──────────────────┘
        一个巨无霸类"]
    end

    subgraph After["重构后 ✅"]
        direction TB
        A1["OrderValidator(验证)"]
        A2["PriceCalculator(计算)"]
        A3["OrderRepository(存储)"]
        A4["Logger(日志)"]
        A5["Notifier(通知)"]
        A6["OrderProcessor
        → 只编排，不实现"]
    end

    Before -->|"SRP+OCP+LSP+ISP+DIP"| After

    style Before fill:#ffebee,stroke:#c62828
    style After fill:#e8f5e9,stroke:#2e7d32
```
