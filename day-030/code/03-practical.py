"""
Day 030 — 阶段项目：命令行工具
======================================================================
实战案例：完整的多功能 CLI 工具集
  1. 文件信息查看器 (file-info)
  2. 代码统计工具 (code-stats)
  3. 目录树查看器 (tree)
  4. 日志分析器 (log-analyzer)
======================================================================
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict

# ====================================================================
# 工具模块
# ====================================================================

class FileInfoTool:
    """文件信息查看器"""

    @staticmethod
    def get_info(path):
        """获取文件/目录的详细信息"""
        p = Path(path)
        if not p.exists():
            return {"error": f"路径不存在: {path}"}

        info = {
            "path": str(p.absolute()),
            "name": p.name,
            "type": "文件" if p.is_file() else "目录" if p.is_dir() else "其他",
            "size": p.stat().st_size if p.exists() else 0,
        }

        if p.is_file():
            info.update({
                "extension": p.suffix,
                "parent": str(p.parent),
            })
        elif p.is_dir():
            files = list(p.rglob('*'))
            info.update({
                "total_items": len(files),
                "files": sum(1 for f in files if f.is_file()),
                "dirs": sum(1 for f in files if f.is_dir()),
            })

        # 权限
        stat = p.stat()
        info["permissions"] = oct(stat.st_mode)[-3:]
        info["modified"] = datetime.fromtimestamp(
            stat.st_mtime).isoformat()
        info["created"] = datetime.fromtimestamp(
            stat.st_ctime).isoformat()

        return info

    @staticmethod
    def format_size(size_bytes):
        """人性化显示文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    @staticmethod
    def display(info):
        """显示文件信息"""
        if "error" in info:
            print(f"❌ {info['error']}")
            return

        print(f"\n📁 文件信息")
        print(f"  {'名称':<12}: {info['name']}")
        print(f"  {'路径':<12}: {info['path']}")
        print(f"  {'类型':<12}: {info['type']}")
        print(f"  {'大小':<12}: {FileInfoTool.format_size(info['size'])}")

        if 'extension' in info:
            print(f"  {'扩展名':<12}: {info['extension']}")
        if 'total_items' in info:
            print(f"  {'总项目':<12}: {info['total_items']} "
                  f"(文件: {info['files']}, 目录: {info['dirs']})")

        print(f"  {'权限':<12}: {info['permissions']}")
        print(f"  {'修改时间':<12}: {info['modified']}")
        print(f"  {'创建时间':<12}: {info['created']}")


class CodeStatsTool:
    """代码统计工具"""

    LANG_MAP = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.java': 'Java',
        '.c': 'C',
        '.cpp': 'C++',
        '.h': 'C/C++ Header',
        '.html': 'HTML',
        '.css': 'CSS',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
    }

    @staticmethod
    def count_file(filepath):
        """统计单个文件"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        total = len(lines)
        code = 0
        comments = 0
        blanks = 0
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blanks += 1
                continue

            # 多行注释检查
            if in_multiline_comment:
                comments += 1
                if '*/' in stripped or '"""' in stripped:
                    in_multiline_comment = False
                continue

            if stripped.startswith('#'):
                comments += 1
            elif stripped.startswith('//'):
                comments += 1
            elif '/*' in stripped:
                comments += 1
                if '*/' not in stripped:
                    in_multiline_comment = True
            elif '"""' in stripped and stripped.count('"""') % 2 != 0:
                comments += 1
                in_multiline_comment = True
            else:
                code += 1

        return {
            'file': str(filepath),
            'total': total,
            'code': code,
            'comments': comments,
            'blanks': blanks,
        }

    @staticmethod
    def count_directory(root_dir, extensions=None):
        """统计整个目录"""
        if extensions is None:
            extensions = list(CodeStatsTool.LANG_MAP.keys())

        results = []
        total = {'files': 0, 'total': 0, 'code': 0,
                 'comments': 0, 'blanks': 0}
        lang_totals = defaultdict(lambda: {'files': 0, 'code': 0})

        for path in Path(root_dir).rglob('*'):
            if path.is_file() and path.suffix in extensions:
                stats = CodeStatsTool.count_file(path)
                results.append(stats)

                total['files'] += 1
                total['total'] += stats['total']
                total['code'] += stats['code']
                total['comments'] += stats['comments']
                total['blanks'] += stats['blanks']

                lang = CodeStatsTool.LANG_MAP.get(
                    path.suffix, path.suffix)
                lang_totals[lang]['files'] += 1
                lang_totals[lang]['code'] += stats['code']

        return total, lang_totals, results

    @staticmethod
    def display_summary(total, lang_totals):
        """显示汇总"""
        print(f"\n📊 代码统计汇总")
        print(f"  {'='*45}")
        print(f"  {'总文件数':<15}: {total['files']}")
        print(f"  {'总行数':<15}: {total['total']:,}")
        print(f"  {'代码行':<15}: {total['code']:,} "
              f"({total['code']/max(total['total'],1)*100:.1f}%)")
        print(f"  {'注释行':<15}: {total['comments']:,} "
              f"({total['comments']/max(total['total'],1)*100:.1f}%)")
        print(f"  {'空行':<15}: {total['blanks']:,} "
              f"({total['blanks']/max(total['total'],1)*100:.1f}%)")

        print(f"\n  📈 按语言统计:")
        print(f"  {'语言':<20} {'文件数':<8} {'代码行':<10}")
        print(f"  {'-'*38}")
        for lang, stats in sorted(
                lang_totals.items(),
                key=lambda x: -x[1]['code']):
            print(f"  {lang:<20} {stats['files']:<8} {stats['code']:<10,}")


