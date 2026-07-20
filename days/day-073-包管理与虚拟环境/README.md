# Day 073 — 包管理与虚拟环境

## 概述

Python 的强大之处在于其丰富的生态系统——上百万个第三方包等着你使用。但如何管理这些依赖？如何创建独立的项目环境？如何打包发布自己的包？

**今天你将学到：**
1. pip 与 requirements.txt — 基础包管理
2. Poetry/PDM — 现代包管理工具
3. 虚拟环境原理 — venv/conda
4. 打包与发布 — setup.py / pyproject.toml
5. **实战：发布自己的 Python 包**

> 💡 **为什么重要？**
> - 不同项目可能需要不同版本的库（项目A用 requests 2.25，项目B用 2.28）
> - 全局安装会导致版本冲突
> - 虚拟环境让每个项目拥有独立的依赖空间
> - 打包让你的代码可以被全世界的开发者使用

---

## 1. pip 与 requirements.txt

### 1.1 pip 基础

```bash
# 安装包
pip install requests          # 最新版本
pip install requests==2.28.0  # 指定版本
pip install requests>=2.25    # 最低版本

# 升级包
pip install --upgrade requests

# 卸载包
pip uninstall requests

# 查看已安装的包
pip list
pip show requests

# 查看过期的包
pip list --outdated

# 导出当前环境的所有包
pip freeze > requirements.txt
```

### 1.2 requirements.txt 规范

```txt
# requirements.txt 示例

# 精确版本（推荐用于生产环境）
requests==2.28.0
flask==2.3.2

# 版本范围（开发环境可用）
numpy>=1.20,<2.0
pandas~=1.5    # 兼容版本（>=1.5.0, <1.6.0）

# 从 Git 安装
git+https://github.com/user/repo.git@main

# 从本地文件安装
-e ./local-package

# 环境变量（用于私有包）
# --index-url https://pypi.org/simple/
# --extra-index-url https://private.pypi.org/simple/
```

### 1.3 版本号规范

```python
# 语义化版本号：MAJOR.MINOR.PATCH
# 1.2.3
#  │ │ │
#  │ │ └── PATCH：bug 修复
#  │ └──── MINOR：新功能（向后兼容）
#  └────── MAJOR：破坏性更改

# 版本约束符号
# ==   精确匹配
# >=   大于等于
# <=   小于等于
# ~=   兼容版本（≈）
# !=   排除版本

# 示例
"""
requests>=2.20,<3.0    # 2.20.x 到 2.x.x
flask~=2.3             # >=2.3.0, <2.4.0
numpy!=1.19.0          # 排除 1.19.0
"""
```

### 1.4 pip 镜像配置

```bash
# 国内用户建议使用镜像源

# 临时使用
pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple

# 永久配置
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 或创建 ~/.pip/pip.conf
"""
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
"""
```

**避坑说明：**
- ⚠️ 不要在全局环境安装太多包，容易冲突
- ⚠️ `pip freeze` 会导出所有包，包括依赖的依赖
- ⚠️ 生产环境务必使用精确版本号
- ⚠️ `requirements.txt` 不记录 Python 版本要求

---

## 2. 虚拟环境原理

### 2.1 为什么需要虚拟环境？

```python
# 问题场景：
# 项目A需要 requests==2.25
# 项目B需要 requests==2.28
# 如果全局安装，只能选一个版本！

# 解决方案：虚拟环境
# 每个项目有自己的 Python 解释器和包目录
```

### 2.2 venv 模块（推荐）

```bash
# 创建虚拟环境
python -m venv myenv          # 创建名为 myenv 的目录
python -m venv --clear myenv  # 清除已有环境重新创建
python -m venv --system-site-packages myenv  # 继承系统包

# 激活虚拟环境
# Linux/macOS:
source myenv/bin/activate

# Windows:
myenv\Scripts\activate

# 退出虚拟环境
deactivate

# 查看当前环境的 Python 路径
which python   # Linux/macOS
where python   # Windows
```

