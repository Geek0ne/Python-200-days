# Day 098 - 学习笔记

## 关键收获

1. **字节码不是黑盒**：通过 `dis` 模块可以完全窥探 Python 的执行过程
2. **一切皆对象**：CPython 中所有数据都是 PyObject，包括类型本身
3. **引用计数为主，GC 为辅**：CPython 的内存管理策略
4. **栈帧是执行的原子单元**：每次函数调用都创建新的栈帧

## 常用命令速查

```python
# 反汇编
import dis
dis.dis(func)

# 查看代码对象
func.__code__.co_consts    # 常量池
func.__code__.co_varnames  # 变量名
func.__code__.co_code      # 原始字节码

# 引用计数
import sys
sys.getrefcount(obj)

# 垃圾回收
import gc
gc.get_stats()
gc.collect()

# 内存大小
import sys
sys.getsizeof(obj)
```

## 明日预习

Day 099 将学习 Python 扩展（Cython、Pybind11），了解如何用 C/C++ 扩展 Python 的性能。
