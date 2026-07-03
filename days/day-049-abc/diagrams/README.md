# Day 049 — 抽象基类（ABC）图解

## ABC 强制接口实现流程

```mermaid
flowchart TD
    A[定义抽象基类] --> B[标记 @abstractmethod]
    B --> C[创建子类]
    C --> D{实现所有抽象方法?}
    D -->|是| E[✅ 子类可实例化]
    D -->|否| F[❌ TypeError]
    F --> G[报错: 缺少 abstract method]

    E --> H[实例化对象]
    H --> I[调用方法]
```

## ABC 类层次结构

```mermaid
classDiagram
    class ABC {
        <<abstract>>
    }
    class Shape {
        <<abstract>>
        +area() float*
        +perimeter() float*
        +describe() str
    }
    class Circle {
        -radius: float
        +area() float
        +perimeter() float
    }
    class Rectangle {
        -width: float
        -height: float
        +area() float
        +perimeter() float
    }

    ABC <|-- Shape
    Shape <|-- Circle
    Shape <|-- Rectangle
```

## register() 虚拟子类

```
┌─────────────────────────────────────────┐
│           虚拟子类注册                    │
├─────────────────────────────────────────┤
│                                         │
│  Drawable (ABC)                         │
│    └── @abstractmethod draw()           │
│                                         │
│  LegacyWidget (普通类)                   │
│    └── draw() # 有实现                   │
│                                         │
│  Drawable.register(LegacyWidget)        │
│    └── ✅ issubclass → True             │
│    └── ⚠️ 但不强制检查接口               │
│                                         │
└─────────────────────────────────────────┘
```

## ABC vs Protocol 对比

```
┌─────────────────────┬─────────────────────────┐
│       ABC           │      Protocol           │
├─────────────────────┼─────────────────────────┤
│ 显式继承            │ 隐式匹配（鸭子类型）       │
│ 必须 subclass       │ 只要方法签名匹配即可       │
│ 运行时强制检查       │ mypy 静态检查             │
│ from abc import     │ from typing import       │
│                     │                         │
│ class Shape(ABC):   │ class Shape(Protocol):   │
│   @abstractmethod  │   def area(self):        │
│   def area(self):   │     ...                 │
│     ...            │                         │
└─────────────────────┴─────────────────────────┘
```
