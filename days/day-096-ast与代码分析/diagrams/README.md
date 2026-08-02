# Day 096 — AST 与代码分析 — 图解

## 1. Python 代码执行流程

```
┌──────────────────────────────────────────────────────────────┐
│                    Python 代码执行流程                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  源代码 (.py)                                                 │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐                                             │
│  │  Tokenizer   │  词法分析：把代码拆成 Token                  │
│  │  词法分析器   │  "x = 1 + 2" → NAME(x) EQUAL NUMBER(1)   │
│  └──────┬──────┘         PLUS NUMBER(2)                     │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐                                             │
│  │   Parser     │  语法分析：Token → AST                     │
│  │  语法分析器   │  检查语法是否合法                           │
│  └──────┬──────┘                                             │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────┐                     │
│  │   AST（抽象语法树）                  │  ← 我们操作的层次   │
│  │                                     │                     │
│  │  Module                              │                     │
│  │  └── Assign                          │                     │
│  │      ├── targets: [Name('x')]        │                     │
│  │      └── value: BinOp                │                     │
│  │          ├── left: Constant(1)       │                     │
│  │          ├── op: Add()               │                     │
│  │          └── right: Constant(2)      │                     │
│  └──────────────┬──────────────────────┘                     │
│                 │                                            │
│                 ▼                                            │
│  ┌─────────────┐                                             │
│  │  Compiler    │  编译 AST → 字节码                         │
│  │  编译器       │  (bytecode / .pyc)                        │
│  └──────┬──────┘                                             │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐                                             │
│  │  Python VM   │  执行字节码                                 │
│  │  虚拟机       │                                            │
│  └─────────────┘                                             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## 2. AST 节点类型层次

```
AST (基类)
│
├── mod (模块)
│   ├── Module         # 顶层模块
│   ├── Expression     # 单个表达式
│   └── Interactive    # 交互式输入
│
├── stmt (语句) ──────────── 出现在 body 列表中
│   ├── FunctionDef    # def foo():
│   ├── AsyncFunctionDef
│   ├── ClassDef       # class Foo:
│   ├── Return         # return x
│   ├── Delete         # del x
│   ├── Assign         # x = 1
│   ├── AugAssign      # x += 1
│   ├── AnnAssign      # x: int = 1
│   ├── For / While    # 循环
│   ├── If             # 条件
│   ├── With           # 上下文管理器
│   ├── Raise          # raise
│   ├── Try            # try/except/finally
│   ├── Assert         # assert
│   ├── Import         # import
│   ├── Global / Nonlocal
│   ├── Expr           # 表达式语句
│   └── Pass / Break / Continue
│
├── expr (表达式) ────────── 出现在值/条件等位置
│   ├── Name           # 变量名
│   ├── Constant       # 字面量 (3.8+)
│   ├── BinOp          # a + b
│   ├── UnaryOp        # -x, not x
│   ├── BoolOp         # a and b
│   ├── Compare        # a > b
│   ├── Call           # func(args)
│   ├── Attribute      # obj.attr
│   ├── Subscript      # obj[key]
│   ├── starred        # *args
│   ├── List / Tuple / Set / Dict
│   ├── ListComp / SetComp / DictComp / GeneratorExp
│   ├── Lambda         # lambda x: ...
│   ├── IfExp          # a if cond else b
│   └── Await / Yield / JoinedStr / FormattedValue
│
├── keyword (关键字参数)
├── alias (import 别名)
├── arguments (函数参数)
├── arg (单个参数)
└── operator (运算符)
    ├── Add, Sub, Mult, Div, Mod, Pow
    ├── LShift, RShift, BitOr, BitXor, BitAnd
    ├── MatMult
    └── And, Or, Not
```

## 3. NodeVisitor 遍历流程

```
源代码
  │
  ▼
ast.parse() → AST Root
  │
  ▼
Visitor.visit(Root)
  │
  ├── visit_语句类型(node)
  │     │
  │     ├── 检查/处理当前节点
  │     │
  │     └── generic_visit(node)  ← 遍历子节点
  │           │
  │           ├── visit_子节点类型(child1)
  │           │     └── ...
  │           ├── visit_子节点类型(child2)
  │           │     └── ...
  │           └── visit_子节点类型(child3)
  │                 └── ...
  │
  └── 返回收集的结果
```

## 4. Linter 分析流程

```
┌────────────────────────────────────────────────────────┐
│                  自定义 Linter 工作流程                   │
├────────────────────────────────────────────────────────┤
│                                                        │
│  1. 读取源文件                                         │
│     source = open("file.py").read()                   │
│     │                                                  │
│     ▼                                                  │
│  2. 解析为 AST                                         │
│     tree = ast.parse(source)                           │
│     │                                                  │
│     ▼                                                  │
│  3. 创建 Linter 实例                                   │
│     linter = MyLinter()                                │
│     │                                                  │
│     ▼                                                  │
│  4. 遍历 AST 触发规则检查                               │
│     linter.visit(tree)                                 │
│     │                                                  │
│     ├── visit_FunctionDef  → 检查 W001/W002/W003       │
│     ├── visit_Assign       → 检查 W004                 │
│     ├── visit_ClassDef     → 检查 W005                 │
│     └── visit_ExceptHandler → 检查 E001                │
│     │                                                  │
│     ▼                                                  │
│  5. 收集告警                                           │
│     linter.warnings → [LintWarning, ...]              │
│     │                                                  │
│     ▼                                                  │
│  6. 格式化输出                                         │
│     ├── L3:10 [W001] 函数名应使用 snake_case           │
│     ├── L15:5 [W002] 函数超过 50 行                    │
│     └── L28:0 [E001] 不应使用裸 except                 │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## 5. AST 变换 vs NodeVisitor 对比

```
NodeVisitor（只读）          NodeTransformer（可修改）
─────────────────          ────────────────────────
                           返回修改后的节点
  visit_Xxx(node):           visit_Xxx(node):
    # 读取信息                  # 修改节点
    self.data.append(...)        node.value = new_value
    # 不修改节点                 return node  ← 关键！
                               # 或返回新创建的节点
```

## 6. 安全执行对比

```
eval(user_input)               ast.literal_eval(user_input)
─────────────────              ──────────────────────────
❌ 危险！可执行任意代码           ✅ 安全！只解析字面量
                               

eval("__import__('os').system('ls')")  # ✅ 执行了！
eval("os.system('ls')")                # ✅ 执行了！

ast.literal_eval("{'a': 1}")          # ✅ 正确解析
ast.literal_eval("1 + 2")             # ❌ ValueError（表达式不允许）
```
