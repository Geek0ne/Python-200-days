"""
Day 125 - 综合AI应用：模型训练与评估
02-model-training.py

演示多种模型的训练、评估、对比和模型保存
"""

import pandas as pd
import numpy as np
import joblib
import json
import time
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report, confusion_matrix
)
from sklearn.model_selection import cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
import re


# ============================================================
# 数据准备（复用 01 的逻辑）
# ============================================================

def create_sample_data(n_samples=2000, random_state=42):
    """生成模拟数据集"""
    np.random.seed(random_state)

    positive_templates = [
        "这款{}真的太棒了，{}非常满意",
        "{}质量很好，{}推荐购买",
        "朋友推荐的{}，果然{}没有让我失望",
        "性价比很高，{}物超所值",
        "{}做工精细，{}手感很好",
    ]
    negative_templates = [
        "这款{}太差了，{}非常失望",
        "{}质量不行，{}用了一天就坏",
        "客服{}态度差，{}完全不解决问题",
        "物流{}太慢了，{}等了两周才到",
        "和描述{}不符，{}完全是虚假宣传",
    ]
    products = ["手机壳", "耳机", "充电器", "键盘", "鼠标"]
    actions_pos = ["质量好", "好用", "耐用", "值", "棒"]
    actions_neg = ["质量差", "不好用", "容易坏", "差劲", "坑"]

    texts, labels = [], []
    for _ in range(n_samples // 2):
        texts.append(np.random.choice(positive_templates).format(
            np.random.choice(products), np.random.choice(actions_pos)))
        labels.append(1)
        texts.append(np.random.choice(negative_templates).format(
            np.random.choice(products), np.random.choice(actions_neg)))
        labels.append(0)

    return pd.DataFrame({"text": texts, "label": labels}).sample(
        frac=1, random_state=random_state).reset_index(drop=True)


def clean_text(text):
    """文本清洗"""
    if not isinstance(text, str):
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'http\S+|www\.\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ============================================================
# 模型训练与评估
# ============================================================

def get_models():
    """获取候选模型字典"""
    return {
        "逻辑回归": LogisticRegression(max_iter=1000, C=1.0, random_state=42),
        "SVM": LinearSVC(C=1.0, max_iter=1000, random_state=42),
        "朴素贝叶斯": MultinomialNB(alpha=1.0),
        "随机森林": RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
    }


def train_and_evaluate(model, X_train, X_test, y_train, y_test, model_name):
    """
    统一的训练与评估流程

    返回:
        dict: 包含模型、指标、时间的字典
    """
    print(f"\n{'─'*50}")
    print(f"🔧 训练模型: {model_name}")
    print(f"{'─'*50}")

    # 训练
    start_time = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start_time

    # 预测
    start_time = time.time()
    y_pred = model.predict(X_test)
    predict_time = time.time() - start_time

    # 评估指标
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')

    print(f"  准确率:   {accuracy:.4f}")
    print(f"  精确率:   {precision:.4f}")
    print(f"  召回率:   {recall:.4f}")
    print(f"  F1 分数:  {f1:.4f}")
    print(f"  训练时间: {train_time:.3f}s")
    print(f"  预测时间: {predict_time:.4f}s")

    return {
        "model": model,
        "name": model_name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "train_time": train_time,
        "predict_time": predict_time,
    }


def cross_validate_model(model, X, y, model_name, cv=5):
    """交叉验证"""
    scores = cross_val_score(model, X, y, cv=cv, scoring='f1_weighted')
    print(f"  {model_name} {cv}折交叉验证 F1: {scores.mean():.4f} ± {scores.std():.4f}")
    return {"mean": scores.mean(), "std": scores.std()}


def compare_models(results_list):
    """模型对比"""
    print(f"\n{'='*60}")
    print("📊 模型对比总结")
    print(f"{'='*60}")

    # 按 F1 分数排序
    results_list.sort(key=lambda x: x['f1'], reverse=True)

    print(f"\n{'模型':<12} {'准确率':>8} {'F1':>8} {'训练时间':>10}")
    print("-" * 45)
    for r in results_list:
        print(f"{r['name']:<12} {r['accuracy']:>8.4f} {r['f1']:>8.4f} {r['train_time']:>8.3f}s")

    best = results_list[0]
    print(f"\n🏆 最佳模型: {best['name']} (F1={best['f1']:.4f})")
    return best


# ============================================================
# 模型保存与加载
# ============================================================

def save_model(model, vectorizer, metrics, save_dir="model_artifacts"):
    """保存模型产物"""
    save_path = Path(save_dir)
    save_path.mkdir(exist_ok=True)

    # 保存 sklearn 模型
    joblib.dump(model, save_path / "model.joblib")
    joblib.dump(vectorizer, save_path / "vectorizer.joblib")

    # 保存指标
    with open(save_path / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 模型已保存到 {save_dir}/")
    print(f"  - model.joblib: 训练好的模型")
    print(f"  - vectorizer.joblib: TF-IDF 向量化器")
    print(f"  - metrics.json: 评估指标")

    return save_path


def load_model(save_dir="model_artifacts"):
    """加载模型产物"""
    save_path = Path(save_dir)
    model = joblib.load(save_path / "model.joblib")
    vectorizer = joblib.load(save_path / "vectorizer.joblib")

    with open(save_path / "metrics.json") as f:
        metrics = json.load(f)

    print(f"✅ 模型已加载 (指标: accuracy={metrics['accuracy']:.4f})")
    return model, vectorizer, metrics


def predict_text(text, model, vectorizer):
    """单条文本预测"""
    features = vectorizer.transform([text])
    prediction = model.predict(features)[0]

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(features)[0]
        confidence = max(proba)
    else:
        confidence = 0.95

    sentiment = "✅ 正面" if prediction == 1 else "❌ 负面"
    return {
        "text": text,
        "sentiment": sentiment,
        "confidence": round(confidence, 4)
    }


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("📊 Day 125 - 模型训练与评估")
    print("=" * 60)

    # 步骤 1: 准备数据
    print("\n🔧 步骤 1: 数据准备")
    df = create_sample_data(2000)
    df['text'] = df['text'].apply(clean_text)
    df = df[df['text'].str.len() >= 3].reset_index(drop=True)

    X_train, X_test, y_train, y_test = train_test_split(
        df['text'], df['label'], test_size=0.2, random_state=42, stratify=df['label']
    )

    # TF-IDF
    vectorizer = TfidfVectorizer(
        max_features=3000, ngram_range=(1, 2), min_df=2, max_df=0.95, sublinear_tf=True
    )
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    print(f"  训练集: {X_train_tfidf.shape}, 测试集: {X_test_tfidf.shape}")

    # 步骤 2: 训练多个模型
    print("\n🔧 步骤 2: 训练多个模型")
    models = get_models()
    results = []

    for name, model in models.items():
        result = train_and_evaluate(model, X_train_tfidf, X_test_tfidf, y_train, y_test, name)
        results.append(result)

    # 步骤 3: 模型对比
    best_result = compare_models(results)

    # 步骤 4: 交叉验证最佳模型
    print("\n🔧 步骤 4: 交叉验证")
    cross_validate_model(best_result['model'], X_train_tfidf, y_train, best_result['name'])

    # 步骤 5: 保存最佳模型
    print("\n🔧 步骤 5: 保存模型")
    save_model(
        best_result['model'],
        vectorizer,
        {
            "accuracy": best_result['accuracy'],
            "precision": best_result['precision'],
            "recall": best_result['recall'],
            "f1": best_result['f1'],
        }
    )

    # 步骤 6: 测试预测
    print("\n🔧 步骤 6: 预测测试")
    test_texts = [
        "这款手机壳质量很好，非常满意",
        "物流太慢了，等了两周才到",
        "做工精细，手感很好，推荐购买",
        "质量不行，用了一天就坏了",
    ]

    for text in test_texts:
        result = predict_text(text, best_result['model'], vectorizer)
        print(f"  「{result['text'][:20]}...」 → {result['sentiment']} (置信度: {result['confidence']})")

    # 步骤 7: 特征重要性（仅逻辑回归）
    if hasattr(best_result['model'], 'coef_'):
        print("\n🔧 步骤 7: Top 10 重要特征")
        feature_names = vectorizer.get_feature_names_out()
        coefs = best_result['model'].coef_[0]
        top_positive = np.argsort(coefs)[-10:][::-1]
        top_negative = np.argsort(coefs)[:10]

        print("  正面特征:", [feature_names[i] for i in top_positive])
        print("  负面特征:", [feature_names[i] for i in top_negative])

    print("\n" + "=" * 60)
    print("✅ 模型训练完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
