#!/usr/bin/env python3
"""
Day 118 - 代码示例 2：TF-IDF 文本表示进阶
功能：TF-IDF 原理手写实现 + sklearn 实现 + 文本相似度计算
依赖：pip install jieba scikit-learn numpy
"""

import math
import re
from collections import Counter

import jieba
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


# ═══════════════════════════════════════════════════════════════
# 第一部分：手写 TF-IDF 实现（理解原理）
# ═══════════════════════════════════════════════════════════════

def tokenize(text):
    """中文分词"""
    stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
                 "都", "一", "上", "也", "很", "到", "说", "要", "去", "你"}
    words = jieba.cut(text)
    return [w.strip() for w in words if w not in stopwords and len(w.strip()) > 1]


def compute_tf(tokens):
    """计算词频 TF"""
    counter = Counter(tokens)
    total = len(tokens)
    return {word: count / total for word, count in counter.items()}


def compute_idf(doc_tokens_list):
    """计算逆文档频率 IDF"""
    num_docs = len(doc_tokens_list)
    # 统计每个词出现在多少篇文档中
    doc_freq = Counter()
    for tokens in doc_tokens_list:
        unique_tokens = set(tokens)
        for token in unique_tokens:
            doc_freq[token] += 1

    # IDF = log(N / (df + 1))，+1 防止分母为 0
    return {word: math.log(num_docs / (df + 1)) + 1  # +1 是平滑
            for word, df in doc_freq.items()}


def compute_tfidf(tf, idf):
    """计算 TF-IDF"""
    return {word: tf_val * idf.get(word, 0) for word, tf_val in tf.items()}


def demo_handwritten_tfidf():
    """手写 TF-IDF 演示"""
    print("=" * 60)
    print("📌 手写 TF-IDF 实现")
    print("=" * 60)

    corpus = [
        "机器学习是人工智能的一个分支",
        "深度学习是机器学习的重要方法",
        "自然语言处理使用深度学习",
        "Python 是广泛使用的编程语言",
    ]

    # 分词
    doc_tokens = [tokenize(doc) for doc in corpus]

    # 计算 IDF（基于整个语料库）
    idf = compute_idf(doc_tokens)

    # 逐篇文档计算 TF-IDF
    print("\n  各文档的 TF-IDF 向量:")
    for i, (doc, tokens) in enumerate(zip(corpus, doc_tokens)):
        tf = compute_tf(tokens)
        tfidf = compute_tfidf(tf, idf)
        print(f"\n  文档 {i+1}: {doc}")
        # 按 TF-IDF 值排序，只显示前 5 个
        sorted_tfidf = sorted(tfidf.items(), key=lambda x: x[1], reverse=True)[:5]
        for word, score in sorted_tfidf:
            print(f"    {word:8s} TF-IDF = {score:.4f}")

    # 查看 IDF 值
    print("\n  IDF 值（所有词）:")
    sorted_idf = sorted(idf.items(), key=lambda x: x[1], reverse=True)
    for word, score in sorted_idf:
        print(f"    {word:8s} IDF = {score:.4f}")


# ═══════════════════════════════════════════════════════════════
# 第二部分：sklearn TF-IDF 实战
# ═══════════════════════════════════════════════════════════════

def demo_sklearn_tfidf():
    """sklearn TfidfVectorizer 使用"""
    print("\n" + "=" * 60)
    print("📌 sklearn TfidfVectorizer")
    print("=" * 60)

    corpus = [
        "机器学习是人工智能的一个分支",
        "深度学习是机器学习的重要方法",
        "自然语言处理使用深度学习",
        "Python 是广泛使用的编程语言",
    ]

    # 分词预处理
    processed = [" ".join(tokenize(doc)) for doc in corpus]

    # 基础用法
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(processed)

    feature_names = vectorizer.get_feature_names_out()
    print(f"\n  特征词数量: {len(feature_names)}")
    print(f"  TF-IDF 矩阵形状: {tfidf_matrix.shape}")

    # 可视化 TF-IDF 矩阵
    dense = tfidf_matrix.toarray()
    print(f"\n  TF-IDF 矩阵:")
    print(f"  {'词':10s}", end="")
    for i in range(len(corpus)):
        print(f"  D{i+1:4d}", end="")
    print()

    for j, word in enumerate(feature_names):
        print(f"  {word:10s}", end="")
        for i in range(len(corpus)):
            print(f"  {dense[i][j]:.3f}", end="")
        print()


