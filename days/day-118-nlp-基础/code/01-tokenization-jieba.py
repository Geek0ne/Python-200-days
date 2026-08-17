#!/usr/bin/env python3
"""
Day 118 - 代码示例 1：jieba 分词基础用法
功能：演示 jieba 的三种分词模式、自定义词典、词性标注
依赖：pip install jieba
"""

import jieba
import jieba.posseg as pseg

def demo_basic_cut():
    """精确模式分词 — 最常用的分词方式"""
    print("=" * 60)
    print("📌 精确模式（默认）")
    print("=" * 60)

    text = "我在北京大学学习自然语言处理"
    # jieba.cut 返回生成器，用 "/" 连接查看
    words = jieba.cut(text)
    result = "/".join(words)
    print(f"  原文: {text}")
    print(f"  分词: {result}")
    print()

    # 多行对比
    examples = [
        "南京市长江大桥",
        "结婚的和尚未结婚的",
        "中华人民共和国",
        "他说的确实在理",
    ]

    for ex in examples:
        words = "/".join(jieba.cut(ex))
        print(f"  {ex}")
        print(f"  → {words}")
        print()


def demo_cut_all():
    """全模式 — 所有可能的组合"""
    print("=" * 60)
    print("📌 全模式")
    print("=" * 60)

    text = "我在北京大学学习自然语言处理"
    words = jieba.cut(text, cut_all=True)
    result = "/".join(words)
    print(f"  原文: {text}")
    print(f"  分词: {result}")
    print(f"  说明: 全模式会扫描所有可能的词语组合，召回率高但精确率低")
    print()


def demo_search_mode():
    """搜索引擎模式 — 兼顾召回和精确"""
    print("=" * 60)
    print("📌 搜索引擎模式")
    print("=" * 60)

    text = "南京市长江大桥"
    words = jieba.cut_for_search(text)
    result = "/".join(words)
    print(f"  原文: {text}")
    print(f"  分词: {result}")
    print(f"  说明: 在精确模式基础上，对长词再切分")
    print()


def demo_custom_dict():
    """自定义词典 — 添加领域专有名词"""
    print("=" * 60)
    print("📌 自定义词典")
    print("=" * 60)

    # 添加自定义词
    jieba.add_word("机器学习", freq=10000)
    jieba.add_word("深度学习", freq=10000)
    jieba.add_word("自然语言处理", freq=10000)
    jieba.add_word("聂生", freq=10000, tag="nr")  # nr = 人名

    text = "聂生研究机器学习和深度学习"
    before = "/".join(jieba.cut(text))
    print(f"  原文: {text}")
    print(f"  添加词典后: {before}")

    # 删除词
    jieba.del_word("机器学习")
    after = "/".join(jieba.cut(text))
    print(f"  删除词典后: {after}")
    print()

    # 外部词典文件格式说明
    print("  📄 外部词典文件格式（每行一个词）:")
    print("    机器学习 10000 n")
    print("    深度学习 10000 n")
    print("    聂生 10000 nr")
    print("  使用方式: jieba.load_userdict('mydict.txt')")
    print()


def demo_pos_tagging():
    """词性标注 — 给每个词标注词性"""
    print("=" * 60)
    print("📌 词性标注 (POS Tagging)")
    print("=" * 60)

    text = "我爱自然语言处理和机器学习"
    words = pseg.cut(text)

    print(f"  原文: {text}")
    print(f"  结果:")
    for word, flag in words:
        print(f"    {word:8s} → {flag} ({get_flag_desc(flag)})")
    print()


def get_flag_desc(flag):
    """获取词性标签的中文说明"""
    flag_map = {
        "n": "名词",
        "v": "动词",
        "a": "形容词",
        "r": "代词",
        "d": "副词",
        "m": "数词",
        "q": "量词",
        "p": "介词",
        "c": "连词",
        "u": "助词",
        "eng": "英文",
        "l": "习用语",
        "ns": "地名",
        "nr": "人名",
        "nt": "机构名",
        "nz": "其他专名",
    }
    return flag_map.get(flag, "其他")


def demo_tokenize_performance():
    """分词性能对比"""
    print("=" * 60)
    print("📌 分词性能对比")
    print("=" * 60)

    import time

    test_text = "自然语言处理是人工智能和机器学习领域的重要研究方向" * 100
    repeat = 1000

    # 精确模式
    start = time.time()
    for _ in range(repeat):
        list(jieba.cut(test_text))
    precise_time = time.time() - start

    # 全模式
    start = time.time()
    for _ in range(repeat):
        list(jieba.cut(test_text, cut_all=True))
    full_time = time.time() - start

    # 搜索引擎模式
    start = time.time()
    for _ in range(repeat):
        list(jieba.cut_for_search(test_text))
    search_time = time.time() - start

    print(f"  测试文本长度: {len(test_text)} 字符")
    print(f"  重复次数: {repeat}")
    print(f"  精确模式:   {precise_time:.3f}s")
    print(f"  全模式:     {full_time:.3f}s")
    print(f"  搜索模式:   {search_time:.3f}s")
    print()


if __name__ == "__main__":
    demo_basic_cut()
    demo_cut_all()
    demo_search_mode()
    demo_custom_dict()
    demo_pos_tagging()
    demo_tokenize_performance()
