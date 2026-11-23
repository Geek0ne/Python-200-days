#!/usr/bin/env python3
"""
02 - 混淆识别与反混淆基础（进阶/避坑）
=====================================
演示：
1. 识别常见混淆特征（_0x 数组、eval、十六进制字符串）
2. 模拟字符串数组混淆的"动态执行破解"思路
3. 避坑：为什么正则替换不可靠

运行：python3 02-deobfuscate-basic.py
"""
import re

# ---------------------------------------------------------------
# 1. 混淆特征检测器
# ---------------------------------------------------------------
def detect_obfuscation(js_code: str) -> list:
    """返回检测到的混淆特征列表"""
    features = []
    if re.search(r"_0x[a-f0-9]{4,}", js_code):
        features.append("十六进制乱名（obfuscator.io 典型特征）")
    if re.search(r"var\s+_0x[a-f0-9]+\s*=\s*\[", js_code):
        features.append("字符串数组（需运行时解密取值）")
    if re.search(r"\\x[0-9a-f]{2}", js_code):
        features.append("十六进制字符串编码")
    if "eval(" in js_code:
        features.append("eval 动态执行")
    if re.search(r"while\s*\(\s*!!\[\]\s*\)\s*\{", js_code):
        features.append("控制流平坦化（while-switch 状态机）")
    if re.search(r"atob\s*\(", js_code):
        features.append("base64 编码字符串")
    return features

# ---------------------------------------------------------------
# 2. 模拟"Console 动态执行"破解字符串数组
#    原理：混淆代码在浏览器必然解密后才能使用，
#    所以直接调用取值函数就能拿到明文
# ---------------------------------------------------------------
OBFUSCATED = r"""
var _0x4e2c = ['\x73\x61\x6c\x74\x31\x32\x33', '\x67\x65\x6e\x53\x69\x67\x6e'];
function _0xget(i) { return _0x4e2c[i]; }
function genSign(page) { return md5(String(page) + _0xget(0)); }
"""

def hex_unescape(s: str) -> str:
    """模拟浏览器里解密 \\x 十六进制字符串"""
    return s.encode().decode("unicode_escape")

def reveal_string_array(js_code: str) -> list:
    """提取并解密字符串数组 -- 相当于在 Console 执行 _0xget(i)"""
    m = re.search(r"\[((?:'[^']*'(?:,\s*)?)+)\]", js_code)
    strings = re.findall(r"'([^']*)'", m.group(1))
    return [hex_unescape(s) for s in strings]

# ---------------------------------------------------------------
# 3. 避坑演示：正则替换为什么不可靠
# ---------------------------------------------------------------
TRAP_CODE = "var a = 'sign'; var b = 'sign' + x; // sign in comment"

if __name__ == "__main__":
    print("== 1. 混淆特征检测 ==\n")
    feats = detect_obfuscation(OBFUSCATED)
    for f in feats:
        print(f"  ⚠️ 检测到: {f}")
    if not feats:
        print("  未检测到已知混淆特征")

    print("\n== 2. 字符串数组动态解密（模拟 Console 执行）==\n")
    plain = reveal_string_array(OBFUSCATED)
    for i, s in enumerate(plain):
        print(f"  _0xget({i}) = {s!r}")
    print(f"\n  结论：算法是 md5(page + '{plain[0]}')，密钥到手 ✅")

    print("\n== 3. 正则替换陷阱 ==\n")
    # 想把 sign 替换成 token：
    naive = TRAP_CODE.replace("sign", "token")   # 连注释、字符串全替换了
    print(f"  原始: {TRAP_CODE}")
    print(f"  替换: {naive}")
    print("  问题: 注释和字符串都被误替换 -- 这就是为什么专业工具用 AST 而不是正则")
    print("  AST 按语法节点精确操作（只改 Identifier），格式无关、永不误伤")
