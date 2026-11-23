"""
Day 061 - 实战：文件同步工具
使用 pathlib + shutil 实现目录差异比较与同步

运行方式：python3 03-shutil-sync-tool.py
"""

import shutil
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


# ─── 数据模型 ───

@dataclass
class FileDiff:
    """文件差异"""
    rel_path: str
    action: str  # "create", "update", "delete", "unchanged"
    src_path: Optional[Path] = None
    dst_path: Optional[Path] = None
    src_size: int = 0
    dst_size: int = 0
    src_mtime: float = 0.0
    dst_mtime: float = 0.0

    @property
    def size_change(self) -> int:
        return self.src_size - self.dst_size

    def __str__(self):
        icons = {"create": "📄", "update": "🔄", "delete": "🗑️", "unchanged": "✅"}
        icon = icons.get(self.action, "?")
        action_str = self.action.upper()

        if self.action == "unchanged":
            return f"{icon} [{action_str}] {self.rel_path}"
        elif self.action == "delete":
            return f"{icon} [{action_str}] {self.rel_path} ({self.dst_size:,} bytes)"
        else:
            return (f"{icon} [{action_str}] {self.rel_path} "
                    f"({self.src_size:,} bytes)")


@dataclass
class SyncStats:
    """同步统计"""
    created: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0
    total_bytes: int = 0

    @property
    def total_changes(self) -> int:
        return self.created + self.updated + self.deleted

    def __str__(self):
        return (f"创建: {self.created}, 更新: {self.updated}, "
                f"删除: {self.deleted}, 未变: {self.unchanged}, "
                f"总字节: {self.total_bytes:,}")


# ─── 文件哈希计算 ───

def file_hash(filepath: Path, chunk_size: int = 8192) -> str:
    """计算文件 MD5 哈希"""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def quick_hash(filepath: Path) -> str:
    """快速哈希：基于大小 + mtime（不读文件内容）"""
    stat = filepath.stat()
    return f"{stat.st_size}_{stat.st_mtime:.6f}"


# ─── 核心同步逻辑 ───

class FileSyncer:
    """文件同步器"""

    def __init__(self, src_dir: Path, dst_dir: Path, use_content_hash: bool = False):
        self.src_dir = src_dir.resolve()
        self.dst_dir = dst_dir.resolve()
        self.use_content_hash = use_content_hash
        self.stats = SyncStats()

    def compare(self) -> List[FileDiff]:
        """比较两个目录的差异"""
        diffs = []

        # 获取源目录文件
        src_files = {}
        for f in self.src_dir.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(self.src_dir))
                src_files[rel] = f

        # 获取目标目录文件
        dst_files = {}
        for f in self.dst_dir.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(self.dst_dir))
                dst_files[rel] = f

        # 找出差异
        all_paths = set(src_files.keys()) | set(dst_files.keys())

        for rel_path in sorted(all_paths):
            src = src_files.get(rel_path)
            dst = dst_files.get(rel_path)

            if src and not dst:
                # 新文件
                stat = src.stat()
                diffs.append(FileDiff(
                    rel_path=rel_path,
                    action="create",
                    src_path=src,
                    src_size=stat.st_size,
                    src_mtime=stat.st_mtime,
                ))
            elif not src and dst:
                # 需要删除
                stat = dst.stat()
                diffs.append(FileDiff(
                    rel_path=rel_path,
                    action="delete",
                    dst_path=dst,
                    dst_size=stat.st_size,
                ))
            else:
                # 两个都存在，检查是否需要更新
                src_stat = src.stat()
                dst_stat = dst.stat()

                needs_update = False
                if src_stat.st_mtime > dst_stat.st_mtime:
                    needs_update = True
                elif src_stat.st_size != dst_stat.st_size:
                    needs_update = True
                elif self.use_content_hash:
                    if file_hash(src) != file_hash(dst):
                        needs_update = True

                if needs_update:
                    diffs.append(FileDiff(
                        rel_path=rel_path,
                        action="update",
                        src_path=src,
                        dst_path=dst,
                        src_size=src_stat.st_size,
                        dst_size=dst_stat.st_size,
                        src_mtime=src_stat.st_mtime,
                        dst_mtime=dst_stat.st_mtime,
                    ))
                else:
                    diffs.append(FileDiff(
                        rel_path=rel_path,
                        action="unchanged",
                        src_path=src,
                        dst_path=dst,
                        src_size=src_stat.st_size,
                        dst_size=dst_stat.st_size,
                    ))

        return diffs

    def sync(self, dry_run: bool = True) -> SyncStats:
        """执行同步"""
        diffs = self.compare()
        self.stats = SyncStats()

        print(f"\n📂 比较: {self.src_dir} → {self.dst_dir}")
        print(f"   模式: {'🔍 预览 (dry-run)' if dry_run else '⚡ 执行'}")

        if not any(d.action != "unchanged" for d in diffs):
            print("\n✅ 两个目录已同步，无需操作")
            return self.stats

        # 显示差异
        for action_type in ["create", "update", "delete"]:
            items = [d for d in diffs if d.action == action_type]
            if items:
                print(f"\n{'─' * 50}")
                print(f"  {action_type.upper()} ({len(items)} 个)")
                print(f"{'─' * 50}")
                for d in items:
                    print(f"  {d}")

        unchanged = [d for d in diffs if d.action == "unchanged"]
        print(f"\n{'─' * 50}")
        print(f"  未变化: {len(unchanged)} 个")
        print(f"{'─' * 50}")

        # 执行操作
        if not dry_run:
            print(f"\n{'═' * 50}")
            print(f"  执行同步...")
            print(f"{'═' * 50}")

            for diff in diffs:
                if diff.action == "create":
                    self._do_create(diff)
                elif diff.action == "update":
                    self._do_update(diff)
                elif diff.action == "delete":
                    self._do_delete(diff)

        return self.stats

    def _do_create(self, diff: FileDiff):
        """创建新文件"""
        dst = self.dst_dir / diff.rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(diff.src_path, dst)
        self.stats.created += 1
        self.stats.total_bytes += diff.src_size
        print(f"  ✅ 创建: {diff.rel_path}")

    def _do_update(self, diff: FileDiff):
        """更新文件"""
        shutil.copy2(diff.src_path, diff.dst_path)
        self.stats.updated += 1
        self.stats.total_bytes += abs(diff.size_change)
        print(f"  🔄 更新: {diff.rel_path}")

    def _do_delete(self, diff: FileDiff):
        """删除文件"""
        diff.dst_path.unlink()
        self.stats.deleted += 1
        print(f"  🗑️ 删除: {diff.rel_path}")


