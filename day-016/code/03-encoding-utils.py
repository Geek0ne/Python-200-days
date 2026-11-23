#!/usr/bin/env python3
"""
Day 016 — 编码处理工具实战
============================
功能：
1. 自动检测文件编码（使用 chardet 或内置检测）
2. 编码转换（任意编码间转换）
3. 批量文件转码
4. 编码错误修复策略
5. 命令行接口
"""

import os
import sys
import glob
import io
import argparse
from pathlib import Path
from collections import Counter


# ════════════════════════════════════════════
# 编码检测（内置 fallback 实现）
# ════════════════════════════════════════════

# 尝试导入 chardet，如果没有则使用内置简单检测
try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False
    print("⚠️  chardet 未安装，将使用内置的简单编码检测")
    print("   建议安装: pip install chardet")
    print()


# 常见编码的 BOM 标记
BOM_SIGNATURES = {
    b"\xef\xbb\xbf": "utf-8-sig",     # UTF-8 with BOM
    b"\xff\xfe": "utf-16-le",          # UTF-16 Little Endian
    b"\xfe\xff": "utf-16-be",          # UTF-16 Big Endian
    b"\xff\xfe\x00\x00": "utf-32-le",   # UTF-32 Little Endian
    b"\x00\x00\xfe\xff": "utf-32-be",   # UTF-32 Big Endian
}


def detect_encoding_by_bom(data: bytes) -> str | None:
    """通过 BOM 标记检测编码"""
    for bom, encoding in BOM_SIGNATURES.items():
        if data.startswith(bom):
            return encoding
    return None


def detect_encoding_simple(data: bytes) -> str:
    """简单的编码检测（不依赖 chardet）"""
    # 先检查 BOM
    bom_enc = detect_encoding_by_bom(data)
    if bom_enc:
        return bom_enc
    
    # 尝试常见的编码
    encodings_to_try = ["utf-8", "gbk", "gb2312", "shift_jis", "euc-kr",
                        "iso-8859-1", "cp1252", "big5", "utf-16"]
    
    for enc in encodings_to_try:
        try:
            data.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    
    # 如果都不行，用 latin-1（永远不会失败，但可能乱码）
    return "latin-1"


def detect_encoding(filepath: str) -> dict:
    """检测文件编码
    
    Returns:
        dict: {
            "encoding": str,
            "confidence": float,
            "detector": str,  # "chardet" | "bom" | "simple"
        }
    """
    # 读取文件的前 1MB 用于检测
    with open(filepath, "rb") as f:
        raw = f.read(1024 * 1024)  # 1MB 足够检测
    
    # 1. BOM 检测
    bom_enc = detect_encoding_by_bom(raw)
    if bom_enc:
        return {
            "encoding": bom_enc,
            "confidence": 1.0,
            "detector": "bom",
        }
    
    # 2. chardet 检测
    if HAS_CHARDET:
        result = chardet.detect(raw)
        if result["encoding"] and result["confidence"] > 0.5:
            return {
                "encoding": result["encoding"].lower(),
                "confidence": result["confidence"],
                "detector": "chardet",
            }
    
    # 3. 简单检测
    enc = detect_encoding_simple(raw)
    return {
        "encoding": enc,
        "confidence": 0.5 if enc != "latin-1" else 0.1,
        "detector": "simple",
    }


# ════════════════════════════════════════════
# 编码转换核心
# ════════════════════════════════════════════

ENCODING_ALIASES = {
    "utf8": "utf-8",
    "utf-8-sig": "utf-8",  # BOM 版本，读时会自动去掉 BOM
    "gb2312": "gbk",
    "gb18030": "gbk",
    "cp936": "gbk",
    "ms936": "gbk",
    "shiftjis": "shift_jis",
    "sjis": "shift_jis",
    "euckr": "euc-kr",
    "latin1": "latin-1",
    "latin": "latin-1",
    "iso88591": "iso-8859-1",
    "iso8859-1": "latin-1",
}


def normalize_encoding(encoding: str) -> str:
    """规范化编码名称"""
    enc = encoding.lower().replace("-", "").replace("_", "")
    return ENCODING_ALIASES.get(enc, encoding.lower())


