"""
Day 061 - pathlib 现代路径操作
进阶用法：面向对象路径 + glob + 批量操作

运行方式：python3 02-pathlib-modern.py
"""

import shutil
import tempfile
import os
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath


def demo_path_creation():
    """Path 对象创建"""
    print("=" * 60)
    print("🔧 Path 对象创建")
    print("=" * 60)

    # 多种创建方式
    p1 = Path("home/user/file.txt")
    p2 = Path.home() / "documents" / "report.pdf"
    p3 = Path.cwd()
    p4 = Path("/etc/hosts")
    p5 = Path(".", "subdir", "file.txt")
    p6 = Path("folder", "subfolder", "file.txt")

    paths = [
        ("字符串创建", p1),
        ("home 拼接", p2),
        ("当前目录", p3),
        ("绝对路径", p4),
        ("多段拼接", p5),
        ("跨平台拼接", p6),
    ]

    for label, p in paths:
        print(f"  {label:12s} → {p}")


def demo_path_properties():
    """路径属性"""
    print("\n" + "=" * 60)
    print("📊 路径属性")
    print("=" * 60)

    p = Path("/home/user/documents/report.pdf")

    print(f"\n路径: {p}")
    print(f"  .name       = {p.name!r:30s}  # 文件名")
    print(f"  .stem       = {p.stem!r:30s}  # 不含后缀")
    print(f"  .suffix     = {p.suffix!r:30s}  # 后缀")
    print(f"  .suffixes   = {p.suffixes!r:30s}  # 所有后缀")
    print(f"  .parent     = {str(p.parent)!r:30s}  # 父目录")
    print(f"  .root       = {p.root!r:30s}  # 根目录")
    print(f"  .parts      = {p.parts!r:30s}  # 各部分")
    print(f"  .as_posix() = {p.as_posix()!r:30s}  # POSIX 格式")

    # 相对路径
    p2 = Path("docs/README.md")
    print(f"\n相对路径: {p2}")
    print(f"  .is_absolute() = {p2.is_absolute()}")
    print(f"  .resolve()     = {p2.resolve()}")

    # PurePath（不访问文件系统）
    pp = PureWindowsPath("C:/Users/Admin/file.txt")
    print(f"\nPureWindowsPath: {pp}")
    print(f"  .drive = {pp.drive!r}")
    print(f"  .root  = {pp.root!r}")


def demo_path_navigation():
    """路径导航"""
    print("\n" + "=" * 60)
    print("🧭 路径导航")
    print("=" * 60)

    p = Path("/home/user/projects/myapp/src/main.py")

    print(f"起点: {p}")
    print(f"  .parent      = {p.parent}")
    print(f"  .parent.parent = {p.parent.parent}")
    print(f"  parents[0]   = {p.parents[0]}")
    print(f"  parents[1]   = {p.parents[1]}")
    print(f"  parents[2]   = {p.parents[2]}")

    # 相对路径计算
    base = Path("/home/user/projects")
    print(f"\n相对路径:")
    print(f"  p.relative_to(base) = {p.relative_to(base)}")

    # 路径修改
    print(f"\n路径修改:")
    print(f"  p.with_name('app.py')     = {p.with_name('app.py')}")
    print(f"  p.with_suffix('.jsx')     = {p.with_suffix('.jsx')}")
    print(f"  p.with_stem('test')       = {p.with_stem('test')}")


def demo_glob_pattern():
    """glob 模式匹配"""
    print("\n" + "=" * 60)
    print("🔍 glob 模式匹配")
    print("=" * 60)

    # 创建测试目录结构
    work_dir = Path(tempfile.mkdtemp(prefix="glob_demo_"))

    # 创建文件结构
    structure = [
        "src/main.py",
        "src/utils.py",
        "src/__init__.py",
        "tests/test_main.py",
        "tests/test_utils.py",
        "docs/README.md",
        "docs/guide.md",
        "data/input.csv",
        "data/output.json",
        "config/settings.yaml",
        "config/defaults.json",
    ]

    for file_path in structure:
        full_path = work_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(f"# {file_path}\n")

    print(f"目录结构:")
    for f in sorted(work_dir.rglob("*")):
        if f.is_file():
            rel = f.relative_to(work_dir)
            print(f"  📄 {rel}")

    # glob 匹配
    print(f"\nglob('*.py') → {sorted(f.name for f in work_dir.glob('*.py'))}")

    print(f"\nrglob('*.py') → {[f.relative_to(work_dir) for f in work_dir.rglob('*.py')]}")

    print(f"\nglob('**/*.md') → {[f.relative_to(work_dir) for f in work_dir.glob('**/*.md')]}")

    # 复杂模式
    test_files = list(work_dir.glob("tests/test_*.py"))
    print(f"\nglob('tests/test_*.py') → {[f.name for f in test_files]}")

    json_files = list(work_dir.rglob("*.json"))
    print(f"rglob('*.json') → {[f.relative_to(work_dir) for f in json_files]}")

    # 清理
    shutil.rmtree(work_dir)


