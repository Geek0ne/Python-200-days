# Day 097 — 领域特定语言（DSL）

## 📌 今日学习目标

1. 理解 DSL 的概念、分类与设计原则
2. 掌握用 Python 元编程构建 DSL 的核心技巧
3. 实战：构建配置 DSL 与规则引擎

---

## 一、DSL 概念与分类

### 1.1 什么是 DSL？

**DSL（Domain Specific Language，领域特定语言）** 是一种专门为特定问题域设计的语言，它不像 Python、Java 这样的通用语言（GPL）那样面面俱到，而是在某个狭窄领域内提供更自然、更高效的表达能力。

> **打个比方**：通用语言是「普通话」，什么都能说；DSL 是「行话」——医生说"心肌梗死"，外行人听不懂，但对医生来说，四个字就包含了大量精确信息。

### 1.2 DSL vs GPL

| 特性 | DSL（领域特定语言） | GPL（通用语言） |
|------|---------------------|-----------------|
| 范围 | 特定领域 | 通用 |
| 表达力 | 该领域内极强 | 广泛但不专精 |
| 学习曲线 | 领域专家容易上手 | 需要编程基础 |
| 典例 | SQL、HTML、CSS、正则、Makefile | Python、Java、C++ |

### 1.3 DSL 的分类

```
DSL 分类
├── 外部 DSL（External DSL）
│   ├── 独立语法：SQL、HTML、CSS
│   ├── 需要解析器/编译器
│   └── 完全自定义语法
├── 内部 DSL（Internal DSL / Embedded DSL）
│   ├── 嵌入宿主语言（如 Python）
│   ├── 利用宿主语言语法
│   └── 如：SQLAlchemy ORM、pytest、Hy
└── 中间 DSL（Mid-level DSL）
    ├── 有部分独立语法
    ├── 但依赖宿主语言执行
    └── 如：Jinja2 模板、Mako
```

---

## 二、Python 构建 DSL 的核心技巧

Python 因其动态特性，是构建内部 DSL 的绝佳语言。以下是核心技巧：

### 2.1 装饰器（Decorator）—— DSL 的「语法糖」

```python
# 用装饰器定义路由规则 → 这就是 Flask 的 DSL
@app.route("/users")
def list_users():
    return "Hello"

# 装饰器让代码读起来像声明式 DSL
```

### 2.2 上下文管理器（Context Manager）—— DSL 的「作用域」

```python
# 用 with 语句创建 DSL 领域
with database.transaction() as db:
    db.insert("users", {"name": "Alice"})
    db.insert("orders", {"user": "Alice"})
# with 块结束时自动提交/回滚
```

### 2.3 函数调用链 / Builder 模式 —— DSL 的「流畅接口」

```python
# 链式调用让代码像自然语言
query = (select("*")
         .from_("users")
         .where("age > 18")
         .order_by("name")
         .limit(10))
```

### 2.4 元类与描述符 —— DSL 的「声明式语法」

```python
# 用元类自动生成方法
class ModelMeta(type):
    def __new__(cls, name, bases, namespace):
        # 自动为字段生成 getter/setter
        ...
```

### 2.5 动态属性与 `__getattr__` —— DSL 的「魔法」

```python
class DSL:
    def __getattr__(self, name):
        # 任何属性访问都变成 DSL 命令
        return lambda *args: self._execute(name, *args)

dsl = DSL()
dsl.select("*").from_("users").where("id=1")
```

### 2.6 运算符重载 —— DSL 的「符号语言」

```python
# 重载 __or__, __and__ 等运算符
# SQLAlchemy 的 filter_by 就用了这个
query.filter(User.age > 18)  # > 被重载为 SQL 条件
```

---

## 三、实战 1：配置 DSL

让我们构建一个简单的配置 DSL，让配置文件既可读又灵活。

```python
# config_dsl.py
"""配置 DSL —— 用 Python 语法写配置"""

class ConfigBuilder:
    def __init__(self):
        self._config = {}
    
    def __call__(self, **kwargs):
        """支持 Config(key=value) 语法"""
        self._config.update(kwargs)
        return self
    
    def __getattr__(self, name):
        """支持 Config.key 语法"""
        return lambda value=None, **kwargs: self._set(name, value, **kwargs)
    
    def _set(self, name, value, **kwargs):
        if value is not None:
            self._config[name] = value
        if kwargs:
            self._config[name] = kwargs
        return self
    
    def build(self):
        return dict(self._config)

# 使用：像声明式 DSL 一样写配置
config = (ConfigBuilder()
    .database(host="localhost", port=5432, name="mydb")
    .cache(ttl=3600, backend="redis")
    .logging(level="INFO", format="%(asctime)s")
    .build())

print(config)
```

---

## 四、实战 2：规则引擎 DSL

