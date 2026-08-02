# Day 096 — AST 与代码分析 — 练习清单

## ✅ 今日完成清单

- [ ] 理解 AST 的概念和 Python 中 ast 模块的基本用法
- [ ] 掌握 `ast.parse()`、`ast.unparse()`、`ast.dump()` 的使用
- [ ] 学会使用 `ast.NodeVisitor` 遍历 AST
- [ ] 理解 `ast.NodeTransformer` 进行代码变换
- [ ] 了解静态分析的基本原理
- [ ] 实现一个简单的函数复杂度分析器
- [ ] 完成自定义 Linter 的编写

---

## 📝 基础练习题

### 练习 1：AST 遍历入门
使用 `ast.NodeVisitor` 编写一个程序，找出 Python 源文件中所有的 `import` 语句，输出导入的模块名。

**要求：**
- 支持 `import os` 和 `from os import path` 两种形式
- 输出格式：`行号: import 模块名`

**测试代码：**
```python
import os
import sys
from pathlib import Path
from collections import defaultdict
import json as j
```

### 练习 2：提取所有函数签名
编写一个函数，输入 Python 源代码字符串，返回所有函数的签名信息（函数名 + 参数列表）。

**要求：**
- 使用 `ast.parse()` 解析代码
- 支持默认参数值的提取
- 返回格式：`[("函数名", ["参数1", "参数2=默认值"])]`

### 练习 3：统计代码行数
用 AST 统计一个 Python 文件中：
- 函数定义数量
- 类定义数量
- 总语句数（不计空行和注释）

---

## 🚀 进阶挑战题

### 挑战 1：实现 dead code 检测
编写一个 Linter 规则，检测函数中定义了但从未使用的局部变量。

**提示：**
- 用 `ScopeAnalyzer` 的思路
- 遍历函数体，收集赋值和引用
- 找出有定义但无引用的变量

### 挑战 2：自动生成文档字符串
编写一个 AST 变换器，自动给没有 docstring 的函数生成基于函数名和参数的文档模板。

**示例输出：**
```python
def calculate_discount(price, rate):
    """
    Calculate discount.

    Args:
        price: Price value
        rate: Discount rate
    """
    return price * rate
```

### 挑战 3：实现 SQL 注入检测
用 AST 分析代码，检测字符串拼接中是否可能包含 SQL 注入风险。

**检测模式：**
```python
# 危险模式：字符串拼接构造 SQL
query = "SELECT * FROM users WHERE name = '" + user_input + "'"

# 安全模式：参数化查询
query = "SELECT * FROM users WHERE name = %s"
cursor.execute(query, (user_input,))
```

### 挑战 4：构建代码复杂度报告工具
综合运用所学知识，构建一个可以输出 Markdown 格式报告的代码分析工具，包含：
- 函数复杂度排名
- 未使用变量列表
- 命名规范检查结果
- 代码行数统计

---

## 💡 思考题

1. 如果要分析一个 10 万行的项目，AST 分析和正则表达式分析哪个更高效？为什么？

2. `ast.literal_eval` 为什么不支持表达式？设计一个安全的表达式求值器需要考虑哪些因素？

3. 如何让自定义 Linter 支持 `.lintrc` 配置文件来启用/禁用规则？设计一个简单的插件架构。

4. AST 变换时，`fix_missing_locations()` 到底修复了什么？如果省略会报什么错？

5. 如果要实现一个 Python 到 JavaScript 的代码翻译器，AST 可以扮演什么角色？
