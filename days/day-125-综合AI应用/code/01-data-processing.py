"""
Day 125 - 综合AI应用：数据处理与特征工程
01-data-processing.py

演示完整的数据处理流程：数据生成、清洗、预处理、特征工程
"""

import pandas as pd
import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from pathlib import Path


# ============================================================
# 1. 数据生成（模拟情感分析数据集）
# ============================================================

def create_sample_data(n_samples=2000, random_state=42):
    """
    生成模拟的情感分析数据集

    Args:
        n_samples: 总样本数
        random_state: 随机种子

    Returns:
        DataFrame: 包含 text 和 label 列的数据集
    """
    np.random.seed(random_state)

    # 正面评价模板
    positive_templates = [
        "这款{}真的太棒了，{}非常满意",
        "{}质量很好，{}推荐购买",
        "朋友推荐的{}，果然{}没有让我失望",
        "性价比很高，{}物超所值",
        "{}做工精细，{}手感很好",
        "客服{}态度好，{}回复及时",
        "物流{}很快，包装{}完好",
        "{}安装简单，{}使用方便",
        "第二次购买了，{}依然很好",
        "{}超出预期，{}非常惊喜",
    ]

    # 负面评价模板
    negative_templates = [
        "这款{}太差了，{}非常失望",
        "{}质量不行，{}用了一天就坏",
        "客服{}态度差，{}完全不解决问题",
        "物流{}太慢了，{}等了两周才到",
        "和描述{}不符，{}完全是虚假宣传",
        "{}价格虚高，{}不值这个价",
        "包装{}破损，{}产品有划痕",
        "{}退货流程复杂，{}折腾了好久",
        "{}噪音很大，{}影响使用体验",
        "做工{}粗糙，{}细节处理不到位",
    ]

    # 填充词
    products = ["手机壳", "耳机", "充电器", "键盘", "鼠标", "手表", "音箱", "支架"]
    qualities = ["质量", "做工", "外观", "手感", "功能", "性能", "续航", "音质"]
    adverbs_pos = ["非常", "特别", "真的", "确实", "实在", "简直", "相当", "格外"]
    adverbs_neg = ["非常", "特别", "真的", "确实", "实在", "简直", "相当", "格外"]
    actions_pos = ["质量好", "做工好", "好用", "耐用", "值", "棒", "满意", "喜欢"]
    actions_neg = ["质量差", "不好用", "容易坏", "差劲", "坑", "垃圾", "失望", "后悔"]

    texts, labels = [], []

    for _ in range(n_samples // 2):
        # 生成正面样本
        template = np.random.choice(positive_templates)
        text = template.format(
            np.random.choice(products),
            np.random.choice(actions_pos)
        )
        texts.append(text)
        labels.append(1)

        # 生成负面样本
        template = np.random.choice(negative_templates)
        text = template.format(
            np.random.choice(products),
            np.random.choice(actions_neg)
        )
        texts.append(text)
        labels.append(0)

    df = pd.DataFrame({"text": texts, "label": labels})
    return df.sample(frac=1, random_state=random_state).reset_index(drop=True)


# ============================================================
# 2. 数据清洗
# ============================================================

def clean_text(text):
    """
    文本清洗：去除噪声、统一格式

    清洗步骤：
    1. 去除 HTML 标签
    2. 去除 URL
    3. 去除特殊字符
    4. 去除多余空白
    """
    if not isinstance(text, str):
        return ""

    # 去除 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去除 URL
    text = re.sub(r'http\S+|www\.\S+', '', text)
    # 去除特殊字符（保留中文和英文数字）
    text = re.sub(r'[^\w\u4e00-\u9fff\s]', '', text)
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def preprocess_dataframe(df):
    """
    DataFrame 预处理

    处理步骤：
    1. 去除重复文本
    2. 文本清洗
    3. 去除过短文本
    4. 重置索引
    """
    original_size = len(df)
    print(f"原始数据量: {original_size}")

    # 去除重复文本
    df = df.drop_duplicates(subset='text')
    print(f"去重后: {len(df)} (去除 {original_size - len(df)} 条重复)")

    # 文本清洗
    df = df.copy()
    df['text'] = df['text'].apply(clean_text)

    # 去除过短文本（少于3个字符）
    before = len(df)
    df = df[df['text'].str.len() >= 3]
    print(f"去短文本后: {len(df)} (去除 {before - len(df)} 条过短)")

    return df.reset_index(drop=True)


# ============================================================
# 3. 特征工程 — TF-IDF
# ============================================================

def build_tfidf_features(X_train, X_test, max_features=5000, ngram_range=(1, 2)):
    """
    构建 TF-IDF 特征

    Args:
        X_train: 训练集文本
        X_test: 测试集文本
        max_features: 最大特征数
        ngram_range: n-gram 范围

    Returns:
        X_train_tfidf: 训练集 TF-IDF 特征矩阵
        X_test_tfidf: 测试集 TF-IDF 特征矩阵
        vectorizer: 训练好的向量化器
    """
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        min_df=2,            # 最小文档频率
        max_df=0.95,         # 最大文档频率
        sublinear_tf=True,   # 使用 1 + log(tf)
        strip_accents='unicode',
        token_pattern=r'(?u)\b\w+\b',  # 匹配所有单词
    )

    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    print(f"TF-IDF 特征矩阵:")
    print(f"  训练集: {X_train_tfidf.shape}")
    print(f"  测试集: {X_test_tfidf.shape}")
    print(f"  词汇表大小: {len(vectorizer.vocabulary_)}")

    return X_train_tfidf, X_test_tfidf, vectorizer


