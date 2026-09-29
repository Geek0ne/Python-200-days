#!/usr/bin/env python3
"""Day 147 - 03 实战：文件完整性校验工具

实现一个类似 sha256sum 的迷你工具，支持：
  1. generate: 为目录生成 SHA256SUMS 清单
  2. verify:   逐文件校验，报告被篡改/缺失的文件
  3. 用 HMAC 对清单本身签名，防止"连清单一起篡改"的攻击

用法:
  python3 03-file-integrity.py generate <目录>
  python3 03-file-integrity.py verify   <目录>
  python3 03-file-integrity.py sign     <目录>
  python3 03-file-integrity.py check    <目录>
"""

import hashlib
import hmac
import os
import sys

CHUNK = 1 << 20  # 1 MiB
MANIFEST = "SHA256SUMS"
SIGNED_MANIFEST = "SHA256SUMS.sig"
KEY_FILE = ".integrity-key"


# ---------------------------------------------------------
# 核心函数：流式哈希（大文件内存恒定）
# ---------------------------------------------------------
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def load_key() -> bytes:
    """签名密钥：首次自动生成，存本地（演示用；生产应放 KMS/环境变量）"""
    if os.path.exists(KEY_FILE):
        return open(KEY_FILE, "rb").read()
    key = os.urandom(32)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    os.chmod(KEY_FILE, 0o600)   # 只有 owner 可读
    return key


def list_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in sorted(filenames):
            if name in (MANIFEST, SIGNED_MANIFEST, KEY_FILE):
                continue
            yield os.path.join(dirpath, name)


# ---------------------------------------------------------
# 子命令 1：生成清单
# ---------------------------------------------------------
def cmd_generate(root: str) -> None:
    lines = []
    for path in list_files(root):
        rel = os.path.relpath(path, root)
        lines.append(f"{sha256_file(path)}  {rel}")
    out = os.path.join(root, MANIFEST)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"✅ 已生成 {out}（{len(lines)} 个文件）")


# ---------------------------------------------------------
# 子命令 2：校验清单
# ---------------------------------------------------------
def cmd_verify(root: str) -> bool:
    manifest = os.path.join(root, MANIFEST)
    if not os.path.exists(manifest):
        print(f"❌ 找不到 {manifest}，请先 generate")
        return False

    ok = missing = mismatch = 0
    with open(manifest, encoding="utf-8") as f:
        entries = [line.split("  ", 1) for line in f if line.strip()]

    expected = {rel.strip(): digest for digest, rel in entries}
    # 1) 清单里的文件逐一校验
    for rel, digest in expected.items():
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            print(f"  ❌ 缺失: {rel}")
            missing += 1
        elif not hmac.compare_digest(sha256_file(path), digest):
            print(f"  ⚠️  被篡改: {rel}")
            mismatch += 1
        else:
            ok += 1
    # 2) 清单外多出来的文件也要报告
    for path in list_files(root):
        rel = os.path.relpath(path, root)
        if rel not in expected:
            print(f"  ➕ 未登记的新文件: {rel}")
    print(f"\n结果: {ok} 通过 / {missing} 缺失 / {mismatch} 篡改")
    return missing == 0 and mismatch == 0


# ---------------------------------------------------------
# 子命令 3/4：对清单本身做 HMAC 签名 / 验签
#    防止攻击者改完文件再把清单一起改掉
# ---------------------------------------------------------
def cmd_sign(root: str) -> None:
    manifest = os.path.join(root, MANIFEST)
    mac = hmac.new(load_key(), open(manifest, "rb").read(), hashlib.sha256).hexdigest()
    with open(os.path.join(root, SIGNED_MANIFEST), "w") as f:
        f.write(mac)
    print(f"✅ 清单已签名 → {SIGNED_MANIFEST}")


def cmd_check(root: str) -> bool:
    manifest = os.path.join(root, MANIFEST)
    sig_path = os.path.join(root, SIGNED_MANIFEST)
    if not os.path.exists(sig_path):
        print("❌ 缺少签名文件")
        return False
    expected = open(sig_path).read().strip()
    actual = hmac.new(load_key(), open(manifest, "rb").read(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(actual, expected):
        print("❌ 清单签名校验失败 —— 清单本身被动过！")
        return False
    print("✅ 清单签名有效，继续逐文件校验…")
    return cmd_verify(root)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in {"generate", "verify", "sign", "check"}:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    root = sys.argv[2]
    if cmd == "generate":
        cmd_generate(root)
    elif cmd == "verify":
        sys.exit(0 if cmd_verify(root) else 1)
    elif cmd == "sign":
        cmd_sign(root)
    else:
        sys.exit(0 if cmd_check(root) else 1)
