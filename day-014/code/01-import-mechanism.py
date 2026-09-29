"""
Day 014 - 01: import 机制深度演示
==================================
展示 sys.path、sys.modules 缓存、import 查找过程和标准写法。
可直接运行：python3 01-import-mechanism.py
"""

import sys
import os


# ============================================================
# 1. 查看系统模块搜索路径
# ============================================================
print("=" * 70)
print("1️⃣  sys.path —— 模块搜索路径")
print("=" * 70)

for i, path in enumerate(sys.path, 1):
    print(f"  {i}. {path}")

print()
print(f"  📍 sys.path[0]（脚本目录）: {sys.path[0]}")
print(f"  📍 当前工作目录: {os.getcwd()}")


# ============================================================
# 2. 模块缓存（sys.modules）
# ============================================================
print("\n" + "=" * 70)
print("2️⃣  sys.modules —— 模块缓存机制")
print("=" * 70)

# 查看一些基础模块是否已加载
builtin_modules = ['sys', 'os', 'math', 'json', 're']
for name in builtin_modules:
    loaded = name in sys.modules
    print(f"  {'✅' if loaded else '⬜'} {name}: {'已加载' if loaded else '未加载'}")

print(f"\n  已加载模块总数: {len(sys.modules)}")
print(f"  前 10 个模块名: {list(sys.modules.keys())[:10]}")


# ============================================================
# 3. 演示缓存的效果
# ============================================================
print("\n" + "=" * 70)
print("3️⃣  缓存效果演示 —— 两次导入同一模块")
print("=" * 70)

# 第一次导入 json
print("\n  第 1 次导入 json...")
import json
print(f"  sys.modules 中有 'json': {'json' in sys.modules}")

# 第二次导入 json —— 完全使用缓存
print("\n  第 2 次导入 json（应该瞬间完成）...")
import json
print(f"  两次导入是同一个对象: {sys.modules['json'] is json}")

# 获取 json 的元信息
json_module = sys.modules['json']
print(f"  json.__name__: {json_module.__name__}")
print(f"  json.__file__: {json_module.__file__}")


# ============================================================
# 4. import 的六种写法
# ============================================================
print("\n" + "=" * 70)
print("4️⃣  import 的六种写法")
print("=" * 70)

# 写法 1：导入整个模块
print("\n  写法 1：import math")
import math
result = math.sqrt(16)
print(f"    math.sqrt(16) = {result}")

# 写法 2：导入特定名称
print("\n  写法 2：from math import pi")
from math import pi
print(f"    pi = {pi}")

# 写法 3：导入多个名称
print("\n  写法 3：from math import sqrt, sin, cos")
from math import sqrt, sin, cos
print(f"    sin(pi/2) = {sin(pi/2):.1f}")
print(f"    cos(pi)   = {cos(pi):.1f}")

# 写法 4：起别名
print("\n  写法 4：import module as alias")
import math as m
print(f"    m.sqrt(25) = {m.sqrt(25)}")

from math import floor as int_part
print(f"    floor(3.14) = {int_part(3.14)}")

# 写法 5：在所有公开名称（谨慎使用）
print("\n  写法 5：from math import *")
from math import *
print(f"    log(e)  = {log(e):.4f}")  # log, e 都来自 math
print(f"    ceil(3.14) = {ceil(3.14)}")

# 写法 6：函数内延迟导入
print("\n  写法 6：函数内延迟导入")


def lazy_import_demo():
    """在函数内部导入模块 —— 函数调用时才加载"""
    import random       # 这个导入只在此函数中可见
    return random.randint(1, 100)


print(f"    lazy_import_demo() = {lazy_import_demo()}")


# ============================================================
# 5. 动态添加搜索路径
# ============================================================
print("\n" + "=" * 70)
print("5️⃣  动态修改 sys.path")
print("=" * 70)

# 创建一个临时模块
tmp_dir = "/tmp/custom_pylib"
os.makedirs(tmp_dir, exist_ok=True)

tmp_module_path = os.path.join(tmp_dir, "myhelper.py")
with open(tmp_module_path, "w") as f:
    f.write('''"""
myhelper - 动态创建的测试模块
"""
VERSION = "0.1.0"

def greet(name):
    return f"你好，{name}！"

def add(a, b):
    return a + b

PI = 3.14159
''')

print(f"  📝 创建临时模块: {tmp_module_path}")

# 在导入前，先检查 sys.path 是否包含 tmp_dir
before = tmp_dir in sys.path
print(f"  添加前 tmp_dir 在 sys.path 中: {before}")

