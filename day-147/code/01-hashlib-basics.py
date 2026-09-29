#!/usr/bin/env python3
"""Day 147 - 01 哈希基础用法

演示 hashlib 核心操作：一次性哈希、增量 update、
算法对比、hex/digest 两种输出、大文件流式哈希。

直接运行: python3 01-hashlib-basics.py
"""

import hashlib

# ---------------------------------------------------------
# 1. 最基础的用法：一次性哈希
# ---------------------------------------------------------
data = "hello world".encode("utf-8")   # hashlib 只吃 bytes，字符串必须先 encode
print("SHA-256:", hashlib.sha256(data).hexdigest())
print("MD5    :", hashlib.md5(data).hexdigest())
print("SHA-1  :", hashlib.sha1(data).hexdigest())
print("BLAKE2b:", hashlib.blake2b(data).hexdigest())

# ---------------------------------------------------------
# 2. 雪崩效应：只改 1 个字符，摘要面目全非
# ---------------------------------------------------------
h1 = hashlib.sha256(b"hello world").hexdigest()
h2 = hashlib.sha256(b"hello worLd").hexdigest()   # 只把 w 换成 L？不，改了最后一个字母大小写
print("\n雪崩效应对比:")
print("  hello worLd:", h2)
print("  相同前缀位数:", sum(a == b for a, b in zip(h1, h2)), "/", len(h1))

# ---------------------------------------------------------
# 3. 增量 update：分多次喂入 == 一次性喂入
#    这是流式处理大文件的基础
# ---------------------------------------------------------
h = hashlib.sha256()
h.update(b"hello ")
h.update(b"world")
print("\n增量哈希与一次性一致:", h.hexdigest() == hashlib.sha256(b"hello world").hexdigest())

# ---------------------------------------------------------
# 4. digest() vs hexdigest()
# ---------------------------------------------------------
d = hashlib.sha256(b"hello world")
raw = d.digest()          # 32 字节二进制
hexs = d.hexdigest()      # 64 字符十六进制
print("digest 字节数:", len(raw), "| hex 字符数:", len(hexs))
print("两者互转:", raw.hex() == hexs)

# ---------------------------------------------------------
# 5. 哈希对象的元信息
# ---------------------------------------------------------
print("\n算法名:", d.name, "| 摘要长度:", d.digest_size, "字节 | 分块大小:", d.block_size, "字节")

# ---------------------------------------------------------
# 6. 流式计算本文件自身的 SHA-256（大文件标准姿势）
# ---------------------------------------------------------
def sha256_file(path: str, chunk_size: int = 1 << 20) -> str:
    """按 1 MiB 分块读取，内存占用恒定，适合任意大小文件。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()

print("\n本文件 SHA-256:", sha256_file(__file__))

# ---------------------------------------------------------
# 7. 可用算法一览
# ---------------------------------------------------------
print("\n保证可用的算法:", sorted(hashlib.algorithms_guaranteed))
