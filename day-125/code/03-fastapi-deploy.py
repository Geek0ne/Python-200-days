"""
Day 125 - 综合AI应用：FastAPI 部署与预测接口
03-fastapi-deploy.py

演示如何将训练好的模型部署为 REST API 服务

运行方法:
    pip install fastapi uvicorn joblib scikit-learn
    python 03-fastapi-deploy.py

测试:
    curl -X POST http://localhost:8000/predict \
        -H "Content-Type: application/json" \
        -d '{"text": "这款产品非常好用"}'

    或浏览器访问: http://localhost:8000/docs (Swagger UI)
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import joblib
import json
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

# ============================================================
# 配置
# ============================================================

MODEL_DIR = Path("model_artifacts")
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


# ============================================================
# Pydantic 数据模型
# ============================================================

class TextInput(BaseModel):
    """单条文本输入"""
    text: str = Field(..., min_length=1, max_length=1000, description="待分析的文本")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "这款产品非常好用，推荐购买"
            }
        }


class BatchInput(BaseModel):
    """批量文本输入"""
    texts: List[str] = Field(..., min_items=1, max_items=100, description="待分析的文本列表")


class PredictionOutput(BaseModel):
    """单条预测结果"""
    text: str
    sentiment: str
    confidence: float
    model_version: str = "v1.0"


class BatchOutput(BaseModel):
    """批量预测结果"""
    predictions: List[PredictionOutput]
    total: int
    processing_time_ms: float


class HealthOutput(BaseModel):
    """健康检查输出"""
    status: str
    model_loaded: bool
    model_version: str
    uptime: str


class StatsOutput(BaseModel):
    """统计信息输出"""
    total_predictions: int
    positive_count: int
    negative_count: int
    avg_confidence: float
    avg_processing_time_ms: float


# ============================================================
# 应用初始化
# ============================================================

app = FastAPI(
    title="情感分析 API",
    description="基于机器学习的中文文本情感分析服务",
    version="1.0.0",
)

# 全局状态
start_time = datetime.now()
stats = {
    "total": 0,
    "positive": 0,
    "negative": 0,
    "confidence_sum": 0.0,
    "time_sum": 0.0,
}

# 模型和向量化器（延迟加载）
model = None
vectorizer = None
model_version = "v1.0"


def load_model():
    """加载模型和向量化器"""
    global model, vectorizer

    try:
        model_path = MODEL_DIR / "model.joblib"
        vectorizer_path = MODEL_DIR / "vectorizer.joblib"

        if not model_path.exists() or not vectorizer_path.exists():
            logger.warning(f"模型文件不存在，先训练模型...")
            train_demo_model()

        model = joblib.load(model_path)
        vectorizer = joblib.load(vectorizer_path)
        logger.info(f"✅ 模型加载成功 (版本: {model_version})")
        return True

    except Exception as e:
        logger.error(f"❌ 模型加载失败: {e}")
        return False


def train_demo_model():
    """快速训练一个演示模型"""
    from sklearn.linear_model import LogisticRegression
    from sklearn.feature_extraction.text import TfidfVectorizer

    # 简单训练数据
    texts = [
        "质量很好推荐", "非常满意", "好用", "物超所值", "推荐购买",
        "质量差", "太差了", "非常失望", "不好用", "垃圾",
    ] * 20
    labels = [1] * 100 + [0] * 100

    vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
    X = vectorizer.fit_transform(texts)

    model = LogisticRegression(max_iter=1000)
    model.fit(X, labels)

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_DIR / "model.joblib")
    joblib.dump(vectorizer, MODEL_DIR / "vectorizer.joblib")
    logger.info("✅ 演示模型训练完成")


# ============================================================
# 路由
# ============================================================

@app.on_event("startup")
async def startup_event():
    """应用启动时加载模型"""
    load_model()


@app.get("/", response_class=HTMLResponse)
def root():
    """首页 - 返回简单的 HTML 页面"""
    return """
    <html>
        <head>
            <title>情感分析 API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; }
                h1 { color: #333; }
                code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
                .endpoint { background: #e8f5e9; padding: 10px; margin: 10px 0; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>🎯 情感分析 API</h1>
            <p>基于机器学习的中文文本情感分析服务</p>

            <h2>API 端点</h2>
            <div class="endpoint">
                <strong>POST /predict</strong> - 单条文本预测
            </div>
            <div class="endpoint">
                <strong>POST /predict/batch</strong> - 批量文本预测
            </div>
            <div class="endpoint">
                <strong>GET /health</strong> - 健康检查
            </div>
            <div class="endpoint">
                <strong>GET /stats</strong> - 统计信息
            </div>

            <h2>测试</h2>
            <p>访问 <a href="/docs">/docs</a> 查看 Swagger 文档</p>
            <pre>
curl -X POST http://localhost:8000/predict \\
    -H "Content-Type: application/json" \\
    -d '{"text": "这款产品非常好用"}'
            </pre>
        </body>
    </html>
    """


@app.get("/health", response_model=HealthOutput)
def health_check():
    """健康检查"""
    uptime = str(datetime.now() - start_time).split('.')[0]
    return HealthOutput(
        status="healthy" if model is not None else "degraded",
        model_loaded=model is not None,
        model_version=model_version,
        uptime=uptime,
    )


@app.post("/predict", response_model=PredictionOutput)
def predict_sentiment(input_data: TextInput):
    """
    单条文本情感预测

    Args:
        input_data: 包含待分析文本的对象

    Returns:
        PredictionOutput: 预测结果
    """
    if model is None or vectorizer is None:
        raise HTTPException(status_code=503, detail="模型未加载")

    import time
    start = time.time()

    try:
        # 文本向量化
        features = vectorizer.transform([input_data.text])

        # 预测
        prediction = model.predict(features)[0]

        # 获取置信度
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(features)[0]
            confidence = float(max(proba))
        else:
            confidence = 0.95

        sentiment = "正面" if prediction == 1 else "负面"

        elapsed = (time.time() - start) * 1000

        # 更新统计
        stats["total"] += 1
        stats["positive" if prediction == 1 else "negative"] += 1
        stats["confidence_sum"] += confidence
        stats["time_sum"] += elapsed

        logger.info(f"预测: {input_data.text[:30]}... → {sentiment} ({confidence:.3f}) [{elapsed:.1f}ms]")

        return PredictionOutput(
            text=input_data.text,
            sentiment=sentiment,
            confidence=round(confidence, 4),
            model_version=model_version,
        )

    except Exception as e:
        logger.error(f"预测失败: {e}")
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@app.post("/predict/batch", response_model=BatchOutput)
def predict_batch(input_data: BatchInput):
    """
    批量文本情感预测

    Args:
        input_data: 包含文本列表的对象

    Returns:
        BatchOutput: 批量预测结果
    """
    if model is None or vectorizer is None:
        raise HTTPException(status_code=503, detail="模型未加载")

    import time
    start = time.time()

    try:
        # 批量向量化
        features = vectorizer.transform(input_data.texts)

        # 批量预测
        predictions = model.predict(features)

        # 批量获取置信度
        if hasattr(model, "predict_proba"):
            probas = model.predict_proba(features)
            confidences = [float(max(p)) for p in probas]
        else:
            confidences = [0.95] * len(predictions)

        # 构建结果
        results = []
        for text, pred, conf in zip(input_data.texts, predictions, confidences):
            sentiment = "正面" if pred == 1 else "负面"
            results.append(PredictionOutput(
                text=text,
                sentiment=sentiment,
                confidence=round(conf, 4),
                model_version=model_version,
            ))

        elapsed = (time.time() - start) * 1000

        logger.info(f"批量预测: {len(input_data.texts)} 条 [{elapsed:.1f}ms]")

        return BatchOutput(
            predictions=results,
            total=len(results),
            processing_time_ms=round(elapsed, 2),
        )

    except Exception as e:
        logger.error(f"批量预测失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量预测失败: {str(e)}")


@app.get("/stats", response_model=StatsOutput)
def get_stats():
    """获取统计信息"""
    total = stats["total"] or 1
    return StatsOutput(
        total_predictions=stats["total"],
        positive_count=stats["positive"],
        negative_count=stats["negative"],
        avg_confidence=round(stats["confidence_sum"] / total, 4),
        avg_processing_time_ms=round(stats["time_sum"] / total, 2),
    )


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🚀 情感分析 API 启动")
    print("=" * 60)
    print(f"  文档地址: http://localhost:8000/docs")
    print(f"  健康检查: http://localhost:8000/health")
    print(f"  统计信息: http://localhost:8000/stats")
    print("=" * 60)

    uvicorn.run(
        "03-fastapi-deploy:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
