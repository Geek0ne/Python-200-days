# Day 075 — 阶段项目：标准库综合实战

## 概述

Phase 5 的最后一天，我们将**综合运用所有学到的知识**，构建一个完整的 CLI 工具——文件批量重命名工具。

**今天你将学到：**
1. 构建完整的 CLI 工具（argparse + logging + json + pathlib）
2. 项目结构规范（src layout）
3. 文档编写（README + docstring）
4. 测试编写（unittest）
5. **实战：文件批量重命名工具**

> 💡 **为什么要做综合项目？**
> - 知识点只有在实际项目中才能真正掌握
> - 综合项目能暴露你对各模块理解的不足
> - 完整的项目经历是简历上的亮点
> - 学会从零构建一个可用的工具

---

## 1. 项目规划

### 1.1 功能需求

```
文件批量重命名工具 rename-tool
├── 基本重命名
│   ├── 添加前缀/后缀
│   ├── 替换字符串
│   └── 序号重命名
├── 高级功能
│   ├── 正则替换
│   ├── 日期重命名
│   └── 大小写转换
├── 安全特性
│   ├── 预览模式（dry-run）
│   ├── 确认提示
│   └── 撤销支持
└── 输出格式
    ├── 终端输出
    ├── JSON 报告
    └── 日志记录
```

### 1.2 项目结构

```
rename-tool/
├── src/
│   └── rename_tool/
│       ├── __init__.py
│       ├── cli.py          # 命令行接口
│       ├── core.py         # 核心重命名逻辑
│       ├── utils.py        # 工具函数
│       └── exceptions.py   # 自定义异常
├── tests/
│   ├── __init__.py
│   ├── test_core.py
│   ├── test_cli.py
│   └── test_utils.py
├── pyproject.toml
├── README.md
├── CHANGELOG.md
└── LICENSE
```

---

## 2. 核心代码实现

### 2.1 异常定义

```python
# src/rename_tool/exceptions.py
"""自定义异常"""


class RenameToolError(Exception):
    """重命名工具基础异常"""
    pass


class FileNotFoundError(RenameToolError):
    """文件不存在"""
    pass


class PermissionError(RenameToolError):
    """权限不足"""
    pass


class ConflictError(RenameToolError):
    """文件名冲突"""
    pass


class PatternError(RenameToolError):
    """正则模式错误"""
    pass
```

### 2.2 核心重命名逻辑

