#!/usr/bin/env python3
"""
Day 123 - FastAPI 模型服务
演示如何用 FastAPI 部署机器学习模型（推荐方式）
"""

import os
import json
import time
import pickle
import logging
import numpy as np
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# ============================================================
# 1. 日志配置
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# 2. Pydantic 数据模型
# ============================================================

class PredictionRequest(BaseModel):
    """单条预测请求"""
    features: List[float] = Field(
        ..., 
        description="特征向量",
        min_length=4,
        max_length=4,
        examples=[[5.1, 3.5, 1.4, 0.2]]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"features": [5.1, 3.5, 1.4, 0.2]},
                {"features": [6.2, 2.9, 4.3, 1.3]},
                {"features": [7.7, 3.0, 6.1, 2.3]},
            ]
        }
    }


class BatchPredictionRequest(BaseModel):
    """批量预测请求"""
    samples: List[List[float]] = Field(
        ...,
        description="特征矩阵",
        min_length=1,
        examples=[[[5.1, 3.5, 1.4, 0.2], [6.2, 2.9, 4.3, 1.3]]]
    )


class PredictionResponse(BaseModel):
    """预测响应"""
    prediction: int
    predicted_class: str
    probabilities: dict
    confidence: float
    inference_time_ms: float


class BatchPredictionResponse(BaseModel):
    """批量预测响应"""
    predictions: List[dict]
    total: int
    inference_time_ms: float


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    model_loaded: bool
    uptime_seconds: float
    version: str


class ModelInfoResponse(BaseModel):
    """模型信息响应"""
    model_name: str
    algorithm: str
    features: List[str]
    classes: List[str]
    accuracy: float
    created_at: str


class StatsResponse(BaseModel):
    """统计响应"""
    total_requests: int
    successful_predictions: int
    failed_predictions: int
    avg_inference_time_ms: float
    uptime_seconds: float


# ============================================================
# 3. 全局状态
# ============================================================

class AppState:
    """应用状态管理"""
    def __init__(self):
        self.model = None
        self.metadata = None
        self.start_time = None
        self.total_requests = 0
        self.successful_predictions = 0
        self.failed_predictions = 0
        self.inference_times = []


state = AppState()


# ============================================================
# 4. 生命周期管理
# ============================================================

def load_model():
    """加载模型"""
    model_path = 'models/iris_model.pkl'
    metadata_path = 'models/metadata.json'
    
    if not os.path.exists(model_path):
        # 训练模型
        logger.info("模型文件不存在，开始训练...")
        train_model()
    
    with open(model_path, 'rb') as f:
        state.model = pickle.load(f)
    
    with open(metadata_path, 'r') as f:
        state.metadata = json.load(f)
    
    logger.info(f"✅ 模型加载成功: {state.metadata.get('model_name', 'unknown')}")


def train_model():
    """训练模型"""
    from sklearn.datasets import load_iris
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    
    iris = load_iris()
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, random_state=42
    )
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    accuracy = accuracy_score(y_test, model.predict(X_test))
    
    os.makedirs('models', exist_ok=True)
    
    with open('models/iris_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    metadata = {
        "model_name": "Iris 分类器",
        "algorithm": "RandomForest",
        "features": iris.feature_names.tolist(),
        "classes": iris.target_names.tolist(),
        "accuracy": float(accuracy),
        "created_at": datetime.now().isoformat(),
        "version": "1.0",
    }
    
    with open('models/metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ 模型训练完成, 准确率: {accuracy:.4f}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    state.start_time = time.time()
    load_model()
    yield
    # 关闭时
    logger.info("服务关闭")


# ============================================================
# 5. FastAPI 应用
# ============================================================

app = FastAPI(
    title="ML 模型服务",
    description="基于 FastAPI 的机器学习模型部署示例",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", tags=["根路径"])
async def root():
    """API 说明"""
    return {
        "service": "Iris 分类模型服务",
        "version": "1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", response_model=HealthResponse, tags=["运维"])
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        model_loaded=state.model is not None,
        uptime_seconds=round(time.time() - state.start_time, 2) if state.start_time else 0,
        version="1.0",
    )


@app.get("/model/info", response_model=ModelInfoResponse, tags=["模型"])
async def model_info():
    """获取模型信息"""
    if state.metadata is None:
        raise HTTPException(status_code=503, detail="模型未加载")
    return ModelInfoResponse(**state.metadata)


@app.post("/predict", response_model=PredictionResponse, tags=["预测"])
async def predict(request: PredictionRequest):
    """单条预测"""
    state.total_requests += 1
    
    if state.model is None:
        state.failed_predictions += 1
        raise HTTPException(status_code=503, detail="模型未加载")
    
    try:
        features = np.array(request.features).reshape(1, -1)
        
        start = time.time()
        prediction = state.model.predict(features)[0]
        probability = state.model.predict_proba(features)[0]
        inference_time = (time.time() - start) * 1000
        
        state.inference_times.append(inference_time)
        state.successful_predictions += 1
        
        class_names = state.metadata.get('classes', [])
        predicted_class = class_names[prediction] if prediction < len(class_names) else str(prediction)
        
        return PredictionResponse(
            prediction=int(prediction),
            predicted_class=predicted_class,
            probabilities={
                name: round(float(prob), 4) 
                for name, prob in zip(class_names, probability)
            },
            confidence=round(float(max(probability)), 4),
            inference_time_ms=round(inference_time, 2),
        )
    
    except Exception as e:
        state.failed_predictions += 1
        logger.error(f"预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch_predict", response_model=BatchPredictionResponse, tags=["预测"])
async def batch_predict(request: BatchPredictionRequest):
    """批量预测"""
    state.total_requests += 1
    
    if state.model is None:
        state.failed_predictions += 1
        raise HTTPException(status_code=503, detail="模型未加载")
    
    try:
        features = np.array(request.samples)
        
        start = time.time()
        predictions = state.model.predict(features)
        probabilities = state.model.predict_proba(features)
        inference_time = (time.time() - start) * 1000
        
        state.inference_times.append(inference_time)
        state.successful_predictions += 1
        
        class_names = state.metadata.get('classes', [])
        
        results = []
        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            results.append({
                "index": i,
                "prediction": int(pred),
                "predicted_class": class_names[pred] if pred < len(class_names) else str(pred),
                "confidence": round(float(max(prob)), 4),
            })
        
        return BatchPredictionResponse(
            predictions=results,
            total=len(results),
            inference_time_ms=round(inference_time, 2),
        )
    
    except Exception as e:
        state.failed_predictions += 1
        logger.error(f"批量预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResponse, tags=["运维"])
async def stats():
    """服务统计"""
    avg_time = (
        round(np.mean(state.inference_times), 2) 
        if state.inference_times else 0
    )
    
    return StatsResponse(
        total_requests=state.total_requests,
        successful_predictions=state.successful_predictions,
        failed_predictions=state.failed_predictions,
        avg_inference_time_ms=avg_time,
        uptime_seconds=round(time.time() - state.start_time, 2) if state.start_time else 0,
    )


# ============================================================
# 6. 启动
# ============================================================

if __name__ == '__main__':
    import uvicorn
    
    print("=" * 60)
    print("🚀 FastAPI 模型服务启动")
    print("=" * 60)
    print(f"\n服务地址: http://localhost:8000")
    print(f"Swagger 文档: http://localhost:8000/docs")
    print(f"ReDoc 文档: http://localhost:8000/redoc")
    print(f"\n使用示例:")
    print(f'  curl -X POST http://localhost:8000/predict \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{{"features": [5.1, 3.5, 1.4, 0.2]}}\'')
    
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')
