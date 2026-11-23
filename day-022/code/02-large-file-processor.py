#!/usr/bin/env python3
"""
Day 022 - Large File Processor
大文件逐行处理实战：日志分析、CSV解析、分组汇总、文件分块

Updated 2026-06-15: Added memory-efficient log analyzer and file merger
"""

import io
import os
import tempfile
import gzip
import itertools
from collections import Counter


# ============================================================
# 1. 大文件逐行读取
# ============================================================

def read_large_file(file_path, chunk_size=1024):
    """生成器：按块读取大文件，避免内存溢出

    对于超大文件（GB 级别）非常重要——不会一次性加载整个文件。
    每次只读取 chunk_size 字节到内存。

    Args:
        file_path: 文件路径
        chunk_size: 每次读取的字节数

    Yields:
        文件块（bytes 或 str）
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def read_lines(file_path):
    """生成器：逐行读取文件

    Python 的文件对象本身就是按行缓冲的迭代器，
    但显式写出来可以更好地控制和处理。
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            yield line.rstrip('\n')  # 去掉换行符，但保留空行


def read_lines_buffered(file_path, buffer_size=8192):
    """生成器：带缓冲区控制的行读取器"""
    buffer = ''
    with open(file_path, 'r', encoding='utf-8') as f:
        while True:
            chunk = f.read(buffer_size)
            if not chunk:
                # 最后剩余的 buffer 内容
                if buffer:
                    yield buffer
                break

            buffer += chunk
            lines = buffer.split('\n')

            # 除了最后一段，其他都是完整的行
            for line in lines[:-1]:
                yield line

            # 最后一段可能不完整，保留到下次
            buffer = lines[-1]


# ============================================================
# 2. 模拟大文件生成
# ============================================================

def generate_large_log(num_lines=100000):
    """生成一个模拟的日志文件（用于测试）

    生成器在内存中创建虚拟日志数据，避免真的写到磁盘。
    这在需要处理大量数据的测试中非常有用。
    """
    import random
    levels = ['INFO', 'WARN', 'ERROR', 'DEBUG']
    modules = ['server', 'database', 'auth', 'api', 'cache']
    messages = [
        'Connection established',
        'Request processed',
        'Cache miss',
        'Authentication failed',
        'Query executed',
        'Disk I/O timeout',
        'Memory usage warning',
        'User logged in',
        'Session expired',
        'Background task completed',
    ]

    for i in range(num_lines):
        timestamp = f"2026-06-{random.randint(1,30):02d} "
        timestamp += f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
        level = random.choice(levels)
        module = random.choice(modules)
        message = random.choice(messages)
        yield f"{timestamp} [{level:>8}] [{module:>10}] {message}"


# ============================================================
# 3. 日志分析管道
# ============================================================

class LogAnalyzer:
    """基于生成器的日志分析器

    使用生成器构建处理管道：
    读取 → 过滤 → 解析 → 分组 → 统计
    """

    def __init__(self, log_generator):
        self.log_generator = log_generator

    def filter_by_level(self, level):
        """过滤指定级别的日志"""
        for line in self.log_generator:
            if f"[{level:>8}]" in line:
                yield line

    def parse(self):
        """解析日志行"""
        for line in self.log_generator:
            parts = line.split(' ', 3)
            if len(parts) >= 4:
                yield {
                    'timestamp': parts[0] + ' ' + parts[1],
                    'level': parts[2].strip('[]'),
                    'module': parts[3].strip('[]'),
                    'message': ' '.join(parts[4:]) if len(parts) > 4 else ''
                }

    def group_by_level(self):
        """按级别分组统计"""
        counter = Counter()
        for entry in self.parse():
            counter[entry['level']] += 1
        return counter

    def group_by_module(self):
        """按模块分组统计"""
        counter = Counter()
        for entry in self.parse():
            counter[entry['module']] += 1
        return counter