class TreeTool:
    """目录树查看器"""

    SYMBOLS = {
        'branch': '├── ',
        'last': '└── ',
        'pipe': '│   ',
        'space': '    ',
    }

    @staticmethod
    def generate(root_dir, max_depth=None, show_size=False,
                 show_hidden=False, exclude_dirs=None):
        """生成目录树"""
        root = Path(root_dir)
        if not root.exists():
            return f"错误: 目录不存在 '{root_dir}'"

        if exclude_dirs is None:
            exclude_dirs = {'.git', '__pycache__', '.venv',
                           'node_modules', '.idea'}

        lines = [f"\n🌳 目录树: {root.absolute()}"]

        def _walk(path, prefix='', depth=0):
            if max_depth is not None and depth > max_depth:
                return

            try:
                entries = sorted(
                    path.iterdir(),
                    key=lambda p: (not p.is_dir(), p.name.lower())
                )
            except PermissionError:
                return

            for i, entry in enumerate(entries):
                is_last = (i == len(entries) - 1)

                # 跳过隐藏文件
                if not show_hidden and entry.name.startswith('.'):
                    continue

                # 跳过排除目录
                if entry.name in exclude_dirs:
                    continue

                # 选择符号
                connector = TreeTool.SYMBOLS['last'] if is_last \
                    else TreeTool.SYMBOLS['branch']

                # 文件大小
                size_str = ""
                if show_size and entry.is_file():
                    size = entry.stat().st_size
                    size_str = f" ({FileInfoTool.format_size(size)})"

                lines.append(f"{prefix}{connector}{entry.name}{size_str}")

                # 递归子目录
                if entry.is_dir():
                    next_prefix = prefix + \
                        (TreeTool.SYMBOLS['space'] if is_last
                         else TreeTool.SYMBOLS['pipe'])
                    _walk(entry, next_prefix, depth + 1)

        _walk(root)
        return '\n'.join(lines)


class LogAnalyzer:
    """日志分析器"""

    @staticmethod
    def parse_log_line(line):
        """解析单行日志（假设格式: 2024-01-01 12:00:00 [LEVEL] message）"""
        try:
            parts = line.strip().split(' ', 2)
            if len(parts) >= 3:
                timestamp = f"{parts[0]} {parts[1]}"
                rest = parts[2]
                if rest.startswith('['):
                    level = rest[1:rest.index(']')]
                    message = rest[rest.index(']') + 2:]
                    return {
                        'timestamp': timestamp,
                        'level': level,
                        'message': message,
                    }
            return None
        except (ValueError, IndexError):
            return None

    @staticmethod
    def analyze(log_file):
        """分析日志文件"""
        if not os.path.exists(log_file):
            return {"error": f"文件不存在: {log_file}"}

        stats = Counter()
        errors = []
        hourly = defaultdict(int)
        messages = []

        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parsed = LogAnalyzer.parse_log_line(line)
                if parsed:
                    stats[parsed['level']] += 1
                    messages.append(parsed)

                    if parsed['level'] == 'ERROR':
                        errors.append(parsed)

                    # 按小时统计
                    try:
                        hour = datetime.fromisoformat(
                            parsed['timestamp']).hour
                        hourly[hour] += 1
                    except ValueError:
                        pass

        return {
            'total_lines': len(messages),
            'level_stats': dict(stats),
            'errors': errors[:10],  # 只保留前10个错误
            'hourly_distribution': dict(sorted(hourly.items())),
            'sample_messages': messages[:5],
        }

    @staticmethod
    def display(results):
        """显示分析结果"""
        if "error" in results:
            print(f"❌ {results['error']}")
            return

        print(f"\n📋 日志分析报告")
        print(f"  {'='*45}")
        print(f"  总消息数: {results['total_lines']}")

        print(f"\n  级别分布:")
        levels = {'INFO': 'INFO', 'WARNING': 'WARN',
                  'ERROR': 'ERR', 'DEBUG': 'DEBUG'}
        colors = {'INFO': '✅', 'WARNING': '⚠️',
                  'ERROR': '❌', 'DEBUG': '🔍'}
        for level, count in sorted(
                results['level_stats'].items(),
                key=lambda x: -x[1]):
            emoji = colors.get(level, '📝')
            print(f"    {emoji} {level:<10} {count:>5} 条")

        if results['errors']:
            print(f"\n  错误示例 (前{len(results['errors'])}条):")
            for err in results['errors']:
                print(f"    ❌ [{err['timestamp']}] {err['message'][:60]}")

        print(f"\n  按小时分布 (活跃时段):")
        peak_hour = max(results['hourly_distribution'],
                        key=results['hourly_distribution'].get)
        total = sum(results['hourly_distribution'].values())
        for hour in range(0, 24):
            count = results['hourly_distribution'].get(hour, 0)
            bar = '█' * int(count / max(total, 1) * 30)
            marker = ' ◀ PEAK' if hour == peak_hour else ''
            if count > 0:
                print(f"    {hour:02d}:00 {bar} {count}{marker}")


