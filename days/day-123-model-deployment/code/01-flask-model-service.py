#!/usr/bin/env python3
"""
Day 123 - Flask 模型服务
演示如何用 Flask 部署机器学习模型
"""

from flask import Flask, request, jsonify
import pickle
import numpy as np
import os
import json
import time
from datetime import datetime


# ============================================================
# 1. 训练一个简单的模型用于演示
# ============================================================

def train_demo_model():
    """训练一个简单的分类模型"""
    from sklearn.datasets import load_iris
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    
    # 加载数据
    iris = load_iris()
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, random_state=42
    )
    
    # 训练模型
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # 评估
    accuracy = accuracy_score(y_test, model.predict(X_test))
    print(f"模型准确率: {accuracy:.4f}")
    
    # 保存模型和元数据
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
    }
    
    with open('models/metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 模型已保存到 models/iris_model.pkl")
    return model, metadata


# ============================================================
# 2. Flask 模型服务
# ============================================================

app = Flask(__name__)

# 全局变量
model = None
metadata = None
request_count = 0
start_time = None


@app.before_request
def before_request():
    """请求前处理"""
    global request_count
    request_count += 1


@app.route('/')
def index():
    """首页 - API 说明"""
    return jsonify({
        "service": "Iris 分类模型服务",
        "version": "1.0",
        "endpoints": {
            "GET /": "API 说明",
            "GET /health": "健康检查",
            "GET /model/info": "模型信息",
            "POST /predict": "单条预测",
            "POST /batch_predict": "批量预测",
            "GET /stats": "服务统计",
        }
    })


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None,
        "uptime_seconds": time.time() - start_time if start_time else 0,
    })


@app.route('/model/info')
def model_info():
    """获取模型信息"""
    if metadata is None:
        return jsonify({"error": "模型未加载"}), 503
    return jsonify(metadata)


@app.route('/predict', methods=['POST'])
def predict():
    """单条预测"""
    if model is None:
        return jsonify({"error": "模型未加载"}), 503
    
    try:
        data = request.get_json()
        
        if 'features' not in data:
            return jsonify({"error": "缺少 features 字段"}), 400
        
        features = np.array(data['features']).reshape(1, -1)
        
        # 校验特征维度
        expected_features = 4
        if features.shape[1] != expected_features:
            return jsonify({
                "error": f"特征维度错误: 期望 {expected_features}, 实际 {features.shape[1]}"
            }), 400
        
        # 预测
        start = time.time()
        prediction = model.predict(features)[0]
        probability = model.predict_proba(features)[0]
        inference_time = (time.time() - start) * 1000  # ms
        
        # 类别名称
        class_names = metadata.get('classes', [])
        predicted_class = class_names[prediction] if prediction < len(class_names) else str(prediction)
        
        return jsonify({
            "prediction": int(prediction),
            "predicted_class": predicted_class,
            "probabilities": {
                name: float(prob) for name, prob in zip(class_names, probability)
            },
            "confidence": float(max(probability)),
            "inference_time_ms": round(inference_time, 2),
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/batch_predict', methods=['POST'])
def batch_predict():
    """批量预测"""
    if model is None:
        return jsonify({"error": "模型未加载"}), 503
    
    try:
        data = request.get_json()
        samples = data.get('samples', [])
        
        if not samples:
            return jsonify({"error": "samples 列表为空"}), 400
        
        features = np.array(samples)
        
        # 预测
        start = time.time()
        predictions = model.predict(features)
        probabilities = model.predict_proba(features)
        inference_time = (time.time() - start) * 1000
        
        class_names = metadata.get('classes', [])
        
        results = []
        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            results.append({
                "index": i,
                "prediction": int(pred),
                "predicted_class": class_names[pred] if pred < len(class_names) else str(pred),
                "confidence": float(max(prob)),
            })
        
        return jsonify({
            "predictions": results,
            "total": len(results),
            "inference_time_ms": round(inference_time, 2),
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/stats')
def stats():
    """服务统计"""
    return jsonify({
        "total_requests": request_count,
        "uptime_seconds": round(time.time() - start_time, 2) if start_time else 0,
        "model_loaded": model is not None,
    })


# ============================================================
# 3. 启动服务
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Flask 模型服务启动")
    print("=" * 60)
    
    # 训练并保存模型
    model, metadata = train_demo_model()
    
    start_time = time.time()
    
    print(f"\n服务地址: http://localhost:5000")
    print(f"健康检查: http://localhost:5000/health")
    print(f"模型信息: http://localhost:5000/model/info")
    print(f"\n使用示例:")
    print(f'  curl -X POST http://localhost:5000/predict \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{{"features": [5.1, 3.5, 1.4, 0.2]}}\'')
    
    app.run(host='0.0.0.0', port=5000, debug=True)