### 2.3 虚拟环境的原理

```python
# 虚拟环境本质上是：
# 1. 复制了一份 Python 解释器（或创建符号链接）
# 2. 创建了独立的 site-packages 目录
# 3. 修改了 PATH 环境变量

# 目录结构：
"""
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

# 查看 site-packages 位置
import site
print(site.getsitepackages())
# 输出: ['/path/to/myenv/lib/python3.x/site-packages']
```

### 2.4 conda 环境

```bash
# conda 是 Anaconda/Miniconda 的包管理器
# 特点：可以管理非 Python 包（如 CUDA、MKL）

# 创建环境
conda create -n myenv python=3.11

# 激活环境
conda activate myenv

# 安装包
conda install numpy
pip install requests  # conda 环境中也可以用 pip

# 导出环境
conda env export > environment.yml

# 从文件创建环境
conda env create -f environment.yml

# 查看所有环境
conda env list

# 删除环境
conda env remove -n myenv
```

### 2.5 venv vs conda 对比

| 特性 | venv | conda |
|------|------|-------|
| Python 版本 | 需要预先安装 | 可以安装任意 Python 版本 |
| 非 Python 包 | ❌ 不支持 | ✅ 支持（CUDA 等） |
| 速度 | 快 | 较慢 |
| 磁盘占用 | 小 | 大 |
| 跨平台 | ✅ | ✅ |
| 推荐场景 | 纯 Python 项目 | 数据科学、机器学习 |

**避坑说明：**
- ⚠️ 不要在虚拟环境外安装包
- ⚠️ 激活环境后才能使用其中的包
- ⚠️ 不同项目的虚拟环境不要混用
- ⚠️ conda 和 pip 混用可能导致依赖冲突

---

## 3. 现代包管理工具

### 3.1 Poetry

```bash
# 安装 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 或使用 pip
pip install poetry

# 创建新项目
poetry new my-project
# 生成结构：
# my-project/
# ├── pyproject.toml
# ├── README.md
# ├── my_project/
# │   └── __init__.py
# └── tests/
#     └── __init__.py

# 初始化已有项目
cd existing-project
poetry init

# 添加依赖
poetry add requests           # 运行时依赖
poetry add --group dev pytest # 开发依赖

# 安装所有依赖
poetry install

# 运行命令
poetry run python main.py
poetry run pytest

# 构建包
poetry build

# 发布到 PyPI
poetry publish --build
```

### 3.2 pyproject.toml 配置

```toml
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
```

### 3.3 PDM（更快的选择）

```bash
# 安装 PDM
pip install pdm

# 创建项目
pdm init

# 添加依赖
pdm add requests
pdm add -d pytest  # 开发依赖

# 安装依赖
pdm install

# 运行命令
pdm run python main.py

# 构建包
pdm build

# 发布
pdm publish
```

### 3.4 Poetry vs PDM 对比

| 特性 | Poetry | PDM |
|------|--------|-----|
| 速度 | 快 | 更快 |
| 依赖解析 | 优秀 | 优秀 |
| PyPA 标准 | 部分支持 | 完全支持 |
| 插件生态 | 丰富 | 成长中 |
| 锁文件 | poetry.lock | pdm.lock |
| 推荐场景 | 成熟项目 | 新项目 |

**避坑说明：**
- ⚠️ Poetry 和 PDM 不要混用
- ⚠️ 选择一个工具后，整个项目保持一致
- ⚠️ 锁文件要提交到 Git
- ⚠️ 不要手动编辑 `pyproject.toml` 的依赖部分

---

## 4. 打包与发布

### 4.1 项目结构

```
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
```

### 4.2 pyproject.toml 打包配置

