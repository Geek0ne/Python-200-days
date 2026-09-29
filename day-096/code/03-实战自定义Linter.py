"""
Day 096 - 代码分析 - 03: 实战 — 自定义 Linter
一个完整的、可运行的代码检查工具，检查命名规范、代码质量等。
"""
import ast
import re
import sys
from dataclasses import dataclass
from typing import List, Optional


# =============================================
# 数据结构：一条 Lint 告警
# =============================================

@dataclass
class LintWarning:
    """
    一条 Lint 告警
    - line: 行号
    - col: 列号
    - code: 规则编号（如 W001, E001）
    - message: 告警描述
    - severity: 严重程度（warning / error）
    """
    line: int
    col: int
    code: str
    message: str
    severity: str

    def __str__(self):
        icon = "⚠️" if self.severity == "warning" else "❌"
        return f"  {icon} L{self.line}:{self.col} [{self.code}] {self.message}"


# =============================================
# Linter 核心：规则检查器
# =============================================

class MyLinter(ast.NodeVisitor):
    """
    自定义 Linter，包含 6 条检查规则：
    - W001: 函数名应使用 snake_case
    - W002: 函数不应超过 50 行
    - W003: 函数参数不应超过 5 个
    - W004: 变量名应使用 snake_case
    - W005: 类名应使用 PascalCase
    - E001: 不应使用裸 except（不指定异常类型）
    """

    def __init__(self):
        self.warnings: List[LintWarning] = []
        self._current_class: Optional[str] = None

    # ----- 节点访问入口 -----

    def visit_FunctionDef(self, node):
        self._rule_func_name(node)
        self._rule_func_length(node)
        self._rule_func_args(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        # 异步函数也走同样的规则
        self._rule_func_name(node)
        self._rule_func_length(node)
        self._rule_func_args(node)
        self.generic_visit(node)

    def visit_Assign(self, node):
        self._rule_var_name(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self._rule_class_name(node)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self._rule_bare_except(node)
        self.generic_visit(node)

    # ----- 规则实现 -----

    def _rule_func_name(self, node):
        """W001: 函数名应使用 snake_case"""
        if not re.match(r'^_?[a-z][a-z0-9_]*$', node.name):
            self.warnings.append(LintWarning(
                line=node.lineno, col=node.col_offset,
                code="W001",
                message=f"函数名 '{node.name}' 应使用 snake_case 命名风格",
                severity="warning"
            ))

    def _rule_func_length(self, node):
        """W002: 函数不应超过 50 行"""
        end_line = getattr(node, 'end_lineno', None)
        if end_line:
            length = end_line - node.lineno + 1
            if length > 50:
                self.warnings.append(LintWarning(
                    line=node.lineno, col=node.col_offset,
                    code="W002",
                    message=f"函数 '{node.name}' 共 {length} 行，建议不超过 50 行",
                    severity="warning"
                ))

    def _rule_func_args(self, node):
        """W003: 函数参数不应超过 5 个"""
        args = node.args.args
        # 排除 self/cls
        real_args = [a for a in args if a.arg not in ('self', 'cls')]
        if len(real_args) > 5:
            self.warnings.append(LintWarning(
                line=node.lineno, col=node.col_offset,
                code="W003",
                message=f"函数 '{node.name}' 有 {len(real_args)} 个参数，建议不超过 5 个",
                severity="warning"
            ))

    def _rule_var_name(self, node):
        """W004: 变量名应使用 snake_case"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                # 跳过下划线开头的私有变量
                if name.startswith('_'):
                    continue
                if not re.match(r'^[a-z][a-z0-9_]*$', name):
                    self.warnings.append(LintWarning(
                        line=node.lineno, col=node.col_offset,
                        code="W004",
                        message=f"变量名 '{name}' 应使用 snake_case",
                        severity="warning"
                    ))

    def _rule_class_name(self, node):
        """W005: 类名应使用 PascalCase"""
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
            self.warnings.append(LintWarning(
                line=node.lineno, col=node.col_offset,
                code="W005",
                message=f"类名 '{node.name}' 应使用 PascalCase",
                severity="warning"
            ))

    def _rule_bare_except(self, node):
        """E001: 不应使用裸 except（不指定异常类型）"""
        if node.type is None:
            self.warnings.append(LintWarning(
                line=node.lineno, col=node.col_offset,
                code="E001",
                message="不应使用裸 except，请指定异常类型（如 except ValueError）",
                severity="error"
            ))

    def get_summary(self) -> dict:
        """获取统计摘要"""
        errors = [w for w in self.warnings if w.severity == "error"]
        warnings = [w for w in self.warnings if w.severity == "warning"]
        return {
            'total': len(self.warnings),
            'errors': len(errors),
            'warnings': len(warnings),
        }


# =============================================
# 项目级 Linter：多文件扫描
# =============================================

class ProjectLinter:
    """项目级别的 Linter，支持递归扫描"""

    SKIP_DIRS = {'venv', '.venv', 'node_modules', '__pycache__', '.git', 'dist', 'build'}

    def __init__(self, root_dir: str):
        from pathlib import Path
        self.root = Path(root_dir)

    def find_files(self) -> list:
        """查找所有 .py 文件（排除虚拟环境等目录）"""
        files = []
        for path in self.root.rglob("*.py"):
            if any(skip in path.parts for skip in self.SKIP_DIRS):
                continue
            files.append(path)
        return sorted(files)

    def lint_file(self, filepath) -> tuple:
        """分析单个文件，返回 (source, warnings)"""
        try:
            source = filepath.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(filepath))
            linter = MyLinter()
            linter.visit(tree)
            return source, linter.warnings
        except SyntaxError as e:
            return "", [LintWarning(
                line=e.lineno or 1,
                col=e.offset or 0,
                code="E999",
                message=f"语法错误: {e.msg}",
                severity="error"
            )]

    def lint_project(self) -> tuple:
        """扫描整个项目"""
        files = self.find_files()
        print(f"🔍 扫描 {len(files)} 个 Python 文件...\n")

        all_warnings = []
        files_with_issues = 0

        for filepath in files:
            source, warnings = self.lint_file(filepath)
            if warnings:
                files_with_issues += 1
                rel = filepath.relative_to(self.root)
                print(f"📄 {rel}")
                for w in warnings:
                    print(w)
                print()

                # 显示问题代码行
                if source:
                    lines = source.splitlines()
                    for w in warnings:
                        if w.line and 0 < w.line <= len(lines):
                            code_line = lines[w.line - 1].rstrip()
                            print(f"    → {w.line} | {code_line}")
                    print()

            all_warnings.extend(warnings)

        # 统计
        errors = sum(1 for w in all_warnings if w.severity == "error")
        warns = sum(1 for w in all_warnings if w.severity == "warning")

        print("=" * 60)
        print(f"📊 扫描完成: {files_with_issues} 个文件有问题")
        print(f"   ❌ 错误: {errors}")
        print(f"   ⚠️  警告: {warns}")

        # 按规则统计
        rule_counts = {}
        for w in all_warnings:
            rule_counts[w.code] = rule_counts.get(w.code, 0) + 1

        if rule_counts:
            print("\n   规则命中统计:")
            for code in sorted(rule_counts):
                print(f"     {code}: {rule_counts[code]} 次")

        return errors, warns


# =============================================
# 演示：分析自己的代码
# =============================================

if __name__ == "__main__":
    # 分析一个示例代码（故意写一些有问题的代码来测试）
    test_code = '''
class bad_className:
    """一个命名不规范的类"""

    def BadFunc(self, too, many, arguments, here, extra, another):
        """函数参数过多 + 命名不规范"""
        BadVariable = 10
        anotherBad = 20
        result = BadVariable + anotherBad

        if result > 0:
            try:
                x = result / 0
            except:
                print("裸 except")
        else:
            for i in range(result):
                if i > 5:
                    print(i)

        return result

    def simpleFunc(self):
        return 42
'''

    print("📝 分析示例代码：")
    print("-" * 60)
    print(test_code)
    print("-" * 60)

    tree = ast.parse(test_code)
    linter = MyLinter()
    linter.visit(tree)

    summary = linter.get_summary()
    print(f"\n发现 {summary['total']} 个问题（{summary['errors']} 错误, {summary['warnings']} 警告）\n")
    for w in sorted(linter.warnings, key=lambda x: x.line):
        print(w)

    print("\n✅ 自定义 Linter 运行完成！")
    print("\n💡 提示：这个 Linter 可以扩展为项目级别的代码检查工具。")
    print("   通过 ProjectLinter 类可以扫描整个项目目录。")