# ====================================================================
# 演示入口
# ====================================================================
print("=" * 60)
print("📦 Day 30 实战案例：多功能命令行工具集")
print("=" * 60)

# ---- 案例1：文件信息查看器 ----
print("\n" + "=" * 60)
print("案例1: 文件信息查看器")
print("=" * 60)
info = FileInfoTool.get_info(__file__)
FileInfoTool.display(info)

# ---- 案例2：代码统计工具 ----
print("\n" + "=" * 60)
print("案例2: 代码统计工具")
print("=" * 60)
total, lang_totals, _ = CodeStatsTool.count_directory(
    Path(__file__).parent, extensions=['.py'])
CodeStatsTool.display_summary(total, lang_totals)

# ---- 案例3：目录树查看器 ----
print("\n" + "=" * 60)
print("案例3: 目录树查看器")
print("=" * 60)
tree = TreeTool.generate(
    Path(__file__).parent,
    max_depth=2,
    show_size=True
)
print(tree)

# ---- 案例4：日志分析器 ----
print("\n" + "=" * 60)
print("案例4: 日志分析器")
print("=" * 60)

# 生成模拟日志
log_path = Path('/tmp/test_app.log')
log_lines = [
    "2024-06-20 08:15:30 [INFO] Application started",
    "2024-06-20 08:15:31 [INFO] Loading configuration...",
    "2024-06-20 08:15:32 [DEBUG] Config loaded: {'debug': True}",
    "2024-06-20 08:15:33 [INFO] Connecting to database...",
    "2024-06-20 08:15:35 [WARNING] Connection pool at 80% capacity",
    "2024-06-20 08:15:36 [INFO] Database connection established",
    "2024-06-20 08:15:40 [INFO] User login: alice",
    "2024-06-20 08:15:42 [INFO] User login: bob",
    "2024-06-20 08:20:01 [ERROR] Connection timeout to backup server",
    "2024-06-20 08:20:02 [ERROR] Backup failed: retrying in 30s",
    "2024-06-20 08:20:05 [WARNING] Disk usage at 85%",
    "2024-06-20 08:25:00 [INFO] Scheduled task started: cleanup",
    "2024-06-20 08:25:01 [DEBUG] Cleaning temp files...",
    "2024-06-20 08:25:05 [INFO] Cleanup complete: 150MB freed",
    "2024-06-20 09:00:00 [ERROR] Database connection lost",
    "2024-06-20 09:00:01 [ERROR] Reconnection failed: max retries",
    "2024-06-20 09:00:02 [CRITICAL] Service unavailable",
    "2024-06-20 09:05:00 [INFO] Service restart initiated",
    "2024-06-20 09:05:03 [INFO] Service restarted successfully",
    "2024-06-20 09:10:00 [INFO] User logout: alice",
]
log_path.write_text('\n'.join(log_lines))

results = LogAnalyzer.analyze(str(log_path))
LogAnalyzer.display(results)

# ---- 案例5：Phase 2 结项总结 ----
print("\n" + "=" * 60)
print("🎉 Phase 2 结项 — 核心编程概念阶段完成!")
print("=" * 60)

print(f"""
  Phase 2 涵盖内容:
  ┌─────────────────────────────────────────────┐
  │  Day 16: 列表详解                            │
  │  Day 17: 元组与集合                          │
  │  Day 18: 字典详解                            │
  │  Day 19: 字符串处理                          │
  │  Day 20: 函数进阶                            │
  │  Day 21: 迭代器与生成器                      │
  │  Day 22: 装饰器                              │
  │  Day 23: 高阶函数与函数式编程                │
  │  Day 24: 装饰器进阶                          │
  │  Day 25: 上下文管理器                        │
  │  Day 26: 字符串进阶                          │
  │  Day 27: datetime 模块                       │
  │  Day 28: 数据结构综合                        │
  │  Day 29: 算法入门                            │
  │  Day 30: 命令行工具 (阶段项目) 🏆            │
  └─────────────────────────────────────────────┘

  核心能力:
  ✅ 掌握 Python 所有内置数据结构
  ✅ 理解函数式编程与高阶函数
  ✅ 能编写装饰器与上下文管理器
  ✅ 理解时间复杂度和基本算法
  ✅ 能构建命令行工具

  下一阶段: Phase 3 — 面向对象编程 🚀
""")

print("=" * 60)
print("✅  实战案例全部完成!")
print("=" * 60)
