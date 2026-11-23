#!/usr/bin/env python3
"""
Day 026 — 字符串编码专题：从 ASCII 到 Unicode

涵盖：
1. ord() / chr() 与码点概念
2. 不同编码的字节长度对比
3. BOM (Byte Order Mark) 详解
4. 常见编码错误与修复
5. 文件编码自动检测
6. 编码规范最佳实践

可直接运行：python3 04-encoding-practical.py
"""

import sys

print("=" * 60)
print("1. ord() / chr() — 字符与码点转换")
print("=" * 60)

# ord: 字符 → 码点 (整数)
# chr: 码点 → 字符
chars = ['A', 'a', '0', '中', '😊', '你', '\n']
for c in chars:
    code_point = ord(c)
    hex_str = f"U+{code_point:04X}"
    print(f"  ord('{c}'): {code_point:>5}  →  {hex_str}")

print()

# chr 反向验证
for code in [65, 97, 20013, 128522]:
    char = chr(code)
    print(f"  chr({code}): '{char}'")

print("\n" + "=" * 60)
print("2. 不同编码的字节表示对比")
print("=" * 60)

test_chars = [
    ('A', '拉丁字母'),
    ('中', '汉字'),
    ('😊', 'Emoji'),
    ('\u0000', '空字符'),
]

print(f"{'字符':<8} {'编码':<12} {'字节表示':<35} {'长度':<6}")
print("-" * 60)
for char, desc in test_chars:
    for enc in ['utf-8', 'utf-16-le', 'utf-32-le', 'gbk']:
        try:
            encoded = char.encode(enc)
            hex_str = encoded.hex(' ')
            print(f"  '{char}' ({enc:10s}): {hex_str:<33} {len(encoded)} bytes")
        except UnicodeEncodeError:
            print(f"  '{char}' ({enc:10s}): {'❌ 无法编码':<33}")

print("\n" + "=" * 60)
print("3. BOM (Byte Order Mark) 的秘密")
print("=" * 60)

# BOM 是文件开头的特殊字节序列，标记编码方式和字节序
text = "Hello"

# UTF-8 的 BOM (EF BB BF) — 仅用于标记"这是 UTF-8"
utf8_bom = b'\xef\xbb\xbf' + text.encode('utf-8')
print(f"UTF-8 BOM:      {utf8_bom.hex(' ')}")
print(f"UTF-8 无 BOM:   {(text.encode('utf-8')).hex(' ')}")
print(f"带 BOM 解码:   {utf8_bom.decode('utf-8-sig')}")  # utf-8-sig 自动去除 BOM
print(f"带 BOM 解码(普通): {utf8_bom.decode('utf-8')}")   # 保留 BOM 字符 \ufeff

# UTF-16 LE BOM (FF FE)
utf16le_bom = b'\xff\xfe' + text.encode('utf-16-le')
print(f"\nUTF-16 LE BOM:  {utf16le_bom.hex(' ')}")

# UTF-16 BE BOM (FE FF)
utf16be_bom = b'\xfe\xff' + text.encode('utf-16-be')
print(f"UTF-16 BE BOM:  {utf16be_bom.hex(' ')}")

print(f"\n💡 通过前2个字节判断字节序:")
print(f"  FF FE → Little Endian (小端)")
print(f"  FE FF → Big Endian (大端)")

print("\n" + "=" * 60)
print("4. 常见编码错误场景与修复")
print("=" * 60)

# 场景 1: 用错误编码打开文件
print("--- 场景1: 编码不匹配 ---")
bytes_wrong = '你好世界'.encode('gbk')
try:
    bytes_wrong.decode('utf-8')  # 用 utf-8 解码 gbk 数据
except UnicodeDecodeError as e:
    print(f"  ❌ UTF-8 解码 GBK 数据: {e}")

correct = bytes_wrong.decode('gbk')
print(f"  ✅ GBK 解码: {correct}")

# 场景 2: 混合编码
print("\n--- 场景2: 混合编码（部分乱码修复）---")
# 模拟一个不小心混合了两种编码的字符串
mixed = "用户".encode('utf-8') + "信息".encode('gbk')
print(f"  混合编码 bytes: {mixed.hex(' ')}")