def test_log_analyzer():
    """测试日志分析器"""
    print("=" * 60)
    print("日志分析器（生成器管道）")
    print("=" * 60)

    # 生成测试日志
    print("\n▶ 生成 10000 条模拟日志...")
    log_gen = generate_large_log(10000)
    analyzer = LogAnalyzer(log_gen)

    # 按级别统计
    print("\n▶ 按级别统计:")
    by_level = analyzer.group_by_level()
    for level, count in by_level.most_common():
        print(f"   {level:>8}: {count:>6} 条 ({count/100:.1f}%)")

    # 按模块统计
    print("\n▶ 按模块统计:")
    log_gen = generate_large_log(10000)
    analyzer = LogAnalyzer(log_gen)
    by_module = analyzer.group_by_module()
    for module, count in by_module.most_common():
        print(f"   {module:>10}: {count:>6} 条 ({count/100:.1f}%)")

    print("\n▶ 内存使用: 只有少量日志行在内存中")
    print("   全程不需要将所有日志加载到内存！")


# ============================================================
# 4. 大文件分块处理
# ============================================================

def chunk_processor(file_path, chunk_size_mb=10):
    """生成器：按大小分块处理文件

    以 10MB 为单位处理大文件，每个块独立处理。
    适合需要在批处理中提交的场景（如数据库批量插入）。
    """
    chunk_size = chunk_size_mb * 1024 * 1024  # 字节
    chunk_num = 0
    current_chunk = []

    for line in read_lines(file_path):
        current_chunk.append(line)
        # 估算当前块的大小
        if sum(len(l) for l in current_chunk) >= chunk_size:
            chunk_num += 1
            yield chunk_num, current_chunk
            current_chunk = []

    # 最后剩余的块
    if current_chunk:
        chunk_num += 1
        yield chunk_num, current_chunk


def test_chunk_processor():
    """测试分块处理"""
    print("=" * 60)
    print("大文件分块处理")
    print("=" * 60)

    # 创建模拟文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        for i in range(1000):
            f.write(f"Line {i}: {'x' * 100}\n")
        temp_path = f.name

    print(f"\n▶ 临时文件: {temp_path}")
    print(f"   大小: {os.path.getsize(temp_path)} 字节")

    # 分块读取（每块很小，仅用于演示）
    print(f"\n▶ 以 1KB 为一块分块处理:")
    chunk_count = 0
    total_lines = 0
    for chunk_num, chunk_lines in chunk_processor(temp_path, 0.001):  # ~1KB
        chunk_count += 1
        total_lines += len(chunk_lines)
        if chunk_count <= 3:
            print(f"   块 {chunk_num}: {len(chunk_lines)} 行")

    print(f"\n▶ 总计: {chunk_count} 个数据块, {total_lines} 行")

    # 清理
    os.unlink(temp_path)


# ============================================================
# 5. CSV 文件解析器
# ============================================================

def parse_csv_line(line):
    """解析 CSV 行（简单实现，支持引号）"""
    result = []
    current = []
    in_quotes = False
    for char in line:
        if char == '"':
            in_quotes = not in_quotes
        elif char == ',' and not in_quotes:
            result.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
    result.append(''.join(current).strip())
    return result


def read_csv_generator(file_path, has_header=True):
    """生成器：逐行读取 CSV 文件

    使用生成器实现惰性 CSV 解析，适合大文件。
    """
    lines = read_lines(file_path)
    headers = None

    if has_header:
        try:
            header_line = next(lines)
            headers = parse_csv_line(header_line)
        except StopIteration:
            return

    for line in lines:
        if not line.strip():  # 跳过空行
            continue
        values = parse_csv_line(line)
        if headers:
            yield dict(zip(headers, values))
        else:
            yield values


