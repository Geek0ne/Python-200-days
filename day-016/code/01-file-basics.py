#!/usr/bin/env python3
"""
Day 016 — 文件 I/O 基础用法
=============================
涵盖：所有打开模式示例、with 语句、文件读写、seek/tell
"""

import os
import sys
import tempfile
import io

# ──────────── 准备工作 ────────────

TEMP_DIR = tempfile.mkdtemp(prefix="file_io_demo_")
TEST_FILE = os.path.join(TEMP_DIR, "demo.txt")
BINARY_FILE = os.path.join(TEMP_DIR, "demo.bin")

def setup():
    """创建测试用的临时目录和文件"""
    os.makedirs(TEMP_DIR, exist_ok=True)
    with open(TEST_FILE, "w", encoding="utf-8") as f:
        f.write("Hello, 文件 I/O!\n这是第二行。\n第三行：Python 文件操作。\n")

def cleanup():
    """清理临时文件"""
    for f in [TEST_FILE, BINARY_FILE]:
        if os.path.exists(f):
            os.remove(f)
    if os.path.exists(TEMP_DIR):
        os.rmdir(TEMP_DIR)

def section(title):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ════════════════════════════════════════════
# 1. 各种打开模式演示
# ════════════════════════════════════════════

def demo_read_modes():
    """演示 r / rb 读取模式"""
    section("读取模式: r (只读文本)")
    
    setup()
    
    # r — 只读文本模式
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        print(f"r 模式读取 ({f.mode}):")
        print(f"  {repr(content[:50])}...")
    
    # rb — 只读二进制模式
    with open(TEST_FILE, "rb") as f:
        raw = f.read()
        print(f"\nrb 模式读取 ({f.mode}):")
        print(f"  原始字节: {raw[:20]}...")
    
    # 逐行读取
    print("\n逐行读取（推荐大文件）:")
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            print(f"  第{i}行: {repr(line)}")


def demo_write_modes():
    """演示 w / a / x 写入模式"""
    section("写入模式: w / a / x")
    
    # w — 写入（清空）
    file_w = os.path.join(TEMP_DIR, "write_demo.txt")
    with open(file_w, "w", encoding="utf-8") as f:
        f.write("第一次写入\n")
    print("w 模式写入完成")
    
    # 再次写入（会清空之前内容！）
    with open(file_w, "w", encoding="utf-8") as f:
        f.write("第二次写入（覆盖）\n")
    print("w 模式再次写入（覆盖）")
    with open(file_w, "r", encoding="utf-8") as f:
        print(f"  内容: {repr(f.read())}")
    
    # a — 追加
    with open(file_w, "a", encoding="utf-8") as f:
        f.write("追加的内容\n")
        f.write("再追加一行\n")
    print("\na 模式追加写入完成")
    with open(file_w, "r", encoding="utf-8") as f:
        print(f"  内容:\n{f.read()}")
    
    # x — 排他创建（文件不存在才成功）
    file_x = os.path.join(TEMP_DIR, "exclusive.txt")
    with open(file_x, "x", encoding="utf-8") as f:
        f.write("排他模式创建的文件\n")
    print(f"\nx 模式创建成功: {os.path.exists(file_x)}")
    
    # 再次尝试 x 模式 → 抛出 FileExistsError
    print("\n尝试用 x 模式打开已存在的文件:")
    try:
        with open(file_x, "x", encoding="utf-8") as f:
            f.write("这不会被执行\n")
    except FileExistsError:
        print("  → FileExistsError! 文件已存在，不会覆盖")
    
    # 清理
    os.remove(file_w)
    os.remove(file_x)


def demo_readwrite_modes():
    """演示 r+ / w+ / a+ 读写模式"""
    section("读写模式: r+ / w+ / a+")
    
    setup()
    
    # r+ — 可读可写，不截断
    file_rp = os.path.join(TEMP_DIR, "rw_demo.txt")
    with open(TEST_FILE, "r", encoding="utf-8") as src:
        content = src.read()
    with open(file_rp, "w", encoding="utf-8") as dst:
        dst.write(content)
    
    with open(file_rp, "r+", encoding="utf-8") as f:
        print(f"1. r+ 模式，初始位置: {f.tell()}")
        line = f.readline()
        print(f"2. 读取第一行: {repr(line)}")
        print(f"3. 当前指针: {f.tell()}")
        # 写入（覆盖从当前位置开始的内容）
        f.write("【这是 r+ 写入的插入内容】\n")
        print(f"4. 写入后指针: {f.tell()}")
    
    print("\n最终文件内容:")
    with open(file_rp, "r", encoding="utf-8") as f:
        print(f"  {repr(f.read())}")
    
    # w+ — 可读可写，先清空
    with open(file_rp, "w+", encoding="utf-8") as f:
        print(f"\nw+ 模式，清空文件，位置: {f.tell()}")
        f.write("w+ 写入的内容\n")
        f.seek(0)  # 写完后指针在末尾，需要 seek 到开头才能读
        content = f.read()
        print(f"seek(0) 后读取: {repr(content)}")
    
    # a+ — 可读可追加，指针在末尾
    with open(file_rp, "a+", encoding="utf-8") as f:
        print(f"\na+ 模式，初始位置: {f.tell()}（末尾）")
        f.write("a+ 追加的内容\n")
        # 要读取已有内容，需要 seek 到开头
        f.seek(0)
        content = f.read()
        print(f"追加后读回: {repr(content)}")
    
    os.remove(file_rp)


