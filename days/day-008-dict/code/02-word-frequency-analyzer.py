#!/usr/bin/env python3
"""
02-word-frequency-analyzer.py
Day 008 — 实战：词频统计器

一个完整的文本词频分析工具，涵盖：
- defaultdict / Counter 高效计数
- 字典排序与 Top-N 选取
- 文本预处理（去标点、小写化）
- 停用词过滤
- 结果可视化（直方图）
- 数据导出（CSV / JSON）

可直接运行：python3 02-word-frequency-analyzer.py
"""

import re
import json
import math
from collections import defaultdict, Counter
from typing import List, Tuple, Optional


# ============================================================
# 一、文本预处理模块
# ============================================================

class TextPreprocessor:
    """文本清洗与分词处理器"""

    # 常见英语停用词
    STOP_WORDS_EN = frozenset({
        "a", "an", "the", "and", "or", "but", "if", "because", "as",
        "what", "which", "this", "that", "these", "those", "then",
        "just", "so", "than", "such", "both", "through", "about",
        "for", "is", "are", "was", "were", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "can", "could", "shall", "should", "may", "might", "must",
        "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
        "you", "your", "yours", "yourself", "yourselves",
        "he", "him", "his", "himself", "she", "her", "hers", "herself",
        "it", "its", "itself", "they", "them", "their", "theirs",
        "themselves", "what", "which", "who", "whom", "this", "that",
        "these", "those", "am", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "having", "do", "does",
        "did", "doing", "would", "could", "should", "might", "must",
        "shall", "can", "need", "dare", "ought", "used",
        "no", "nor", "not", "only", "own", "same", "so", "than",
        "too", "very", "just", "because", "as", "until", "while",
        "of", "at", "by", "for", "with", "about", "against",
        "between", "into", "through", "during", "before", "after",
        "above", "below", "to", "from", "up", "down", "in", "out",
        "on", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how",
        "all", "each", "every", "both", "few", "more", "most",
        "other", "some", "such", "no", "nor", "not", "only",
        "own", "same", "than", "too", "very",
    })

    # 中文停用词
    STOP_WORDS_ZH = frozenset({
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
        "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
        "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她",
        "它", "们", "那", "些", "为", "所", "以", "能", "及", "但",
        "而", "或", "与", "被", "把", "从", "对", "向", "让", "将",
        "约", "等", "之", "其", "中", "如", "更", "已", "还", "又",
        "可", "该", "这个", "那个", "什么", "怎么", "哪", "谁", "因为",
        "所以", "如果", "虽然", "但是", "而且", "然后", "不过", "否则",
    })

    def __init__(self, language: str = "auto", remove_stopwords: bool = True):
        """
        Args:
            language: "en" / "zh" / "auto"（自动检测）
            remove_stopwords: 是否移除停用词
        """
        self.language = language
        self.remove_stopwords = remove_stopwords

    def _detect_language(self, text: str) -> str:
        """简易语言检测：检查中文字符比例"""
        zh_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(text.strip())
        if total_chars == 0:
            return "en"
        return "zh" if zh_chars / total_chars > 0.1 else "en"

    def _is_stopword(self, word: str, lang: str) -> bool:
        """检查是否为停用词"""
        word = word.lower().strip()
        if lang == "zh":
            return word in self.STOP_WORDS_ZH
        return word in self.STOP_WORDS_EN

    def clean(self, text: str) -> str:
        """基础清洗：去 HTML 标签、统一空白"""
        # 去 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        # 统一空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def tokenize(self, text: str) -> List[str]:
        """
        分词并清洗
        返回小写化的单词列表（英文）
        或字符/词语列表（中文）
        """
        lang = self.language if self.language != "auto" else self._detect_language(text)

        if lang == "zh":
            # 中文：按字符切分（简化处理，不支持 jieba 时用字符级）
            # 也可以用简单正则匹配中文词语和英文单词
            tokens = re.findall(r'[\u4e00-\u9fff]+', text)
            # 进一步将中文拆成单字（简易模式）
            result = []
            for token in tokens:
                for char in token:
                    result.append(char)
            return result
        else:
            # 英文：按非字母字符分割
            text = text.lower()
            tokens = re.findall(r"[a-z']+", text)
            # 过滤纯引号
            return [t for t in tokens if t.strip("'")]

    def process(self, text: str) -> List[str]:
        """
        完整处理管道：
        清洗 → 分词 → 停用词过滤 → 长度过滤
        """
        lang = self.language if self.language != "auto" else self._detect_language(text)

        # 清洗
        cleaned = self.clean(text)

        # 分词
        tokens = self.tokenize(cleaned)

        # 过滤
        filtered = []
        for token in tokens:
            # 跳过过短的词
            if len(token.strip("'")) < 2 and lang != "zh":
                continue
            if lang == "zh" and len(token) < 1:
                continue

            # 停用词过滤
            if self.remove_stopwords and self._is_stopword(token, lang):
                continue

            filtered.append(token)

        return filtered