class EncodingErrorHandler:
    """编码错误处理策略"""
    
    STRATEGIES = {
        "strict": {
            "decode": "strict",
            "encode": "strict",
            "desc": "遇到非法编码时抛出异常（最安全）",
        },
        "ignore": {
            "decode": "ignore",
            "encode": "ignore",
            "desc": "静默跳过非法字节（可能丢失数据）",
        },
        "replace": {
            "decode": "replace",
            "encode": "replace",
            "desc": "用 ? 替换非法字节",
        },
        "backslashreplace": {
            "decode": "backslashreplace",
            "encode": "backslashreplace",
            "desc": "用 \\xNN \\uNNNN 转义（不丢失信息）",
        },
        "xmlcharrefreplace": {
            "decode": "strict",      # 只对 encode 有效
            "encode": "xmlcharrefreplace",
            "desc": "用 XML/HTML 字符引用替换（如 &#xxxx;）",
        },
        "surrogateescape": {
            "decode": "surrogateescape",
            "encode": "surrogateescape",
            "desc": "Python 专用，用于系统接口（如文件系统）",
        },
    }
    
    @classmethod
    def list_strategies(cls) -> str:
        lines = ["编码错误处理策略:", "─" * 40]
        for name, info in cls.STRATEGIES.items():
            lines.append(f"  {name:<22s} {info['desc']}")
        return "\n".join(lines)


def convert_encoding(
    data: str | bytes,
    from_encoding: str = "utf-8",
    to_encoding: str = "utf-8",
    errors: str = "strict",
) -> bytes:
    """编码转换
    
    Args:
        data: 要转换的数据（str 或 bytes）
        from_encoding: 源编码（data 为 str 时忽略）
        to_encoding: 目标编码
        errors: 错误处理策略
    
    Returns:
        bytes: 转换后的字节数据
    """
    if isinstance(data, bytes):
        text = data.decode(from_encoding, errors=errors)
    else:
        text = data
    
    return text.encode(to_encoding, errors=errors)


def convert_file(
    src_path: str,
    dst_path: str = None,
    from_encoding: str = None,
    to_encoding: str = "utf-8",
    errors: str = "replace",
    inplace: bool = False,
) -> dict:
    """文件编码转换
    
    Args:
        src_path: 源文件路径
        dst_path: 目标文件路径（None 时自动命名）
        from_encoding: 源编码（None 时自动检测）
        to_encoding: 目标编码
        errors: 错误处理策略
        inplace: 是否原地转换（覆盖原文件）
    
    Returns:
        dict: 转换统计信息
    """
    # 自动检测源编码
    if from_encoding is None:
        detected = detect_encoding(src_path)
        from_encoding = detected["encoding"]
        source_confidence = detected["confidence"]
    else:
        source_confidence = 1.0
    
    # 读取源文件
    with open(src_path, "rb") as f:
        raw_data = f.read()
    
    # 解码
    try:
        text = raw_data.decode(from_encoding, errors=errors)
    except UnicodeDecodeError as e:
        return {
            "success": False,
            "error": f"解码失败 ({from_encoding}): {e}",
            "from_encoding": from_encoding,
            "to_encoding": to_encoding,
        }
    
    # 编码为目标编码
    output = text.encode(to_encoding, errors=errors)
    
    # 确定目标路径
    if inplace:
        output_path = src_path
    elif dst_path:
        output_path = dst_path
    else:
        # 自动命名: original_utf8.txt
        p = Path(src_path)
        output_path = str(p.parent / f"{p.stem}_{to_encoding.replace('-', '')}{p.suffix}")
    
    # 写入
    with open(output_path, "wb") as f:
        f.write(output)
    
    src_size = len(raw_data)
    dst_size = len(output)
    
    return {
        "success": True,
        "file": src_path,
        "output": output_path,
        "from_encoding": from_encoding,
        "to_encoding": to_encoding,
        "source_confidence": source_confidence,
        "errors": errors,
        "src_size": src_size,
        "dst_size": dst_size,
        "size_change": dst_size - src_size,
        "chars_converted": len(text),
    }


