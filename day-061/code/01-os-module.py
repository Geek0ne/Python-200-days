"""
Day 061 - os 模块基础文件操作
基础用法：目录遍历、文件信息、环境变量

运行方式：python3 01-os-module.py
"""

import os
import time
import tempfile
import shutil
from pathlib import Path


def demo_directory_ops():
    """目录操作演示"""
    print("=" * 60)
    print("📁 目录操作")
    print("=" * 60)

    # 创建临时工作目录
    work_dir = Path(tempfile.mkdtemp(prefix="os_demo_"))
    print(f"工作目录: {work_dir}\n")

    # 创建目录结构
    dirs = [
        work_dir / "documents",
        work_dir / "projects" / "python",
        work_dir / "projects" / "rust",
        work_dir / "photos" / "2024",
        work_dir / "photos" / "2025",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        # 创建一些文件
        (d / f"file_{d.name}.txt").write_text(f"Content in {d.name}")

    # 列出目录
    print("--- os.listdir ---")
    for entry in os.listdir(work_dir):
        full_path = work_dir / entry
        type_icon = "📁" if full_path.is_dir() else "📄"
        print(f"  {type_icon} {entry}")

    # 递归遍历
    print("\n--- os.walk ---")
    for root, dirs_list, files in os.walk(work_dir):
        level = str(root).replace(str(work_dir), "").count(os.sep)
        indent = "  " * level
        print(f"{indent}📁 {Path(root).name}/")
        for f in files:
            print(f"{indent}  📄 {f}")

    # glob 模式匹配
    print("\n--- os.listdir + 过滤 ---")
    txt_files = [f for f in os.listdir(work_dir) if f.endswith(".txt")]
    print(f"  根目录 .txt 文件: {txt_files}")

    # 清理
    shutil.rmtree(work_dir)
    print(f"\n✅ 已清理临时目录")


def demo_file_info():
    """文件信息演示"""
    print("\n" + "=" * 60)
    print("📊 文件信息")
    print("=" * 60)

    # 创建测试文件
    test_file = Path(tempfile.mktemp(suffix=".txt"))
    test_file.write_text("Hello, file info!\n" * 100)

    # 获取文件信息
    stat_info = os.stat(test_file)

    print(f"\n文件: {test_file.name}")
    print(f"  大小:       {stat_info.st_size:,} bytes ({stat_info.st_size/1024:.1f} KB)")
    print(f"  权限:       {oct(stat_info.st_mode)}")
    print(f"  所有者 UID: {stat_info.st_uid}")
    print(f"  修改时间:   {time.ctime(stat_info.st_mtime)}")
    print(f"  访问时间:   {time.ctime(stat_info.st_atime)}")
    print(f"  状态变更:   {time.ctime(stat_info.st_ctime)}")

    # os.path 函数
    print(f"\n--- os.path 函数 ---")
    path_str = str(test_file)
    print(f"  basename:   {os.path.basename(path_str)}")
    print(f"  dirname:    {os.path.dirname(path_str)}")
    print(f"  splitext:   {os.path.splitext(path_str)}")
    print(f"  abspath:    {os.path.abspath(path_str)}")
    print(f"  isabs:      {os.path.isabs(path_str)}")

    # 路径拼接
    print(f"\n--- 路径拼接 ---")
    joined = os.path.join("/home", "user", "docs", "file.txt")
    print(f"  os.path.join: {joined}")

    # 清理
    test_file.unlink()


def demo_environment():
    """环境变量与系统信息"""
    print("\n" + "=" * 60)
    print("🌍 环境变量与系统信息")
    print("=" * 60)

    # 常用环境变量
    env_vars = ["HOME", "USER", "SHELL", "LANG", "PATH", "TMPDIR", "PWD"]
    print("\n--- 常用环境变量 ---")
    for var in env_vars:
        value = os.environ.get(var, "(未设置)")
        if var == "PATH":
            # PATH 太长，只显示前几个
            paths = value.split(":")
            value = f"{paths[0]}:... ({len(paths)} 个路径)"
        print(f"  {var:10s} = {value}")

    # 路径展开
    print(f"\n--- 路径展开 ---")
    print(f"  ~/docs    → {os.path.expanduser('~/docs')}")
    print(f"  $HOME     → {os.path.expandvars('$HOME')}")

    # 系统信息
    print(f"\n--- 系统信息 ---")
    print(f"  os.name:     {os.name}")
    print(f"  os.sep:      '{os.sep}'")
    print(f"  os.linesep:  {repr(os.linesep)}")
    print(f"  os.cpu_count(): {os.cpu_count()}")

    # 磁盘使用
    print(f"\n--- 磁盘使用 ---")
    usage = shutil.disk_usage("/")
    print(f"  总计: {usage.total // (1024**3)} GB")
    print(f"  已用: {usage.used // (1024**3)} GB")
    print(f"  可用: {usage.free // (1024**3)} GB")
    print(f"  使用率: {usage.used/usage.total*100:.1f}%")


def demo_file_operations():
    """文件读写操作"""
    print("\n" + "=" * 60)
    print("📝 文件读写操作")
    print("=" * 60)

    work_dir = Path(tempfile.mkdtemp(prefix="file_ops_"))

    # --- 文本文件 ---
    print("\n--- 文本文件 ---")
    text_file = work_dir / "sample.txt"

    # 写入
    with open(text_file, "w", encoding="utf-8") as f:
        f.write("第一行\n")
        f.write("第二行\n")
        f.write("第三行：中文内容 ✅\n")

    # 读取全部
    content = text_file.read_text(encoding="utf-8")
    print(f"  读取全部: {repr(content[:50])}...")

    # 逐行读取
    print(f"  逐行读取:")
    with open(text_file, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            print(f"    行{i}: {line.rstrip()}")

    # --- 二进制文件 ---
    print("\n--- 二进制文件 ---")
    bin_file = work_dir / "data.bin"

    # 写入二进制
    data = bytes(range(256))
    bin_file.write_bytes(data)
    print(f"  写入 {len(data)} 字节")

    # 读取二进制
    read_data = bin_file.read_bytes()
    print(f"  读取 {len(read_data)} 字节")
    print(f"  前10字节: {list(read_data[:10])}")

    # --- 追加写入 ---
    print("\n--- 追加写入 ---")
    append_file = work_dir / "log.txt"
    append_file.write_text("日志 1\n")

    with open(append_file, "a", encoding="utf-8") as f:
        f.write("日志 2\n")
        f.write("日志 3\n")

    print(f"  内容: {append_file.read_text()}")

    # --- 文件锁定（Linux）---
    print("\n--- 文件信息查询 ---")
    print(f"  文件名:     {text_file.name}")
    print(f"  后缀:       {text_file.suffix}")
    print(f"  大小:       {text_file.stat().st_size} bytes")
    print(f"  绝对路径:   {text_file.resolve()}")
    print(f"  父目录:     {text_file.parent.name}")

    # 清理
    shutil.rmtree(work_dir)


if __name__ == "__main__":
    demo_directory_ops()
    demo_file_info()
    demo_environment()
    demo_file_operations()
    print("\n✅ os 模块演示完成！")