# ─── 高级功能 ───

class SmartSyncer(FileSyncer):
    """智能同步器：支持过滤、备份、日志"""

    def __init__(self, *args, excludes=None, backup=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.excludes = excludes or []
        self.backup = backup
        self.backup_dir = self.dst_dir / ".backup"

    def compare(self) -> List[FileDiff]:
        """带过滤的比较"""
        diffs = super().compare()

        # 过滤排除的文件
        filtered = []
        for d in diffs:
            skip = False
            for pattern in self.excludes:
                if pattern in d.rel_path:
                    skip = True
                    break
            if not skip:
                filtered.append(d)

        return filtered

    def _do_update(self, diff: FileDiff):
        """更新前备份旧文件"""
        if self.backup:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = self.backup_dir / diff.rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            if diff.dst_path.exists():
                shutil.copy2(diff.dst_path, backup_path)

        super()._do_update(diff)


# ─── 演示 ───

def demo():
    import tempfile

    print("=" * 60)
    print("🔄 文件同步工具演示")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="sync_demo_") as tmp:
        src = Path(tmp) / "source"
        dst = Path(tmp) / "dest"

        # 创建源目录
        src.mkdir()
        (src / "readme.md").write_text("# Project\n")
        (src / "main.py").write_text("print('hello')\n")
        (src / "utils.py").write_text("def helper(): pass\n")
        (src / "config.json").write_text('{"key": "value"}\n')
        (src / ".gitignore").write_text("__pycache__/\n")
        (src / "data").mkdir()
        (src / "data" / "input.csv").write_text("a,b,c\n1,2,3\n")

        # 创建目标目录（模拟之前的部分同步）
        dst.mkdir()
        (dst / "readme.md").write_text("# Project\nOld content\n")
        (dst / "main.py").write_text("print('hello')\n")
        (dst / "old_module.py").write_text("# This should be deleted\n")

        print(f"\n源目录 ({src}):")
        for f in sorted(src.rglob("*")):
            if f.is_file():
                print(f"  📄 {f.relative_to(src)}")

        print(f"\n目标目录 ({dst}):")
        for f in sorted(dst.rglob("*")):
            if f.is_file():
                print(f"  📄 {f.relative_to(dst)}")

        # Dry-run
        syncer = FileSyncer(src, dst)
        stats = syncer.sync(dry_run=True)

        # 实际同步
        print(f"\n{'='*50}")
        stats = syncer.sync(dry_run=False)

        # 结果
        print(f"\n📊 统计: {stats}")

        # 验证
        print(f"\n同步后目标目录:")
        for f in sorted(dst.rglob("*")):
            if f.is_file() and ".backup" not in str(f):
                print(f"  📄 {f.relative_to(dst)}: {f.read_text()[:30].strip()}...")

    print("\n✅ 文件同步工具演示完成！")


if __name__ == "__main__":
    demo()
