#!/usr/bin/env python3
"""
Day 098 - Python 内部机制
示例 03: 实战 - 字节码分析器

一个完整的字节码分析工具，可以：
1. 反汇编任意函数或代码字符串
2. 统计指令频率
3. 分析常量池和变量
4. 检测潜在的性能问题
5. 生成可读的分析报告
"""

import dis
import sys
import timeit
import types
import ast
from collections import Counter, defaultdict
from io import StringIO


class BytecodeAnalyzer:
    """字节码分析器"""

    def __init__(self):
        self.results = {}

    def analyze_function(self, func):
        """分析一个函数的字节码"""
        if not callable(func):
            raise ValueError(f"参数必须是可调用对象，得到: {type(func)}")

        code = func.__code__ if hasattr(func, '__code__') else func
        if not isinstance(code, types.CodeType):
            raise ValueError(f"无法获取代码对象: {type(code)}")

        instructions = list(dis.get_instructions(code))

        result = {
            "name": getattr(func, '__name__', '<unknown>'),
            "code_object": code,
            "instructions": instructions,
            "code_size": len(code.co_code),
            "instruction_count": len(instructions),
            "argcount": code.co_argcount,
            "nlocals": code.co_nlocals,
            "stacksize": code.co_stacksize,
            "consts": code.co_consts,
            "varnames": code.co_varnames,
            "names": code.co_names,
            "filename": code.co_filename,
            "firstlineno": code.co_firstlineno,
            "flags": code.co_flags,
        }

        # 指令频率统计
        opcode_counts = Counter(instr.opname for instr in instructions)
        result["opcode_frequency"] = dict(opcode_counts.most_common())

        # 操作数分析
        arg_counts = Counter()
        for instr in instructions:
            if instr.arg is not None:
                arg_counts[instr.opname] += 1
        result["arg_frequency"] = dict(arg_counts.most_common())

        # 调用分析
        calls = [instr for instr in instructions if "CALL" in instr.opname]
        result["calls"] = [
            {"opname": c.opname, "arg": c.arg, "argval": c.argval}
            for c in calls
        ]

        # 跳转分析
        jumps = [instr for instr in instructions if "JUMP" in instr.opname or "FOR_ITER" in instr.opname]
        result["jumps"] = [
            {"opname": j.opname, "arg": j.arg, "argval": j.argval}
            for j in jumps
        ]

        # 循环检测
        result["has_loops"] = any("FOR_ITER" in j["opname"] for j in result["jumps"])

        # 异常处理
        result["has_try"] = any(instr.opname == "SETUP_FINALLY" or
                                instr.opname == "PUSH_EXC_INFO"
                                for instr in instructions)

        self.results[result["name"]] = result
        return result

    def analyze_code_string(self, code_str):
        """分析代码字符串"""
        code = compile(code_str, "<analysis>", "exec")
        return self.analyze_function(code)

    def format_disassembly(self, func):
        """格式化反汇编输出"""
        output = StringIO()
        dis.dis(func, file=output)
        return output.getvalue()

    def generate_report(self, name=None):
        """生成分析报告"""
        if name and name in self.results:
            results = {name: self.results[name]}
        else:
            results = self.results

        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("              Python 字节码分析报告")
        report_lines.append("=" * 70)

        for fname, result in results.items():
            report_lines.append(f"\n{'─' * 70}")
            report_lines.append(f"函数: {result['name']}")
            report_lines.append(f"源文件: {result['filename']}")
            report_lines.append(f"起始行号: {result['firstlineno']}")
            report_lines.append(f"{'─' * 70}")

            # 基本信息
            report_lines.append(f"\n📊 基本信息:")
            report_lines.append(f"  字节码大小: {result['code_size']} 字节")
            report_lines.append(f"  指令数: {result['instruction_count']}")
            report_lines.append(f"  参数数: {result['argcount']}")
            report_lines.append(f"  局部变量数: {result['nlocals']}")
            report_lines.append(f"  栈大小: {result['stacksize']}")
            report_lines.append(f"  标志位: {bin(result['flags'])}")

            # 常量池
            report_lines.append(f"\n📦 常量池 ({len(result['consts'])} 个):")
            for i, const in enumerate(result["consts"]):
                const_type = type(const).__name__
                report_lines.append(f"  [{i}] {const_type}: {repr(const)}")

            # 变量名
            report_lines.append(f"\n📝 局部变量 ({len(result['varnames'])} 个):")
            for i, var in enumerate(result["varnames"]):
                report_lines.append(f"  [{i}] {var}")

            # 全局/属性名
            report_lines.append(f"\n🌐 全局/属性名 ({len(result['names'])} 个):")
            for i, name in enumerate(result["names"]):
                report_lines.append(f"  [{i}] {name}")

            # 指令频率
            report_lines.append(f"\n📈 指令频率 (Top 10):")
            for opname, count in list(result["opcode_frequency"].items())[:10]:
                bar = "█" * min(count, 30)
                report_lines.append(f"  {opname:25s} {count:3d} {bar}")

            # 函数调用
            if result["calls"]:
                report_lines.append(f"\n📞 函数调用 ({len(result['calls'])} 个):")
                for call in result["calls"]:
                    report_lines.append(f"  {call['opname']}: {call['argval']}")

            # 跳转指令
            if result["jumps"]:
                report_lines.append(f"\n🔀 跳转指令 ({len(result['jumps'])} 个):")
                for jump in result["jumps"]:
                    report_lines.append(f"  {jump['opname']}: 目标偏移={jump['arg']}")

            # 特征检测
            report_lines.append(f"\n🔍 特征检测:")
            report_lines.append(f"  包含循环: {'✅ 是' if result['has_loops'] else '❌ 否'}")
            report_lines.append(f"  包含 try-except: {'✅ 是' if result['has_try'] else '❌ 否'}")

            # 反汇编
            report_lines.append(f"\n🔧 完整反汇编:")
            disasm = self.format_disassembly(
                result["code_object"] if isinstance(result["code_object"], types.CodeType) else func
            )
            for line in disasm.split('\n'):
                report_lines.append(f"  {line}")

        report_lines.append(f"\n{'=' * 70}")
        report_lines.append(f"分析完成！共分析 {len(results)} 个函数/代码块")
        report_lines.append(f"{'=' * 70}")

        return '\n'.join(report_lines)

    def compare_functions(self, func1, func2):
        """比较两个函数的字节码"""
        r1 = self.analyze_function(func1)
        r2 = self.analyze_function(func2)

        comparison = []
        comparison.append("=" * 70)
        comparison.append("           函数字节码对比分析")
        comparison.append("=" * 70)

        comparison.append(f"\n{'指标':<20s} {'函数1':>12s} {'函数2':>12s} {'差异':>12s}")
        comparison.append("-" * 60)

        metrics = [
            ("字节码大小", "code_size"),
            ("指令数", "instruction_count"),
            ("参数数", "argcount"),
            ("局部变量数", "nlocals"),
            ("栈大小", "stacksize"),
            ("常量数", None),
        ]

        for label, key in metrics:
            v1 = r1[key] if key else len(r1["consts"])
            v2 = r2[key] if key else len(r2["consts"])
            diff = v2 - v1
            diff_str = f"+{diff}" if diff > 0 else str(diff)
            comparison.append(f"{label:<20s} {v1:>12d} {v2:>12d} {diff_str:>12s}")

        # 指令频率对比
        comparison.append(f"\n📊 指令频率对比:")
        all_opcodes = set(r1["opcode_frequency"].keys()) | set(r2["opcode_frequency"].keys())
        for op in sorted(all_opcodes):
            c1 = r1["opcode_frequency"].get(op, 0)
            c2 = r2["opcode_frequency"].get(op, 0)
            if c1 != c2:
                comparison.append(f"  {op:25s}: {c1:3d} → {c2:3d}")

        return '\n'.join(comparison)

    def detect_performance_issues(self, func):
        """检测潜在的性能问题"""
        result = self.analyze_function(func)
        issues = []

        # 检查 1: 过多的全局变量访问
        global_loads = sum(1 for instr in result["instructions"]
                          if instr.opname == "LOAD_GLOBAL")
        if global_loads > 5:
            issues.append({
                "severity": "warning",
                "message": f"全局变量访问过多 ({global_loads} 次)，考虑使用局部变量",
            })

        # 检查 2: 过深的嵌套
        max_depth = 0
        current_depth = 0
        for instr in result["instructions"]:
            if instr.opname in ("SETUP_FINALLY", "SETUP_WITH"):
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif instr.opname in ("POP_BLOCK",):
                current_depth -= 1

        if max_depth > 3:
            issues.append({
                "severity": "warning",
                "message": f"嵌套深度过深 ({max_depth} 层)，考虑重构",
            })

        # 检查 3: 字节码大小
        if result["code_size"] > 1000:
            issues.append({
                "severity": "info",
                "message": f"字节码较大 ({result['code_size']} 字节)，考虑拆分函数",
            })

        # 检查 4: 指令数
        if result["instruction_count"] > 200:
            issues.append({
                "severity": "info",
                "message": f"指令数较多 ({result['instruction_count']})，考虑简化逻辑",
            })

        # 检查 5: 没有循环但有很多跳转
        if not result["has_loops"] and len(result["jumps"]) > 10:
            issues.append({
                "severity": "info",
                "message": f"无循环但有 {len(result['jumps'])} 个跳转，可能存在复杂条件逻辑",
            })

        return issues


