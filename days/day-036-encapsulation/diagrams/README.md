# Day 036 — 封装与数据隐藏：图解

> Mermaid 与 ASCII 示意图，帮助理解封装机制、名称改写、Property 和描述符

---

## 1️⃣ 封装的概念

```mermaid
flowchart TB
    subgraph 封装类
        I[接口层]
        I --> M[公开方法]
        I --> P[公开属性]
    end

    subgraph 内部实现
        D[私有数据]
        L[内部逻辑]
        S[状态管理]
    end

    M -.->|控制访问| D
    M -.->|调用| L
    P -.->|读取/验证| D

    style I fill:#90EE90
    style D fill:#FFB6C1
```

### 封装的比喻

```
🚗 汽车驾驶 vs 引擎内部

    用户看到:                   用户不关心:
    ┌─────────┐                ┌──────────────────┐
    │ 方向盘   │ ← 接口          │ 燃油喷射系统      │
    │ 油门     │                │ 气缸点火时序      │
    │ 刹车     │                │ 变速箱齿轮比      │
    │ 仪表盘   │                │ ECU 控制算法      │
    └─────────┘                │ 排气催化转化      │
                               └──────────────────┘

    用户通过接口操作               内部实现可以随意修改
    接口保持一致                   不影响用户使用
```

---

## 2️⃣ 名称改写（Name Mangling）机制

```mermaid
flowchart LR
    C["class MyClass"] --> A1["self.__secret = 42"]
    A1 --> A2["解释器处理:"]
    A2 --> A3["self._MyClass__secret = 42"]

    style A3 fill:#FFD700

    B1["obj.__secret"] -.->|AttributeError| B2["❌"]
    B3["obj._MyClass__secret"] -.->|42| B4["✅"]
```

### 名称改写规则

```
源代码:                    实际存储:
══════════                ══════════════

public = "公开"            public = "公开"
_protected = "受保护"      _protected = "受保护"
__private = "私有"         _ClassName__private = "私有"
__magic__ = "魔术"         __magic__ = "魔术" (不改写)
```

### 继承链中的名称改写

```mermaid
classDiagram
    class Base {
        +name: str
        _internal: str
        -__secret: str  # _Base__secret
    }

    class Derived {
        -__secret: str  # _Derived__secret
    }

    Base <|-- Derived

    note for Base: Base 的 __secret 是 _Base__secret
    note for Derived: Derived 的 __secret 是 _Derived__secret
    note for Derived: ⚠️ 它们不冲突！
```

```
实例 d = Derived()

d.__dict__:
    _Base__secret = "Base的秘密"     ← 来自 Base.__init__
    _Derived__secret = "Derived的秘密" ← 来自 Derived.__init__

d.get_base_secret():
    访问 _Base__secret → "Base的秘密"

d.get_derived_secret():
    访问 _Derived__secret → "Derived的秘密"
```

---

## 3️⃣ Python 属性约定

```
命名约定层级:

                       公开 API
                     ┌──────────┐
                     │  name    │ ← 公共接口的一部分
                     │  price   │    保证稳定
                     │  get()   │
                     └──────────┘

                   内部实现（约定）
                     ┌──────────┐
                     │  _data   │ ← 内部使用
                     │  _cache  │    可以随时修改
                     │  _init() │    子类可以访问
                     └──────────┘

                   名称改写私有
                     ┌──────────┐
                     │  __key   │ ← 避免子类覆盖
                     │  __secret│    更强的私有暗示
                     └──────────┘

                   魔术方法
                     ┌──────────┐
                     │  __init__│ ← Python 内部协议
                     │  __str__ │    不要自己发明
                     └──────────┘
```

---

## 4️⃣ @property 工作流程