def demo_tfidf_params():
    """TF-IDF 参数调优"""
    print("\n" + "=" * 60)
    print("📌 TF-IDF 参数调优")
    print("=" * 60)

    corpus = [
        "机器学习是人工智能的一个分支",
        "深度学习是机器学习的重要方法",
        "自然语言处理使用深度学习",
        "Python 是广泛使用的编程语言",
        "机器学习和深度学习在工业界广泛应用",
    ]

    processed = [" ".join(tokenize(doc)) for doc in corpus]

    # 参数 1: max_features
    print("\n  参数 max_features:")
    for n in [3, 5, None]:
        vec = TfidfVectorizer(max_features=n)
        matrix = vec.fit_transform(processed)
        names = vec.get_feature_names_out()
        print(f"    max_features={n}: {list(names)}")

    # 参数 2: ngram_range
    print("\n  参数 ngram_range:")
    for ngram in [(1, 1), (1, 2)]:
        vec = TfidfVectorizer(ngram_range=ngram)
        matrix = vec.fit_transform(processed)
        names = vec.get_feature_names_out()
        print(f"    ngram_range={ngram}: {len(names)} 个特征")
        if ngram == (1, 2):
            # 只展示部分
            print(f"    示例: {list(names[:10])}...")

    # 参数 3: sublinear_tf（对数 TF）
    print("\n  参数 sublinear_tf:")
    vec_normal = TfidfVectorizer(sublinear_tf=False)
    vec_log = TfidfVectorizer(sublinear_tf=True)
    m1 = vec_normal.fit_transform(processed)
    m2 = vec_log.fit_transform(processed)
    print(f"    sublinear_tf=False: 非零元素均值={m1.data.mean():.4f}")
    print(f"    sublinear_tf=True:  非零元素均值={m2.data.mean():.4f}")


def demo_text_similarity():
    """基于 TF-IDF 的文本相似度计算"""
    print("\n" + "=" * 60)
    print("📌 基于 TF-IDF 的文本相似度")
    print("=" * 60)

    corpus = [
        "机器学习是人工智能的一个分支",
        "深度学习是机器学习的重要方法",
        "自然语言处理使用深度学习",
        "Python 是广泛使用的编程语言",
    ]

    processed = [" ".join(tokenize(doc)) for doc in corpus]

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(processed)

    # 计算余弦相似度矩阵
    from sklearn.metrics.pairwise import cosine_similarity
    similarity_matrix = cosine_similarity(tfidf_matrix)

    print("\n  余弦相似度矩阵:")
    print(f"  {'':15s}", end="")
    for i in range(len(corpus)):
        print(f"  D{i+1:4d}", end="")
    print()

    for i in range(len(corpus)):
        print(f"  文档{i+1:2d}", end="")
        for j in range(len(corpus)):
            print(f"  {similarity_matrix[i][j]:.3f}", end="")
        print()

    # 找最相似的文档对
    print("\n  最相似的文档对:")
    max_sim = 0
    best_pair = (0, 0)
    for i in range(len(corpus)):
        for j in range(i + 1, len(corpus)):
            sim = similarity_matrix[i][j]
            if sim > max_sim:
                max_sim = sim
                best_pair = (i, j)

    print(f"    文档{best_pair[0]+1}: {corpus[best_pair[0]]}")
    print(f"    文档{best_pair[1]+1}: {corpus[best_pair[1]]}")
    print(f"    相似度: {max_sim:.4f}")

    # 新文本相似度查询
    print("\n  🔍 新文本相似度查询:")
    query = "深度学习在自然语言处理中的应用"
    query_processed = " ".join(tokenize(query))
    query_vec = vectorizer.transform([query_processed])
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()

    print(f"    查询: {query}")
    for i, sim in enumerate(similarities):
        bar = "█" * int(sim * 30)
        print(f"    与文档{i+1}: {sim:.4f} {bar}")


if __name__ == "__main__":
    demo_handwritten_tfidf()
    demo_sklearn_tfidf()
    demo_tfidf_params()
    demo_text_similarity()
