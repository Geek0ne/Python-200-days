"""
file_tools.py — 文件管理工具集

提供日常文件批量操作功能：批量重命名、文件查找、
目录大小统计和文件分类整理。

功能列表:
    batch_rename()   — 批量重命名文件（前缀/后缀/替换/序号）
    find_files()     — 按多种条件查找文件
    dir_size_stats() — 统计目录大小分布
    classify_files() — 按扩展名分类整理文件
"""

import os
import re
import shutil
import time
from datetime import datetime, date
from typing import Optional, Union


class FileToolError(Exception):
    """文件工具操作异常基类。"""
    pass


class FileExistsError_(FileToolError):
    """目标文件已存在的异常。"""
    pass


# ──────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────


def _safe_rename(src: str, dst: str, overwrite: bool = False) -> bool:
    """
    安全重命名文件，避免数据丢失。

    Args:
        src: 源文件路径。
        dst: 目标文件路径。
        overwrite: 是否覆盖已存在的文件。

    Returns:
        是否重命名成功。

    Raises:
        FileExistsError_: 目标文件存在且 overwrite=False 时。
    """
    if not os.path.exists(src):
        return False

    if os.path.exists(dst) and not overwrite:
        raise FileExistsError_(f"目标文件已存在: {dst}")

    try:
        os.rename(src, dst)
        return True
    except OSError as e:
        raise FileToolError(f"重命名失败 {src} -> {dst}: {e}")


def _format_size(size_bytes: int) -> str:
    """
    将字节数转换为人类可读的文件大小格式。

    Args:
        size_bytes: 字节数。

    Returns:
        格式化后的字符串，如 "1.23 MB"。
    """
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


# ──────────────────────────────────────────────
# 批量重命名
# ──────────────────────────────────────────────


def batch_rename(
    path: str,
    prefix: str = "",
    suffix: str = "",
    replace: Optional[tuple[str, str]] = None,
    ext: Optional[Union[str, tuple[str, ...]]] = None,
    start: int = 1,
    dry_run: bool = False,
    overwrite: bool = False,
) -> dict:
    """
    批量重命名指定目录中的文件。

    Args:
        path:     目标目录路径。
        prefix:   添加到文件名前的字符串。
        suffix:   添加到文件名（扩展名前）的字符串。
        replace:  替换旧字符串和新字符串的元组 (old, new)。
        ext:      只处理指定扩展名的文件，如 ".txt" 或 (".jpg", ".png")。
        start:    序号起始值（仅当使用序号模式时有效）。
        dry_run:  仅模拟运行，不实际执行重命名。
        overwrite:是否覆盖已存在的目标文件。

    Returns:
        包含操作统计信息的字典：
        {
            "total": 总数,
            "renamed": 成功数,
            "skipped": 跳过数,
            "errors": 错误列表,
            "changes": [(原名, 新名), ...]
        }

    Examples:
        # 给所有 .txt 文件添加前缀
        >>> batch_rename("/tmp/files", prefix="backup_", ext=".txt")

        # 替换文件名中的空格为下划线
        >>> batch_rename("/tmp/files", replace=(" ", "_"))

        # 序号重命名所有 .jpg 文件
        >>> batch_rename("/tmp/photos", prefix="photo_", ext=".jpg", start=1)
    """
    if not os.path.isdir(path):
        raise FileNotFoundError(f"目录不存在: {path}")

    files = sorted(os.listdir(path))
    changes: list[tuple[str, str]] = []
    errors: list[str] = []
    skipped = 0

    counter = start

    for filename in files:
        full_path = os.path.join(path, filename)

        # 只处理文件，不处理目录
        if not os.path.isfile(full_path):
            continue

        # 按扩展名过滤
        if ext is not None:
            _, file_ext = os.path.splitext(filename)
            if isinstance(ext, str):
                if file_ext.lower() != ext.lower():
                    continue
            else:
                if file_ext.lower() not in [e.lower() for e in ext]:
                    continue

        name_part, ext_part = os.path.splitext(filename)

        # 生成新文件名
        new_name = name_part

        # 序号模式：如果没有前缀后缀替换，自动使用序号
        if prefix or suffix or replace:
            new_name = prefix + name_part + suffix
        else:
            new_name = f"{counter:04d}"
            counter += 1

        # 替换模式
        if replace:
            old_str, new_str = replace
            new_name = new_name.replace(old_str, new_str)

        new_full_path = os.path.join(path, new_name + ext_part)

        if new_full_path == full_path:
            skipped += 1
            continue

        changes.append((full_path, new_full_path))

    renamed = 0
    for src, dst in changes:
        if dry_run:
            print(f"[DRY RUN] {os.path.basename(src)} -> {os.path.basename(dst)}")
            continue
        try:
            if _safe_rename(src, dst, overwrite=overwrite):
                renamed += 1
        except FileExistsError_:
            errors.append(f"目标存在: {dst}")
            skipped += 1
        except FileToolError as e:
            errors.append(str(e))
            skipped += 1

    return {
        "total": len(changes),
        "renamed": renamed,
        "skipped": skipped,
        "errors": errors,
        "changes": changes,
    }