def demo_binary_modes():
    """演示二进制模式 wb / rb / ab"""
    section("二进制模式: wb / rb / ab")
    
    # 写入二进制数据
    data = bytes(range(256))  # 0x00 - 0xFF 所有字节
    
    with open(BINARY_FILE, "wb") as f:
        f.write(data)
    print(f"wb 写入 {len(data)} 字节到 {BINARY_FILE}")
    
    # 读取部分
    with open(BINARY_FILE, "rb") as f:
        # 读取前 16 字节
        header = f.read(16)
        print(f"rb 读取前 16 字节: {header.hex(' ')}")
        print(f"  作为列表: {list(header)}")
        
        # 从位置 128 开始读 8 字节
        f.seek(128)
        middle = f.read(8)
        print(f"  位置 128+8: {list(middle)}")
    
    # 证明文本模式 vs 二进制模式对换行符的处理差异
    section("文本模式 vs 二进制模式 — 换行符处理")
    
    win_file = os.path.join(TEMP_DIR, "newline_test.txt")
    
    # 文本模式写入
    with open(win_file, "w", encoding="utf-8") as f:
        written = f.write("line1\nline2\nline3\n")
    print(f"文本模式写入 '\\n'，写入字符数: {written}")
    
    with open(win_file, "rb") as f:
        raw = f.read()
    print(f"二进制模式读回: {raw}")
    actual_newlines = raw.count(b"\n")
    actual_crlf = raw.count(b"\r\n")
    print(f"  \\n 出现次数: {actual_newlines}")
    print(f"  \\r\\n 出现次数: {actual_crlf}")
    print(f"  (Linux 上 \\n 不变，Windows 上 \\n→\\r\\n)")
    
    os.remove(win_file)


# ════════════════════════════════════════════
# 2. with 语句深入理解
# ════════════════════════════════════════════

def demo_with_statement():
    """展示 with 语句的多种用法"""
    section("with 语句深入理解")
    
    setup()
    
    # 基础用法
    print("1. 基础用法:")
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        print(f"   文件已打开: {not f.closed}")
        first_line = f.readline().strip()
        print(f"   第一行: {first_line}")
    print(f"   离开 with 块: {f.closed}")
    
    # 多个文件同时打开
    print("\n2. 同时打开多个文件:")
    dest = os.path.join(TEMP_DIR, "copy_demo.txt")
    with (
        open(TEST_FILE, "r", encoding="utf-8") as src,
        open(dest, "w", encoding="utf-8") as dst,
    ):
        dst.write(src.read())
    print(f"   文件复制完成")
    with open(dest, "r", encoding="utf-8") as f:
        print(f"   目标文件内容:\n{f.read()}")
    os.remove(dest)
    
    # 上下文管理器协议实现
    print("\n3. 自定义上下文管理器:")
    
    class FileManager:
        def __init__(self, filename, mode, encoding=None):
            self.filename = filename
            self.mode = mode
            self.encoding = encoding
            self.file = None
        
        def __enter__(self):
            print(f"   __enter__: 打开 {self.filename}")
            if self.encoding:
                self.file = open(self.filename, self.mode, encoding=self.encoding)
            else:
                self.file = open(self.filename, self.mode)
            return self.file
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            print(f"   __exit__: 关闭 {self.filename}")
            if self.file:
                self.file.close()
            if exc_type:
                print(f"   捕获异常: {exc_type.__name__}: {exc_val}")
            # 返回 False 让异常继续传播，返回 True 吞掉异常
            return False
    
    with FileManager(TEST_FILE, "r", encoding="utf-8") as f:
        print(f"   读取: {f.read(20)}...")
    print("   离开 with 块")
    
    # contextlib.contextmanager 装饰器
    print("\n4. 使用 @contextmanager:")
    from contextlib import contextmanager
    
    @contextmanager
    def managed_open(filename, mode, encoding=None):
        print(f"   准备打开: {filename}")
        f = open(filename, mode, encoding=encoding) if encoding else open(filename, mode)
        try:
            yield f
        finally:
            print(f"   关闭: {filename}")
            f.close()
    
    with managed_open(TEST_FILE, "r", encoding="utf-8") as f:
        print(f"   读取: {f.read(20)}...")


