# Day 106 — 机器学习基础：完成清单 & 练习题

## ✅ 今日完成清单

- [ ] 理解机器学习三大范式（监督/无监督/强化学习）
- [ ] 掌握 Scikit-learn 统一 API（fit/predict/score）
- [ ] 理解 train_test_split 的原理和参数
- [ ] 掌握四大评估指标（准确率/精确率/召回率/F1）
- [ ] 理解数据泄露问题及避免方法
- [ ] 能使用 Pipeline 串联预处理和模型
- [ ] 完成代码示例 01（基础 ML 流程）
- [ ] 完成代码示例 02（交叉验证与模型对比）
- [ ] 完成代码示例 03（手写数字实战）
- [ ] 完成下方练习题

---

## 📝 练习题

### 基础题

**练习 1：自定义模型评估**

用 `load_wine()` 数据集（sklearn 内置），完成以下任务：
1. 加载数据并查看基本信息
2. 拆分训练/测试集（test_size=0.3, random_state=42）
3. 用 `LogisticRegression` 训练模型
4. 打印 `classification_report`

```python
from sklearn.datasets import load_wine
# 你的代码...
```

**练习 2：特征缩放对比**

用鸢尾花数据集，对比以下两种情况的 KNN 准确率：
- 不做特征缩放
- 使用 StandardScaler 缩放

回答：为什么 KNN 对特征缩放敏感？

**练习 3：交叉验证实践**

对 `load_digits()` 数据集，用 `cross_val_score` 对 Random Forest 进行 10 折交叉验证，输出每折的准确率和平均准确率。

---

### 进阶题

**练习 4：Pipeline 构建**

构建一个 Pipeline，包含以下步骤：
1. StandardScaler（标准化）
2. PCA（降维到 2 个主成分）
3. LogisticRegression（分类）

对鸢尾花数据集进行训练和评估。

```python
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
# 你的代码...
```

**练习 5：错误分析深入**

在手写数字识别项目中，找出模型最容易混淆的两个数字对（如 3 和 8），分析原因并提出改进方案。

**练习 6：设计你自己的 ML 项目**

选择一个你感兴趣的场景：
- 预测明天是否下雨（天气数据）
- 判断评论是正面还是负面（文本数据）
- 预测某商品是否会被购买（用户行为数据）

回答以下问题：
1. 这是监督学习还是无监督学习？
2. 是分类任务还是回归任务？
3. 你需要什么数据？从哪里获取？
4. 你会用什么评估指标？为什么？
5. 画出你的 ML 工作流（文字描述即可）

---

## 💡 提示

- 跑代码前确认 scikit-learn 已安装：`pip install scikit-learn`
- 所有代码示例可以直接 `python3 xxx.py` 运行
- 遇到问题可以查阅 [Scikit-learn 官方文档](https://scikit-learn.org/stable/)