```mermaid
flowchart TB
    AC["obj.attr"] --> Q{有 @property 吗?}
    Q -->|是| G["调用 getter 方法"]
    Q -->|否| D["直接访问实例字典"]

    AS["obj.attr = value"] --> QS{有 setter 吗?}
    QS -->|是| GS["调用 setter 方法<br/>(可以验证数据)"]
    QS -->|否| DS["直接写入实例字典"]

    style G fill:#90EE90
    style GS fill:#90EE90

    subgraph 验证逻辑
        V1["检查类型"]
        V2["检查范围"]
        V3["触发事件"]
    end

    GS --> V1
    GS --> V2
    GS --> V3
```

### Property vs 直接属性

```
直接属性访问:                      使用 @property:
═════════════════                  ═══════════════════

class Circle:                      class Circle:
    def __init__(self, r):             def __init__(self, r):
        self.radius = r                    self._radius = r

                                     @property
c = Circle(-5)  # ✅ 可接受负数!     def radius(self):
                                         return self._radius

# 想加验证怎么办?                   @radius.setter
# 改为 set_radius() → 接口变了!     def radius(self, value):
                                         if value <= 0:
                                              raise ValueError(...)
                                     c = Circle(-5)  # ❌ ValueError
                                     c.radius = 10  # ✅ 像属性一样赋值!
```

---

## 5️⃣ 描述符协议

```mermaid
flowchart LR
    subgraph 描述符协议
        GET["__get__(self, obj, type)"]
        SET["__set__(self, obj, value)"]
        DEL["__delete__(self, obj)"]
        NAME["__set_name__(self, owner, name)"]
    end

    subgraph 类定义
        C["class Order:"]
        F1["quantity = NonNegative()"]
        F2["price = NonNegative()"]
    end

    subgraph 访问过程
        A1["o.quantity"] -->|查找| M["类字典中找到 NonNegative 描述符"]
        M -->|调用| GET
    end

    C --> F1
    C --> F2
```

### 描述符访问优先级

```
obj.attr 查找顺序:
1. 数据描述符（定义了 __set__ 或 __delete__）
2. 实例 __dict__
3. 非数据描述符（只定义了 __get__）
4. 类 __dict__
5. __getattr__（如果定义了）

示例：@property 是数据描述符
     @cached_property 是非数据描述符（只定义 __get__）
```

---

## 6️⃣ 安全 API 客户端架构

```mermaid
classDiagram
    class APIClient {
        -__api_key: str
        -__api_secret: str
        -__base_url: str
        -__session: Session
        -__call_count: int
        -__failed_count: int
        #rate_limit: int
        #timeout: int
        +base_url: str (property)
        +api_key: str (property, masked)
        +call_count: int (property)
        +success_rate: float (property)
        +rate_limit: int (property)
        +get(path) dict
        +post(path, data) dict
        +put(path, data) dict
        +delete(path) dict
        +close() void
        +health_check() dict
        #_request() dict
        #_log() void
        #_check_rate_limit() void
        #_make_signature() str
        #_get_session() Session
    }

    class SecureAPIClient {
        #users: UsersAPI
        +users: UsersAPI (property)
    }

    class UsersAPI {
        #client: APIClient
        +list() dict
        +get(id) dict
        +create(name, email) dict
        +update(id, **kwargs) dict
        +delete(id) dict
    }

    APIClient <|-- SecureAPIClient
    SecureAPIClient --> UsersAPI : 组合
```

---

## 7️⃣ 属性控制模式对比

```
模式                     访问控制    验证逻辑    计算属性    内存开销
══════════════════════    ═══════    ═══════    ═══════    ═══════

直接属性访问              无          无          无         低
self.x

单下划线约定              约定         无          无         低
self._x

@property                完全控制    有          有          中
@property.setter

描述符协议                可复用      可复用      可复用      高
class Validator

__getattr__              动态创建    无          N/A         无缓存
__setattr__              完全拦截
```

### 使用建议

| 需求 | 推荐方案 |
|------|---------|
| 简单属性 | `self.name` |
| 内部实现细节 | `self._internal` |
| 需要验证的计算属性 | `@property` + `.setter` |
| 多个类共用验证逻辑 | 描述符 |
| 适应未来变化 | 先 `self._x` + `@property` 后期添加 |
| 避免子类覆盖 | `__name` 名称改写 |