```toml
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
docs = [
    "sphinx>=5.0",
]

[project.urls]
Homepage = "https://github.com/yourname/my-package"
Documentation = "https://my-package.readthedocs.io"
Repository = "https://github.com/yourname/my-package"
Issues = "https://github.com/yourname/my-package/issues"

[project.scripts]
my-cli = "my_package.cli:main"  # 命令行入口点

[tool.setuptools.packages.find]
where = ["src"]
```

### 4.3 传统 setup.py 方式

```python
# setup.py（仍然广泛使用）
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
```

### 4.4 构建与发布

```bash
# 方法1：使用 build 模块
pip install build
python -m build  # 生成 dist/ 目录

# 方法2：使用 setuptools
python setup.py sdist bdist_wheel

# 方法3：使用 Poetry
poetry build

# 方法4：使用 PDM
pdm build

# 生成的文件：
# dist/
# ├── my_package-0.1.0.tar.gz      # 源码包
# └── my_package-0.1.0-py3-none-any.whl  # 轮子包

# 发布到 PyPI
pip install twine
twine upload dist/*

# 或使用 Poetry
poetry publish --build

# 或使用 PDM
pdm publish
```

### 4.5 PyPI 发布流程

```bash
# 1. 注册 PyPI 账号
# 访问 https://pypi.org/account/register/

# 2. 创建 API Token
# 访问 https://pypi.org/manage/account/token/

# 3. 配置 ~/.pypirc
"""
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
"""

# 4. 先在 TestPyPI 测试
twine upload --repository testpypi dist/*

# 5. 正式发布
twine upload dist/*

# 6. 安装测试
pip install my-package
```

**避坑说明：**
- ⚠️ 包名不能与 PyPI 上已有的包重名
- ⚠️ 版本号每次发布必须递增
- ⚠️ 发布前先在 TestPyPI 测试
- ⚠️ 不要把敏感信息（密码、密钥）提交到 Git
- ⚠️ README.md 要写清楚，这是用户第一眼看到的

---

## 5. 依赖管理最佳实践

### 5.1 锁文件的重要性

```bash
# 锁文件（lock file）记录了所有依赖的确切版本
# 确保团队成员和生产环境使用相同的依赖

# Poetry: poetry.lock
# PDM: pdm.lock
# pip-tools: requirements.txt (锁定版本)

# 提交锁文件到 Git
git add pyproject.toml poetry.lock
git commit -m "Update dependencies"
```

### 5.2 依赖分组

```toml
# pyproject.toml 中的依赖分组
[tool.poetry.group]
[tool.poetry.group.dev.dependencies]  # 开发依赖
pytest = "^7.0"
black = "^23.0"

[tool.poetry.group.docs.dependencies]  # 文档依赖
sphinx = "^5.0"

[tool.poetry.group.test.dependencies]  # 测试依赖
pytest-cov = "^4.0"
```

### 5.3 安全扫描

```bash
# 检查依赖中的安全漏洞
pip install safety
safety check

# 或使用 pip-audit
pip install pip-audit
pip-audit

# Poetry 内置安全检查
poetry show --outdated
```

---

## 实战项目：发布自己的 Python 包

我们将创建一个简单的工具包并发布到 TestPyPI。

```python
"""
实战：发布自己的 Python 包
创建一个字符串工具包并发布到 TestPyPI
"""
# 首先创建项目结构：
"""
stringtools/
├── src/
│   └── stringtools/
│       ├── __init__.py
│       ├── case.py
│       ├── validate.py
│       └── transform.py
├── tests/
│   ├── __init__.py
│   ├── test_case.py
│   ├── test_validate.py
│   └── test_transform.py
├── pyproject.toml
└── README.md
"""
```

### 项目代码

```python
# src/stringtools/__init__.py
"""字符串工具包 - 常用字符串操作的集合"""

__version__ = "0.1.0"
__author__ = "Your Name"

from .case import to_camel, to_snake, to_pascal
from .validate import is_email, is_phone, is_url
from .transform import slugify, truncate, wrap_text

__all__ = [
    "to_camel",
    "to_snake",
    "to_pascal",
    "is_email",
    "is_phone",
    "is_url",
    "slugify",
    "truncate",
    "wrap_text",
]
```

