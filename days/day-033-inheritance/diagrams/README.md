# Day 033 — 继承：图解

> 继承关系图、MRO 解析、C3 算法、菱形继承、Mixin 组合、形状层次结构

---

## 1️⃣ 基本继承关系

```
     ┌──────────┐
     │  Animal  │  ← 父类 / 基类 / superclass
     ├──────────┤
     │ name     │
     │ age      │
     ├──────────┤
     │ speak()  │
     │ move()   │
     └────┬─────┘
          │
    ┌─────┴──────┐
    │            │
┌───┴────┐  ┌───┴────┐
│  Dog   │  │  Cat   │  ← 子类 / 派生类 / subclass
├────────┤  ├────────┤
│(继承)   │  │(继承)   │
├────────┤  ├────────┤
│ speak()│  │ speak()│  ← 重写 (override)
│ wag()  │  │ purr() │  ← 新增方法
└────────┘  └────────┘

Dog is an Animal    ✓
Cat is an Animal    ✓
Animal is a Dog     ✗  （猫不是狗）
```

## 2️⃣ MRO (方法解析顺序)

### 简单继承

```
class B(A): pass

B.__mro__ = [B, A, object]

方法查找: B.method()
  B.__dict__ → 找到? → 返回
    没找到   → A.__dict__ → 找到? → 返回
                没找到   → object.__dict__
```

### 多重继承

```
class D(B, C): pass

MRO: D → B → C → A → object
     ↑___声明顺序___↓

D.__mro__:
  [D, B, C, A, object]
```

### 菱形继承

```
         A
       /   \
      B     C
       \   /
         D

MRO: D → B → C → A → object

调用 D().method()
  D.method: "D"
    → super() → B.method: "B → "
        → super() → C.method: "C → "    ← 不是 A!
            → super() → A.method: "A"
                → super() → object

输出: "D → B → C → A"
```

## 3️⃣ C3 线性化算法

```
L[Class(Base1, Base2)] = Class + merge(L[Base1], L[Base2], [Base1, Base2])

merge 规则:
  取第一个列表 head，如果不在任何其它列表的 tail 中，取出它
  否则尝试下一个列表的 head

示例: L[D(B, C)] where B(A), C(A):

L[A]   = A, O
L[B]   = B, A, O
L[C]   = C, A, O

L[D]   = D + merge(L[B], L[C], [B, C])
       = D + merge([B, A, O], [C, A, O], [B, C])
       
       head=B, B 在 [C] 尾部? 没有 → 取出 B
       = D, B + merge([A, O], [C, A, O], [C])
       
       head=A, A 在 [C, A, O] 尾部? YES (在尾部) → 跳过
       head=C, C 在 [] 尾部? 没有 → 取出 C
       = D, B, C + merge([A, O], [A, O])
       
       head=A, A 在 [A, O] 尾部? NO (在头部) → 取出 A
       = D, B, C, A + merge([O], [O])
       
       head=O, O 在 [O] 尾部? NO → 取出 O
       = D, B, C, A, O

验证: D.__mro__ = [D, B, C, A, object] ✓
```

## 4️⃣ super() 调用链

```
class Base:
    def method(self): return "Base"

class A(Base):
    def method(self): return f"A → {super().method()}"

class B(Base):
    def method(self): return f"B → {super().method()}"

class C(A, B):
    def method(self): return f"C → {super().method()}"

C.__mro__ = [C, A, B, Base, object]

C().method() 执行链:

  C.method()
    ↓
  "C → " + A.method()
              ↓
            "A → " + super().method()
                      ↓
                    在 A 的上下文中，super() 看 C.__mro__ 中 A 之后的类
                    → B.method()    ← 不是 Base!
                      ↓
                    "B → " + super().method()
                              ↓
                            Base.method()
                              ↓
                            "Base"

结果: "C → A → B → Base"

关键理解:
  super() 不总是调用字面父类!
  super() 使用 self.__class__.__mro__ 来决定调用链
```

## 5️⃣ Mixin 组合模式

```
SerializableMixin    ValidateMixin     LogMixin     TimestampMixin
  │                     │                │              │
  │  to_json()          │  validate()    │  log()       │  created_at
  │  to_dict()          │  add_valid..   │              │  updated_at
  └─────────┬───────────┴───────┬────────┴──────────────┘
            │                   │
            └───────────────────┘
                     │
                     ▼
                Product
             ┌──────────────┐
             │ name         │
             │ price        │
             │ stock        │
             ├──────────────┤
             │ to_json()    │  ← 来自 SerializableMixin
             │ validate()   │  ← 来自 ValidateMixin
             │ log()        │  ← 来自 LogMixin
             │ created_at   │  ← 来自 TimestampMixin
             └──────────────┘
```

## 6️⃣ 形状层次结构

```
                    Shape (ABC)
                    ──────────
                    + area()
                    + perimeter()
                    + describe()
                    + scale()
                    + __eq__/__lt__
                    │
          ┌─────────┼──────────┐
          │         │          │
        Circle  Rectangle   Triangle   SolidShape (ABC)
          │         │          │         ────────────
          │     Square         │         + volume()
          │                    │         + surface_area()
          │                    │         │
          │                    │    ┌────┼────┐
          │                    │    │    │    │
          │                    │  Sphere Box Cylinder

形状继承:
  Shape ← 抽象基类，定义接口
  ├── Circle      → is-a Shape ✓
  ├── Rectangle   → is-a Shape ✓
  │   └── Square  → is-a Rectangle ✓, is-a Shape ✓
  ├── Triangle    → is-a Shape ✓
  └── SolidShape  → is-a Shape ✓
      ├── Sphere  → is-a SolidShape ✓, is-a Shape ✓
      ├── Box     → is-a SolidShape ✓, is-a Shape ✓
      └── Cylinder→ is-a SolidShape ✓, is-a Shape ✓

多态:
  shapes = [Circle(5), Square(4), Sphere(3)]
  for s in shapes:
      print(s.area())    ← 每个类各自实现
      print(s.describe())← 每个类可能重写
```

## 7️⃣ isinstance vs type

```
              Animal
              │
          ┌───┴────┐
        Dog       Cat
          │
        Puppy

p = Puppy()

type(p)                 = <class 'Puppy'>
type(p) is Puppy        = True
type(p) is Dog          = False  ← type 不检查继承!
type(p) is Animal       = False

isinstance(p, Puppy)    = True
isinstance(p, Dog)      = True   ← Puppy is a Dog
isinstance(p, Animal)   = True   ← Puppy is an Animal
isinstance(p, Cat)      = False
isinstance(p, (Dog, Cat))= True  ← 可以是多种类型

issubclass(Puppy, Dog)  = True
issubclass(Dog, Puppy)  = False
issubclass(Puppy, (Dog, Cat)) = True
```
