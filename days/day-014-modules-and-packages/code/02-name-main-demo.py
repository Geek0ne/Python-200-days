"""
Day 014 - 02: __name__ == '__main__' 深度演示
===============================================
展示 __name__ 变量的运行时赋值原理，及其在直接运行 vs 导入时的行为差异。
可直接运行：python3 02-name-main-demo.py
"""

import sys


# ============================================================
# 1. 最基础的 __name__ 演示
# ============================================================
print("=" * 70)
print("1️⃣  当前模块的 __name__ 值")
print("=" * 70)

print(f"\n  当前 __name__ = '{__name__}'")
print(f"  当前 __file__ = '{__file__}'")

# __name__ 的值决定了这是直接运行还是被导入
if __name__ == '__main__':
    print(f"\n  🟢 当前模块是【直接运行】的（python3 {__file__}）")
else:
    print("\n  🔵 当前模块是【被导入】的（import 语句触发）")

print(f"\n  当前模块的 __package__ = '{__package__}'")


# ============================================================
# 2. 查看其他模块的 __name__
# ============================================================
print("\n" + "=" * 70)
print("2️⃣  其他模块的 __name__ 值")
print("=" * 70)

import math
import os
import json
import re
import datetime

modules_to_check = [math, os, json, re, datetime, sys]
for mod in modules_to_check:
    print(f"  {mod.__name__:20s} __name__ = '{mod.__name__}'")


# ============================================================
# 3. __name__ 的设计原理
# ============================================================
print("\n" + "=" * 70)
print("3️⃣  __name__ 的设计原理")
print("=" * 70)

print("""
  为什么需要 __name__ 机制？
  ────────────────────────────
  
  在 C 或 Java 中，程序的入口由 main() 函数明确指定：
  int main() { ... }          ← 编译器知道这是入口
  
  但在 Python 中，脚本从第一行开始顺序执行，没有"入口函数"的概念。
  
  问题：一个 .py 文件既可以作为脚本直接运行，也可以作为模块被导入。
  如果模块中有测试代码，在导入时也会执行 —— 这不合理。
  
  解决方案：引入运行时变量 __name__
  ┌───────────────────────────────────────────────┐
  │                                                │
  │  python3 script.py    →  __name__ = '__main__'  │
  │                                                │
  │  import script        →  __name__ = 'script'    │
  │                                                │
  └───────────────────────────────────────────────┘
  
  这样，通过检查 __name__ 的值，代码就能判断自己是
  被直接运行还是被导入，从而决定是否执行测试代码。
""")


# ============================================================
# 4. 模拟：直接运行时的执行流程
# ============================================================
print("=" * 70)
print("4️⃣  模拟模块的两种执行场景")
print("=" * 70)


def demo_functionality():
    """模块的核心功能 —— 不管运行方式如何都执行"""
    print("  📦 执行模块核心功能...")
    return "模块功能已加载"


def demo_self_test():
    """模块的自测试代码 —— 只在直接运行时执行"""
    print("  🧪 执行自测试...")
    # 简单冒烟测试
    assert demo_functionality() is not None
    print("  ✅ 自测试通过！")
    return True


def show_usage():
    """交互式演示"""
    print("\n  📖 模块使用说明：")
    print("  ──────────────")
    print("  import name_main_demo")
    print("  name_main_demo.demo_functionality()")


# 不管运行方式，核心功能总是执行
module_data = {
    'name': 'name_main_demo',
    'version': '1.0.0',
    'features': ['__name__ 检测', '运行模式判断']
}


# ============================================================
# 5. __name__ 的 5 种常见用法模式
# ============================================================
print("\n" + "=" * 70)
print("5️⃣  __name__ == '__main__' 的 5 种常见模式")
print("=" * 70)

print("""
  模式 1️⃣  简单测试
  ┌─────────────────────────────────────┐
  │ if __name__ == '__main__':          │
  │     assert add(2, 3) == 5          │
  │     print('✅ 测试通过')            │
  └─────────────────────────────────────┘

  模式 2️⃣  主函数模式
  ┌─────────────────────────────────────┐
  │ def main():                         │
  │     # 程序逻辑                      │
  │     pass                            │
  │                                     │
  │ if __name__ == '__main__':          │
  │     main()                          │
  └─────────────────────────────────────┘

  模式 3️⃣  命令行参数处理
  ┌─────────────────────────────────────┐
  │ if __name__ == '__main__':          │
  │     import sys                      │
  │     if len(sys.argv) > 1:           │
  │         # 处理 sys.argv[1:]         │
  │     else:                           │
  │         # 交互模式                  │
  └─────────────────────────────────────┘

  模式 4️⃣  自动运行单元测试
  ┌─────────────────────────────────────┐
  │ if __name__ == '__main__':          │
  │     import unittest                 │
  │     unittest.main()                 │
  └─────────────────────────────────────┘

  模式 5️⃣  性能基准测试
  ┌─────────────────────────────────────┐
  │ if __name__ == '__main__':          │
  │     import timeit                   │
  │     t = timeit.timeit(stmt, ...)    │
  │     print(f'耗时: {t}秒')           │
  └─────────────────────────────────────┘
""")


