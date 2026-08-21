# Day 123 — 模型部署 — 练习清单

## ✅ 今日完成清单

- [ ] 理解模型部署的基本流程和方式
- [ ] 掌握 Flask 模型服务搭建
- [ ] 掌握 FastAPI 模型服务搭建（推荐方式）
- [ ] 理解 ONNX 格式及其优势
- [ ] 了解 Docker 容器化部署
- [ ] 了解模型版本管理和灰度发布
- [ ] 完成 3 个代码示例的运行和理解
- [ ] 完成以下练习题

---

## 📝 基础练习题

### 练习 1：FastAPI 模型服务

基于 `02-fastapi-model-service.py`，实现以下功能：

1. 添加 `/model/reload` 端点，支持热重载模型（不重启服务）
2. 添加请求参数校验：特征值必须在合理范围内
3. 添加 CORS 支持，允许跨域请求
4. 添加 API Key 认证中间件

```python
# 提示: FastAPI 中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

---

### 练习 2：ONNX 模型转换

将以下 PyTorch 模型转换为 ONNX 格式：

```python
import torch
import torch.nn as nn

class SimpleNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(10, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        return self.fc3(x)
```

**要求：**
1. 训练模型并导出为 ONNX
2. 使用 ONNX Runtime 验证推理结果一致性
3. 对比 PyTorch vs ONNX 的推理速度

---

### 练习 3：Docker 部署

为 FastAPI 模型服务编写完整的 Dockerfile：

**要求：**
1. 使用多阶段构建减小镜像大小
2. 添加健康检查
3. 非 root 用户运行
4. 优化层缓存

---

## 🔥 进阶挑战题

### 挑战 1：模型 A/B 测试

实现一个简单的 A/B 测试框架：

1. 将请求随机分配到两个模型版本
2. 记录每个版本的预测结果和延迟
3. 统计两个版本的准确率差异
4. 实现流量比例动态调整

```python
# 提示: 负载均衡策略
import random

class ABTestRouter:
    def __init__(self, model_a, model_b, traffic_ratio=0.5):
        self.model_a = model_a
        self.model_b = model_b
        self.ratio = traffic_ratio
    
    def route(self, request):
        if random.random() < self.ratio:
            return self.model_a, "A"
        else:
            return self.model_b, "B"
```

---

### 挑战 2：模型监控告警

实现模型性能监控系统：

1. 记录每次预测的输入、输出、延迟
2. 检测数据漂移（输入分布变化）
3. 检测概念漂移（预测准确率下降）
4. 超过阈值时发送告警

```python
# 数据漂移检测: KL散度
from scipy.stats import entropy

def detect_drift(reference_dist, current_dist, threshold=0.1):
    kl_div = entropy(reference_dist, current_dist)
    return kl_div > threshold
```

---

### 挑战 3：批量推理优化

实现高性能批量推理服务：

1. 请求合并：将短时间内的多个请求合并为一个 batch
2. 异步处理：使用 asyncio 非阻塞处理
3. 动态批处理：根据负载自动调整 batch size
4. GPU 推理：支持 CUDA 加速

---

## 📚 扩展阅读

- [BentoML 框架](https://www.bentoml.com/) - 一站式 ML 部署平台
- [MLflow 模型管理](https://mlflow.org/) - 模型生命周期管理
- [Seldon Core](https://www.seldon.io/) - 企业级 ML 部署平台
- [TensorFlow Serving](https://www.tensorflow.org/tfx/guide/serving) - TF 模型服务
- [Triton Inference Server](https://github.com/triton-inference-server) - NVIDIA 推理服务器
