"""
Day 075 — 文件批量重命名工具：核心逻辑
运行方式：python file_renamer.py --help
"""
import os
import re
import json
import logging
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


# ========== 自定义异常 ==========


class RenameToolError(Exception):
    """重命名工具基础异常"""
    pass


class DirectoryNotFoundError(RenameToolError):
    """目录不存在"""
    pass


class PatternError(RenameToolError):
    """正则模式错误"""
    pass


# ========== 日志配置 ==========


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """配置日志"""
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
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


logger = logging.getLogger(__name__)


# ========== 核心类 ==========


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
            raise DirectoryNotFoundError(f"目录不存在: {directory}")

        if not self.directory.is_dir():
            raise ValueError(f"不是目录: {directory}")

    def _get_files(self, pattern: Optional[str] = None) -> List[Path]:
        """获取文件列表"""
        if pattern:
            return sorted(self.directory.glob(pattern))
        return sorted(self.directory.iterdir())

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
                    new_stem = re.sub(r'([A-Z])', r'_\1', stem).lower().lstrip('_')
                elif case == "camel":
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


# ========== 工具函数 ==========


def preview_changes(operations: List[RenameOperation]) -> None:
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


def save_report(result: RenameResult, output_file: str) -> None:
    """保存重命名报告"""
    report = result.to_dict()
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"报告已保存: {output_file}")


# ========== 命令行接口 ==========


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="file-renamer",
        description="文件批量重命名工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 添加前缀
  python file_renamer.py add-prefix --prefix "photo_" --directory ./images

  # 替换字符串
  python file_renamer.py replace --old " " --new "_" --directory ./files

  # 序号重命名
  python file_renamer.py sequence --template "doc_{index:03d}" --directory ./docs

  # 预览模式
  python file_renamer.py add-prefix --prefix "test_" --directory ./images --dry-run
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