def batch_convert(
    directory: str,
    pattern: str = "*",
    from_encoding: str = None,
    to_encoding: str = "utf-8",
    errors: str = "replace",
    recursive: bool = False,
    backup: bool = False,
) -> list[dict]:
    """批量文件编码转换
    
    Args:
        directory: 目录路径
        pattern: 文件匹配模式 (如 "*.txt")
        from_encoding: 源编码（None 时自动检测）
        to_encoding: 目标编码
        errors: 错误处理策略
        recursive: 是否递归子目录
        backup: 是否备份原文件
    
    Returns:
        list: 每个文件的转换结果
    """
    results = []
    search_path = os.path.join(directory, "**", pattern) if recursive else os.path.join(directory, pattern)
    files = glob.glob(search_path, recursive=recursive)
    
    if not files:
        print(f"⚠️  未匹配到文件: {search_path}")
        return results
    
    # 排除非文件
    files = [f for f in files if os.path.isfile(f)]
    
    # 过滤二进制文件
    text_extensions = {
        ".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json",
        ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
        ".csv", ".log", ".sql", ".sh", ".bat", ".ps1", ".rst", ".tex",
    }
    files = [f for f in files if Path(f).suffix.lower() in text_extensions]
    
    print(f"📄 找到 {len(files)} 个文本文件")
    
    for i, filepath in enumerate(files, 1):
        result = convert_file(
            src_path=filepath,
            from_encoding=from_encoding,
            to_encoding=to_encoding,
            errors=errors,
            inplace=True,
        )
        result["file"] = filepath
        
        if result["success"]:
            print(f"  [{i:3d}/{len(files):3d}] ✅ {Path(filepath).name}: "
                  f"{result['from_encoding']} → {result['to_encoding']} "
                  f"({result['src_size']} → {result['dst_size']} bytes)")
        else:
            print(f"  [{i:3d}/{len(files):3d}] ❌ {Path(filepath).name}: {result['error']}")
        
        results.append(result)
    
    return results


# ════════════════════════════════════════════
# 编码修复工具
# ════════════════════════════════════════════

COMMON_ENCODING_PAIRS = [
    # (乱码情况的源编码, 实际编码)
    ("gbk", "utf-8"),        # GBK 编码的文本被当作 UTF-8 读取
    ("utf-8", "gbk"),        # UTF-8 编码被当作 GBK 读取
    ("latin-1", "utf-8"),    # Latin-1 编码被当作 UTF-8
    ("shift_jis", "utf-8"),  # 日文被当作 UTF-8
    ("utf-8-sig", "utf-8"),  # 有 BOM 的 UTF-8
]


def try_repair_garbled_text(filepath: str) -> list[dict]:
    """尝试修复乱码文本
    
    尝试常见的编码误判组合，找到可读性最好的版本
    
    Returns:
        list[dict]: 按可读性评分排序的修复结果
    """
    with open(filepath, "rb") as f:
        raw = f.read()
    
    results = []
    
    # 方案 1: 直接尝试各种编码
    for wrong_enc, correct_enc in COMMON_ENCODING_PAIRS:
        try:
            # 模拟错误解码 + 正确解码
            wrongly_decoded = raw.decode(wrong_enc, errors="replace")
            repaired = wrongly_decoded.encode(correct_enc, errors="replace")
            final_text = repaired.decode(correct_enc, errors="replace")
            
            score = _readability_score(final_text)
            results.append({
                "wrong_encoding": wrong_enc,
                "correct_encoding": correct_enc,
                "text": final_text,
                "score": score,
                "method": "encoding_mismatch",
            })
        except Exception:
            continue
    
    # 方案 2: 直接用 chardet 检测的编码
    detected = detect_encoding(filepath)
    try:
        text = raw.decode(detected["encoding"], errors="replace")
        results.append({
            "wrong_encoding": "?",
            "correct_encoding": detected["encoding"],
            "text": text,
            "score": _readability_score(text),
            "method": "direct_detect",
        })
    except Exception:
        pass
    
    # 按可读性排序
    results.sort(key=lambda x: -x["score"])
    
    return results


def _readability_score(text: str) -> float:
    """评估文本可读性（越高越好）"""
    if not text:
        return 0.0
    
    score = 0.0
    total = len(text)
    
    # ASCII 可打印字符
    ascii_printable = sum(1 for c in text if 32 <= ord(c) <= 126)
    
    # CJK 字符
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    
    # 常见标点
    common_punct = sum(1 for c in text if c in "，。、；：？！""''（）【】《》…—·")
    
    # 替换字符（表示编码错误）
    replacement_chars = sum(1 for c in text if c in ('\ufffd', '?'))
    
    # 控制字符（除了常见空白）
    control_chars = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
    
    score += (ascii_printable + cjk * 2 + common_punct * 3) / total
    score -= replacement_chars / total * 5
    score -= control_chars / total * 10
    
    return max(0.0, min(1.0, score))