# 尝试自动逐段解码
def smart_decode(data: bytes) -> str:
    """尝试对每段数据进行最优解码"""
    result = []
    remaining = data
    while remaining:
        best = None
        best_len = 0
        for enc in ['utf-8', 'utf-16', 'gbk', 'gb2312', 'latin-1']:
            try:
                decoded = remaining.decode(enc)
                if len(decoded) > best_len:
                    best = decoded
                    best_len = len(decoded)
            except UnicodeDecodeError:
                continue
        if best:
            result.append(str(best_len))
            result.append(":" + str(best[:20]))
            break
        else:
            result.append("?")
            remaining = remaining[1:]
    return ", ".join(result[:5])

print(f"  智能解码尝试: {smart_decode(mixed)[:50]}...")

# 场景 3: 文件名编码
print("\n--- 场景3: 文件名编码问题 ---")
# 在 Linux 上，文件名是 bytes，需要用 surrogateescape 处理
bad_filename = '文件\xff名称'.encode('utf-8', errors='surrogateescape')
print(f"  含非法字节的文件名: {bad_filename}")
print(f"  用 surrogateescape 解码: ", end="")
print(bad_filename.decode('utf-8', errors='surrogateescape'))

print("\n" + "=" * 60)
print("5. 实用工具函数")
print("=" * 60)


def safe_write_to_file(filename: str, content: str, encoding: str = 'utf-8'):
    """带编码异常处理的文件写入"""
    try:
        with open(filename, 'w', encoding=encoding) as f:
            f.write(content)
        print(f"  ✅ 成功写入 {filename} (编码: {encoding})")
    except UnicodeEncodeError as e:
        print(f"  ❌ 写入失败: {e}")
        print(f"  💡 建议: 使用 'utf-8' 编码，它支持所有 Unicode 字符")


def detect_text_encoding(data: bytes) -> str:
    """
    简易编码检测（生产环境请用 chardet 库）

    基于 BOM 和常见编码启发式判断
    """
    # BOM 检测
    if data[:3] == b'\xef\xbb\xbf':
        return 'utf-8-sig'
    if data[:2] == b'\xff\xfe':
        return 'utf-16-le'
    if data[:2] == b'\xfe\xff':
        return 'utf-16-be'

    # 尝试解码
    for enc in ['utf-8', 'gbk', 'shift_jis', 'euc-jp', 'latin-1']:
        try:
            data.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    return 'unknown'


# 测试编码检测
test_cases = [
    ('Pure ASCII', 'hello world'.encode('ascii')),
    ('UTF-8 中文', '你好'.encode('utf-8')),
    ('GBK 中文', '你好'.encode('gbk')),
    ('日文 Shift-JIS', 'こんにちは'.encode('shift_jis')),
    ('UTF-8 BOM', b'\xef\xbb\xbf' + '你好'.encode('utf-8')),
    ('UTF-16 LE', '你好'.encode('utf-16-le')),
]

print("编码检测结果:")
for desc, data in test_cases:
    detected = detect_text_encoding(data)
    print(f"  {desc:20s}: 检测为 {detected}")

print("\n" + "=" * 60)
print("6. 编码最佳实践总结")
print("=" * 60)

print("""
📋 Python 编码黄金法则:

1. 🏠 内存中用 str (Unicode) — 所有字符串操作在 str 上进行
2. 📤 输出时用 .encode() — 写文件/网络/数据库时转 bytes
3. 📥 输入时用 .decode() — 读文件/网络/数据库时转 str
4. 📁 文件操作永远指定 encoding= 参数
5. 🌐 默认编码用 'utf-8' — 除非有明确的兼容性需求
6. ❌ 遇到编码错误先确认: 数据实际是什么编码？
7. 🔧 使用 errors='replace' 或 'surrogateescape' 处理异常
8. 🔍 不确定编码时用 chardet 库自动检测

❌ 常见反模式:
  - 用 str.encode() 再 str() 包装 → 应该用 bytes.decode()
  - 不指定文件编码 → 依赖平台默认编码（跨平台必炸）
  - 假设所有文本都是 ASCII → 国际化项目原样处理
""")

# 系统编码信息
print(f"💻 当前系统默认编码:")
print(f"  sys.getdefaultencoding(): {sys.getdefaultencoding()}")
print(f"  sys.getfilesystemencoding(): {sys.getfilesystemencoding()}")
print(f"  sys.stdout.encoding: {sys.stdout.encoding}")

print("\n✅ 编码专题演示完成！")
