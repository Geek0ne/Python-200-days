# Day 019 — Lambda 与函数式编程 🧪

## 📖 学习目标

- 理解 Lambda 表达式的语法、原理与作用域
- 掌握 `map()` / `filter()` / `reduce()` 的用法与内部机制
- 理解函数式编程与命令式编程的风格差异
- 掌握高阶函数的概念与实践
- 通过 Mermaid 图解理解函数式数据流

---

## 一、Lambda 表达式

### 1.1 什么是 Lambda

Lambda 表达式是一种 **匿名函数** —— 没有函数名的、单行的、立即使用的函数。

```python
# 普通函数
def add(x, y):
    return x + y

# Lambda 表达式
add = lambda x, y: x + y
```

### 1.2 语法与作用域

**语法：**

```
lambda 参数列表: 表达式
```

- 左侧：逗号分隔的参数（可为 0 个或多个）
- 右侧：单个表达式（不能含语句、赋值、return）

**作用域规则：**

```python
x = 10
f = lambda y: x + y   # x 来自外部作用域（闭包捕捉）
print(f(5))            # 15
```

> ⚠️ **Late Binding 陷阱**：Lambda 中的变量在 **调用时** 才查找，而非定义时。

```python
# ❌ 陷阱：所有函数打印 3
funcs = [lambda: i for i in range(3)]
for f in funcs:
    print(f())  # 3, 3, 3

# ✅ 修复：使用默认参数绑定当前值
funcs = [lambda i=i: i for i in range(3)]
for f in funcs:
    print(f())  # 0, 1, 2
```

### 1.3 Lambda vs 普通函数

| 特性 | 普通函数 | Lambda |
|------|---------|--------|
| 名称 | 有函数名 | 匿名 |
| 行数 | 多行 | 单行 |
| 语句支持 | 支持 | 不支持（仅表达式） |
| `return` | 显式 | 隐式 |
| 文档字符串 | 支持 | 不支持 |
| 调试友好度 | 高 | 低 |
| 适用场景 | 通用 | 简单的一次性逻辑 |