# 动态添加路径
sys.path.insert(0, tmp_dir)
print(f"  添加后 tmp_dir 在 sys.path[0]: {sys.path[0] == tmp_dir}")

# 现在可以导入了
import myhelper
print(f"  成功导入 myhelper（VERSION = {myhelper.VERSION}）")
print(f"  myhelper.greet('Python') = {myhelper.greet('Python')}")
print(f"  myhelper.add(10, 20) = {myhelper.add(10, 20)}")
print(f"  myhelper.PI = {myhelper.PI}")

# 查看缓存
print(f"  sys.modules 中的 myhelper: {sys.modules['myhelper']}")

# 清理
sys.path.remove(tmp_dir)
del sys.modules['myhelper']


# ============================================================
# 6. 条件导入 —— 跨平台
# ============================================================
print("\n" + "=" * 70)
print("6️⃣  条件导入（跨平台兼容）")
print("=" * 70)

if sys.platform.startswith('win'):
    print("  🪟 Windows 平台")
    # import msvcrt
else:
    print(f"  🐧 Unix/Linux 平台（当前: {sys.platform}）")
    # import termios


# ============================================================
# 7. 模块的属性
# ============================================================
print("\n" + "=" * 70)
print("7️⃣  模块对象的属性和方法")
print("=" * 70)

# 模块是对象 —— 可以查看其属性
print(f"\n  math 模块的属性列表（前 10 个）:")
math_attrs = [a for a in dir(math) if not a.startswith('_')]
for name in math_attrs[:10]:
    print(f"    {name}")

print(f"  ... 共 {len(math_attrs)} 个公开属性")

# 模块的 __dict__ —— 就是它的命名空间
print(f"\n  math.__dict__ 的类型: {type(math.__dict__)}")
print(f"  math.__dict__ 的大小: {len(math.__dict__)} 项")
print(f"  math.__dict__['pi'] = {math.__dict__['pi']}")

# 查看模块元数据
print(f"\n  os.__name__: {os.__name__}")
print(f"  os.__file__: {os.__file__}")
print(f"  os.__doc__[:50]: {os.__doc__[:50] if os.__doc__ else 'None'}...")


# ============================================================
# 8. 使用 importlib 手动加载模块
# ============================================================
print("\n" + "=" * 70)
print("8️⃣  importlib —— 手动控制模块加载")
print("=" * 70)

import importlib
import importlib.util

# 检查模块是否存在
spec = importlib.util.find_spec("math")
print(f"  math 模块的 spec: {spec}")
print(f"  math 的 origin: {spec.origin}")

# 检查不存在的模块
spec = importlib.util.find_spec("non_existent_module_xyz")
print(f"  不存在的模块 spec: {spec}")

# 演示 inspect 查看模块
import inspect
# math 是内置模块，getfile 会失败，用 os 替代
print(f"\n  inspect.getfile(os): {inspect.getfile(os)}")
print(f"  inspect.getsource(math.sqrt):")
try:
    print(inspect.getsource(math.sqrt))
except (OSError, TypeError):
    print("    （math.sqrt 是内置 C 函数，无法获取源代码）")


# ============================================================
# 9. 总结：完整的 import 流程
# ============================================================
print("\n" + "=" * 70)
print("📚 总结：Python import 流程")
print("=" * 70)
print("""
当执行 import mymodule 时，Python 执行以下步骤：

1️⃣  在 sys.modules 中查找 'mymodule'
    ├── 找到 → ✅ 直接返回缓存（不重复执行模块代码）
    └── 未找到 → 继续下一步

2️⃣  在 sys.path 中按顺序遍历每个路径
    ├── 找到 mymodule.py → 使用
    ├── 找到 mymodule/ → 作为包使用
    └── 全部未找到 → ❌ ModuleNotFoundError

3️⃣  编译源文件为字节码（.pyc）
    ├── 检查 __pycache__/ 中是否有 .pyc 且版本/时间戳匹配
    ├── 匹配 → 跳过编译，直接加载字节码
    └── 不匹配 → 重新编译并写入 __pycache__/

4️⃣  创建新的 module 对象
    ├── 在模块命名空间中执行源代码
    ├── 定义的所有变量/函数/类都存入该命名空间
    └── 模块的 __dict__ 就是该命名空间

5️⃣  将模块存入 sys.modules 缓存
    └── 确保同模块只被导入一次

6️⃣  将模块名绑定到当前作用域
    ├── import mymodule → mymodule 变量指向模块对象
    └── from mymodule import func → func 指向模块中的函数对象
""")


# 当直接运行时执行测试
if __name__ == '__main__':
    print("\n✅ 01-import-mechanism.py 运行完成！")
