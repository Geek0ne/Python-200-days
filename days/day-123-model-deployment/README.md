# Day 123 — 模型部署

> 训练好的模型只有部署到生产环境才能产生价值。本章介绍 ML 模型从训练到上线的完整流程。

---

## 1. 模型部署概述

### 1.1 为什么需要部署

```
训练环境                        生产环境
┌─────────────┐                ┌─────────────┐
│  Jupyter    │    模型文件     │  API 服务   │
│  Notebook   │───────────────▶│  (Flask/    │
│  训练代码   │    (.pkl/onnx) │   FastAPI)  │
└─────────────┘                └──────┬──────┘
                                      │
                                      ▼
                               ┌─────────────┐
                               │  客户端应用  │
                               │  (Web/App)  │
                               └─────────────┘
```

### 1.2 部署方式对比

| 方式 | 适用场景 | 优点 | 缺点 |
|------|----------|------|------|
| Flask/FastAPI | 轻量级 API | 简单快速 | 不支持GPU |
| ONNX Runtime | 跨平台推理 | 高性能、多语言 | 模型转换成本 |
| Docker | 容器化部署 | 环境一致、可移植 | 需要容器管理 |
| Kubernetes | 大规模集群 | 自动扩缩容 | 架构复杂 |
| Serverless | 低频调用 | 按需计费 | 冷启动延迟 |

---

## 2. Flask 模型服务

### 2.1 基本结构

```python
from flask import Flask, request, jsonify
import pickle
import numpy as np

app = Flask(__name__)

# 加载模型
with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    features = np.array(data['features']).reshape(1, -1)
    prediction = model.predict(features)[0]
    return jsonify({
        'prediction': float(prediction),
        'status': 'success'
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### 2.2 Flask 优缺点

**优点：**
- 学习曲线低
- 生态成熟，文档丰富
- 适合原型验证

**缺点：**
- 同步处理，高并发性能差
- 不支持异步
- 缺少自动 API 文档

---

## 3. FastAPI 模型服务（推荐）

### 3.1 FastAPI 优势

- **高性能**：基于 Starlette，性能接近 Node.js/Go
- **自动文档**：Swagger UI / ReDoc 自动生成
- **类型安全**：Pydantic 模型校验
- **异步支持**：原生 async/await

### 3.2 完整示例

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pickle
import numpy as np
from typing import List
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML 模型服务",
    description="机器学习模型预测 API",
    version="1.0.0"
)

# 全局模型变量
model = None

# Pydantic 数据模型
class PredictionRequest(BaseModel):
    features: List[float]
    
    class Config:
        json_schema_extra = {
            "example": {
                "features": [5.1, 3.5, 1.4, 0.2]
            }
        }

class PredictionResponse(BaseModel):
    prediction: float
    probability: float = None
    model_version: str = "1.0"

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    version: str

# 生命周期事件
@app.on_event("startup")
async def load_model():
    global model
    try:
        with open('model.pkl', 'rb') as f:
            model = pickle.load(f)
        logger.info("✅ 模型加载成功")
    except Exception as e:
        logger.error(f"❌ 模型加载失败: {e}")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        model_loaded=model is not None,
        version="1.0"
    )

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="模型未加载")
    
    try:
        features = np.array(request.features).reshape(1, -1)
        prediction = model.predict(features)[0]
        
        # 如果模型支持概率预测
        probability = None
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(features)[0]
            probability = float(max(proba))
        
        return PredictionResponse(
            prediction=float(prediction),
            probability=probability
        )
    except Exception as e:
        logger.error(f"预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch_predict")
async def batch_predict(requests: List[PredictionRequest]):
    """批量预测"""
    results = []
    for req in requests:
        features = np.array(req.features).reshape(1, -1)
        pred = model.predict(features)[0]
        results.append({"prediction": float(pred)})
    return {"predictions": results}
```

### 3.3 运行方式

```bash
# 开发模式
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# 访问自动文档
# http://localhost:8000/docs      (Swagger UI)
# http://localhost:8000/redoc     (ReDoc)
```

---

## 4. ONNX 模型导出

### 4.1 什么是 ONNX

ONNX (Open Neural Network Exchange) 是一个开放的模型格式，支持在不同框架间转换和部署。

```
PyTorch 模型  ──→  ONNX 格式  ──→  ONNX Runtime 推理
TensorFlow 模型 ──→  ONNX 格式  ──→  多语言部署 (C++/Java/Python)
Scikit-learn 模型 ──→  ONNX 格式  ──→  高性能推理
```

### 4.2 从 Scikit-learn 导出 ONNX

```python
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import pickle

# 训练模型
# model = ... (已训练的sklearn模型)

# 定义输入类型
initial_type = [('float_input', FloatTensorType([None, 4]))]

# 转换为 ONNX
onnx_model = convert_sklearn(model, initial_types=initial_type)

# 保存
with open("model.onnx", "wb") as f:
    f.write(onnx_model.SerializeToString())
```

### 4.3 从 PyTorch 导出 ONNX