# ──────────────────────────────────────────────
# 文件查找
# ──────────────────────────────────────────────


def find_files(
    path: str,
    ext: Optional[Union[str, tuple[str, ...]]] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    date_from: Optional[Union[str, date]] = None,
    date_to: Optional[Union[str, date]] = None,
    recursive: bool = True,
) -> dict:
    """
    按条件查找文件。

    Args:
        path:      搜索的根目录路径。
        ext:       文件扩展名过滤，如 ".py" 或 (".jpg", ".png")。
        min_size:  最小文件大小（字节）。
        max_size:  最大文件大小（字节）。
        date_from: 起始修改日期（字符串 "YYYY-MM-DD" 或 date 对象）。
        date_to:   截止修改日期（字符串 "YYYY-MM-DD" 或 date 对象）。
        recursive: 是否递归搜索子目录。

    Returns:
        包含搜索结果和统计信息的字典：
        {
            "files": [(文件路径, 大小, 修改时间), ...],
            "total_count": 总数,
            "total_size": 总大小,
            "filters_applied": 应用的过滤条件
        }

    Examples:
        >>> find_files("/home", ext=".py", min_size=1024)
        >>> find_files("/var/log", ext=(".log", ".txt"), date_from="2024-01-01")
    """
    if not os.path.isdir(path):
        raise FileNotFoundError(f"目录不存在: {path}")

    # 解析日期字符串
    if isinstance(date_from, str):
        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
    if isinstance(date_to, str):
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date()

    matches: list[tuple[str, int, str]] = []
    walker = os.walk(path) if recursive else [(path, [], os.listdir(path))]

    for root, _, files in walker:
        for filename in files:
            full_path = os.path.join(root, filename)

            try:
                stat = os.stat(full_path)
            except OSError:
                continue

            file_size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime).date()

            # 扩展名过滤
            if ext is not None:
                _, file_ext = os.path.splitext(filename)
                if isinstance(ext, str):
                    if file_ext.lower() != ext.lower():
                        continue
                else:
                    if file_ext.lower() not in [e.lower() for e in ext]:
                        continue

            # 大小过滤
            if min_size is not None and file_size < min_size:
                continue
            if max_size is not None and file_size > max_size:
                continue

            # 日期过滤
            if date_from is not None and mtime < date_from:
                continue
            if date_to is not None and mtime > date_to:
                continue

            date_str = mtime.strftime("%Y-%m-%d")
            matches.append((full_path, file_size, date_str))

    matches.sort(key=lambda x: x[1], reverse=True)

    return {
        "files": matches,
        "total_count": len(matches),
        "total_size": sum(m[1] for m in matches),
        "filters_applied": {
            "ext": ext,
            "min_size": min_size,
            "max_size": max_size,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
        },
    }


# ──────────────────────────────────────────────
# 目录大小统计
# ──────────────────────────────────────────────


def dir_size_stats(path: str) -> dict:
    """
    统计目录的大小分布信息。

    Args:
        path: 目标目录路径。

    Returns:
        包含详细大小统计信息的字典：
        {
            "path": 目录路径,
            "total_size": 总大小（字节）,
            "total_size_str": 人类可读总大小,
            "total_files": 文件总数,
            "total_dirs": 子目录数（含嵌套）,
            "subdirs": [
                {"name": "子目录名", "size": 大小, "files": 文件数},
                ...
            ],
            "file_types": {".扩展名": {"count": 数目, "size": 总大小}, ...}
        }

    Examples:
        >>> stats = dir_size_stats("/home/user")
        >>> print(stats["total_size_str"])
    """
    if not os.path.isdir(path):
        raise FileNotFoundError(f"目录不存在: {path}")

    total_size = 0
    total_files = 0
    total_dirs = 0
    subdirs: list[dict] = []
    file_types: dict[str, dict] = {}
    dir_sizes: dict[str, int] = {}

    # 先收集每个目录的大小
    for root, dirs, files in os.walk(path):
        dir_size = 0
        dir_files = 0
        for filename in files:
            try:
                fp = os.path.join(root, filename)
                dir_size += os.path.getsize(fp)
                dir_files += 1
                # 文件类型统计
                _, ext = os.path.splitext(filename)
                ext = ext.lower() if ext else "(no extension)"
                if ext not in file_types:
                    file_types[ext] = {"count": 0, "size": 0}
                file_types[ext]["count"] += 1
                file_types[ext]["size"] += os.path.getsize(fp)
            except OSError:
                continue

        # 使用相对路径作为 key
        rel_path = os.path.relpath(root, path)
        dir_sizes[rel_path] = dir_size

        total_size += dir_size
        total_files += dir_files
        total_dirs += len(dirs)

    # 排序子目录（按大小降序）
    subdirs = [
        {"name": name, "size": size, "size_str": _format_size(size)}
        for name, size in sorted(dir_sizes.items(), key=lambda x: x[1], reverse=True)
    ]

    # 排序文件类型（按大小降序）
    sorted_types = dict(
        sorted(file_types.items(), key=lambda x: x[1]["size"], reverse=True)
    )

    return {
        "path": path,
        "total_size": total_size,
        "total_size_str": _format_size(total_size),
        "total_files": total_files,
        "total_dirs": total_dirs,
        "subdirs": subdirs,
        "file_types": sorted_types,
    }


