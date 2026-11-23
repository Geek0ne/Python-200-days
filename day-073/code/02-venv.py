"""
Day 073 — 虚拟环境原理与实践
运行方式：python 02-venv.py
"""
import sys
import os
import subprocess
import tempfile


def main():
    # ========== 1. 虚拟环境原理 ==========
    print("=" * 60)
    print("🔍 虚拟环境原理")
    print("=" * 60)

    explanation = """
    虚拟环境本质上是：
    1. 复制了一份 Python 解释器（或创建符号链接）
    2. 创建了独立的 site-packages 目录
    3. 修改了 PATH 环境变量

    目录结构：
    myenv/
    ├── bin/              # Linux/macOS
    │   ├── python        # Python 解释器（符号链接或复制）
    │   ├── pip           # pip 命令
    │   ├── activate      # 激活脚本
    │   └── ...
    ├── Scripts/          # Windows
    │   ├── python.exe
    │   ├── pip.exe
    │   ├── activate.bat
    │   └── ...
    ├── lib/
    │   └── python3.x/
    │       └── site-packages/  # 安装的包在这里
    └── pyvenv.cfg        # 环境配置
    """
    print(explanation)

    # ========== 2. 创建和使用虚拟环境 ==========
    print("=" * 60)
    print("📝 创建和使用虚拟环境")
    print("=" * 60)

    print("""
    步骤1：创建虚拟环境
    $ python -m venv myenv

    步骤2：激活虚拟环境
    # Linux/macOS:
    $ source myenv/bin/activate

    # Windows:
    $ myenv\\Scripts\\activate

    步骤3：验证环境
    (myenv) $ which python
    /path/to/myenv/bin/python

    (myenv) $ python --version
    Python 3.x.x

    步骤4：安装包
    (myenv) $ pip install requests

    步骤5：退出环境
    (myenv) $ deactivate
    """)

    # ========== 3. 查看当前环境信息 ==========
    print("=" * 60)
    print("📊 当前环境信息")
    print("=" * 66)

    print(f"Python 版本: {sys.version}")
    print(f"Python 路径: {sys.executable}")
    print(f"平台: {sys.platform}")
    print()

    # 检查是否在虚拟环境中
    if hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    ):
        print("✅ 当前在虚拟环境中")
        print(f"  虚拟环境路径: {sys.prefix}")
        print(f"  系统 Python 路径: {sys.base_prefix}")
    else:
        print("⚠️ 当前不在虚拟环境中")
        print(f"  系统 Python 路径: {sys.prefix}")

    print()

    # ========== 4. venv 命令行操作 ==========
    print("=" * 60)
    print("🖥️ venv 命令行操作")
    print("=" * 60)

    print("""
    创建环境：
    $ python -m venv myenv                    # 基本创建
    $ python -m venv --clear myenv            # 清除重新创建
    $ python -m venv --system-site-packages myenv  # 继承系统包
    $ python -m venv --prompt "(myenv)" myenv # 自定义提示符

    激活环境：
    $ source myenv/bin/activate               # Linux/macOS
    $ myenv\\Scripts\\activate                # Windows
    $ . myenv/bin/activate.fish              # Fish shell

    退出环境：
    $ deactivate

    查看环境：
    $ which python                            # 查看 Python 路径
    $ pip list                                # 查看安装的包
    $ pip freeze                              # 导出依赖
    """)

    # ========== 5. conda 环境 ==========
    print("=" * 60)
    print("🐍 conda 环境")
    print("=" * 60)

    print("""
    conda 是 Anaconda/Miniconda 的包管理器
    特点：可以管理非 Python 包（如 CUDA、MKL）

    创建环境：
    $ conda create -n myenv python=3.11       # 指定 Python 版本
    $ conda create -n myenv numpy pandas      # 创建并安装包

    激活环境：
    $ conda activate myenv

    安装包：
    $ conda install numpy                     # 用 conda 安装
    $ pip install requests                    # 也可以用 pip

    导出环境：
    $ conda env export > environment.yml

    从文件创建：
    $ conda env create -f environment.yml

    查看所有环境：
    $ conda env list

    删除环境：
    $ conda env remove -n myenv
    """)

    # ========== 6. venv vs conda 对比 ==========
    print("=" * 60)
    print("📊 venv vs conda 对比")
    print("=" * 60)

    comparison = """
    ┌─────────────────┬──────────────────┬──────────────────┐
    │ 特性            │ venv             │ conda            │
    ├─────────────────┼──────────────────┼──────────────────┤
    │ Python 版本     │ 需要预先安装      │ 可以安装任意版本  │
    │ 非 Python 包    │ ❌ 不支持         │ ✅ 支持          │
    │ 速度            │ 快               │ 较慢             │
    │ 磁盘占用        │ 小               │ 大               │
    │ 跨平台          │ ✅               │ ✅               │
    │ 推荐场景        │ 纯 Python 项目   │ 数据科学/机器学习 │
    └─────────────────┴──────────────────┴──────────────────┘
    """
    print(comparison)

    # ========== 7. 实用脚本 ==========
    print("=" * 60)
    print("🔧 实用脚本：环境管理器")
    print("=" * 60)

    # 创建一个简单的环境管理脚本示例
    script_example = '''
#!/bin/bash
# env-manager.sh - 简单的环境管理脚本

# 创建环境
create_env() {
    local env_name=$1
    local python_version=${2:-python3}

    echo "创建虚拟环境: $env_name"
    $python_version -m venv $env_name

    echo "激活环境..."
    source $env_name/bin/activate

    echo "升级 pip..."
    pip install --upgrade pip

    echo "环境创建完成！"
    echo "使用 'source $env_name/bin/activate' 激活"
}

# 删除环境
remove_env() {
    local env_name=$1

    if [ -d "$env_name" ]; then
        echo "删除虚拟环境: $env_name"
        rm -rf $env_name
        echo "已删除"
    else
        echo "环境不存在: $env_name"
    fi
}

# 列出环境
list_envs() {
    echo "已创建的虚拟环境："
    ls -d */ 2>/dev/null | grep -v __pycache__
}

# 主函数
case $1 in
    create)
        create_env $2 $3
        ;;
    remove)
        remove_env $2
        ;;
    list)
        list_envs
        ;;
    *)
        echo "用法: $0 {create|remove|list} [环境名]"
        ;;
esac
'''
    print("示例脚本 (env-manager.sh):")
    print(script_example)

    print("\n💡 使用建议：")
    print("1. 每个项目都创建虚拟环境")
    print("2. 虚拟环境目录加入 .gitignore")
    print("3. 定期清理不用的虚拟环境")
    print("4. 纯 Python 项目用 venv，数据科学用 conda")


if __name__ == '__main__':
    main()
