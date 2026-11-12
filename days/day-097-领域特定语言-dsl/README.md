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

**参考答案**

我会选三种特性组合：**装饰器**做任务注册、**链式调用**做时间表达、**上下文管理器**做批量作用域。

- **装饰器**：任务调度本质是「定义即注册」——函数写好的那一刻就该进入调度表，装饰器恰好在定义时执行，无需手动调用注册函数。例如 `@scheduler.task` 一行就把函数登记为任务。
- **链式调用（Fluent Interface）**：时间规则用自然语言式的链条表达最直观，如 `every(10).minutes.do(send_report)`、`every().day.at("08:00").do(backup)`。每个方法返回 self，读起来像英语句子，领域专家（运维、运营）也能看懂。
- **上下文管理器**：用 `with scheduler.batch():` 把一组任务圈进同一作用域，退出 with 块时统一提交或回滚，避免「注册了一半」的中间状态。

为什么这样选：装饰器解决「声明式」，链式调用解决「可读性」，上下文管理器解决「作用域与资源安全」——正好覆盖调度 DSL 的三个核心需求，而且都是 Python 原生语法，不需要写解析器。

2. **对比分析**：SQL 是外部 DSL 还是内部 DSL？SQLAlchemy 呢？两者的优劣各是什么？

**参考答案**

**SQL 是外部 DSL**：它有完全独立的语法（`SELECT ... FROM ... WHERE ...`），不依赖任何宿主语言，必须由专门的解析器（数据库引擎）来解析执行。你在 Python、Java 甚至命令行里都能写同一句 SQL。

**SQLAlchemy 是内部 DSL**：它嵌入在 Python 里，用的全是 Python 语法，例如 `session.query(User).filter(User.age > 18)`——这里的 `>` 是被重载的运算符，生成的是条件对象而不是布尔值。

两者优劣对比：

- **外部 DSL（SQL）**：语法专为查询设计，简洁精确；跨语言通用，学会一次到处能用。代价是要学一套新语法，且与宿主语言割裂——拼接 SQL 字符串容易引入注入漏洞，IDE 也无法检查字符串里的语法错误。
- **内部 DSL（SQLAlchemy）**：不用学新语法，复用 Python 的类型检查、IDE 补全和调试器；条件用对象表达，天然防注入。代价是受宿主语法限制，写复杂查询时往往比原生 SQL 啰嗦，且只能在 Python 生态里用。

一句话总结：外部 DSL 赢在「专用与通用」，内部 DSL 赢在「与宿主语言无缝集成」。

3. **实战挑战**：尝试为"日期范围查询"设计一个 DSL，支持 `date_range("2024-01-01").to("2024-12-31").where("status='active'")` 这样的链式调用。

**参考答案**

核心思路是 **Builder 模式**：每次方法调用只累积状态并返回 `self`，最后由 `build()` 统一输出结果。完整可运行代码（仅用标准库）：

```python
from datetime import date


class DateRangeQuery:
    """日期范围查询 DSL：内部累积状态，build() 时输出 SQL"""

    def __init__(self, start):
        self.start = date.fromisoformat(start)   # 解析起始日期
        self.end = None                          # 结束日期，待 to() 设置
        self.conditions = []                     # 附加过滤条件

    def to(self, end):
        self.end = date.fromisoformat(end)
        if self.end < self.start:
            raise ValueError("结束日期不能早于起始日期")
        return self                              # 返回 self，支持链式调用

    def where(self, condition):
        self.conditions.append(condition)        # 累积条件而不是立即执行
        return self

    def build(self):
        sql = (f"SELECT * FROM records "
               f"WHERE date BETWEEN '{self.start}' AND '{self.end}'")
        if self.conditions:
            sql += " AND " + " AND ".join(self.conditions)
        return sql


def date_range(start):
    """DSL 入口函数"""
    return DateRangeQuery(start)


# 链式调用：读起来接近自然语言
query = (date_range("2024-01-01")
         .to("2024-12-31")
         .where("status='active'"))
print(query.build())
```

预期输出：

```
SELECT * FROM records WHERE date BETWEEN '2024-01-01' AND '2024-12-31' AND status='active'
```

解释：`date_range()` 创建查询对象；`.to()` 和 `.where()` 都只是修改内部状态后返回自身，所以能一直点下去；真正的「执行」（生成 SQL）推迟到 `build()`。这正是第六节执行模型图描述的「状态累积 → 最终输出」过程。

💡 提示：`where()` 直接拼接字符串只适合演示；真实项目应使用参数化查询（占位符 + 参数分离）防止 SQL 注入。

4. **原理思考**：为什么 Python 比 Java 更适合构建内部 DSL？从语言特性角度分析。

**参考答案**

内部 DSL 的本质是「借用宿主语言的语法外壳，装进自己领域的语义」。Python 的动态特性让这种「借用」几乎不受限制：

- **运算符重载无门槛**：任何类都能定义 `__gt__`、`__or__` 等方法。`User.age > 18` 在 SQLAlchemy 里返回条件对象；Java 不支持运算符重载，只能写成 `User.age.gt(18)`，流畅感大打折扣。
- **`__getattr__` 动态属性**：访问不存在的属性时可以即时生成方法，实现 `dsl.select(...).from_(...)` 这类「凭空出现」的 API；Java 的反射做不到在语法层面拦截属性访问。
- **装饰器与元类**：`@app.route("/users")`、声明式 Model 类都是一等公民语法；Java 的注解只是元数据，还需额外的注解处理器/代码生成才能产生行为。
- **关键字参数与默认值**：`task(retries=3, timeout=60)` 自带「命名配置」语义，天然像配置语言；Java 没有关键字参数，只能靠 Builder 类或重载模拟。
- **解释执行、无需编译**：DSL 代码写完即跑，迭代成本极低。

反过来，Java 的静态类型虽然让 DSL 更安全，但语法刚性太强，构建内部 DSL 往往要付出大量样板代码，所以 Java 生态更常见的是外部 DSL（如 Gradle 早年另造 Groovy DSL）。

5. **工程思考**：DSL 的可维护性与可读性如何平衡？DSL 过于「魔法化」会带来什么问题？

**参考答案**

平衡的关键是：**DSL 只包装「高频、稳定」的领域表达，其余留给普通 Python**。具体做法：

- 保持 DSL「薄」：内部尽快落到显式的数据结构或普通函数，魔法只存在于入口一层。
- 提供「逃生通道」：任何 DSL 写法都能退回到等价的普通 API，例如链式构建器保留 `build()` 返回纯字典。
- 显式优于隐式：少用 `__getattr__` 凭空造方法，多用明确定义的方法名；副作用集中在一个明确的终结点（如 `build()`/`execute()`）。
- 写文档和类型提示，让团队成员能查到每个「魔法」背后的真实行为。

过度魔法化的典型问题：

- **调试困难**：报错栈穿过层层 `__getattr__`/元类，看不到真实逻辑。例如拼错 `.selct()` 不会报 AttributeError，而是被 `__getattr__` 静默接受，生成错误查询——错误被推迟到很远的地方才爆发。
- **工具失效**：IDE 补全、跳转定义、mypy 静态检查对动态生成的属性基本无能为力。
- **学习成本转嫁**：DSL 作者省了几行代码，每个使用者都要先学一套「黑话」，人员流动后维护成本极高。

💡 提示：判断标准很简单——如果一段 DSL 代码需要作者本人解释才能看懂，它就已经越过了可读性的边界。

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
