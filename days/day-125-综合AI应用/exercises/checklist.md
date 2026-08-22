# Day 125 — 综合 AI 应用：练习与检查表

## ✅ 完成清单

- [ ] 理解端到端 ML 项目的完整流程
- [ ] 能独立完成数据获取、清洗、预处理
- [ ] 掌握 TF-IDF 特征工程的参数调优
- [ ] 能训练和评估多个 ML 模型
- [ ] 理解模型选择的权衡因素
- [ ] 能将模型部署为 REST API
- [ ] 完成至少 3 道练习题

---

## 📝 基础练习

### 练习 1：数据增强

修改 `01-data-processing.py`，增加数据增强功能：
- 随机同义词替换
- 随机插入/删除词语
- 回译法（中→英→中）

```python
# 提示：使用 synonyms 库或维护同义词词典
# syn替换示例
import random

synonyms = {"好": ["优秀", "出色", "很棒"], "差": ["糟糕", "劣质", "不行"]}

def synonym_replace(text):
    for word, syns in synonyms.items():
        if word in text:
            text = text.replace(word, random.choice(syns), 1)
    return text
```

### 练习 2：模型调参

尝试调整以下参数，观察对模型性能的影响：

| 参数 | 当前值 | 测试值1 | 测试值2 |
|------|--------|---------|---------|
| max_features | 3000 | 1000 | 5000 |
| ngram_range | (1,2) | (1,1) | (1,3) |
| C (逻辑回归) | 1.0 | 0.1 | 10.0 |

记录每组参数的 F1 分数，找出最优组合。

### 练习 3：添加新评估指标

扩展 `02-model-training.py`，添加以下评估指标：
- AUC-ROC 曲线
- 混淆矩阵可视化
- 学习曲线绘制

```python
# 提示：使用 sklearn.metrics 和 matplotlib
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt

# 绘制 ROC 曲线
fpr, tpr, _ = roc_curve(y_test, y_prob)
roc_auc = auc(fpr, tpr)
plt.plot(fpr, tpr, label=f'AUC = {roc_auc:.2f}')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.legend()
plt.show()
```

---

## 🚀 进阶挑战

### 挑战 1：添加模型版本管理

实现一个简单的模型版本管理系统：
- 每次训练保存不同版本的模型
- 支持版本回退
- 记录每个版本的训练参数和指标

```python
# 提示：使用目录结构管理版本
# models/
#   v1.0/
#     model.joblib
#     metrics.json
#   v1.1/
#     model.joblib
#     metrics.json
```

### 挑战 2：实现模型热加载

修改 FastAPI 应用，支持：
- 不重启服务更新模型
- 版本切换 API
- 灰度发布（部分流量用新模型）

### 挑战 3：添加监控和告警

为 API 添加：
- 请求延迟监控
- 错误率统计
- 模型漂移检测
- 简单的告警机制（如错误率 > 5% 时告警）

---

## 💡 思考题

1. **为什么选择 F1 而不是准确率作为主要评估指标？** 在什么场景下准确率更好？

2. **TF-IDF 的局限性是什么？** 有哪些更好的文本表示方法？（提示：词向量、BERT）

3. **如何处理类别不平衡问题？** 如果正面评价占 90%，负面只占 10%，模型会怎样？

4. **FastAPI 的性能瓶颈可能在哪里？** 如何优化高并发场景下的性能？

5. **在生产环境中，如何监控模型是否"过期"？** 有哪些检测概念漂移的方法？
