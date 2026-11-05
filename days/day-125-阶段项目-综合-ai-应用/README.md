# Day 125 — 阶段项目：综合 AI 应用

> 🎯 **今日目标**：完成一个端到端的 AI/ML 项目，涵盖数据获取、预处理、模型训练、评估和部署的完整流程。

---

## 📋 概念总览

本日是一个**综合实战项目**，将前面学习的机器学习、深度学习、模型部署等知识串联起来，构建一个完整的 AI 应用。

### 项目主题：智能文本情感分析系统

**技术栈**：
- 数据处理：`pandas`, `numpy`
- 特征工程：`scikit-learn`（TF-IDF）
- 模型训练：`scikit-learn`（逻辑回归/SVM）+ `PyTorch`（深度学习版）
- 模型评估：`sklearn.metrics`
- 模型部署：`FastAPI` + `joblib`
- 可视化：`matplotlib`

---

## 🏗️ 项目架构

```
┌─────────────────────────────────────────────────────┐
│                   综合 AI 应用架构                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │ 数据获取  │───▶│ 数据清洗  │───▶│ 特征工程  │      │
│  │ & 加载   │    │ & 预处理  │    │ TF-IDF   │      │
│  └──────────┘    └──────────┘    └──────────┘      │
│                                      │              │
│                                      ▼              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │ Web API  │◀───│ 模型保存  │◀───│ 模型训练  │      │
│  │ FastAPI  │    │ joblib   │    │ 评估调优  │      │
│  └──────────┘    └──────────┘    └──────────┘      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🔄 端到端流程详解

### 1. 数据获取与加载

```python
import pandas as pd
import numpy as np
from pathlib import Path