```python
# src/stringtools/case.py
"""大小写转换工具"""


def to_camel(s: str) -> str:
    """将字符串转换为驼峰命名法

    Args:
        s: 输入字符串，支持 snake_case、kebab-case、空格分隔

    Returns:
        驼峰命名法字符串

    Examples:
        >>> to_camel("hello_world")
        'helloWorld'
        >>> to_camel("hello-world")
        'helloWorld'
        >>> to_camel("hello world")
        'helloWorld'
    """
    # 统一分隔符
    s = s.replace("-", "_").replace(" ", "_")
    parts = s.split("_")
    # 第一个单词小写，其余首字母大写
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def to_snake(s: str) -> str:
    """将字符串转换为蛇形命名法

    Args:
        s: 输入字符串，支持 camelCase、PascalCase、kebab-case

    Returns:
        蛇形命名法字符串

    Examples:
        >>> to_snake("helloWorld")
        'hello_world'
        >>> to_snake("HelloWorld")
        'hello_world'
        >>> to_snake("hello-world")
        'hello_world'
    """
    import re
    # 在大写字母前插入下划线
    s = re.sub(r'([A-Z])', r'_\1', s)
    # 统一分隔符
    s = s.replace("-", "_")
    # 去除开头的下划线，转小写
    return s.lstrip("_").lower()


def to_pascal(s: str) -> str:
    """将字符串转换为帕斯卡命名法

    Args:
        s: 输入字符串

    Returns:
        帕斯卡命名法字符串

    Examples:
        >>> to_pascal("hello_world")
        'HelloWorld'
        >>> to_pascal("hello-world")
        'HelloWorld'
    """
    return to_camel(s).capitalize()
```

```python
# src/stringtools/validate.py
"""字符串验证工具"""
import re


def is_email(s: str) -> bool:
    """验证邮箱格式

    Args:
        s: 要验证的字符串

    Returns:
        是否是有效的邮箱格式

    Examples:
        >>> is_email("test@example.com")
        True
        >>> is_email("invalid")
        False
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, s))


def is_phone(s: str) -> bool:
    """验证中国手机号格式

    Args:
        s: 要验证的字符串

    Returns:
        是否是有效的手机号格式

    Examples:
        >>> is_phone("13812345678")
        True
        >>> is_phone("12345")
        False
    """
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, s))


def is_url(s: str) -> bool:
    """验证 URL 格式

    Args:
        s: 要验证的字符串

    Returns:
        是否是有效的 URL 格式

    Examples:
        >>> is_url("https://example.com")
        True
        >>> is_url("not-a-url")
        False
    """
    pattern = r'^https?://\S+$'
    return bool(re.match(pattern, s))
```

```python
# src/stringtools/transform.py
"""字符串转换工具"""


def slugify(s: str) -> str:
    """将字符串转换为 URL 友好的 slug

    Args:
        s: 输入字符串

    Returns:
        URL 友好的字符串

    Examples:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("Python 3.11 Release")
        'python-311-release'
    """
    import re
    # 转小写
    s = s.lower()
    # 替换非字母数字字符为连字符
    s = re.sub(r'[^a-z0-9]+', '-', s)
    # 去除首尾连字符
    return s.strip('-')


def truncate(s: str, max_length: int, suffix: str = "...") -> str:
    """截断字符串

    Args:
        s: 输入字符串
        max_length: 最大长度
        suffix: 截断后添加的后缀

    Returns:
        截断后的字符串

    Examples:
        >>> truncate("Hello World", 5)
        'He...'
        >>> truncate("Hi", 10)
        'Hi'
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def wrap_text(s: str, width: int) -> str:
    """按指定宽度换行

    Args:
        s: 输入字符串
        width: 每行最大宽度

    Returns:
        换行后的字符串

    Examples:
        >>> wrap_text("Hello World", 5)
        'Hello\\nWorld'
    """
    import textwrap
    return textwrap.fill(s, width)
```

