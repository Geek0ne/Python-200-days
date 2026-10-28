#!/usr/bin/env python3
"""04-make-corpus.py — 压测语料生成器（实验 3 的夹具）

为什么单独成一个文件：
  README 里如果要嵌一段"生成带代码围栏的 Markdown"的脚本，
  围栏本身会把外层代码块截断。把夹具放进文件，实验命令就只剩一行。

用法:
    python3 04-make-corpus.py /tmp/day199        # 生成 small/mid/big 三档
    python3 04-make-corpus.py /tmp/day199 --self-test
"""
import os
import sys

FENCE = chr(96) * 3  # 三反引号：代码围栏


def make(path: str, sections: int) -> int:
    parts = ["# 合成文章 %d 段" % sections, ""]
    for i in range(sections):
        parts += [
            "## 小节 %d" % i,
            "",
            "这是一段用于压测体检器的正文，包含内联代码 `x = %d` 与普通句子。" % i,
            "",
            FENCE + "python",
            "print(%d)" % i,
            FENCE,
            "",
        ]
    data = "\n".join(parts)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(data)
    return len(data.encode())


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/day199"
    if "--self-test" in sys.argv:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            size = make(os.path.join(tmp, "x.md"), 2)
            text = open(os.path.join(tmp, "x.md"), encoding="utf-8").read()
            assert FENCE in text and "print(1)" in text, "生成内容缺少代码块"
            assert size > 0
            print(f"SELF-TEST PASS（{size} 字节）")
        return 0
    os.makedirs(out, exist_ok=True)
    for n, name in [(400, "small"), (2000, "mid"), (8000, "big")]:
        size = make(os.path.join(out, name + ".md"), n)
        print(f"  {name}.md  {n} 节  {size} 字节")
    print(f"✅ 语料已生成：{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