# ============================================================
# 4. 主流程
# ============================================================

def main():
    print("=" * 60)
    print("📊 Day 125 - 数据处理与特征工程")
    print("=" * 60)

    # 步骤 1: 生成数据
    print("\n🔧 步骤 1: 生成模拟数据集")
    df = create_sample_data(n_samples=2000)
    print(f"  总样本数: {len(df)}")
    print(f"  类别分布:\n{df['label'].value_counts().to_string()}")

    # 步骤 2: 数据清洗
    print("\n🔧 步骤 2: 数据清洗")
    df = preprocess_dataframe(df)
    print(f"  清洗后样本数: {len(df)}")

    # 步骤 3: 数据分割
    print("\n🔧 步骤 3: 数据分割 (80/20)")
    X_train, X_test, y_train, y_test = train_test_split(
        df['text'], df['label'],
        test_size=0.2,
        random_state=42,
        stratify=df['label']
    )
    print(f"  训练集: {len(X_train)} 条")
    print(f"  测试集: {len(X_test)} 条")

    # 步骤 4: 特征工程
    print("\n🔧 步骤 4: TF-IDF 特征工程")
    X_train_tfidf, X_test_tfidf, vectorizer = build_tfidf_features(
        X_train, X_test,
        max_features=3000,
        ngram_range=(1, 2)
    )

    # 展示特征示例
    print("\n📝 特征示例:")
    feature_names = vectorizer.get_feature_names_out()
    # 获取第一个样本的非零特征
    sample_idx = 0
    sample_vector = X_train_tfidf[sample_idx].toarray().flatten()
    non_zero_indices = sample_vector.nonzero()[0]
    for idx in non_zero_indices[:10]:
        print(f"  {feature_names[idx]}: {sample_vector[idx]:.4f}")

    # 保存处理后的数据
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存为稀疏矩阵
    import scipy.sparse as sp
    sp.save_npz(output_dir / "X_train_tfidf.npz", X_train_tfidf)
    sp.save_npz(output_dir / "X_test_tfidf.npz", X_test_tfidf)
    y_train.to_csv(output_dir / "y_train.csv", index=False)
    y_test.to_csv(output_dir / "y_test.csv", index=False)

    print(f"\n✅ 数据已保存到 {output_dir}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