### 测试代码

```python
# tests/test_case.py
"""测试大小写转换"""
from stringtools import to_camel, to_snake, to_pascal


def test_to_camel():
    assert to_camel("hello_world") == "helloWorld"
    assert to_camel("hello-world") == "helloWorld"
    assert to_camel("hello world") == "helloWorld"


def test_to_snake():
    assert to_snake("helloWorld") == "hello_world"
    assert to_snake("HelloWorld") == "hello_world"
    assert to_snake("hello-world") == "hello_world"


def test_to_pascal():
    assert to_pascal("hello_world") == "HelloWorld"
    assert to_pascal("hello-world") == "HelloWorld"
```

```python
# tests/test_validate.py
"""测试验证函数"""
from stringtools import is_email, is_phone, is_url


def test_is_email():
    assert is_email("test@example.com") is True
    assert is_email("invalid") is False
    assert is_email("@example.com") is False


def test_is_phone():
    assert is_phone("13812345678") is True
    assert is_phone("12345") is False
    assert is_phone("23812345678") is False


def test_is_url():
    assert is_url("https://example.com") is True
    assert is_url("not-a-url") is False
```

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "stringtools-yourname"  # 替换为你的用户名
version = "0.1.0"
description = "A collection of useful string utilities"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.9"

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[tool.setuptools.packages.find]
where = ["src"]
```

### 发布步骤

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS

# 2. 安装开发依赖
pip install -e ".[dev]"
pip install build twine

# 3. 运行测试
pytest

# 4. 构建包
python -m build

# 5. 检查包
twine check dist/*

# 6. 上传到 TestPyPI（先测试）
twine upload --repository testpypi dist/*

# 7. 安装测试
pip install --index-url https://test.pypi.org/simple/ stringtools-yourname

# 8. 正式发布到 PyPI
twine upload dist/*
```

---

## 今日总结

- **pip**：基础包管理工具，配合 `requirements.txt` 使用
- **虚拟环境**：隔离项目依赖，`venv` 是推荐方式
- **Poetry/PDM**：现代包管理工具，集依赖管理、打包、发布于一体
- **pyproject.toml**：现代打包标准，替代 setup.py
- **发布流程**：构建 → 检查 → 上传 TestPyPI → 测试 → 上传 PyPI

---

## 练习题

### 练习 1：创建虚拟环境 ⭐
为你的项目创建一个虚拟环境：
- 创建虚拟环境
- 激活并安装 3 个包
- 导出 requirements.txt
- 用 requirements.txt 重建环境

### 练习 2：依赖分析 ⭐⭐
分析一个项目的依赖关系：
- 读取 requirements.txt
- 找出直接依赖和间接依赖
- 检查版本冲突
- 生成依赖报告

### 练习 3：打包发布 ⭐⭐⭐
将你的一个工具脚本打包成 Python 包：
- 创建标准项目结构
- 编写 pyproject.toml
- 添加测试
- 构建并检查包
- 上传到 TestPyPI

### 练习 4：Poetry 实战 ⭐⭐⭐
使用 Poetry 管理一个项目：
- 用 poetry new 创建项目
- 添加依赖
- 配置开发依赖
- 构建并发布

### 练习 5：依赖安全审计 ⭐⭐⭐⭐
编写一个依赖安全审计工具：
- 读取 requirements.txt
- 调用 PyPI API 检查版本
- 检查已知漏洞
- 生成安全报告
- 建议升级版本

---

## 明天预告

Day 074 我们将学习**单元测试进阶**——TDD 流程、参数化测试、集成测试、异步测试。掌握测试技能是成为专业开发者的关键一步！