```python
# src/rename_tool/core.py
"""核心重命名逻辑"""
import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Callable

from .exceptions import (
    FileNotFoundError,
    PermissionError,
    ConflictError,
    PatternError,
)

logger = logging.getLogger(__name__)


class RenameOperation:
    """单个重命名操作"""

    def __init__(self, old_path: Path, new_path: Path):
        self.old_path = old_path
        self.new_path = new_path
        self.success = False
        self.error: Optional[str] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "old": str(self.old_path),
            "new": str(self.new_path),
            "success": self.success,
            "error": self.error,
        }


class RenameResult:
    """重命名结果"""

    def __init__(self):
        self.operations: List[RenameOperation] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None

    def add(self, operation: RenameOperation):
        """添加操作"""
        self.operations.append(operation)

    def finish(self):
        """完成"""
        self.end_time = datetime.now()

    @property
    def total(self) -> int:
        """总操作数"""
        return len(self.operations)

    @property
    def success_count(self) -> int:
        """成功数"""
        return sum(1 for op in self.operations if op.success)

    @property
    def failure_count(self) -> int:
        """失败数"""
        return self.total - self.success_count

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total": self.total,
            "success": self.success_count,
            "failure": self.failure_count,
            "operations": [op.to_dict() for op in self.operations],
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class Renamer:
    """重命名器"""

    def __init__(self, directory: str, dry_run: bool = False):
        self.directory = Path(directory)
        self.dry_run = dry_run
        self.result = RenameResult()

        if not self.directory.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")

        if not self.directory.is_dir():
            raise ValueError(f"不是目录: {directory}")

    def _get_files(self, pattern: Optional[str] = None) -> List[Path]:
        """获取文件列表"""
        if pattern:
            return sorted(self.directory.glob(pattern))
        return sorted(self.directory.iterdir())

    def _check_conflict(self, new_path: Path) -> bool:
        """检查文件名冲突"""
        if new_path.exists():
            logger.warning(f"目标文件已存在: {new_path}")
            return True
        return False

    def _execute_rename(self, old_path: Path, new_path: Path) -> RenameOperation:
        """执行重命名"""
        operation = RenameOperation(old_path, new_path)

        try:
            if self.dry_run:
                logger.info(f"[预览] {old_path.name} → {new_path.name}")
                operation.success = True
            else:
                old_path.rename(new_path)
                logger.info(f"重命名: {old_path.name} → {new_path.name}")
                operation.success = True
        except Exception as e:
            operation.error = str(e)
            logger.error(f"重命名失败: {old_path.name} - {e}")

        return operation

    def add_prefix(self, prefix: str, pattern: Optional[str] = None) -> RenameResult:
        """添加前缀"""
        files = self._get_files(pattern)
        for file in files:
            if file.is_file():
                new_name = f"{prefix}{file.name}"
                new_path = file.parent / new_name
                operation = self._execute_rename(file, new_path)
                self.result.add(operation)

        self.result.finish()
        return self.result

    def add_suffix(self, suffix: str, pattern: Optional[str] = None) -> RenameResult:
        """添加后缀"""
        files = self._get_files(pattern)
        for file in files:
            if file.is_file():
                stem = file.stem
                new_name = f"{stem}{suffix}{file.suffix}"
                new_path = file.parent / new_name
                operation = self._execute_rename(file, new_path)
                self.result.add(operation)

        self.result.finish()
        return self.result

    def replace(
        self, old: str, new: str, pattern: Optional[str] = None
    ) -> RenameResult:
        """替换字符串"""
        files = self._get_files(pattern)
        for file in files:
            if file.is_file():
                new_name = file.name.replace(old, new)
                new_path = file.parent / new_name
                operation = self._execute_rename(file, new_path)
                self.result.add(operation)

        self.result.finish()
        return self.result

    def regex_replace(
        self, regex_pattern: str, replacement: str, pattern: Optional[str] = None
    ) -> RenameResult:
        """正则替换"""
        try:
            compiled = re.compile(regex_pattern)
        except re.error as e:
            raise PatternError(f"正则表达式错误: {e}")

        files = self._get_files(pattern)
        for file in files:
            if file.is_file():
                new_name = compiled.sub(replacement, file.name)
                new_path = file.parent / new_name
                operation = self._execute_rename(file, new_path)
                self.result.add(operation)

        self.result.finish()
        return self.result

    def sequence(
        self,
        template: str = "{name}_{index:03d}",
        start: int = 1,
        pattern: Optional[str] = None,
    ) -> RenameResult:
        """序号重命名"""
        files = self._get_files(pattern)
        for i, file in enumerate(files, start=start):
            if file.is_file():
                new_name = template.format(
                    name=file.stem,
                    index=i,
                    ext=file.suffix,
                )
                new_path = file.parent / new_name
                operation = self._execute_rename(file, new_path)
                self.result.add(operation)

        self.result.finish()
        return self.result

    def date_rename(
        self,
        date_format: str = "%Y%m%d_%H%M%S",
        pattern: Optional[str] = None,
    ) -> RenameResult:
        """日期重命名"""
        files = self._get_files(pattern)
        for file in files:
            if file.is_file():
                # 获取文件修改时间
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                date_str = mtime.strftime(date_format)
                new_name = f"{date_str}_{file.name}"
                new_path = file.parent / new_name
                operation = self._execute_rename(file, new_path)
                self.result.add(operation)

        self.result.finish()
        return self.result

    def case转换(self, case: str, pattern: Optional[str] = None) -> RenameResult:
        """大小写转换"""
        files = self._get_files(pattern)
        for file in files:
            if file.is_file():
                stem = file.stem
                suffix = file.suffix

                if case == "lower":
                    new_stem = stem.lower()
                elif case == "upper":
                    new_stem = stem.upper()
                elif case == "title":
                    new_stem = stem.title()
                elif case == "snake":
                    # 简单的蛇形命名
                    new_stem = re.sub(r'([A-Z])', r'_\1', stem).lower().lstrip('_')
                elif case == "camel":
                    # 简单的驼峰命名
                    parts = stem.split('_')
                    new_stem = parts[0] + ''.join(p.capitalize() for p in parts[1:])
                else:
                    raise ValueError(f"未知的大小写模式: {case}")

                new_name = f"{new_stem}{suffix}"
                new_path = file.parent / new_name
                operation = self._execute_rename(file, new_path)
                self.result.add(operation)

        self.result.finish()
        return self.result
```

