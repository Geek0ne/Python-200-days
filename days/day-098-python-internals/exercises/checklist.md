# Day 098 - Python 内部机制 - 练习与检查表

## ✅ 今日学习完成清单

- [ ] 理解 Python 字节码的概念和作用
- [ ] 掌握 `dis` 模块的基本使用
- [ ] 理解 Code Object 的结构和属性
- [ ] 掌握值栈（Value Stack）的执行模型
- [ ] 理解 CPython 虚拟机的栈帧结构
- [ ] 掌握引用计数机制
- [ ] 理解分代垃圾回收的工作原理
- [ ] 了解 PyObject 的内存布局
- [ ] 了解三级内存分配器
- [ ] 完成字节码分析器实战项目

---

## 📝 基础练习题

### 练习 1: 反汇编分析

使用 `dis` 模块反汇编以下函数，分析每条指令的作用：

```python
def mystery(n):
    result = 0
    for i in range(n):
        if i % 2 == 0:
            result += i
        else:
            result -= i
    return result
```

**要求：**
1. 反汇编该函数
2. 解释每条指令的作用
3. 绘制执行流程图
4. 预测 `mystery(5)` 的返回值

---

### 练习 2: Code Object 分析

分析以下函数的 Code Object：

```python
def analyze_me(x, y=10, *args, **kwargs):
    z = x + y
    for arg in args:
        z += arg
    return z
```

**要求：**
1. 列出 `co_consts` 的内容
2. 列出 `co_varnames` 的内容
3. 解释 `co_flags` 的含义
4. 计算 `co_stacksize` 的最小值

---

### 练习 3: 引用计数实验

预测以下代码的输出，然后运行验证：

```python
import sys

a = []
b = a
c = [a]
del b
print(sys.getrefcount(a))
c.clear()
print(sys.getrefcount(a))
del c
print(sys.getrefcount(a))
```

**要求：**
1. 写出你的预测
2. 解释每次变化的原因
3. 绘制引用关系图

---

### 练习 4: 字节码比较

比较以下两种实现的字节码差异：

```python
# 方式 1: 列表推导式
def method1(n):
    return [x**2 for x in range(n)]

# 方式 2: 普通循环
def method2(n):
    result = []
    for x in range(n):
        result.append(x**2)
    return result
```

**要求：**
1. 反汇编两个函数
2. 比较字节码大小
3. 比较指令数量
4. 分析为什么列表推导式更快

---

## 🚀 进阶练习题

### 练习 5: 字节码修改（高级）

尝试修改函数的字节码，使其返回不同的值：

```python
import dis

def original():
    return 42

def target():
    return 100

# 任务: 修改 original 函数，使其行为与 target 相同
# 提示: 可以尝试修改 co_consts 或 co_code
```

**要求：**
1. 分析两个函数的字节码差异
2. 尝试修改 `original` 的 `co_consts`
3. 验证修改后的函数行为

---

### 练习 6: sys.settrace 实现代码覆盖率

使用 `sys.settrace` 实现一个简单的代码覆盖率工具：

```python
import sys

class CoverageTracker:
    def __init__(self):
        self.covered_lines = set()
        self.total_lines = 0
    
    def trace(self, frame, event, arg):
        # 实现追踪逻辑
        pass
    
    def start(self):
        sys.settrace(self.trace)
    
    def stop(self):
        sys.settrace(None)
    
    def report(self):
        # 输出覆盖率报告
        pass

# 测试
tracker = CoverageTracker()
tracker.start()

def test_function():
    x = 1
    if x > 0:
        print("positive")
    else:
        print("negative")
    return x

test_function()
tracker.stop()
tracker.report()
```

**要求：**
1. 实现 `CoverageTracker` 类
2. 追踪行号执行情况
3. 计算覆盖率百分比
4. 输出详细的覆盖报告

---

### 练习 7: 性能分析工具

扩展字节码分析器，添加以下功能：

```python
class EnhancedAnalyzer:
    def analyze_performance(self, func):
        """分析函数的性能特征"""
        # 1. 统计循环深度
        # 2. 识别热点代码
        # 3. 分析函数调用开销
        # 4. 检测不必要的全局变量访问
        pass
    
    def suggest_optimizations(self, func):
        """提供优化建议"""
        # 根据分析结果，给出具体的优化建议
        pass
```

**要求：**
1. 实现性能分析功能
2. 生成优化建议报告
3. 用实际例子验证建议的有效性

---

### 练习 8: 内存分析器

实现一个内存使用分析器：

```python
class MemoryAnalyzer:
    def __init__(self):
        self.snapshots = []
    
    def take_snapshot(self, label=""):
        """获取当前内存快照"""
        pass
    
    def compare(self, label1, label2):
        """比较两个快照的内存差异"""
        pass
    
    def find_leaks(self):
        """检测可能的内存泄漏"""
        pass
```

**要求：**
1. 使用 `gc.get_objects()` 获取对象列表
2. 统计不同类型对象的数量和大小
3. 检测循环引用
4. 输出内存使用报告

---

## 🏆 挑战题

### 挑战 1: 实现一个简单的字节码虚拟机

```python
class SimpleVM:
    """一个简单的字节码虚拟机"""
    
    def __init__(self):
        self.stack = []
        self.variables = {}
    
    def execute(self, bytecode):
        """执行字节码"""
        # 实现基本的字节码执行
        # 支持: PUSH, POP, ADD, SUB, LOAD, STORE, PRINT
        pass
```

**要求：**
1. 实现基本的栈操作
2. 支持算术运算
3. 支持变量存储
4. 支持条件跳转

---

### 挑战 2: 实现一个字节码优化器

```python
class BytecodeOptimizer:
    """字节码优化器"""
    
    def optimize(self, code):
        """优化字节码"""
        # 1. 常量折叠: 3 + 4 → 7
        # 2. 死代码消除: 不可达代码
        # 3. 内联小函数
        # 4. 循环展开
        pass
```

**要求：**
1. 实现至少 2 种优化
2. 验证优化前后的等价性
3. 测量优化效果

---

### 挑战 3: 实现一个 Python Profiler

```python
class SimpleProfiler:
    """简单的 Python 性能分析器"""
    
    def __init__(self):
        self.call_stats = {}
    
    def trace_calls(self, frame, event, arg):
        """追踪函数调用"""
        pass
    
    def start(self):
        """开始分析"""
        pass
    
    def stop(self):
        """停止分析"""
        pass
    
    def report(self):
        """输出分析报告"""
        pass
```

**要求：**
1. 统计每个函数的调用次数
2. 统计每个函数的执行时间
3. 统计每个函数的调用者
4. 生成可读的性能报告

---

## 📚 参考资源

- [Python 官方文档 - dis 模块](https://docs.python.org/3/library/dis.html)
- [CPython 源码](https://github.com/python/cpython)
- [Python 字节码指令参考](https://docs.python.org/3/library/dis.html#python-bytecode-instructions)
- [Real Python - Python 字节码](https://realpython.com/learning-paths/python-internals/)

---

## 💡 学习建议

1. **多动手实践**：使用 `dis` 模块分析你写的每一个函数
2. **阅读源码**：尝试阅读 CPython 的 C 源码，理解底层实现
3. **性能意识**：在编写代码时，思考其字节码执行效率
4. **工具使用**：熟练使用 `dis`、`sys`、`gc` 等内置模块