def demo_batch_operations():
    """批量文件操作"""
    print("\n" + "=" * 60)
    print("📦 批量文件操作")
    print("=" * 60)

    work_dir = Path(tempfile.mkdtemp(prefix="batch_demo_"))
    src_dir = work_dir / "source"
    dst_dir = work_dir / "dest"
    src_dir.mkdir()
    dst_dir.mkdir()

    # 创建源文件
    for i in range(5):
        (src_dir / f"file_{i:03d}.txt").write_text(f"Content {i}\n")

    # 1. 批量重命名
    print("\n--- 批量重命名 ---")
    for f in src_dir.glob("*.txt"):
        new_name = src_dir / f"data_{f.stem.split('_')[1]}{f.suffix}"
        f.rename(new_name)
        print(f"  {f.name} → {new_name.name}")

    # 2. 批量复制
    print("\n--- 批量复制 ---")
    for f in src_dir.glob("*.txt"):
        shutil.copy2(f, dst_dir / f.name)
        print(f"  复制: {f.name}")

    # 3. 批量统计
    print("\n--- 文件统计 ---")
    total_size = 0
    file_count = 0
    for f in dst_dir.glob("*.txt"):
        size = f.stat().st_size
        total_size += size
        file_count += 1
        print(f"  {f.name}: {size} bytes")

    print(f"\n  总计: {file_count} 个文件, {total_size} bytes")

    # 4. 批量删除
    print("\n--- 批量删除 ---")
    for f in dst_dir.glob("*.txt"):
        f.unlink(missing_ok=True)
        print(f"  删除: {f.name}")

    # 清理
    shutil.rmtree(work_dir)


def demo_path_conversion():
    """路径转换与兼容"""
    print("\n" + "=" * 60)
    print("🔄 路径转换")
    print("=" * 60)

    p = Path("/home/user/report.pdf")

    # 转为字符串
    print(f"str(p)        = {str(p)}")
    print(f"repr(p)       = {repr(p)}")
    print(f"format(p)     = {format(p)}")

    # 与字符串互转
    path_str = "/tmp/data.txt"
    p_from_str = Path(path_str)
    print(f"\nPath('{path_str}')  = {p_from_str}")

    # PurePath 演示
    print(f"\n--- PurePath（不访问文件系统）---")
    pp = PurePosixPath("/home/user/file.txt")
    print(f"PurePosixPath: {pp}")
    print(f"  .parts = {pp.parts}")

    pw = PureWindowsPath("C:/Users/Admin/file.txt")
    print(f"PureWindowsPath: {pw}")
    print(f"  .drive = '{pw.drive}'")
    print(f"  .root  = '{pw.root}'")
    print(f"  .parts = {pw.parts}")

    # f-string 格式化
    print(f"\n--- f-string 格式化 ---")
    name = "report"
    ext = "pdf"
    print(f"  f'{{Path.home() / f\"{name}.{{ext}}\"}}'")
    print(f"  = {Path.home() / f'{name}.{ext}'}")


def demo_advanced_patterns():
    """高级路径模式"""
    print("\n" + "=" * 60)
    print("🎯 高级模式")
    print("=" * 60)

    work_dir = Path(tempfile.mkdtemp(prefix="pattern_demo_"))

    # 创建文件
    files = [
        "app_v1.0.py",
        "app_v1.1.py",
        "app_v2.0.py",
        "test_app.py",
        "config.json",
        "data_2024.csv",
        "data_2025.csv",
        "README.md",
    ]
    for f in files:
        (work_dir / f).write_text("content")

    # 后缀过滤
    print(f".py 文件: {sorted(f.name for f in work_dir.glob('*.py'))}")
    print(f".csv 文件: {sorted(f.name for f in work_dir.glob('*.csv'))}")

    # 正则风格匹配（用 fnmatch）
    import fnmatch
    print(f"\napp_v*.py: {sorted(f.name for f in work_dir.glob('app_v*.py'))}")
    print(f"data_*.csv: {sorted(f.name for f in work_dir.glob('data_*.csv'))}")

    # 组合模式
    print(f"\n--- 组合模式 ---")
    all_files = list(work_dir.iterdir())
    py_files = [f for f in all_files if f.suffix == ".py"]
    large_files = [f for f in all_files if f.stat().st_size > 0]

    print(f"Python 文件: {len(py_files)} 个")
    print(f"有内容的文件: {len(large_files)} 个")

    # 按大小排序
    sorted_by_size = sorted(all_files, key=lambda f: f.stat().st_size, reverse=True)
    print(f"\n按大小排序:")
    for f in sorted_by_size:
        print(f"  {f.name:25s} {f.stat().st_size:6d} bytes")

    shutil.rmtree(work_dir)


if __name__ == "__main__":
    demo_path_creation()
    demo_path_properties()
    demo_path_navigation()
    demo_glob_pattern()
    demo_batch_operations()
    demo_path_conversion()
    demo_advanced_patterns()
    print("\n✅ pathlib 演示完成！")