# ──────────────────────────────────────────────
# 文件分类整理
# ──────────────────────────────────────────────


# 预定义的分类映射
EXTENSION_CATEGORIES = {
    # 图片
    ".jpg": "images",
    ".jpeg": "images",
    ".png": "images",
    ".gif": "images",
    ".bmp": "images",
    ".svg": "images",
    ".webp": "images",
    ".ico": "images",
    # 文档
    ".txt": "documents",
    ".pdf": "documents",
    ".doc": "documents",
    ".docx": "documents",
    ".xls": "documents",
    ".xlsx": "documents",
    ".ppt": "documents",
    ".pptx": "documents",
    ".md": "documents",
    ".csv": "documents",
    ".json": "documents",
    ".xml": "documents",
    ".yaml": "documents",
    ".yml": "documents",
    # 音频
    ".mp3": "audio",
    ".wav": "audio",
    ".flac": "audio",
    ".aac": "audio",
    ".ogg": "audio",
    ".m4a": "audio",
    ".wma": "audio",
    # 视频
    ".mp4": "video",
    ".avi": "video",
    ".mkv": "video",
    ".mov": "video",
    ".wmv": "video",
    ".flv": "video",
    ".webm": "video",
    # 压缩包
    ".zip": "archives",
    ".rar": "archives",
    ".tar": "archives",
    ".gz": "archives",
    ".bz2": "archives",
    ".7z": "archives",
    ".tgz": "archives",
    # 代码
    ".py": "code",
    ".js": "code",
    ".html": "code",
    ".css": "code",
    ".java": "code",
    ".cpp": "code",
    ".c": "code",
    ".h": "code",
    ".ts": "code",
    ".go": "code",
    ".rs": "code",
    ".sh": "code",
    ".bat": "code",
    # 可执行文件
    ".exe": "executables",
    ".msi": "executables",
    ".dmg": "executables",
    ".app": "executables",
    ".deb": "executables",
    ".rpm": "executables",
}


def classify_files(
    path: str,
    dry_run: bool = False,
    custom_categories: Optional[dict[str, str]] = None,
) -> dict:
    """
    将目录中的文件按扩展名分类整理到对应子文件夹。

    Args:
        path:              要整理的目录路径。
        dry_run:           仅模拟运行，不实际移动文件。
        custom_categories: 自定义分类映射，覆盖默认分类。
                           格式: {".ext": "category_name", ...}

    Returns:
        包含整理统计信息的字典：
        {
            "total": 文件总数,
            "moved": 成功移动数,
            "categories": {"分类名": [文件名列表], ...},
            "skipped": 跳过的文件列表,
            "category_counts": {"分类名": 文件数, ...}
        }

    Examples:
        >>> classify_files("/tmp/downloads")
        >>> classify_files("/tmp/files", dry_run=True)
    """
    if not os.path.isdir(path):
        raise FileNotFoundError(f"目录不存在: {path}")

    # 合并用户自定义分类
    categories = dict(EXTENSION_CATEGORIES)
    if custom_categories:
        categories.update(custom_categories)

    # 按分类分组文件
    categorized: dict[str, list[str]] = {}
    skipped: list[str] = []

    for filename in sorted(os.listdir(path)):
        full_path = os.path.join(path, filename)
        if not os.path.isfile(full_path):
            continue

        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        category = categories.get(ext)
        if category is None:
            category = "other"

        if category not in categorized:
            categorized[category] = []
        categorized[category].append(filename)

    # 创建分类目录并移动文件
    moved = 0
    for category, filenames in categorized.items():
        category_dir = os.path.join(path, category)
        if not os.path.exists(category_dir):
            if not dry_run:
                os.makedirs(category_dir, exist_ok=True)
            prefix_tag = "[DRY RUN] " if dry_run else ""
            print(f"{prefix_tag}创建目录: {category_dir}")

        for filename in filenames:
            src = os.path.join(path, filename)
            dst = os.path.join(category_dir, filename)

            if dry_run:
                print(f"[DRY RUN] {filename} -> {category}/")
                continue

            # 如果目标文件已存在，添加序号
            if os.path.exists(dst):
                name_part, ext_part = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dst):
                    dst = os.path.join(
                        category_dir, f"{name_part}_{counter}{ext_part}"
                    )
                    counter += 1

            try:
                shutil.move(src, dst)
                moved += 1
            except OSError as e:
                skipped.append(filename)
                print(f"移动失败 {filename}: {e}")

    # 统计数据（排除隐藏目录如 .git）
    category_counts = {
        cat: len(files) for cat, files in categorized.items()
    }

    return {
        "total": sum(len(v) for v in categorized.values()),
        "moved": moved,
        "categories": categorized,
        "skipped": skipped,
        "category_counts": category_counts,
    }
