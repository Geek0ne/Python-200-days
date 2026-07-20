"""
Day 073 — pip 与 requirements.txt
运行方式：python 01-pip-basics.py
"""
import subprocess
import sys
import tempfile
import os


def main():
    # ========== 1. pip 命令演示 ==========
    print("=" * 60)
    print("📦 pip 基础命令演示")
    print("=" * 60)

    # 注意：这些命令在实际环境中执行，这里只演示用法

    print("\n1. 安装包:")
    print("   pip install requests")
    print("   pip install requests==2.28.0")
    print("   pip install 'requests>=2.25,<3.0'")
    print()

    print("2. 升级包:")
    print("   pip install --upgrade requests")
    print()

    print("3. 卸载包:")
    print("   pip uninstall requests")
    print()

    print("4. 查看信息:")
    print("   pip list              # 列出所有包")
    print("   pip show requests     # 查看包详情")
    print("   pip list --outdated   # 查看过期包")
    print()

    print("5. 导出/导入:")
    print("   pip freeze > requirements.txt  # 导出")
    print("   pip install -r requirements.txt  # 导入")
    print()

    # ========== 2. requirements.txt 生成 ==========
    print("=" * 60)
    print("📝 生成 requirements.txt")
    print("=" * 60)

    # 方法1：使用 pip freeze（包含所有依赖）
    print("\n方法1：pip freeze")
    print("   pip freeze > requirements.txt")
    print("   优点：简单直接")
    print("   缺点：包含所有包，包括间接依赖")
    print()

    # 方法2：使用 pipreqs（只包含直接依赖）
    print("方法2：pipreqs")
    print("   pip install pipreqs")
    print("   pipreqs . --force")
    print("   优点：只扫描 import 语句")
    print("   缺点：需要额外安装")
    print()

    # 方法3：手动编写（最精确）
    print("方法3：手动编写")
    print("   创建 requirements.txt，手动列出依赖")
    print("   优点：最精确，可以注释说明")
    print("   缺点：需要手动维护")
    print()

    # ========== 3. 版本号规范 ==========
    print("=" * 60)
    print("🔢 版本号规范")
    print("=" * 60)

    version_rules = """
    语义化版本号：MAJOR.MINOR.PATCH
    │ │ │
    │ │ └── PATCH：bug 修复（向后兼容）
    │ └──── MINOR：新功能（向后兼容）
    └────── MAJOR：破坏性更改

    版本约束符号：
    ├── == 2.28.0    精确匹配
    ├── >= 2.25      大于等于
    ├── <= 3.0       小于等于
    ├── ~= 2.28      兼容版本（>=2.28.0, <2.29.0）
    ├── != 2.28.0    排除版本
    └── >=2.20,<3.0  版本范围

    示例：
    ├── requests==2.28.0        # 生产环境：精确版本
    ├── flask~=2.3              # 开发环境：兼容版本
    └── numpy>=1.20,<2.0        # 范围约束
    """
    print(version_rules)

    # ========== 4. 实际操作示例 ==========
    print("=" * 60)
    print("🔧 实际操作示例")
    print("=" * 60)

    # 创建示例 requirements.txt
    example_requirements = """
# requirements.txt 示例

# 运行时依赖（生产环境）
requests==2.28.0
flask~=2.3
numpy>=1.20,<2.0

# 开发依赖（开发环境）
# pytest>=7.0
# black>=23.0
# mypy>=1.0

# 可选依赖
# pandas>=1.5  # 数据处理
# sqlalchemy>=2.0  # 数据库
"""
    print("示例 requirements.txt:")
    print(example_requirements)

    print("使用方式:")
    print("1. 创建虚拟环境: python -m venv venv")
    print("2. 激活环境: source venv/bin/activate")
    print("3. 安装依赖: pip install -r requirements.txt")
    print("4. 开始开发!")
    print()

    # ========== 5. 避坑指南 ==========
    print("=" * 60)
    print("⚠️ 避坑指南")
    print("=" * 60)

    pitfalls = """
    1. 不要在全局环境安装太多包
       → 使用虚拟环境隔离

    2. 不要使用 pip install -r requirements.txt 安装开发依赖
       → 分离运行时和开发依赖

    3. 不要忘记提交 requirements.txt 到 Git
       → 确保团队成员使用相同版本

    4. 不要在 requirements.txt 中使用 * 版本
       → 指定明确的版本范围

    5. 不要忽略锁文件
       → 使用 poetry.lock 或 pdm.lock

    6. 国内用户配置镜像源
       → pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
    """
    print(pitfalls)


if __name__ == '__main__':
    main()