# ════════════════════════════════════════════
# 演示功能
# ════════════════════════════════════════════

def demo():
    """演示编码检测和转换功能"""
    print("=" * 60)
    print("  Day 016 — 编码处理工具演示")
    print("=" * 60)
    
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建不同编码的测试文件
        test_cases = [
            ("utf8_demo.txt", "utf-8", "Hello 你好 こんにちは"),
            ("gbk_demo.txt", "gbk", "Python 文件编码处理"),
            ("bom_demo.txt", "utf-8-sig", "\ufeff带BOM的UTF-8文件"),
        ]
        
        print("\n1. 编码检测演示")
        print("─" * 40)
        
        for fname, encoding, content in test_cases:
            fpath = os.path.join(tmpdir, fname)
            raw = content.encode(encoding)
            with open(fpath, "wb") as f:
                f.write(raw)
            
            result = detect_encoding(fpath)
            print(f"  {fname}:")
            print(f"    检测结果: {result['encoding']} "
                  f"(置信度: {result['confidence']:.0%}, "
                  f"检测器: {result['detector']})")
            print(f"    实际编码: {encoding}")
            match = "✅" if normalize_encoding(result['encoding']) == normalize_encoding(encoding) else "❌"
            print(f"    匹配: {match}")
        
        print("\n2. 编码转换演示")
        print("─" * 40)
        
        src = os.path.join(tmpdir, "gbk_demo.txt")
        dst = os.path.join(tmpdir, "gbk_to_utf8.txt")
        
        result = convert_file(src, dst, from_encoding="gbk")
        if result["success"]:
            print(f"  转换结果: {Path(src).name} → {Path(dst).name}")
            print(f"  源编码: {result['from_encoding']}")
            print(f"  目标编码: {result['to_encoding']}")
            print(f"  大小变化: {result['src_size']} → {result['dst_size']} bytes")
            
            with open(dst, "r", encoding="utf-8") as f:
                print(f"  内容: {f.read()}")
        
        print("\n3. 错误处理策略示例")
        print("─" * 40)
        
        # 创建一个含非法 UTF-8 字节的文件
        bad_file = os.path.join(tmpdir, "corrupted.txt")
        bad_data = b"Hello \xff\xfe World"  # 非法字节
        with open(bad_file, "wb") as f:
            f.write(bad_data)
        
        for strategy in ["strict", "ignore", "replace", "backslashreplace"]:
            try:
                with open(bad_file, "rb") as f:
                    raw = f.read()
                text = raw.decode("utf-8", errors=strategy)
                print(f"  {strategy:<20s}: {repr(text[:50])}")
            except UnicodeDecodeError as e:
                print(f"  {strategy:<20s}: ❌ {e}")
        
        print("\n4. 编码修复演示")
        print("─" * 40)
        
        # 模拟一个 UTF-8 文件被当作 GBK 读取后的乱码
        garbled_file = os.path.join(tmpdir, "garbled.txt")
        original = "这是中文内容"
        # 模拟错误: 用 GBK 编码的字节，但用 UTF-8 读取
        garbled_bytes = original.encode("gbk")
        wrongly_decoded = garbled_bytes.decode("utf-8", errors="replace")
        with open(garbled_file, "w", encoding="utf-8") as f:
            f.write(wrongly_decoded)
        print(f"  原始: {original}")
        print(f"  乱码: {wrongly_decoded}")
        
        repairs = try_repair_garbled_text(garbled_file)
        if repairs:
            best = repairs[0]
            print(f"  最佳修复: {best['text']}")
            print(f"  评分: {best['score']:.2f}")
            print(f"  方法: {best['method']}")
            print(f"  实际编码: {best['correct_encoding']}")
        
        print("\n✅ 演示完成")


