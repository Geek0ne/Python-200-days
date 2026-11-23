#!/usr/bin/env python3
"""02-data-cleaner.py — 数据清洗管线：去重 / 校验 / 归一化

读 raw_data.jsonl -> 清洗 -> 写 clean_data.jsonl + 清洗报告。
用法: python3 02-data-cleaner.py [raw_data.jsonl]
"""
import hashlib
import html as html_lib
import json
import re
import sys
import unicodedata

RAW = sys.argv[1] if len(sys.argv) > 1 else "raw_data.jsonl"
OUT = "clean_data.jsonl"

# 必填字段与类型
REQUIRED_FIELDS = {"url": str, "title": str}
TAG_RE = re.compile(r"<[^>]+>")

# ⚠️ 避坑1: \xa0 不间断空格用 strip() 去不掉，必须先 NFKC 归一化
# ⚠️ 避坑2: html.unescape 要在去标签【之后】再做一次，防止正文里
#            残留 &amp;lt; 这类双重转义


def normalize_text(s: str) -> str:
    """文本归一化：NFKC(全角->半角/\xa0->空格) + 去标签 + 反转义 + 压缩空白。"""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKC", s)   # ① 归一化字符
    s = TAG_RE.sub("", s)                  # ② 去掉 HTML 标签
    s = html_lib.unescape(s)               # ③ 反转义实体
    s = TAG_RE.sub("", s)                  # ④ 防双重转义再过一次
    s = re.sub(r"\s+", " ", s).strip()     # ⑤ 压缩空白
    return s


def fingerprint(title: str, content: str) -> str:
    """内容指纹：规范化后取摘要，容忍排版差异。"""
    key = (normalize_text(title).lower() + "|" + normalize_text(content)[:500].lower())
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def validate(item: dict) -> list[str]:
    """字段级校验，返回错误列表。"""
    errors = []
    for field, typ in REQUIRED_FIELDS.items():
        v = item.get(field)
        if v is None or (isinstance(v, str) and not v.strip()):
            errors.append(f"缺少必填字段 {field}")
        elif not isinstance(v, typ):
            errors.append(f"{field} 类型错误: 期望{typ.__name__}")
    return errors


def clean(records: list[dict]) -> tuple[list[dict], dict]:
    seen: dict[str, int] = {}
    clean_list, report = [], {
        "input": len(records), "invalid": 0, "duplicates": 0, "cleaned": 0}

    for idx, item in enumerate(records):
        # 1) 校验
        errors = validate(item)
        if errors:
            report["invalid"] += 1
            print(f"  [丢弃#{idx}] {errors}")
            continue

        # 2) 清洗文本字段
        out = dict(item)
        for k, v in item.items():
            if isinstance(v, str):
                out[k] = normalize_text(v)

        # 3) 指纹去重
        fp = fingerprint(out.get("title", ""), out.get("content", ""))
        if fp in seen:
            report["duplicates"] += 1
            print(f"  [去重#{idx}] 与第 {seen[fp]} 条重复: {out['title'][:30]}")
            continue
        seen[fp] = idx

        out["_fingerprint"] = fp
        clean_list.append(out)

    report["cleaned"] = len(clean_list)
    return clean_list, report


def main():
    records = []
    try:
        with open(RAW, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    except FileNotFoundError:
        # 没有输入文件时用内置脏数据演示
        print(f"(未找到 {RAW}，使用内置脏数据演示)")
        records = [
            {"url": "https://x.com/a", "title": " Hello  World ", "content": "<p>A&nbsp;&amp; B</p>"},
            {"url": "https://x.com/a2", "title": "hello world", "content": "A & B"},       # 与上条同指纹
            {"url": "https://x.com/b", "title": "", "content": "缺标题"},                    # 无效
            {"url": "https://x.com/c", "title": "Ｎｅｗｓ：全角标题", "content": "正文　带全角空格"},  # 需归一化
            {"url": "https://x.com/d", "title": 12345, "content": "标题类型错误"},            # 类型错
        ]

    clean_list, report = clean(records)

    with open(OUT, "w", encoding="utf-8") as f:
        for item in clean_list:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print("\n== 清洗报告 ==")
    for k, v in report.items():
        print(f"  {k:10s}: {v}")
    print(f"输出: {OUT}")

if __name__ == "__main__":
    main()