# ════════════════════════════════════════════
# 3. 文件指针操作
# ════════════════════════════════════════════

def demo_seek_tell():
    """演示 seek() 和 tell() 的用法"""
    section("文件指针: seek / tell")
    
    setup()
    
    print("文件内容:")
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        for i, ch in enumerate(content[:30]):
            print(f"  [{i:2d}] {repr(ch)}")
    
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        print(f"\n1. 初始位置: {f.tell()}")
        
        f.seek(7)
        print(f"2. seek(7) 后: {f.tell()}")
        print(f"   读取: {repr(f.read(10))}")
        print(f"   读取后位置: {f.tell()}")
        
        # 回到开头
        f.seek(0)
        print(f"\n3. seek(0) 回到开头: {f.tell()}")
        print(f"   读取第一行: {repr(f.readline())}")
        
        # 二进制模式下更灵活的 seek
        section("二进制模式下的 seek")
    
    with open(TEST_FILE, "rb") as f:
        # SEEK_END 从末尾算
        f.seek(-10, os.SEEK_END)
        print(f"1. seek(-10, SEEK_END): 末尾前10字节")
        print(f"   位置: {f.tell()}, 读取: {f.read()}")
        
        # SEEK_CUR 从当前位置算
        f.seek(-10, os.SEEK_END)
        f.seek(5, os.SEEK_CUR)
        print(f"\n2. seek(-10, END) → seek(5, CUR): 位置: {f.tell()}")
        
        # SEEK_SET 从开头算
        f.seek(0, os.SEEK_SET)
        print(f"\n3. seek(0, SET) 回到开头: 位置: {f.tell()}")


# ════════════════════════════════════════════
# 4. 多种读取方法对比
# ════════════════════════════════════════════

def demo_read_methods():
    """对比不同的读取方式"""
    section("多种读取方法对比")
    
    setup()
    
    # 1. read() — 全量读取
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    print(f"1. read() → 返回 str, 长度: {len(content)}")
    print(f"   {repr(content)}")
    
    # 2. readline() — 逐行
    print(f"\n2. readline() 逐行:")
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        while True:
            line = f.readline()
            if not line:  # readline() 读到末尾返回空字符串
                break
            print(f"   行 ({len(line)} chars): {repr(line)}")
    
    # 3. readlines() — 所有行
    print(f"\n3. readlines() → 返回列表:")
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines, 1):
        print(f"   [{i}] {repr(line)}")
    
    # 4. 迭代器方式
    print(f"\n4. for line in f — 迭代器:")
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            print(f"   [{i}] {repr(line)}")


# ════════════════════════════════════════════
# 5. flush、truncate、fileno 等特殊方法
# ════════════════════════════════════════════

def demo_special_methods():
    """演示 flush、truncate、fileno 等"""
    section("特殊方法: flush / truncate / fileno")
    
    # truncate — 截断文件
    file_t = os.path.join(TEMP_DIR, "truncate_demo.txt")
    with open(file_t, "w", encoding="utf-8") as f:
        f.write("这是要被截断的内容，只保留前几个字")
    
    with open(file_t, "r+", encoding="utf-8") as f:
        print(f"截断前大小: {os.path.getsize(file_t)}")
        f.truncate(10)  # 保留前 10 个字符（在 UTF-8 中可能是 10+ 字节）
    
    with open(file_t, "r", encoding="utf-8") as f:
        print(f"截断后内容: {repr(f.read())}")
    print(f"截断后大小: {os.path.getsize(file_t)}")
    os.remove(file_t)
    
    # fileno — 获取文件描述符
    setup()
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        fd = f.fileno()
        print(f"\nfileno(): 文件描述符 = {fd}")
        print(f"  os.read(fd, 10): {os.read(fd, 10)}")
    
    # 其他属性
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        print(f"\n文件对象属性:")
        print(f"  name: {f.name}")
        print(f"  mode: {f.mode}")
        print(f"  encoding: {f.encoding}")
        print(f"  closed: {f.closed}")
        print(f"  seekable: {f.seekable()}")
        print(f"  readable: {f.readable()}")
        print(f"  writable: {f.writable()}")
    
    with open(TEST_FILE, "rb") as f:
        print(f"\n二进制模式属性:")
        print(f"  mode: {f.mode}")
        print(f"  seekable: {f.seekable()}")


# ════════════════════════════════════════════
# 6. 写入方法演示
# ════════════════════════════════════════════