### 2.3 工具函数

```python
# src/rename_tool/utils.py
"""工具函数"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
) -> None:
    """配置日志"""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # 文件处理器（可选）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def format_file_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def save_report(result, output_file: str) -> None:
    """保存重命名报告"""
    report = result.to_dict()
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"报告已保存: {output_file}")


def preview_changes(operations) -> None:
    """预览变更"""
    print("\n" + "=" * 60)
    print("📋 变更预览")
    print("=" * 60)

    for i, op in enumerate(operations, 1):
        old_name = op.old_path.name
        new_name = op.new_path.name
        status = "✅" if op.success else "❌"
        print(f"{i:3d}. {status} {old_name} → {new_name}")

    print("=" * 60)
```

### 2.4 命令行接口

```python
# src/rename_tool/cli.py
"""命令行接口"""
import argparse
import sys
import logging
from pathlib import Path

from .core import Renamer
from .utils import setup_logging, save_report, preview_changes

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="rename-tool",
        description="文件批量重命名工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 添加前缀
  rename-tool add-prefix --prefix "photo_" --directory ./images

  # 替换字符串
  rename-tool replace --old " " --new "_" --directory ./files

  # 序号重命名
  rename-tool sequence --template "doc_{index:03d}" --directory ./docs

  # 正则替换
  rename-tool regex --pattern "(\\d+)" --replacement "file_\\1" --directory ./data
        """,
    )

    # 通用参数
    parser.add_argument(
        "-d", "--directory",
        required=True,
        help="目标目录",
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="预览模式，不实际重命名",
    )
    parser.add_argument(
        "-f", "--filter",
        help="文件过滤模式（如 *.txt）",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出 JSON 报告文件",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出",
    )
    parser.add_argument(
        "--log-file",
        help="日志文件路径",
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # add-prefix
    prefix_parser = subparsers.add_parser("add-prefix", help="添加前缀")
    prefix_parser.add_argument("--prefix", required=True, help="要添加的前缀")

    # add-suffix
    suffix_parser = subparsers.add_parser("add-suffix", help="添加后缀")
    suffix_parser.add_argument("--suffix", required=True, help="要添加的后缀")

    # replace
    replace_parser = subparsers.add_parser("replace", help="替换字符串")
    replace_parser.add_argument("--old", required=True, help="要替换的字符串")
    replace_parser.add_argument("--new", required=True, help="替换后的字符串")

    # regex
    regex_parser = subparsers.add_parser("regex", help="正则替换")
    regex_parser.add_argument("--pattern", required=True, help="正则表达式")
    regex_parser.add_argument("--replacement", required=True, help="替换内容")

    # sequence
    seq_parser = subparsers.add_parser("sequence", help="序号重命名")
    seq_parser.add_argument(
        "--template",
        default="{name}_{index:03d}",
        help="命名模板（默认: {name}_{index:03d}）",
    )
    seq_parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="起始序号（默认: 1）",
    )

    # date
    date_parser = subparsers.add_parser("date", help="日期重命名")
    date_parser.add_argument(
        "--format",
        default="%Y%m%d_%H%M%S",
        help="日期格式（默认: %Y%m%d_%H%M%S）",
    )

    # case
    case_parser = subparsers.add_parser("case", help="大小写转换")
    case_parser.add_argument(
        "--mode",
        choices=["lower", "upper", "title", "snake", "camel"],
        required=True,
        help="转换模式",
    )

    return parser


def main(args=None):
    """主入口"""
    parser = create_parser()
    args = parser.parse_args(args)

    # 配置日志
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level, log_file=args.log_file)

    # 检查命令
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 创建重命名器
    try:
        renamer = Renamer(args.directory, dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        sys.exit(1)

    # 执行命令
    try:
        if args.command == "add-prefix":
            result = renamer.add_prefix(args.prefix, args.filter)
        elif args.command == "add-suffix":
            result = renamer.add_suffix(args.suffix, args.filter)
        elif args.command == "replace":
            result = renamer.replace(args.old, args.new, args.filter)
        elif args.command == "regex":
            result = renamer.regex_replace(args.pattern, args.replacement, args.filter)
        elif args.command == "sequence":
            result = renamer.sequence(args.template, args.start, args.filter)
        elif args.command == "date":
            result = renamer.date_rename(args.format, args.filter)
        elif args.command == "case":
            result = renamer.case转换(args.mode, args.filter)
        else:
            parser.print_help()
            sys.exit(1)

        # 显示结果
        preview_changes(result.operations)

        print(f"\n📊 统计: 成功 {result.success_count}, 失败 {result.failure_count}")

        # 保存报告
        if args.output:
            save_report(result, args.output)

    except Exception as e:
        logger.error(f"执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### 2.5 项目配置

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "rename-tool"
version = "1.0.0"
description = "文件批量重命名工具"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.9"

[project.scripts]
rename-tool = "rename_tool.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"

[tool.coverage.run]
source = ["rename_tool"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__",
]
```

