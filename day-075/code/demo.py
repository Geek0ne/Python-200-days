"""
Day 075 — 实战演示脚本
运行方式：python demo.py
"""
import tempfile
import os
from pathlib import Path
from file_renamer import Renamer, preview_changes


def main():
    """演示文件重命名工具的各种功能"""

    print("=" * 60)
    print("🎯 文件批量重命名工具演示")
    print("=" * 60)

    # 创建临时演示目录
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n📁 演示目录: {tmpdir}")

        # 创建演示文件
        print("\n📝 创建演示文件...")
        for i in range(5):
            (Path(tmpdir) / f"document_{i}.txt").touch()
            (Path(tmpdir) / f"photo {i}.jpg").touch()
        print("   创建了 10 个文件")

        # 列出原始文件
        print("\n📋 原始文件:")
        for f in sorted(Path(tmpdir).iterdir()):
            print(f"   - {f.name}")

        # 演示1：添加前缀
        print("\n" + "=" * 60)
        print("📌 演示1：添加前缀")
        print("=" * 60)

        renamer = Renamer(tmpdir, dry_run=True)
        result = renamer.add_prefix("demo_")
        preview_changes(result.operations)

        # 演示2：替换空格
        print("\n" + "=" * 60)
        print("📌 演示2：替换空格为下划线")
        print("=" * 60)

        renamer = Renamer(tmpdir, dry_run=True)
        result = renamer.replace(" ", "_")
        preview_changes(result.operations)

        # 演示3：序号重命名
        print("\n" + "=" * 60)
        print("📌 演示3：序号重命名")
        print("=" * 60)

        renamer = Renamer(tmpdir, dry_run=True)
        result = renamer.sequence("file_{index:03d}.txt", pattern="*.txt")
        preview_changes(result.operations)

        # 演示4：正则替换
        print("\n" + "=" * 60)
        print("📌 演示4：正则替换")
        print("=" * 60)

        renamer = Renamer(tmpdir, dry_run=True)
        result = renamer.regex_replace(r"(\d+)", r"num_\1", pattern="*.txt")
        preview_changes(result.operations)

        # 演示5：大小写转换
        print("\n" + "=" * 60)
        print("📌 演示5：小写转换")
        print("=" * 60)

        renamer = Renamer(tmpdir, dry_run=True)
        result = renamer.case转换("lower")
        preview_changes(result.operations)

        print("\n" + "=" * 60)
        print("✅ 演示完成！")
        print("=" * 60)
        print("\n实际使用时，请去掉 dry_run=True 参数")


if __name__ == "__main__":
    main()