def demo_write_methods():
    """演示 write / writelines 等方法"""
    section("写入方法: write / writelines / flush")
    
    # write — 写入字符串
    file_w = os.path.join(TEMP_DIR, "write_methods.txt")
    with open(file_w, "w", encoding="utf-8") as f:
        count = f.write("Hello, World!\n")
        print(f"write() 返回写入字符数: {count}")
        f.write("第二行内容\n")
    
    # writelines — 写入字符串列表
    with open(file_w, "a", encoding="utf-8") as f:
        lines = ["追加行1\n", "追加行2\n", "追加行3\n"]
        f.writelines(lines)
        print(f"writelines() 写入 {len(lines)} 行")
    
    with open(file_w, "r", encoding="utf-8") as f:
        print(f"\n最终内容:")
        print(f.read())
    
    os.remove(file_w)
    
    # flush — 强制刷新缓冲区
    flush_file = os.path.join(TEMP_DIR, "flush_demo.txt")
    with open(flush_file, "w", encoding="utf-8") as f:
        f.write("先写入一些内容...")
        f.flush()  # 立即写入磁盘
        print(f"\nflush() 后文件大小: {os.path.getsize(flush_file)}")
        f.write("再追加一些内容")
        f.flush()
        print(f"再次 flush 后文件大小: {os.path.getsize(flush_file)}")
    os.remove(flush_file)


# ════════════════════════════════════════════
# 主程序
# ════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Day 016 — 文件 I/O 基础用法演示")
    print("=" * 60)
    
    try:
        # 基础模式
        demo_read_modes()
        demo_write_modes()
        demo_readwrite_modes()
        demo_binary_modes()
        
        # with 语句
        demo_with_statement()
        
        # 文件指针
        demo_seek_tell()
        
        # 读取方法
        demo_read_methods()
        
        # 特殊方法
        demo_special_methods()
        
        # 写入方法
        demo_write_methods()
        
        # 编码处理
        demo_encoding_basics()
        
        print(f"\n{'='*60}")
        print(f"  所有演示完成！临时目录: {TEMP_DIR}")
        print(f"{'='*60}")
    
    finally:
        cleanup()


def demo_encoding_basics():
    """演示编码处理基础：编码检测、BOM、errors 策略"""
    section("编码处理基础")

    file_enc = os.path.join(TEMP_DIR, "encoding_demo.txt")

    # 1. 编码检测：通过 BOM
    print("1. BOM 编码检测:")
    for bom_name, bom_bytes, enc in [
        ("UTF-8 with BOM", b"\xef\xbb\xbf", "utf-8-sig"),
        ("UTF-16 LE", b"\xff\xfe", "utf-16-le"),
        ("UTF-16 BE", b"\xfe\xff", "utf-16-be"),
    ]:
        print(f"   {bom_name}: BOM={bom_bytes.hex()} → encoding={enc}")

    # 2. 不同编码的文件读写
    print("\n2. 编码写入与读取:")

    # 写入 UTF-8
    with open(file_enc, "w", encoding="utf-8") as f:
        f.write("Hello, 世界!\n")
    with open(file_enc, "rb") as f:
        raw = f.read()
    print(f"   UTF-8 写入, 原始字节: {raw}")

    # 用不同编码读取
    for enc in ["utf-8", "gbk", "latin-1"]:
        try:
            text = raw.decode(enc)
            print(f"   用 {enc} 读取: {repr(text)}")
        except UnicodeDecodeError as e:
            print(f"   用 {enc} 读取: ❌ {e}")

    # 3. errors 参数处理策略
    print("\n3. 编码错误处理策略对比:")
    bad_bytes = b"Hello \xff\xfe World"  # 包含非法 UTF-8 字节

    strategies = {
        "strict": "抛异常",
        "ignore": "跳过非法字节",
        "replace": "用 ? 替换",
        "backslashreplace": "用 \\xNN 转义",
        "surrogateescape": "代理转义",
    }
    for strategy, desc in strategies.items():
        try:
            text = bad_bytes.decode("utf-8", errors=strategy)
            print(f"   {strategy:<20s} ({desc}): {repr(text)}")
        except UnicodeDecodeError as e:
            print(f"   {strategy:<20s} ({desc}): ❌ {e}")

    # 4. tell/seek 在二进制中的文件导航
    print("\n4. 文件指针在二进制文件中的导航:")
    bin_file = os.path.join(TEMP_DIR, "seek_nav.bin")
    with open(bin_file, "wb") as f:
        f.write(bytes(range(100)))

    with open(bin_file, "rb") as f:
        print(f"   初始: tell()={f.tell()}")
        f.seek(50)
        print(f"   seek(50): tell()={f.tell()}, 读取={list(f.read(5))}")
        f.seek(-10, os.SEEK_END)
        print(f"   seek(-10, END): tell()={f.tell()}, 读取={list(f.read(5))}")
        f.seek(5, os.SEEK_CUR)
        print(f"   seek(5, CUR):  tell()={f.tell()}, 读取={list(f.read(5))}")

    os.remove(bin_file)
    os.remove(file_enc)


if __name__ == "__main__":
    main()
