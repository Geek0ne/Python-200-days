# Day 44：枚举与常量 — 图解

---

## 1. 枚举底层实现原理

```
┌─────────────────────────────────────────────────────────────────┐
│                    Enum 底层实现 (EnumMeta 元类)                  │
└─────────────────────────────────────────────────────────────────┘

  class Color(Enum):         ← class Color(metaclass=EnumMeta)
      RED = 1
      GREEN = 2
      BLUE = 3

│
▼ EnumMeta.__new__(mcs, name, bases, classdict)

┌──────────────────────────────────────────────────────────────┐
│ 1. 收集所有成员定义                                           │
│    classdict = { RED: 1, GREEN: 2, BLUE: 3 }                │
│                                                              │
│ 2. 移除非枚举成员（方法、描述符等保留）                         │
│                                                              │
│ 3. 为每个成员创建实例（单例）                                   │
│    Color.RED   = Color.__new__(Color, 1); __init__("RED")    │
│    Color.GREEN = Color.__new__(Color, 2); __init__("GREEN")  │
│    Color.BLUE  = Color.__new__(Color, 3); __init__("BLUE")   │
│                                                              │
│ 4. 将原始类属性替换为枚举成员实例                               │
│    Color.RED   → <Color.RED: 1>  (单例)                       │
│    Color.GREEN → <Color.GREEN: 2> (单例)                      │
│    Color.BLUE  → <Color.BLUE: 3>  (单例)                      │
│                                                              │
│ 5. 构建反向查找映射                                            │
│    _value2member_map_ = {1: Color.RED, 2: Color.GREEN,       │
│                          3: Color.BLUE}                       │
│                                                              │
│ 6. 冻结枚举类，禁止修改成员                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. 枚举基类选择

```
需要哪种枚举？
      │
      ├── 基本命名常量集 ──────────► Enum（最常用）
      │
      ├── 需要与整数兼容 ──────────► IntEnum
      │    （HTTP 状态码、协议字段）
      │
      ├── 需要字符串兼容 ──────────► StrEnum（Python 3.11+）
      │    （配置键、JSON 字段名）
      │
      └── 需要位标志运算 ──────────► IntFlag
           （权限组合、选项标志）
```

---

## 3. 枚举成员查找方式

```
三种查找方式：

  按名称查找          按值查找            按成员查找
  Color["RED"]        Color(1)            Color(Color.RED)
       │                  │                    │
       ▼                  ▼                    ▼
    _member_names_    _value2member_map_      返回自身
    [ "RED",            { 1: Color.RED,
      "GREEN",           2: Color.GREEN,
      "BLUE" ]           3: Color.BLUE  }
```

---

## 4. auto() 赋值机制

```
auto() 内部计数器（全局）：

  _auto_number_incrementer = 0

  每次调用 auto():
      _auto_number_incrementer += 1
      return _auto_number_incrementer

  所以：
      class Color(Enum):
          RED = auto()    # → 1
          GREEN = auto()  # → 2
          BLUE = auto()   # → 3

  注意：不同枚举类的计数器是独立的！
```

---

## 5. 订单状态机流转图

```
          ┌──────────────────┐
          │    PENDING       │
          │    ⏳ 待处理      │
          └────────┬─────────┘
                   │
          ┌────────┴────────┐
          ▼                 ▼
  ┌───────────────┐  ┌───────────────┐
  │  PROCESSING   │  │  CANCELLED    │
  │  🔄 处理中     │  │  ❌ 已取消    │
  └───────┬───────┘  └───────────────┘
          │                    ▲
   ┌──────┴──────┐             │
   ▼             ▼             │
┌─────────┐ ┌──────────┐      │
│ SHIPPED │ │CANCELLED │      │
│ 📦 已发货│ │ ❌ 已取消 │──────┘
└────┬────┘ └──────────┘
     │
     ▼
┌───────────┐
│ DELIVERED │
│ ✅ 已签收  │
└───────────┘

终态：DELIVERED, CANCELLED（不可再转换）
```

---

## 6. @unique 装饰器行为

```
不加 @unique:                   加 @unique:

class Color(Enum):             @unique
    RED = 1                    class Color(Enum):
    CRIMSON = 1   ← 别名          RED = 1
    GREEN = 2                   CRIMSON = 1   ← ValueError!
    BLUE = 3                    GREEN = 2
                                BLUE = 3

Color(1) → Color.RED           Color(1) → 编译失败
Color.CRIMSON is Color.RED     @unique 防止了别名定义
  → True
```

---

## 7. 枚举 vs 常量的决策树

```
需要一组命名的关联值？
      │
      ├── < 3 个值，无关联逻辑 ────► 普通模块常量
      │       STATUS_OK = 200
      │
      ├── 3+ 个值，同语义 ────────► Enum 🌟
      │       class Status(Enum):
      │           OK = 200
      │           NOT_FOUND = 404
      │
      ├── 需要整数运算兼容 ───────► IntEnum
      │       class Code(IntEnum):
      │           OK = 200
      │
      ├── 需要位运算组合 ────────► IntFlag
      │       class Perm(IntFlag):
      │           READ = 4
      │
      └── 需要状态机逻辑 ────────► Enum + 转移表
              class OrderStatus(Enum):
                  PENDING = auto()
                  ...
```
