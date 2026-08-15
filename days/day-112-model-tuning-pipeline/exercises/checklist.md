# Day 112 — 练习题清单

> 完成以下练习以巩固今日学习内容。建议先完成基础题，再挑战进阶题。

---

## 练习 1：交叉验证实践（基础）

**目标：** 用交叉验证比较不同模型的性能

**要求：**
1. 使用 `sklearn.datasets.load_wine()` 加载红酒数据集
2. 对以下 3 个模型进行 5 折交叉验证：
   - Logistic Regression（需要先标准化）
   - Random Forest（不需要标准化）
   - KNN（需要先标准化）
3. 使用 `accuracy` 和 `f1_macro` 两个指标评估
4. 比较哪个模型最稳定（标准差最小）

**提示：**
- 使用 Pipeline 将标准化和模型串联
- 使用 `cross_val_score` 的 `scoring` 参数切换指标
- 注意 KNN 对特征缩放敏感

---

## 练习 2：超参数搜索（基础）

**目标：** 使用 GridSearchCV 为 SVM 调参

**要求：**
1. 使用乳腺癌数据集（`load_breast_cancer`）
2. 构建 Pipeline：`StandardScaler → SVC`
3. 搜索以下参数组合：
   - `C`: [0.001, 0.01, 0.1, 1, 10, 100]
   - `kernel`: ['linear', 'rbf', 'poly']
   - `gamma`: ['scale', 'auto']
4. 使用 5 折交叉验证，评估指标为 `roc_auc`
5. 输出最佳参数和最佳得分

**扩展：**
- 在搜索结果中找出 Top 3 的参数组合
- 计算总共训练了多少次模型

---

## 练习 3：Pipeline + 特征工程（进阶）

**目标：** 构建包含特征工程的完整 Pipeline

**要求：**
1. 使用合成数据 `make_classification(n_samples=1000, n_features=20, n_informative=5, n_redundant=5)`
2. 构建以下 Pipeline：
   - `StandardScaler → PCA(保留95%方差) → SelectKBest(k=10) → LogisticRegression`
3. 搜索 PCA 的 `n_components`（[5, 10, 15, 20, 'mle']）和 LogisticRegression 的 `C`（[0.01, 0.1, 1, 10]）
4. 对比以下三种 Pipeline 的性能：
   - 无特征工程：`Scaler → LR`
   - 有 PCA：`Scaler → PCA → LR`
   - 有 PCA + 特征选择：`Scaler → PCA → SelectKBest → LR`

**思考：** 特征工程对模型性能有什么影响？

---

## 练习 4：模型持久化与部署（进阶）

**目标：** 保存模型并在新数据上使用

**要求：**
1. 使用练习 3 中最佳的 Pipeline
2. 用全部训练数据重新训练（`pipeline.fit(X_train, y_train)`）
3. 保存模型到文件 `model_practice.pkl`
4. 编写一个函数 `predict_churn(model_path, new_data)` 实现：
   - 加载模型
   - 对新数据进行预测
   - 返回预测结果和概率
5. 用 5 条新数据测试你的函数

**提示：**
- 使用 `joblib.dump` 和 `joblib.load`
- 确保新数据的格式与训练数据一致

---

## 练习 5：综合挑战 — 客户细分（挑战）

**目标：** 构建一个完整的分类 Pipeline

**要求：**
1. 使用 `fetch_california_housing()` 数据集，将其转换为二分类问题（房价中位数 > 2.5 为正类）
2. 构建包含以下步骤的 Pipeline：
   - 数值特征：缺失值填充 → 标准化
   - 可选特征工程：PCA、多项式特征
   - 模型：随机森林
3. 使用 `RandomizedSearchCV`（n_iter=30）搜索超参数
4. 输出完整的评估报告（混淆矩阵、分类报告、AUC）
5. 保存最终模型

**评估标准：**
- Pipeline 结构清晰
- 代码有适当注释
- 评估指标全面
- 模型保存可正常加载

---

## 📝 完成检查

完成练习后，检查以下要点：

- [ ] 练习 1：能正确使用 `cross_val_score` 比较模型
- [ ] 练习 2：能使用 `GridSearchCV` 搜索最优参数
- [ ] 练习 3：能构建包含特征工程的 Pipeline
- [ ] 练习 4：能保存和加载 Pipeline 模型
- [ ] 练习 5：能独立完成完整的 ML 项目流程

---

## 💡 进阶思考

1. 如果你的数据集有 100 万个样本，网格搜索会很慢。你会怎么优化？
2. 在什么情况下你会选择 `RandomizedSearchCV` 而不是 `GridSearchCV`？
3. 如何在 Pipeline 中添加自定义的预处理步骤？
4. 模型保存后，如何在不同的 Python 版本或 scikit-learn 版本中加载？

---

> 完成后可以对比 `code/` 目录下的参考代码，看看是否有更好的实现方式。