# ════════════════════════════════════════════
# 命令行接口
# ════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="编码处理工具 — 检测、转换、修复文件编码",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s detect file.txt                                      # 检测编码
  %(prog)s convert file.txt --to utf-8                          # 转换为 UTF-8
  %(prog)s convert file.txt --from gbk --to utf-8               # 指定源编码转换
  %(prog)s convert file.txt --to utf-8 --inplace                # 原地转换
  %(prog)s convert file.txt --to utf-8 --errors ignore          # 忽略编码错误
  %(prog)s batch . "*.txt" --to utf-8                           # 批量转换
  %(prog)s batch . "*.py" --to utf-8 --recursive                # 递归批量转换
  %(prog)s repair garbled.txt                                   # 修复乱码
  %(prog)s list-strategies                                      # 列出错误处理策略
  %(prog)s demo                                                  # 运行演示
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # detect 子命令
    detect_parser = subparsers.add_parser("detect", help="检测文件编码")
    detect_parser.add_argument("file", help="文件路径")
    
    # convert 子命令
    convert_parser = subparsers.add_parser("convert", help="转换文件编码")
    convert_parser.add_argument("file", help="源文件路径")
    convert_parser.add_argument("--from", dest="from_encoding", default=None, help="源编码（默认自动检测）")
    convert_parser.add_argument("--to", dest="to_encoding", default="utf-8", help="目标编码（默认 utf-8）")
    convert_parser.add_argument("--output", "-o", help="输出文件路径")
    convert_parser.add_argument("--inplace", action="store_true", help="原地转换")
    convert_parser.add_argument("--errors", default="replace",
                                choices=["strict", "ignore", "replace", "backslashreplace"],
                                help="错误处理策略")
    
    # batch 子命令
    batch_parser = subparsers.add_parser("batch", help="批量转换编码")
    batch_parser.add_argument("directory", help="目录路径")
    batch_parser.add_argument("pattern", default="*.txt", nargs="?", help="文件匹配模式")
    batch_parser.add_argument("--from", dest="from_encoding", default=None, help="源编码")
    batch_parser.add_argument("--to", dest="to_encoding", default="utf-8", help="目标编码")
    batch_parser.add_argument("--errors", default="replace", help="错误处理策略")
    batch_parser.add_argument("--recursive", "-r", action="store_true", help="递归子目录")
    batch_parser.add_argument("--backup", action="store_true", help="备份原文件")
    
    # repair 子命令
    repair_parser = subparsers.add_parser("repair", help="尝试修复乱码文件")
    repair_parser.add_argument("file", help="乱码文件路径")
    
    # list-strategies 子命令
    subparsers.add_parser("list-strategies", help="列出编码错误处理策略")
    
    # demo 子命令
    subparsers.add_parser("demo", help="运行功能演示")
    
    args = parser.parse_args()
    
    if args.command == "detect":
        result = detect_encoding(args.file)
        print(f"文件: {args.file}")
        print(f"编码: {result['encoding']}")
        print(f"置信度: {result['confidence']:.1%}")
        print(f"检测方法: {result['detector']}")
    
    elif args.command == "convert":
        result = convert_file(
            src_path=args.file,
            dst_path=args.output,
            from_encoding=args.from_encoding,
            to_encoding=args.to_encoding,
            errors=args.errors,
            inplace=args.inplace,
        )
        if result["success"]:
            print(f"✅ 转换完成")
            print(f"  源文件: {result['file']}")
            print(f"  输出: {result['output']}")
            print(f"  {result['from_encoding']} → {result['to_encoding']}")
            print(f"  大小: {result['src_size']} → {result['dst_size']} bytes")
        else:
            print(f"❌ 转换失败: {result['error']}")
    
    elif args.command == "batch":
        results = batch_convert(
            directory=args.directory,
            pattern=args.pattern,
            from_encoding=args.from_encoding,
            to_encoding=args.to_encoding,
            errors=args.errors,
            recursive=args.recursive,
            backup=args.backup,
        )
        success = sum(1 for r in results if r["success"])
        print(f"\n📊 批量转换完成: {success}/{len(results)} 成功")
    
    elif args.command == "repair":
        repairs = try_repair_garbled_text(args.file)
        if not repairs:
            print("❌ 无法修复该文件")
            return
        
        print(f"找到 {len(repairs)} 个修复方案:")
        for i, r in enumerate(repairs):
            print(f"\n方案 {i+1}:")
            print(f"  使用 {r['correct_encoding']} 编码（评分: {r['score']:.2f}）")
            print(f"  前 100 字符: {r['text'][:100]}")
    
    elif args.command == "list-strategies":
        print(EncodingErrorHandler.list_strategies())
    
    elif args.command == "demo":
        demo()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