```python
import torch

# 定义模型
model = MyModel()
model.load_state_dict(torch.load('model.pth'))
model.eval()

# 导出
dummy_input = torch.randn(1, 3, 224, 224)
torch.onnx.export(
    model, 
    dummy_input, 
    "model.onnx",
    input_names=['input'],
    output_names=['output'],
    dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
)
```

### 4.4 ONNX Runtime 推理

```python
import onnxruntime as ort
import numpy as np

# 加载模型
session = ort.InferenceSession("model.onnx")

# 获取输入输出名
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

# 推理
input_data = np.random.randn(1, 4).astype(np.float32)
result = session.run([output_name], {input_name: input_data})
print(f"预测结果: {result[0]}")
```

### 4.5 ONNX vs Pickle 对比

| 对比维度 | Pickle | ONNX |
|----------|--------|------|
| 跨语言 | Python only | 多语言 (C++/Java/Go) |
| 推理速度 | 较慢 | 快 (C++实现) |
| 模型大小 | 较大 | 较小 (优化后) |
| 安全性 | 低 (反序列化漏洞) | 高 |
| 框架兼容 | sklearn only | 多框架 |

---

## 5. Docker 容器化

### 5.1 Dockerfile 示例

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码和模型
COPY app/ .
COPY models/ ./models/

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.2 docker-compose.yml

```yaml
version: '3.8'

services:
  ml-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models
    environment:
      - MODEL_PATH=/app/models/model.onnx
      - LOG_LEVEL=info
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
    restart: unless-stopped
```

### 5.3 常用命令

```bash
# 构建镜像
docker build -t ml-api:v1 .

# 运行容器
docker run -d -p 8000:8000 --name ml-api ml-api:v1

# 查看日志
docker logs -f ml-api

# 进入容器调试
docker exec -it ml-api /bin/bash
```

---

## 6. 模型版本管理

### 6.1 版本化策略

```
models/
├── v1/
│   ├── model.onnx
│   ├── metadata.json
│   └── metrics.json
├── v2/
│   ├── model.onnx
│   ├── metadata.json
│   └── metrics.json
└── current -> v2/  (符号链接指向当前版本)
```

### 6.2 元数据记录

```json
{
  "model_version": "2.0",
  "algorithm": "RandomForest",
  "training_date": "2026-08-22",
  "features": ["feature_1", "feature_2", "feature_3"],
  "metrics": {
    "accuracy": 0.95,
    "f1_score": 0.93,
    "rmse": 0.12
  },
  "training_data_size": 10000,
  "hyperparameters": {
    "n_estimators": 100,
    "max_depth": 10
  }
}
```

---

## 7. API 网关与负载均衡

### 7.1 Nginx 反向代理

```nginx
upstream ml_api {
    server ml-api-1:8000;
    server ml-api-2:8000;
    server ml-api-3:8000;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://ml_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /health {
        proxy_pass http://ml_api;
    }
}
```

### 7.2 负载均衡策略

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| 轮询 | 依次分配 | 服务器性能一致 |
| 加权轮询 | 按权重分配 | 服务器性能不同 |
| IP Hash | 按IP分配 | 需要会话保持 |
| 最少连接 | 分配给连接最少的 | 长连接场景 |

---

## 8. 性能优化

### 8.1 模型优化技巧

1. **模型量化**：FP32 → INT8，减少模型大小和推理时间
2. **模型剪枝**：移除不重要的参数
3. **知识蒸馏**：用小模型学习大模型
4. **批处理推理**：一次处理多个请求

### 8.2 服务优化

```python
# 使用连接池
from sqlalchemy.pool import QueuePool

# 异步处理
@app.post("/predict_async")
async def predict_async(request: PredictionRequest):
    # 异步推理不阻塞事件循环
    result = await asyncio.to_thread(sync_predict, request)
    return result

# 缓存结果
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_predict(features_hash: str):
    # 缓存相同输入的预测结果
    pass
```

### 8.3 监控指标

```
关键监控指标:
- 请求延迟 (P50/P95/P99)
- QPS (每秒请求数)
- 错误率
- 模型推理时间
- 内存使用率
- CPU/GPU 使用率
```

---

## 9. 实战代码

- `01-flask-model-service.py`：Flask 模型服务
- `02-fastapi-model-service.py`：FastAPI 模型服务（推荐）
- `03-onnx-deployment.py`：ONNX 模型导出与部署

---

## 10. 思考题

1. **Flask 和 FastAPI 在模型服务场景下各有什么优缺点？** 什么情况下你会选择 Flask 而不是 FastAPI？

2. **ONNX 格式相比 Pickle 有什么优势？** 为什么在生产环境中推荐使用 ONNX？

3. **如何实现模型的灰度发布？** 即新旧版本模型同时运行，逐步切换流量。

4. **Docker 容器化部署有哪些注意事项？** 如何处理模型文件过大、GPU 资源分配等问题？

5. **如何监控线上模型的性能衰减？** 当模型效果下降时应该如何处理？

---

## 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [ONNX Runtime](https://onnxruntime.ai/)
- [MLflow 模型管理](https://mlflow.org/)
- [BentoML](https://www.bentoml.com/)