```python
# rule_engine.py
"""简单规则引擎 DSL"""

class Rule:
    def __init__(self, name, condition, action):
        self.name = name
        self.condition = condition
        self.action = action
    
    def matches(self, context):
        return self.condition(context)
    
    def execute(self, context):
        return self.action(context)

class RuleEngine:
    def __init__(self):
        self.rules = []
    
    def rule(self, name):
        """装饰器语法定义规则"""
        def decorator(func):
            self.rules.append(Rule(name, func, None))
            return func
        return decorator
    
    def when(self, condition):
        """链式调用语法定义条件"""
        class RuleBuilder:
            def __init__(self, engine):
                self.engine = engine
                self._condition = condition
            
            def then(self, action):
                rule = Rule("auto", self._condition, action)
                self.engine.rules.append(rule)
                return self
        return RuleBuilder(self)
    
    def evaluate(self, context):
        results = []
        for rule in self.rules:
            if rule.matches(context):
                results.append(rule.execute(context))
        return results

# 使用方式 1：装饰器风格
engine = RuleEngine()

@engine.rule("年龄验证")
def age_check(ctx):
    return ctx.get("age", 0) >= 18
age_check.action = lambda ctx: f"{ctx['name']} 已成年"

# 使用方式 2：链式调用风格
engine.when(lambda ctx: ctx.get("score", 0) > 90) \
     .then(lambda ctx: f"{ctx['name']} 获得优秀评级")

# 测试
results = engine.evaluate({"name": "Alice", "age": 25, "score": 95})
for r in results:
    print(r)
```

---

## 五、实战 3：SQL 构建器 DSL

```python
# sql_builder.py
"""轻量 SQL 构建器 DSL"""

class SQLQuery:
    def __init__(self):
        self._table = ""
        self._columns = ["*"]
        self._conditions = []
        self._order = []
        self._limit_val = None
    
    def select(self, *columns):
        self._columns = list(columns) if columns else ["*"]
        return self
    
    def from_(self, table):
        self._table = table
        return self
    
    def where(self, condition):
        self._conditions.append(condition)
        return self
    
    def order_by(self, *columns):
        self._order = list(columns)
        return self
    
    def limit(self, n):
        self._limit_val = n
        return self
    
    def build(self):
        sql = f"SELECT {', '.join(self._columns)} FROM {self._table}"
        if self._conditions:
            sql += " WHERE " + " AND ".join(self._conditions)
        if self._order:
            sql += " ORDER BY " + ", ".join(self._order)
        if self._limit_val:
            sql += f" LIMIT {self._limit_val}"
        return sql

# DSL 使用
query = (SQLQuery()
    .select("name", "age", "email")
    .from_("users")
    .where("age > 18")
    .where("active = true")
    .order_by("name")
    .limit(10))

print(query.build())
# SELECT name, age, email FROM users WHERE age > 18 AND active = true ORDER BY name LIMIT 10
```

---

## 六、原理深入：DSL 的执行模型

```
┌─────────────────────────────────────────┐
│          DSL 代码（源码）                 │
│  query.select("name").from_("users")    │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         Python 解释器解析                │
│  1. query → 查找属性                     │
│  2. .select → 调用方法                   │
│  3. "name" → 传参                        │
│  4. .from_ → 继续链式调用                │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         DSL 对象状态累积                 │
│  内部存储: table, columns, conditions   │
│  每次方法调用修改自身状态并返回 self      │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         .build() 输出最终结果            │
│  "SELECT name FROM users"               │
└─────────────────────────────────────────┘
```

### 关键设计模式

1. **Builder 模式**：分步构建复杂对象
2. **Fluent Interface**：链式调用，代码读起来像自然语言
3. **Interpreter 模式**：解释执行 DSL 语句
4. **Visitor 模式**：遍历 DSL 抽象语法树

---

## 七、API 速查表

### Python 内建支持 DSL 的特性

| 特性 | 方法 | 用途 |
|------|------|------|
| 装饰器 | `@decorator` | 声明式语法 |
| 上下文管理器 | `__enter__` / `__exit__` | 作用域控制 |
| 动态属性 | `__getattr__` | 魔法属性访问 |
| 运算符重载 | `__or__`、`__and__` 等 | 符号 DSL |
| 元类 | `type.__new__` | 声明式类定义 |
| 描述符 | `__get__`、`__set__` | 字段级 DSL |
| 生成器 | `yield` | 惰性 DSL |

---

## 八、思考题

1. **设计思考**：如果让你为"任务调度"设计一个 DSL，你会选择哪些 Python 特性作为语法基础？为什么？

2. **对比分析**：SQL 是外部 DSL 还是内部 DSL？SQLAlchemy 呢？两者的优劣各是什么？

3. **实战挑战**：尝试为"日期范围查询"设计一个 DSL，支持 `date_range("2024-01-01").to("2024-12-31").where("status='active'")` 这样的链式调用。

4. **原理思考**：为什么 Python 比 Java 更适合构建内部 DSL？从语言特性角度分析。

5. **工程思考**：DSL 的可维护性与可读性如何平衡？DSL 过于「魔法化」会带来什么问题？

---

## 九、今日学习路径

```
1. 理解 DSL 概念 → 分类与特点
       ↓
2. 掌握核心技巧 → 装饰器、上下文管理器、链式调用
       ↓
3. 阅读代码示例 → 从简单到复杂
       ↓
4. 实战练习 → 构建自己的 DSL
       ↓
5. 思考题 → 深入理解设计原则
```

---

> 📝 **学习笔记**：DSL 的核心价值是「让代码读起来像自然语言」。但要注意，DSL 的设计需要平衡表达力和可维护性——过度「魔法化」的 DSL 会让团队成员困惑。
