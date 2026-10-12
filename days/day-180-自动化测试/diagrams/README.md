# Diagrams - Day 180: 自动化测试

## pytest 测试生命周期

```mermaid
flowchart TD
    A[开始] --> B{发现测试文件}
    B -->|pattern match| C[收集测试函数]
    C --> D[运行 fixture setup]
    D --> E[执行测试函数]
    E --> F{断言通过?}
    F -->|是| G[记录通过]
    F -->|否| H[记录失败 + 输出详情]
    G --> I[清理 teardown]
    H --> I
    I --> J{更多测试?}
    J -->|是| C
    J -->|否| K[生成报告]
    K --> L[结束]
```

## 测试金字塔

```mermaid
graph TB
    subgraph E2E["端到端测试 (E2E)"]
        E1[用户界面测试<br/>较少/慢/昂贵]
    end
    
    subgraph Integration["集成测试"]
        I1[模块接口测试<br/>中等速度]
    end
    
    subgraph Unit["单元测试"]
        U1[函数/方法测试<br/>快速/便宜/众多]
    end
    
    Unit --> Integration --> E2E
    
    classDef unit fill:#4CAF50,stroke:#388E3C
    classDef integration fill:#FFC107,stroke:#FFA000
    classDef e2e fill:#F44336,stroke:#D32F2F
    
    class U1 unit
    class I1 integration
    class E1 e2e
```

## Fixture 作用域层次

```mermaid
graph LR
    subgraph Session ["Session 作用域"]
        S[数据库连接池]
    end
    
    subgraph Module ["Module 作用域"]
        M[测试数据准备]
    end
    
    subgraph Class ["Class 作用域"]
        C[模拟服务实例]
    end
    
    subgraph Function ["Function 作用域"]
        F1[测试用例数据]
        F2[清理函数]
    end
    
    Session --> Module --> Class --> Function
```

## TDD 流程

```mermaid
flowchart LR
    A[红色：写测试] --> B[运行测试 失败]
    B --> C[绿色：写实现]
    C --> D[运行测试 通过]
    D --> E{需要重构?}
    E -->|是| F[重构代码]
    F --> G[运行测试 仍通过]
    E -->|否| H[结束]
    G --> H
```

## 测试覆盖率类型

```
语句覆盖 (Statement):
    if x:        → 需要 x=True 才能执行 if 体
        print()

分支覆盖 (Branch):
    if x:         → 需要 x=True 和 x=False 两个分支
        print()
    → 语句 + 分支

条件覆盖 (Condition):
    if x and y:  → 每个条件独立测试 True/False
        print()

路径覆盖 (Path):
    if x:        → 所有可能执行路径
        if y:
            print()
```

```mermaid
graph TD
    A[开始] --> B{x}
    B -->|True| C{y}
    B -->|False| D[结束]
    C -->|True| E[打印]
    C -->|False| D
    E --> D
```

**路径分析：**
- 路径 1: Start → x=True → y=True → print → End
- 路径 2: Start → x=True → y=False → End
- 路径 3: Start → x=False → End