# ============================================================
# 主程序：演示分析器的使用
# ============================================================
def main():
    analyzer = BytecodeAnalyzer()

    # 示例 1: 分析简单函数
    print("\n🔬 示例 1: 分析简单函数\n")

    def fibonacci(n):
        """斐波那契数列（递归实现）"""
        if n <= 1:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)

    report = analyzer.generate_report()  # 空报告，后面会填充
    result = analyzer.analyze_function(fibonacci)
    print(analyzer.generate_report("fibonacci"))

    # 示例 2: 分析列表操作
    print("\n\n🔬 示例 2: 分析列表操作\n")

    def process_data(data):
        """数据处理函数"""
        result = []
        for item in data:
            if isinstance(item, (int, float)):
                result.append(item * 2)
            elif isinstance(item, str):
                result.append(item.upper())
        return result

    analyzer.analyze_function(process_data)
    print(analyzer.generate_report("process_data"))

    # 示例 3: 分析异常处理
    print("\n\n🔬 示例 3: 分析异常处理\n")

    def safe_divide(a, b):
        """安全除法"""
        try:
            result = a / b
        except ZeroDivisionError:
            result = None
        except TypeError:
            result = None
        return result

    analyzer.analyze_function(safe_divide)
    print(analyzer.generate_report("safe_divide"))

    # 示例 4: 对比两个函数
    print("\n\n🔬 示例 4: 对比两个函数\n")

    def list_comp_version(n):
        """列表推导式版本"""
        return [x ** 2 for x in range(n)]

    def loop_version(n):
        """普通循环版本"""
        result = []
        for x in range(n):
            result.append(x ** 2)
        return result

    analyzer.analyze_function(list_comp_version)
    analyzer.analyze_function(loop_version)
    print(analyzer.compare_functions(list_comp_version, loop_version))

    # 示例 5: 性能检测
    print("\n\n🔬 示例 5: 性能问题检测\n")

    def problematic_function():
        """一个有潜在性能问题的函数"""
        import os
        import sys
        import json
        x = 1
        y = 2
        z = 3
        a = os.path.join("a", "b")
        b = sys.path
        c = json.dumps({"x": x})
        return a, b, c

    issues = analyzer.detect_performance_issues(problematic_function)
    if issues:
        print("检测到的潜在问题:")
        for issue in issues:
            emoji = "⚠️" if issue["severity"] == "warning" else "ℹ️"
            print(f"  {emoji} {issue['message']}")
    else:
        print("未检测到明显的性能问题")

    # 示例 6: 分析代码字符串
    print("\n\n🔬 示例 6: 分析代码字符串\n")

    code_str = """
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
"""

    result = analyzer.analyze_code_string(code_str)
    print(analyzer.generate_report("<代码字符串>"))

    print("\n✅ 字节码分析器演示完成！")


if __name__ == "__main__":
    main()