---

## 3. 测试代码

```python
# tests/test_core.py
"""核心功能测试"""
import pytest
import tempfile
import os
from pathlib import Path
from rename_tool.core import Renamer, RenameResult
from rename_tool.exceptions import FileNotFoundError, PatternError


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        for i in range(5):
            (Path(tmpdir) / f"file{i}.txt").touch()
        yield tmpdir


class TestRenamer:
    """重命名器测试"""

    def test_init(self, temp_dir):
        """初始化"""
        renamer = Renamer(temp_dir)
        assert renamer.directory == Path(temp_dir)
        assert renamer.dry_run is False

    def test_init_nonexistent(self):
        """初始化不存在的目录"""
        with pytest.raises(FileNotFoundError):
            Renamer("/nonexistent/path")

    def test_add_prefix(self, temp_dir):
        """添加前缀"""
        renamer = Renamer(temp_dir)
        result = renamer.add_prefix("test_")

        assert result.success_count == 5
        assert result.failure_count == 0

        # 验证文件已重命名
        files = list(Path(temp_dir).glob("test_*.txt"))
        assert len(files) == 5

    def test_add_suffix(self, temp_dir):
        """添加后缀"""
        renamer = Renamer(temp_dir)
        result = renamer.add_suffix("_backup")

        assert result.success_count == 5

        files = list(Path(temp_dir).glob("*_backup.txt"))
        assert len(files) == 5

    def test_replace(self, temp_dir):
        """替换字符串"""
        renamer = Renamer(temp_dir)
        result = renamer.replace("file", "doc")

        assert result.success_count == 5

        files = list(Path(temp_dir).glob("doc*.txt"))
        assert len(files) == 5

    def test_sequence(self, temp_dir):
        """序号重命名"""
        renamer = Renamer(temp_dir)
        result = renamer.sequence("item_{index:03d}.txt")

        assert result.success_count == 5

        files = list(Path(temp_dir).glob("item_*.txt"))
        assert len(files) == 5

    def test_dry_run(self, temp_dir):
        """预览模式"""
        renamer = Renamer(temp_dir, dry_run=True)
        result = renamer.add_prefix("test_")

        assert result.success_count == 5

        # 文件不应该被重命名
        files = list(Path(temp_dir).glob("file*.txt"))
        assert len(files) == 5

    def test_regex_replace(self, temp_dir):
        """正则替换"""
        renamer = Renamer(temp_dir)
        result = renamer.regex_replace(r"(\d+)", r"num_\1")

        assert result.success_count == 5

    def test_invalid_regex(self, temp_dir):
        """无效正则"""
        renamer = Renamer(temp_dir)
        with pytest.raises(PatternError):
            renamer.regex_replace(r"[invalid", "test")


class TestRenameResult:
    """重命名结果测试"""

    def test_empty_result(self):
        """空结果"""
        result = RenameResult()
        assert result.total == 0
        assert result.success_count == 0
        assert result.failure_count == 0

    def test_to_json(self):
        """转换为 JSON"""
        result = RenameResult()
        result.finish()
        json_str = result.to_json()
        assert "start_time" in json_str
        assert "total" in json_str
```

