"""
Day 073 — Poetry 与 PDM 现代包管理
运行方式：python 03-poetry-pdm.py
"""
import os
import subprocess


def main():
    # ========== 1. Poetry 介绍 ==========
    print("=" * 60)
    print("📦 Poetry 介绍")
    print("=" * 60)

    print("""
    Poetry 是现代 Python 包管理工具，功能包括：
    - 依赖管理（精确版本控制）
    - 虚拟环境管理
    - 包构建和发布
    - 锁文件确保可复现

    安装 Poetry：
    $ curl -sSL https://install.python-poetry.org | python3 -
    # 或
    $ pip install poetry

    验证安装：
    $ poetry --version
    """)

    # ========== 2. Poetry 常用命令 ==========
    print("=" * 60)
    print("📝 Poetry 常用命令")
    print("=" * 60)

    print("""
    项目创建：
    $ poetry new my-project              # 创建新项目
    $ cd existing-project
    $ poetry init                        # 初始化已有项目

    依赖管理：
    $ poetry add requests                # 添加运行时依赖
    $ poetry add --group dev pytest      # 添加开发依赖
    $ poetry remove requests             # 移除依赖
    $ poetry show                        # 查看已安装的包
    $ poetry show --tree                 # 查看依赖树

    环境管理：
    $ poetry install                     # 安装所有依赖
    $ poetry update                      # 更新依赖
    $ poetry shell                       # 进入虚拟环境
    $ poetry env info                    # 查看环境信息

    运行命令：
    $ poetry run python main.py          # 在虚拟环境中运行
    $ poetry run pytest                  # 运行测试

    构建发布：
    $ poetry build                       # 构建包
    $ poetry publish --build             # 发布到 PyPI
    """)

    # ========== 3. pyproject.toml 配置 ==========
    print("=" * 60)
    print("⚙️ pyproject.toml 配置")
    print("=" * 60)

    print("""
    # pyproject.toml 示例

    [tool.poetry]
    name = "my-project"
    version = "0.1.0"
    description = "A short description"
    authors = ["Your Name <your@email.com>"]
    readme = "README.md"
    packages = [{include = "my_project"}]

    [tool.poetry.dependencies]
    python = "^3.9"
    requests = "^2.28"
    flask = "^2.3"

    [tool.poetry.group.dev.dependencies]
    pytest = "^7.0"
    black = "^23.0"
    mypy = "^1.0"

    [build-system]
    requires = ["poetry-core"]
    build-backend = "poetry.core.masonry.api"
    """)

    # ========== 4. PDM 介绍 ==========
    print("=" * 60)
    print("🚀 PDM 介绍")
    print("=" * 60)

    print("""
    PDM 是更新的包管理工具，特点：
    - 完全兼容 PEP 标准
    - 更快的速度
    - 支持 PEP 582（不用激活虚拟环境）

    安装 PDM：
    $ pip install pdm

    常用命令：
    $ pdm init                           # 初始化项目
    $ pdm add requests                   # 添加依赖
    $ pdm add -d pytest                  # 添加开发依赖
    $ pdm install                        # 安装依赖
    $ pdm run python main.py             # 运行命令
    $ pdm build                          # 构建包
    $ pdm publish                        # 发布包
    """)

    # ========== 5. Poetry vs PDM 对比 ==========
    print("=" * 60)
    print("📊 Poetry vs PDM 对比")
    print("=" * 60)

    comparison = """
    ┌─────────────────┬──────────────────┬──────────────────┐
    │ 特性            │ Poetry           │ PDM              │
    ├─────────────────┼──────────────────┼──────────────────┤
    │ 速度            │ 快               │ 更快             │
    │ 依赖解析        │ 优秀             │ 优秀             │
    │ PyPA 标准       │ 部分支持         │ 完全支持         │
    │ 插件生态        │ 丰富             │ 成长中           │
    │ 锁文件          │ poetry.lock      │ pdm.lock         │
    │ PEP 582        │ ❌               │ ✅               │
    │ 推荐场景        │ 成熟项目         │ 新项目           │
    └─────────────────┴──────────────────┴──────────────────┘
    """
    print(comparison)

    # ========== 6. 实际操作示例 ==========
    print("=" * 60)
    print("🔧 实际操作示例")
    print("=" * 60)

    print("""
    使用 Poetry 创建项目的完整流程：

    1. 创建项目
    $ poetry new my-project
    $ cd my-project

    2. 添加依赖
    $ poetry add requests
    $ poetry add --group dev pytest black mypy

    3. 编写代码
    $ mkdir -p src/my_project
    $ touch src/my_project/__init__.py

    4. 运行测试
    $ poetry run pytest

    5. 构建包
    $ poetry build

    6. 发布
    $ poetry publish --build
    """)

    # ========== 7. 避坑指南 ==========
    print("=" * 60)
    print("⚠️ 避坑指南")
    print("=" * 60)

    pitfalls = """
    1. 不要混用 Poetry 和 PDM
       → 选择一个工具，整个项目保持一致

    2. 不要手动编辑 pyproject.toml 的依赖部分
       → 使用 poetry add/remove 命令

    3. 不要忘记提交锁文件
       → poetry.lock 或 pdm.lock 要提交到 Git

    4. 不要在全局环境安装 Poetry/PDM
       → 使用 pipx 安装
       $ pipx install poetry
       $ pipx install pdm

    5. 不要忽略 Python 版本
       → 在 pyproject.toml 中指定 requires-python
    """
    print(pitfalls)

    # ========== 8. 推荐工作流 ==========
    print("=" * 60)
    print("📋 推荐工作流")
    print("=" * 60)

    print("""
    新项目推荐使用 Poetry：

    1. 安装 Poetry（使用 pipx）
    $ pipx install poetry

    2. 创建项目
    $ poetry new my-project

    3. 配置 pyproject.toml
    - 设置 Python 版本要求
    - 添加项目描述和作者信息
    - 配置开发依赖

    4. 开发流程
    $ cd my-project
    $ poetry install          # 安装依赖
    $ poetry add requests     # 添加新依赖
    $ poetry run pytest       # 运行测试
    $ poetry build            # 构建包

    5. 发布流程
    $ poetry version patch    # 更新版本号
    $ poetry build            # 构建
    $ poetry publish          # 发布
    """)

    print("\n💡 总结：")
    print("1. 新项目推荐使用 Poetry 或 PDM")
    print("2. 老项目可以继续使用 pip + requirements.txt")
    print("3. 选择一个工具后，整个项目保持一致")
    print("4. 锁文件一定要提交到 Git")


if __name__ == '__main__':
    main()