# ============================================================
# 二、词频统计引擎
# ============================================================

class FrequencyAnalyzer:
    """词频统计分析引擎"""

    def __init__(self):
        self._raw_counter: Counter = Counter()
        self._total_words: int = 0
        self._unique_words: int = 0

    def analyze(self, tokens: List[str]):
        """分析词频"""
        self._raw_counter = Counter(tokens)
        self._total_words = len(tokens)
        self._unique_words = len(self._raw_counter)

    def top_n(self, n: int = 10) -> List[Tuple[str, int]]:
        """获取词频 Top-N"""
        return self._raw_counter.most_common(n)

    def bottom_n(self, n: int = 10) -> List[Tuple[str, int]]:
        """获取出现次数最少的 N 个词（只含正数）"""
        return self._raw_counter.most_common()[:-n - 1:-1] if n > 0 else []

    def frequency_of(self, word: str) -> int:
        """查询特定词的出现次数"""
        return self._raw_counter.get(word.lower(), 0)

    def words_above(self, threshold: int) -> List[Tuple[str, int]]:
        """出现次数超过阈值的词"""
        return [(w, c) for w, c in self._raw_counter.items() if c > threshold]

    def words_below(self, threshold: int) -> List[Tuple[str, int]]:
        """出现次数低于阈值的词（正数）"""
        return [(w, c) for w, c in self._raw_counter.items() if 0 < c < threshold]

    def frequency_distribution(self) -> dict:
        """词频分布：出现次数 → 具有该次数的词数量"""
        dist = defaultdict(int)
        for count in self._raw_counter.values():
            dist[count] += 1
        return dict(sorted(dist.items()))

    def lexical_diversity(self) -> float:
        """词汇丰富度：唯一词数 / 总词数"""
        if self._total_words == 0:
            return 0.0
        return self._unique_words / self._total_words

    @property
    def total_words(self) -> int:
        return self._total_words

    @property
    def unique_words(self) -> int:
        return self._unique_words

    @property
    def raw_counter(self) -> Counter:
        return self._raw_counter


# ============================================================
# 三、结果可视化模块
# ============================================================

class ResultVisualizer:
    """词频结果格式化与可视化"""

    @staticmethod
    def print_table(top_words: List[Tuple[str, int]], title: str = "词频统计"):
        """打印表格"""
        if not top_words:
            print("   (无数据)")
            return

        max_word_len = max(len(w) for w, _ in top_words)
        max_count = max(c for _, c in top_words)
        bar_max = 40  # 柱状图最大宽度

        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")
        print(f"  {'Rank':<5} {'Word':<{max(max_word_len + 2, 8)}} {'Count':<7} {'Bar'}")
        print(f"  {'-' * (55 + max_word_len)}")

        for rank, (word, count) in enumerate(top_words, 1):
            bar_len = max(1, int(count / max_count * bar_max))
            bar = "█" * bar_len
            print(f"  {rank:<5} {word:<{max(max_word_len + 2, 8)}} {count:<7} {bar}")

        print(f"{'=' * 60}")

    @staticmethod
    def print_distribution(dist: dict, title: str = "词频分布"):
        """打印分布信息"""
        print(f"\n  {title}:")
        print(f"  {'频次':<8} {'词数':<8} {'占比'}")
        print(f"  {'-' * 30}")
        total_unique = sum(dist.values())
        for freq, count in sorted(dist.items()):
            pct = count / total_unique * 100 if total_unique > 0 else 0
            bar_len = max(1, int(pct / 2))
            print(f"  {freq:<8} {count:<8} {pct:>5.1f}% {'░' * bar_len}")

    @staticmethod
    def print_statistics(analyzer: FrequencyAnalyzer):
        """打印总体统计信息"""
        top5 = analyzer.top_n(5)
        most_common_word = top5[0][0] if top5 else "N/A"
        most_common_count = top5[0][1] if top5 else 0

        print(f"\n  📊 统计摘要")
        print(f"  {'─' * 40}")
        print(f"  总词数:         {analyzer.total_words:,}")
        print(f"  唯一词数:       {analyzer.unique_words:,}")
        print(f"  词汇丰富度:     {analyzer.lexical_diversity():.2%}")
        print(f"  最高频词:       「{most_common_word}」({most_common_count}次)")
        print(f"  Top 5 占比:     {sum(c for _, c in top5) / analyzer.total_words:.1%}"
              if analyzer.total_words > 0 else "")