# ============================================================
# 6. 主函数模式演示
# ============================================================
def main():
    """作为主程序运行的入口函数"""
    print("\n" + "=" * 70)
    print("🟢  主函数模式 —— main() 正在执行")
    print("=" * 70)

    print(f"\n  模块名称: {__name__}")
    print(f"  文件路径: {__file__}")

    # 演示命令行参数
    if len(sys.argv) > 1:
        print(f"\n  接收到 {len(sys.argv) - 1} 个命令行参数:")
        for i, arg in enumerate(sys.argv[1:], 1):
            print(f"    参数 {i}: {arg}")
    else:
        print("\n  无命令行参数（直接运行）")

    # 执行核心功能
    print(f"\n  模块数据: {module_data}")
    result = demo_functionality()
    print(f"  返回: {result}")

    # 运行测试
    demo_self_test()

    # 显示用法
    show_usage()

    print("\n" + "=" * 70)
    print("✅ 程序执行完毕")
    print("=" * 70)


# ============================================================
# 7. __name__ 的实际使用场景
# ============================================================
print("\n" + "=" * 70)
print("6️⃣  __name__ 在大型项目中的应用")
print("=" * 70)

print("""
  📁 项目结构中使用 __name__：
  
  project/
  ├── main.py              ← 入口文件（__name__ = '__main__'）
  │     if __name__ == '__main__':
  │         app.run()
  │
  ├── utils/
  │   ├── __init__.py
  │   ├── database.py      ← 模块（__name__ = 'utils.database'）
  │   │     if __name__ == '__main__':
  │   │         # 数据库连接测试
  │   │
  │   └── helpers.py       ← 模块（__name__ = 'utils.helpers'）
  │
  └── tests/
      └── test_helpers.py  ← 测试文件（__name__ = '__main__'）
  
  💡 每个模块都可以独立测试！
  任何时候在模块文件中：
    python3 utils/database.py
  就会运行该模块的自测试代码。
""")


# ============================================================
# 8. 不可被导入的模块特征
# ============================================================
print("\n" + "=" * 70)
print("7️⃣  区别对待：直接运行 vs 被导入")
print("=" * 70)


def is_direct_run():
    """判断当前模块是否被直接运行"""
    return __name__ == '__main__'


print(f"\n  当前模块被直接运行: {is_direct_run()}")
print(f"  如果这个模块被 import，is_direct_run() 会返回 False")


# 演示：如果被导入时的行为差异
# 如果直接运行，才打印这个
if __name__ == '__main__':
    print("  🔔 这条消息只会在直接运行时显示！")
    print("  如果 import 这个模块，上面的消息不会出现。")

# 如果被导入，会自动执行这个函数
print("  📌 这条消息不管怎样都会显示（不在 if 块内）")


# ============================================================
# 9. 实用工具函数
# ============================================================
def get_current_module_info():
    """返回当前模块的详细信息"""
    return {
        'name': __name__,
        'file': __file__,
        'is_main': __name__ == '__main__',
        'package': __package__,
        'python_version': sys.version,
        'argv': sys.argv,
    }


if __name__ == '__main__':
    # 显示模块信息
    info = get_current_module_info()
    print(f"\n📋 当前模块信息:")
    for key, value in info.items():
        print(f"  {key:15s}: {value}")

    # 执行主函数
    main()


# ============================================================
# 10. 补充：__name__ 的底层机制
# ============================================================
# 这个代码块在任何模式下都会执行 👇

print("=" * 70)
print("🔧 __name__ 的底层赋值机制")
print("=" * 70)

print("""
  Python 解释器在执行模块时，其底层实现大致如下（伪代码）：
  
  def execute_module(file_path, is_main=False):
      # 创建模块对象
      module = ModuleType()
      
      if is_main:
          module.__name__ = '__main__'
          module.__file__ = file_path
          # 执行模块代码
          exec(compile(file_path), module.__dict__)
      else:
          module_name = derive_name_from_path(file_path)
          module.__name__ = module_name
          module.__file__ = file_path
          module.__package__ = derive_package(module_name)
          # 执行模块代码
          exec(compile(file_path), module.__dict__)
      
      return module
  
  # 执行入口文件时
  if __name__ == '__main__':
      execute_module('script.py', is_main=True)  # → __name__ = '__main__'
  
  # 导入时
  import script
  # → execute_module('script.py', is_main=False)  # → __name__ = 'script'
""")
