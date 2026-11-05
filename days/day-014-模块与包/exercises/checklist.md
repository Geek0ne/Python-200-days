# 检查清单与练习题

> Day 014: 模块与包

---

## ✅ 今日完成清单

### 模块基础
- [ ] 理解模块的概念 —— 每个 `.py` 文件就是一个模块
- [ ] 理解模块即对象 —— `module` 类型及其属性（`__name__`, `__file__`, `__dict__`）
- [ ] 掌握 import 的四种写法：`import`, `from...import`, `as` 别名, `import *`
- [ ] 理解 `sys.path` 的构成（脚本目录 → PYTHONPATH → 标准库 → site-packages）
- [ ] 理解模块搜索顺序及查找机制

### 模块缓存
- [ ] 理解 `sys.modules` 的作用 —— 避免重复加载
- [ ] 掌握 `importlib.reload()` 的用法
- [ ] 理解同模块多次导入只执行一次的原理

### __name__ == '__main__' 原理
- [ ] 理解 `__name__` 的运行时赋值机制
- [ ] 掌握 `if __name__ == '__main__':` 的 5 种常见模式
- [ ] 理解直接运行（`python3 xx.py`）与导入（`import xx`）的行为差异
- [ ] 理解为什么需要这种机制（Python 没有入口函数关键字）

### 包结构
- [ ] 理解包的概念 —— 包含 `__init__.py` 的目录
- [ ] 掌握 `__init__.py` 的五大作用
- [ ] 理解包级 `__all__` 的控制作用
- [ ] 理解命名空间包（Python 3.3+）

### 相对导入与绝对导入
- [ ] 掌握绝对导入的写法
- [ ] 掌握相对导入的写法（`.`, `..`, `...`）
- [ ] 理解相对导入不能在 `__main__` 中使用的限制
- [ ] 理解 PEP 8 推荐优先使用绝对导入

### __pycache__ 与字节码
- [ ] 理解 `__pycache__` 的作用和命名规则
- [ ] 理解 `.pyc` 文件的版本和时间戳验证机制
- [ ] 了解 `-B` 选项和 `PYTHONDONTWRITEBYTECODE`

### 实战
- [ ] 理解 strutils 和 mathutils 工具包的设计
- [ ] 理解相对导入在包内部的使用
- [ ] 理解包级重导出（`__init__.py` 中的 import）

### 避坑
- [ ] 理解循环导入问题及两种解决方案
- [ ] 理解相对导入在 __main__ 中失效的原因
- [ ] 理解 `import *` 的命名覆盖风险
- [ ] 理解 `.gitignore` 中应包含 `__pycache__/`

---

## 📝 练习题

### 练习 1：编写一个可重用的倒计时模块

编写一个模块 `countdown.py`，提供以下功能：

- `countdown(n)`：从 n 倒数到 1，每秒打印一个数字（提示：使用 `time.sleep(1)`）
- `countdown_str(n)`：返回倒计时字符串列表 `['3', '2', '1', 'Go!']`
- 模块包含 `__all__`，只公开这两个函数
- 模块中包含自测试代码（`if __name__ == '__main__':`），演示 5 秒倒计时

```python
# 期望用法
from countdown import countdown, countdown_str

print(countdown_str(3))   # → ['3', '2', '1', 'Go!']
# countdown(5)            # → 5... 4... 3... 2... 1... Go!（每秒打印）
```

**进阶要求**：在另一个文件中 `import countdown`，验证自测试代码不被执行。

---

### 练习 2：创建一个科学计算包

创建一个 `scicalc/` 包，包含以下结构：

```
scicalc/
├── __init__.py
├── arithmetic.py     ← 基础运算（add, subtract, multiply, divide）
├── geometry.py       ← 几何计算（circle_area, rectangle_area, triangle_area）
└── statistics.py     ← 统计计算（mean, median, variance）
```

要求：
- `__init__.py` 中重导出所有公开函数
- `statistics.py` 使用相对导入引入 `arithmetic.py` 中的 `divide` 函数（用于计算均值）
- 每个子模块包含 `__all__` 控制
- 编写一个 `main.py` 使用该包

---

### 练习 3：排查循环导入

给定以下两个模块：

```python
# employee.py
from department import get_department_name

class Employee:
    def __init__(self, name, dept_id):
        self.name = name
        self.dept_id = dept_id
    
    def info(self):
        return f"{self.name} 属于 {get_department_name(self.dept_id)}"

# department.py
from employee import Employee

class Department:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.employees = []
    
    def add_employee(self, name):
        emp = Employee(name, self.id)
        self.employees.append(emp)
        return emp

def get_department_name(dept_id):
    names = {1: "工程部", 2: "市场部", 3: "财务部"}
    return names.get(dept_id, "未知")
```

要求：
1. 运行代码，观察发生的错误类型
2. 使用 **延迟导入** 修复循环导入问题
3. 使用 **提取公共模块** 的方式重构（提示：将 `get_department_name` 移到新文件）

---

### 练习 4：实现一个插件发现系统

编写一个模块 `plugin_loader.py`，能够：
1. 扫描 `plugins/` 目录下的所有 `.py` 文件
2. 动态导入每个模块
3. 检查每个模块是否有一个 `run()` 函数
4. 收集所有有效的 `run()` 函数并执行

```python
# plugins/hello.py
def run():
    print("Hello Plugin!")

# plugins/calculator.py
def run():
    print("Calculator Plugin: 2 + 3 = 5")

# plugin_loader.py 的期望行为
# python3 plugin_loader.py
# → 发现 2 个插件
# → 运行 hello.run() → "Hello Plugin!"
# → 运行 calculator.run() → "Calculator Plugin: 2 + 3 = 5"
```

**提示**：使用 `importlib`、`os.listdir()`、动态 `import()` 或 `__import__()`。

---

### 练习 5：调试 __pycache__ 异常

描述以下场景中可能发生的问题，并给出解决方案：

**场景 A**：团队项目中，Alice 用 Python 3.11 运行了模块，生成了 `__pycache__/`。Bob 用 Python 3.12 运行时遇到了一个奇怪的错误。错误原因是什么？如何修复？

**场景 B**：部署到服务器时，运维人员删除了所有 `.py` 文件但保留了 `__pycache__/`。这会导致什么问题？

**场景 C**：一个模块被两种不同的路径导入（例如通过 `sys.path` 中的两个等效路径），导致模块被加载两次，状态不一致。这是为什么？如何解决？

---

## 📊 自我评估

| 知识点 | 理解程度 (1-5) | 备注 |
|--------|---------------|------|
| import 四种写法 | ⚪⚪⚪⚪⚪ | |
| sys.path 搜索路径 | ⚪⚪⚪⚪⚪ | |
| sys.modules 缓存 | ⚪⚪⚪⚪⚪ | |
| __name__ == '__main__' | ⚪⚪⚪⚪⚪ | |
| 包与 __init__.py | ⚪⚪⚪⚪⚪ | |
| 绝对导入 | ⚪⚪⚪⚪⚪ | |
| 相对导入 | ⚪⚪⚪⚪⚪ | |
| __all__ 控制 | ⚪⚪⚪⚪⚪ | |
| __pycache__ 字节码 | ⚪⚪⚪⚪⚪ | |
| 循环导入排查 | ⚪⚪⚪⚪⚪ | |
| 实战：工具包构建 | ⚪⚪⚪⚪⚪ | |

> 😊 完成练习题后，标记检查清单的对应项，并在自我评估中打分。