# ============================================================
# 四、数据导出模块
# ============================================================

class DataExporter:
    """结果导出工具"""

    @staticmethod
    def to_csv(counter: Counter, filepath: str, top_n: Optional[int] = None):
        """导出为 CSV"""
        items = counter.most_common(top_n) if top_n else counter.most_common()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("word,count\n")
            for word, count in items:
                f.write(f"{word},{count}\n")
        print(f"  ✅ 已导出 CSV → {filepath} （{len(items)} 行）")

    @staticmethod
    def to_json(counter: Counter, filepath: str, indent: int = 2):
        """导出为 JSON"""
        data = {
            "total_unique_words": len(counter),
            "word_frequencies": counter.most_common(),
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        print(f"  ✅ 已导出 JSON → {filepath}")

    @staticmethod
    def to_text_table(counter: Counter, filepath: str, top_n: int = 20):
        """导出为文本表格"""
        items = counter.most_common(top_n)
        lines = ["词频统计结果", "=" * 40, f"{'Rank':<5} {'Word':<15} {'Count':<8}", "-" * 30]
        for rank, (word, count) in enumerate(items, 1):
            lines.append(f"{rank:<5} {word:<15} {count:<8}")
        lines.append("=" * 40)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        print(f"  ✅ 已导出表格 → {filepath}")


# ============================================================
# 五、完整高频词分析管道
# ============================================================

class WordFrequencyPipeline:
    """完整的词频分析管道"""

    def __init__(self, language: str = "auto"):
        self.preprocessor = TextPreprocessor(language=language)
        self.analyzer = FrequencyAnalyzer()
        self.visualizer = ResultVisualizer()
        self.exporter = DataExporter()

    def run(self, text: str, top_n: int = 20, export_prefix: Optional[str] = None):
        """
        执行完整的词频分析

        Args:
            text: 要分析的文本
            top_n: 显示前 N 个高频词
            export_prefix: 如果提供，导出文件到此前缀

        Returns:
            Counter 对象
        """
        print("=" * 60)
        print("  📝 词频统计器 — 完整分析报告")
        print("=" * 60)

        # 步骤 1：预处理
        print("\n  📌 Step 1: 文本预处理")
        tokens = self.preprocessor.process(text)
        print(f"     原始长度: {len(text):,} 字符")
        print(f"     分词后:   {len(tokens):,} 词")

        # 步骤 2：词频分析
        print("\n  📌 Step 2: 词频分析")
        self.analyzer.analyze(tokens)

        # 步骤 3：统计信息
        self.visualizer.print_statistics(self.analyzer)

        # 步骤 4：Top-N 展示
        print("\n  📌 Step 3: Top 词频")
        top_words = self.analyzer.top_n(top_n)
        self.visualizer.print_table(top_words, f"Top {top_n} 高频词")

        # 步骤 5：分布分析
        print("\n  📌 Step 4: 频次分布")
        dist = self.analyzer.frequency_distribution()
        # 只展示前 10 个分布区间
        dist_show = dict(list(dist.items())[:10])
        self.visualizer.print_distribution(dist_show, "频次分布（前 10 区间）")

        # 步骤 6：导出（可选）
        if export_prefix:
            print("\n  📌 Step 5: 数据导出")
            self.exporter.to_csv(self.analyzer.raw_counter, f"{export_prefix}.csv", top_n=50)
            self.exporter.to_json(self.analyzer.raw_counter, f"{export_prefix}.json")
            self.exporter.to_text_table(self.analyzer.raw_counter, f"{export_prefix}.txt", top_n=20)

        print("\n" + "=" * 60)
        print("  ✅ 分析完成！")
        print("=" * 60)

        return self.analyzer.raw_counter


# ============================================================
# 六、主程序：示例文本 + 交互
# ============================================================

def main():
    # ---- 示例 1：英文文本分析 ----
    english_text = """
    Python is an interpreted high-level general-purpose programming language.
    Its design philosophy emphasizes code readability with its use of significant indentation.
    Its language constructs and object-oriented approach aim to help programmers write clear,
    logical code for small and large-scale projects.

    Python is dynamically-typed and garbage-collected. It supports multiple programming paradigms,
    including structured (particularly procedural), object-oriented and functional programming.
    It is often described as a "batteries included" language due to its comprehensive standard library.

    Python was created in the late 1980s by Guido van Rossum at Centrum Wiskunde & Informatica (CWI)
    in the Netherlands as a successor to the ABC programming language. It was first released in 1991
    as Python 0.9.0. Python 2.0 was released in 2000 and Python 3.0 in 2008. Python 3.0 was a major
    revision that is not completely backward-compatible with previous versions. Python 2 was
    officially discontinued in 2020.

    Since 2018, Python has consistently ranked as one of the most popular programming languages,
    according to the TIOBE index and the Stack Overflow Developer Survey. It is widely used in
    various fields including web development, data science, artificial intelligence, machine learning,
    scientific computing, and automation.
    """

    pipeline_en = WordFrequencyPipeline(language="en")
    pipeline_en.run(english_text, top_n=15, export_prefix="/tmp/freq_en")

    # ---- 示例 2：中文文本分析 ----
    chinese_text = """
    Python 是一种广泛使用的解释型、高级和通用的编程语言。Python 由荷兰数学和计算机科学研究学会
    的吉多·范罗苏姆于 1990 年代初设计，作为一门叫做 ABC 语言的替代品。Python 提供了高效的高级
    数据结构，还能简单有效地面向对象编程。

    Python 语法和动态类型，以及解释型语言的本质，使它成为多数平台上写脚本和快速开发应用的
    编程语言。随着版本的不断更新和语言新功能的添加，逐渐被用于独立的、大型项目的开发。

    Python 解释器易于扩展，可以使用 C 或 C++（或者其他可以通过 C 调用的语言）扩展新的功能
    和数据类型。Python 也可用于可定制化软件中的扩展程序语言。Python 丰富的标准库，提供了
    适用于各个主要系统平台的源码或机器码。

    在数据科学和人工智能领域，Python 已经成为最流行的编程语言之一。NumPy、Pandas、Scikit-learn
    等强大的第三方库为数据分析和机器学习提供了丰富的工具。而 TensorFlow 和 PyTorch 等深度学习
    框架更是推动了 AI 领域的发展。
    """

    pipeline_zh = WordFrequencyPipeline(language="zh")
    pipeline_zh.run(chinese_text, top_n=15, export_prefix="/tmp/freq_zh")

    # ---- 示例 3：Counter 专项技巧 ----
    print("\n" + "=" * 60)
    print("  🔬 专项技巧演示")
    print("=" * 60)

    # 多文档词频对比
    doc1 = Counter("python java python go python rust".split())
    doc2 = Counter("python javascript java go typescript".split())

    print("\n  === 多文档词频对比 ===")
    print(f"  Doc1: {doc1}")
    print(f"  Doc2: {doc2}")
    print(f"  共同词: {doc1 & doc2}")
    print(f"  Doc1 独有: {doc1 - doc2}")
    print(f"  Doc2 独有: {doc2 - doc1}")
    print(f"  词汇并集: {doc1 | doc2}")

    # 词频归一化（词频占比）
    print("\n  === 词频归一化（TF，词频） ===")
    total = sum(doc1.values())
    tf = {word: round(count / total, 4) for word, count in doc1.items()}
    for word, score in sorted(tf.items(), key=lambda x: -x[1]):
        print(f"    TF({word}) = {score:.4f}")


if __name__ == "__main__":
    main()