def test_csv_parser():
    """测试 CSV 解析器"""
    print("=" * 60)
    print("CSV 文件解析器（生成器）")
    print("=" * 60)

    # 创建模拟 CSV
    csv_data = """name,age,city,score
Alice,28,Beijing,95.5
Bob,32,Shanghai,87.0
Charlie,25,Guangzhou,91.2
David,30,Shenzhen,78.5
Eve,27,Hangzhou,88.8"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_data)
        temp_path = f.name

    print(f"\n▶ CSV 数据:")
    for line in csv_data.split('\n'):
        print(f"   {line}")

    print(f"\n▶ 逐行解析（惰性）:")
    gen = read_csv_generator(temp_path)
    for i, row in enumerate(gen):
        print(f"   第 {i+1} 行: {row}")

    print(f"\n▶ 平均值计算:")
    gen = read_csv_generator(temp_path)
    scores = [int(float(row['score'])) for row in gen]
    avg = sum(scores) / len(scores)
    print(f"   scores: {scores}, 平均分: {avg:.2f}")

    # 清理
    os.unlink(temp_path)


# ============================================================
# 6. 文件合并器（多个日志文件合并）
# ============================================================

def merge_sorted_logs(*file_paths):
    """生成器：合并多个已排序的日志文件

    类似于 Unix 的 sort -m，用于合并多个已排序的文件。
    每个文件中的日志按时间戳排序。
    """
    import heapq

    # 为每个文件创建迭代器
    iterators = [read_lines(f) for f in file_paths]

    # 使用 heapq.merge 合并
    yield from heapq.merge(*iterators)


def test_log_merger():
    """测试日志合并"""
    print("=" * 60)
    print("多文件日志合并")
    print("=" * 60)

    # 创建多个小日志文件
    files = []
    for server_id in range(3):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(5):
                f.write(f"[Server-{server_id}] Log entry {i}\n")
            files.append(f.name)

    print(f"\n▶ 合并 3 个服务器日志:")
    merged = merge_sorted_logs(*files)
    for i, line in enumerate(merged):
        print(f"   {line}")
        if i >= 10:
            print(f"   ... (更多行)")
            break

    # 清理
    for f in files:
        os.unlink(f)


# ============================================================
# 7. 实时日志监控（热加载）
# ============================================================

def tail_file(file_path, poll_interval=0.1):
    """生成器：类似 tail -f 的日志监控

    持续监听文件新增内容，每次有新增时 yield 新行。
    适合日志实时监控场景。
    """
    with open(file_path, 'r') as f:
        # 先跳到文件末尾
        f.seek(0, 2)

        while True:
            line = f.readline()
            if line:
                yield line.rstrip('\n')
            else:
                import time
                time.sleep(poll_interval)


def test_tail_file():
    """测试 tail 功能"""
    print("=" * 60)
    print("tail -f 模拟（实时日志监控）")
    print("=" * 60)

    print("\n▶ 创建临时文件并追加内容:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write("Line 1\n")
        f.write("Line 2\n")
        temp_path = f.name

    # 创建 tail 迭代器
    tail = tail_file(temp_path, poll_interval=0.01)
    print(f"   初始内容: {next(tail)}")
    print(f"   初始内容: {next(tail)}")

    # 模拟追加内容
    with open(temp_path, 'a') as f:
        f.write("Line 3 (new)\n")
        f.write("Line 4 (new)\n")

    print(f"   追加后: {next(tail)}")
    print(f"   追加后: {next(tail)}")

    # 清理
    os.unlink(temp_path)


# ============================================================
# 8. 内存高效的数据处理
# ============================================================

def process_large_data(file_path):
    """完整的大数据处理流程——使用生成器实现零拷贝

    核心思想：每个步骤都是生成器，数据流从不一次性加载到内存。
    """
    # 读取
    lines = read_lines(file_path)

    # 过滤空行
    non_empty = (line for line in lines if line.strip())

    # 转换
    processed = (line.upper() for line in non_empty)

    # 统计
    counters = itertools.islice(processed, 100)  # 只取前 100 条

    return list(counters)


def test_large_data_processing():
    """测试大数据处理"""
    print("=" * 60)
    print("零拷贝大数据处理管道")
    print("=" * 60)

    # 创建大数据文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.data', delete=False) as f:
        for i in range(10000):
            f.write(f"data item {i}: some value here\n")
        temp_path = f.name

    print(f"\n▶ 处理 10000 行数据（内存高效）:")
    result = process_large_data(temp_path)
    print(f"   处理后前 5 条: {result[:5]}")
    print(f"   总计: {len(result)} 条")

    # 清理
    os.unlink(temp_path)


# ============================================================
# Demo 入口
# ============================================================

def main():
    print("=" * 60)
    print("Day 022 — 大文件逐行处理实战")
    print("=" * 60)

    test_log_analyzer()
    test_chunk_processor()
    test_csv_parser()
    test_log_merger()
    test_tail_file()
    test_large_data_processing()

    print("\n" + "=" * 60)
    print("✅ 大文件处理实战完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