---

## 4. 使用示例

```bash
# 安装工具
pip install -e .

# 添加前缀
rename-tool add-prefix --prefix "photo_" --directory ./images

# 替换空格为下划线
rename-tool replace --old " " --new "_" --directory ./files

# 序号重命名
rename-tool sequence --template "doc_{index:03d}" --directory ./docs

# 正则替换
rename-tool regex --pattern "(\d+)" --replacement "file_\1" --directory ./data

# 预览模式
rename-tool add-prefix --prefix "test_" --directory ./images --dry-run

# 保存报告
rename-tool replace --old " " --new "_" --directory ./files --output report.json

# 详细输出
rename-tool add-prefix --prefix "test_" --directory ./images -v

# 只处理 .txt 文件
rename-tool add-prefix --prefix "text_" --directory ./files --filter "*.txt"
```

---

## 5. 项目文档

### README.md 模板

```markdown
# Rename Tool

文件批量重命名工具 - 让文件管理更简单

## 功能特性

- ✅ 添加前缀/后缀
- ✅ 替换字符串
- ✅ 正则替换
- ✅ 序号重命名
- ✅ 日期重命名
- ✅ 大小写转换
- ✅ 预览模式
- ✅ JSON 报告

## 安装

```bash
pip install rename-tool
```

## 使用方法

```bash
# 添加前缀
rename-tool add-prefix --prefix "photo_" --directory ./images

# 替换字符串
rename-tool replace --old " " --new "_" --directory ./files

# 预览模式
rename-tool add-prefix --prefix "test_" --directory ./images --dry-run
```

## 开发

```bash
# 克隆仓库
git clone https://github.com/yourname/rename-tool.git
cd rename-tool

# 安装依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 生成覆盖率报告
pytest --cov=rename_tool --cov-report=html
```

## 许可证

MIT License
```

---

## 今日总结

- **CLI 工具构建**：argparse + 子命令模式
- **项目结构**：src layout 是现代 Python 项目的标准
- **日志系统**：logging 模块的完整配置
- **测试覆盖**：单元测试 + 集成测试
- **文档编写**：README + docstring + CHANGELOG
- **打包发布**：pyproject.toml + 构建工具

---

## 练习题

### 练习 1：扩展功能 ⭐⭐
为重命名工具添加以下功能：
- 按文件大小重命名
- 按文件类型分组重命名
- 批量移动到子目录
- 支持撤销操作

### 练习 2：Web 界面 ⭐⭐⭐
为重命名工具添加 Web 界面：
- 使用 Flask/FastAPI
- 上传文件并预览重命名
- 实时预览变更
- 下载重命名报告

### 练习 3：插件系统 ⭐⭐⭐
为重命名工具实现插件系统：
- 定义插件接口
- 实现内置插件
- 支持第三方插件
- 插件配置管理

### 练习 4：性能优化 ⭐⭐⭐⭐
优化重命名工具的性能：
- 异步文件操作
- 并发重命名
- 进度条显示
- 内存优化

### 练习 5：完整发布 ⭐⭐⭐⭐
将重命名工具发布到 PyPI：
- 完善项目结构
- 编写完整文档
- 添加 CI/CD
- 发布到 PyPI

---

## 🎉 恭喜完成 Phase 5！

你已经完成了标准库与生态系统的所有学习：
- ✅ Day 072: 正则表达式深入
- ✅ Day 073: 包管理与虚拟环境
- ✅ Day 074: 单元测试进阶
- ✅ Day 075: 阶段项目实战

下一步：Phase 6 将进入**实战项目**阶段，我们将构建真实世界的应用！
