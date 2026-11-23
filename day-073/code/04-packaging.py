"""
Day 073 — 打包与发布
运行方式：python 04-packaging.py
"""
import os


def main():
    # ========== 1. 项目结构 ==========
    print("=" * 60)
    print("📁 推荐项目结构")
    print("=" * 60)

    structure = """
    my-package/
    ├── src/
    │   └── my_package/
    │       ├── __init__.py
    │       ├── core.py
    │       └── utils.py
    ├── tests/
    │   ├── __init__.py
    │   ├── test_core.py
    │   └── test_utils.py
    ├── pyproject.toml      # 推荐（现代标准）
    ├── setup.py            # 传统方式（仍广泛使用）
    ├── README.md
    ├── LICENSE
    └── CHANGELOG.md
    """
    print(structure)

    # ========== 2. pyproject.toml 配置 ==========
    print("=" * 60)
    print("⚙️ pyproject.toml 配置")
    print("=" * 60)

    print("""
    [build-system]
    requires = ["setuptools>=61.0", "wheel"]
    build-backend = "setuptools.backends._legacy:_Backend"

    [project]
    name = "my-package"
    version = "0.1.0"
    description = "A short description of my package"
    readme = "README.md"
    license = {text = "MIT"}
    authors = [
        {name = "Your Name", email = "your@email.com"}
    ]
    requires-python = ">=3.9"
    dependencies = [
        "requests>=2.28",
        "click>=8.0",
    ]

    [project.optional-dependencies]
    dev = [
        "pytest>=7.0",
        "black>=23.0",
    ]

    [project.urls]
    Homepage = "https://github.com/yourname/my-package"
    Documentation = "https://my-package.readthedocs.io"
    Repository = "https://github.com/yourname/my-package"

    [project.scripts]
    my-cli = "my_package.cli:main"  # 命令行入口点

    [tool.setuptools.packages.find]
    where = ["src"]
    """)

    # ========== 3. setup.py 配置 ==========
    print("=" * 60)
    print("📦 setup.py 配置（传统方式）")
    print("=" * 60)

    print("""
    from setuptools import setup, find_packages

    setup(
        name="my-package",
        version="0.1.0",
        description="A short description",
        long_description=open("README.md").read(),
        long_description_content_type="text/markdown",
        author="Your Name",
        author_email="your@email.com",
        url="https://github.com/yourname/my-package",
        packages=find_packages(where="src"),
        package_dir={"": "src"},
        install_requires=[
            "requests>=2.28",
            "click>=8.0",
        ],
        extras_require={
            "dev": ["pytest>=7.0", "black>=23.0"],
        },
        python_requires=">=3.9",
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ],
        entry_points={
            "console_scripts": [
                "my-cli=my_package.cli:main",
            ],
        },
    )
    """)

    # ========== 4. 构建命令 ==========
    print("=" * 60)
    print("🔨 构建命令")
    print("=" * 60)

    print("""
    方法1：使用 build 模块（推荐）
    $ pip install build
    $ python -m build

    方法2：使用 setuptools
    $ python setup.py sdist bdist_wheel

    方法3：使用 Poetry
    $ poetry build

    方法4：使用 PDM
    $ pdm build

    生成的文件：
    dist/
    ├── my_package-0.1.0.tar.gz      # 源码包
    └── my_package-0.1.0-py3-none-any.whl  # 轮子包
    """)

    # ========== 5. 发布到 PyPI ==========
    print("=" * 60)
    print("🚀 发布到 PyPI")
    print("=" * 60)

    print("""
    步骤1：注册 PyPI 账号
    - 访问 https://pypi.org/account/register/

    步骤2：创建 API Token
    - 访问 https://pypi.org/manage/account/token/

    步骤3：配置 ~/.pypirc
    [distutils]
    index-server =
        pypi
        testpypi

    [pypi]
    username = __token__
    password = pypi-xxxxxxxxxxxx

    [testpypi]
    repository = https://test.pypi.org/legacy/
    username = __token__
    password = pypi-xxxxxxxxxxxx

    步骤4：先在 TestPyPI 测试
    $ pip install twine
    $ twine upload --repository testpypi dist/*

    步骤5：正式发布
    $ twine upload dist/*

    步骤6：安装测试
    $ pip install my-package
    """)

    # ========== 6. 版本管理 ==========
    print("=" * 60)
    print("🔢 版本管理")
    print("=" * 60)

    print("""
    语义化版本号：MAJOR.MINOR.PATCH
    │ │ │
    │ │ └── PATCH：bug 修复（向后兼容）
    │ └──── MINOR：新功能（向后兼容）
    └────── MAJOR：破坏性更改

    更新版本：
    # Poetry
    $ poetry version patch  # 0.1.0 → 0.1.1
    $ poetry version minor  # 0.1.1 → 0.2.0
    $ poetry version major  # 0.2.0 → 1.0.0

    # 手动修改
    # pyproject.toml 或 setup.py 中的 version 字段
    """)

    # ========== 7. 避坑指南 ==========
    print("=" * 60)
    print("⚠️ 避坑指南")
    print("=" * 60)

    pitfalls = """
    1. 包名不能与 PyPI 上已有的包重名
       → 先在 PyPI 搜索确认

    2. 版本号每次发布必须递增
       → 使用语义化版本号

    3. 发布前先在 TestPyPI 测试
       → twine upload --repository testpypi dist/*

    4. 不要把敏感信息提交到 Git
       → 使用 .gitignore 排除

    5. README.md 要写清楚
       → 这是用户第一眼看到的

    6. 添加 LICENSE 文件
       → 选择合适的开源协议

    7. 包含 CHANGELOG.md
       → 记录版本更新内容
    """
    print(pitfalls)

    # ========== 8. 实战：创建示例包 ==========
    print("=" * 60)
    print("🎯 实战：创建示例包")
    print("=" * 60)

    print("""
    创建一个简单的字符串工具包：

    1. 创建项目目录
    $ mkdir stringtools && cd stringtools

    2. 创建项目结构
    $ mkdir -p src/stringtools tests

    3. 创建 pyproject.toml
    （见上方配置）

    4. 编写代码
    $ touch src/stringtools/__init__.py
    $ touch src/stringtools/case.py
    $ touch src/stringtools/validate.py

    5. 编写测试
    $ touch tests/__init__.py
    $ touch tests/test_case.py

    6. 构建并测试
    $ python -m build
    $ twine check dist/*

    7. 发布
    $ twine upload --repository testpypi dist/*
    """)

    print("\n💡 总结：")
    print("1. 使用 pyproject.toml（现代标准）")
    print("2. 采用 src/ 目录结构")
    print("3. 先在 TestPyPI 测试")
    print("4. 遵循语义化版本号")
    print("5. 写好 README 和 CHANGELOG")


if __name__ == '__main__':
    main()