# 方式一：使用内置数据集模拟
def create_sample_data(n_samples=2000):
    """生成模拟情感分析数据集"""
    positive_texts = [
        "这部电影太棒了，演员演技出色",
        "服务非常好，物超所值",
        "产品质量很好，物流也快",
        "朋友推荐的，果然没有让我失望",
        "价格合理，性价比很高",
        "包装精美，产品完好无损",
        "客服态度好，回复及时",
        "非常满意，下次还会回购",
        "做工精细，手感很好",
        "安装简单，使用方便",
    ]
    negative_texts = [
        "质量太差了，用了一天就坏了",
        "客服态度差，完全不解决问题",
        "物流太慢了，等了两周才到",
        "和描述不符，非常失望",
        "价格虚高，不值这个价",
        "包装破损，产品有划痕",
        "退货流程复杂，折腾了好久",
        "噪音很大，影响使用体验",
        "做工粗糙，细节处理不到位",
        "说明书不清楚，安装困难",
    ]

    texts, labels = [], []
    for _ in range(n_samples // 2):
        texts.append(np.random.choice(positive_texts))
        labels.append(1)
        texts.append(np.random.choice(negative_texts))
        labels.append(0)

    df = pd.DataFrame({"text": texts, "label": labels})
    return df.sample(frac=1, random_state=42).reset_index(drop=True)

# 方式二：从 CSV 加载真实数据
def load_csv_data(filepath):
    """从 CSV 文件加载数据"""
    df = pd.read_csv(filepath)
    return df

# 使用
df = create_sample_data(2000)
print(f"数据集大小: {len(df)}")
print(f"类别分布:\n{df['label'].value_counts()}")
```

### 2. 数据预处理

```python
import re

def clean_text(text):
    """文本清洗：去除噪声、统一格式"""
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去除URL
    text = re.sub(r'http\S+|www.\S+', '', text)
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def preprocess_dataframe(df):
    """DataFrame 预处理"""
    # 去除重复文本
    df = df.drop_duplicates(subset='text')
    # 文本清洗
    df['text'] = df['text'].apply(clean_text)
    # 去除过短文本
    df = df[df['text'].str.len() > 2]
    return df.reset_index(drop=True)

df = preprocess_dataframe(df)
print(f"清洗后数据集: {len(df)} 条")
```

### 3. 特征工程 — TF-IDF

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split

# 分割数据集
X_train, X_test, y_train, y_test = train_test_split(
    df['text'], df['label'],
    test_size=0.2,
    random_state=42,
    stratify=df['label']  # 保持类别比例
)

# TF-IDF 向量化
vectorizer = TfidfVectorizer(
    max_features=5000,      # 最大特征数
    ngram_range=(1, 2),     # 使用 unigram + bigram
    min_df=2,               # 最小文档频率
    max_df=0.95,            # 最大文档频率
    sublinear_tf=True       # 使用 1 + log(tf)
)

X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)

print(f"训练集特征矩阵: {X_train_tfidf.shape}")
print(f"测试集特征矩阵: {X_test_tfidf.shape}")
```

### 4. 模型训练与评估

```python
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report, confusion_matrix
)
import time

def train_and_evaluate(model, X_train, X_test, y_train, y_test, model_name):
    """统一的训练与评估流程"""
    print(f"\n{'='*50}")
    print(f"训练模型: {model_name}")
    print(f"{'='*50}")

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
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    print(f"准确率:  {accuracy:.4f}")
    print(f"精确率:  {precision:.4f}")
    print(f"召回率:  {recall:.4f}")
    print(f"F1 分数: {f1:.4f}")
    print(f"训练时间: {train_time:.3f}s")
    print(f"预测时间: {predict_time:.3f}s")
    print(f"\n分类报告:\n{classification_report(y_test, y_pred)}")

    return {
        "model": model,
        "accuracy": accuracy,
        "f1": f1,
        "train_time": train_time,
    }

# 模型 1: 逻辑回归
lr_model = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
lr_results = train_and_evaluate(
    lr_model, X_train_tfidf, X_test_tfidf,
    y_train, y_test, "逻辑回归"
)

# 模型 2: 支持向量机
svm_model = LinearSVC(C=1.0, max_iter=1000, random_state=42)
svm_results = train_and_evaluate(
    svm_model, X_train_tfidf, X_test_tfidf,
    y_train, y_test, "支持向量机 (SVM)"
)
```

### 5. 深度学习版（PyTorch）

```python
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

class TextDataset(Dataset):
    """文本数据集"""
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features.toarray())
        self.labels = torch.LongTensor(labels.values)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]

class SentimentClassifier(nn.Module):
    """情感分类神经网络"""
    def __init__(self, input_dim, hidden_dim=128, output_dim=2):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, output_dim)
        )

    def forward(self, x):
        return self.network(x)

def train_dl_model(model, train_loader, criterion, optimizer, epochs=20):
    """训练深度学习模型"""
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for batch_features, batch_labels in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_features)
            loss = criterion(outputs, batch_labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        if (epoch + 1) % 5 == 0:
            avg_loss = total_loss / len(train_loader)
            print(f"Epoch [{epoch+1}/{epochs}], Loss: {avg_loss:.4f}")

    return model

# 准备数据
train_dataset = TextDataset(X_train_tfidf, y_train)
test_dataset = TextDataset(X_test_tfidf, y_test)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=32)

# 训练
input_dim = X_train_tfidf.shape[1]
dl_model = SentimentClassifier(input_dim)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(dl_model.parameters(), lr=0.001)

dl_model = train_dl_model(dl_model, train_loader, criterion, optimizer, epochs=20)
```

### 6. 模型保存与加载

```python
import joblib
from pathlib import Path

def save_model_artifacts(model, vectorizer, metrics, save_dir="model_artifacts"):
    """保存模型产物"""
    save_path = Path(save_dir)
    save_path.mkdir(exist_ok=True)

    # 保存 sklearn 模型
    joblib.dump(model, save_path / "model.joblib")
    joblib.dump(vectorizer, save_path / "vectorizer.joblib")

    # 保存评估指标
    import json
    with open(save_path / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"✅ 模型已保存到 {save_dir}/")
    return save_path

def load_model_artifacts(save_dir="model_artifacts"):
    """加载模型产物"""
    save_path = Path(save_dir)
    model = joblib.load(save_path / "model.joblib")
    vectorizer = joblib.load(save_path / "vectorizer.joblib")

    import json
    with open(save_path / "metrics.json") as f:
        metrics = json.load(f)

    return model, vectorizer, metrics

# 保存最佳模型（比较逻辑回归和SVM）
best_model = lr_results if lr_results["f1"] >= svm_results["f1"] else svm_results
save_model_artifacts(
    best_model["model"],
    vectorizer,
    {"accuracy": best_model["accuracy"], "f1": best_model["f1"]}
)
```

### 7. FastAPI 部署

```python
# save as: app.py
from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import numpy as np

app = FastAPI(title="情感分析 API", version="1.0")

# 加载模型
model = joblib.load("model_artifacts/model.joblib")
vectorizer = joblib.load("model_artifacts/vectorizer.joblib")

class TextInput(BaseModel):
    text: str

class PredictionOutput(BaseModel):
    text: str
    sentiment: str
    confidence: float

@app.post("/predict", response_model=PredictionOutput)
def predict_sentiment(input_data: TextInput):
    """预测文本情感"""
    # 向量化
    features = vectorizer.transform([input_data.text])

    # 预测
    prediction = model.predict(features)[0]

    # 获取概率（如果有 predict_proba）
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(features)[0]
        confidence = float(max(proba))
    else:
        confidence = 0.95  # SVM 默认置信度

    sentiment = "正面" if prediction == 1 else "负面"

    return PredictionOutput(
        text=input_data.text,
        sentiment=sentiment,
        confidence=round(confidence, 4)
    )

@app.get("/")
def root():
    return {"message": "情感分析 API v1.0", "status": "running"}

# 启动命令: uvicorn app:app --reload --port 8000
```

---

## 📊 模型对比分析

| 指标 | 逻辑回归 | SVM | 神经网络 |
|------|---------|-----|---------|
| 训练速度 | ⚡ 快 | ⚡ 快 | 🐢 慢 |
| 推理速度 | ⚡ 快 | ⚡ 快 | ⚡ 快 |
| 内存占用 | 低 | 低 | 中 |
| 可解释性 | ⭐⭐⭐ 高 | ⭐⭐ 低 | ⭐ 很低 |
| 小数据表现 | 好 | 很好 | 差 |
| 调参难度 | 简单 | 中等 | 复杂 |

**选择建议**：
- 数据量小（<10K）→ 逻辑回归/SVM
- 数据量大（>100K）→ 深度学习
- 需要可解释性 → 逻辑回归
- 追求极致性能 → 深度学习 + 微调

---

## 💡 项目最佳实践

### 1. 代码组织
```
project/
├── data/
│   ├── raw/              # 原始数据（不修改）
│   └── processed/        # 处理后的数据
├── models/
│   ├── trained/          # 训练好的模型
│   └── logs/             # 训练日志
├── src/
│   ├── data.py           # 数据处理
│   ├── features.py       # 特征工程
│   ├── train.py          # 模型训练
│   ├── evaluate.py       # 模型评估
│   └── predict.py        # 推理接口
├── tests/                # 测试
├── app.py                # API 服务
├── config.yaml           # 配置文件
└── requirements.txt      # 依赖
```

### 2. 配置管理
```python
from dataclasses import dataclass, field

@dataclass
class Config:
    # 数据
    raw_data_path: str = "data/raw/"
    processed_data_path: str = "data/processed/"

    # 特征
    max_features: int = 5000
    ngram_range: tuple = (1, 2)

    # 模型
    model_type: str = "logistic_regression"  # or "svm", "nn"
    learning_rate: float = 0.001
    epochs: int = 20
    batch_size: int = 32

    # 部署
    api_host: str = "0.0.0.0"
    api_port: int = 8000
```

### 3. 实验记录
```python
import json
from datetime import datetime

def log_experiment(experiment_name, params, metrics):
    """记录实验结果"""
    log = {
        "name": experiment_name,
        "timestamp": datetime.now().isoformat(),
        "params": params,
        "metrics": metrics,
    }

    log_file = "experiments.json"
    try:
        with open(log_file) as f:
            experiments = json.load(f)
    except FileNotFoundError:
        experiments = []

    experiments.append(log)
    with open(log_file, "w") as f:
        json.dump(experiments, f, indent=2, ensure_ascii=False)

    print(f"📝 实验 '{experiment_name}' 已记录")
```

---

## 🤔 思考题

1. **数据质量**：如果训练数据中混入了 10% 的错误标签，模型性能会如何变化？有哪些方法可以检测和处理标签噪声？

2. **特征选择**：TF-IDF 的 `max_features` 参数如何影响模型？当词汇表从 5000 增加到 50000 时，模型性能和训练时间会如何变化？

3. **过拟合**：如果模型在训练集上准确率达到 99% 但测试集只有 70%，说明什么问题？有哪些正则化方法可以缓解？

4. **部署优化**：生产环境中，如何处理高并发请求？如何实现模型的 A/B 测试和灰度发布？

5. **持续学习**：当线上数据分布发生变化（概念漂移）时，如何自动检测并更新模型？

---

## 📚 参考资源

- [scikit-learn 文档](https://scikit-learn.org/stable/)
- [PyTorch 官方教程](https://pytorch.org/tutorials/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [MLOps Best Practices](https://neptune.ai/blog/mlops-best-practices)
