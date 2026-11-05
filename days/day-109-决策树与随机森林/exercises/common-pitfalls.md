# Day 109 — 常见陷阱与避坑指南

## 🚨 决策树常见陷阱

### 陷阱1：不加限制导致过拟合

```python
# ❌ 错误：不限制深度
dt = DecisionTreeClassifier(random_state=42)
dt.fit(X_train, y_train)
# 训练准确率: 1.0000 (记住了一切!)
# 测试准确率: 0.7500 (泛化能力差)

# ✅ 正确：限制树的复杂度
dt = DecisionTreeClassifier(
    max_depth=5,            # 限制深度
    min_samples_split=10,   # 分裂需要足够样本
    min_samples_leaf=5,     # 叶节点至少5个样本
    random_state=42
)
```

**原理**：决策树可以无限生长直到每个叶节点只有一个样本——这等于记住了训练集。

### 陷阱2：忽略类别不平衡

```python
# ❌ 信用数据中违约率只有 5%，模型会倾向于预测"正常"
# 正常: 950 个，违约: 50 个
# 如果全部预测为正常，准确率 = 95%！但这毫无意义

# ✅ 使用 class_weight 平衡类别
dt = DecisionTreeClassifier(class_weight='balanced', random_state=42)
rf = RandomForestClassifier(class_weight='balanced', random_state=42)

# ✅ 或使用 F1/AUC 代替准确率作为评估指标
from sklearn.metrics import f1_score, roc_auc_score
```

### 陷阱3：特征重要性的误导

```python
# ❌ 特征有 ID 列时，决策树会把 ID 作为重要特征
data['user_id'] = range(len(data))
# 决策树发现: 用 user_id 分裂可以完美分类每个样本!
# 但这是过拟合，ID 没有预测价值

# ✅ 训练前删除 ID 列
features = [col for col in data.columns if col != 'user_id']
```

---

## 🌲 随机森林常见陷阱

### 陷阱4：n_estimators 设置过小

```python
# ❌ 只用 10 棵树
rf = RandomForestClassifier(n_estimators=10, random_state=42)
# 集成效果很弱，接近单棵决策树

# ✅ 通常 100-500 棵足够
# 性能提升有边际递减，但不会下降
rf = RandomForestClassifier(n_estimators=300, random_state=42)
```

### 陷阱5：忽略 n_jobs 参数

```python
# ❌ 默认 n_jobs=1，只用 1 个 CPU 核
rf = RandomForestClassifier(n_estimators=300, random_state=42)
# 训练时间: 30秒

# ✅ 使用所有 CPU 核
rf = RandomForestClassifier(n_estimators=300, n_jobs=-1, random_state=42)
# 训练时间: 5秒 (6核CPU)
```

### 陷阱6：重复数据导致 OOB 偏差

```python
# ❌ 训练集和测试集中有重复样本时，OOB 评分虚高
# 因为 OOB 样本可能和训练样本重叠

# ✅ 确保数据无重复
data = data.drop_duplicates()
# ✅ 或用交叉验证替代 OOB 作为主要评估手段
```

---

## 📊 评估指标常见陷阱

### 陷阱7：只看准确率

```
场景：1000 个样本，950 正常，50 违约

模型A 全部预测为正常: 准确率 = 95% (看起来很好?)
模型B 正确识别 40 个违约: 准确率 = 94% (看起来更差?)

但实际上模型B更有价值！因为它能识别违约客户。
```

**正确做法**：
```python
from sklearn.metrics import classification_report
print(classification_report(y_test, y_pred,
                            target_names=['正常', '违约']))
# 关注 Precision, Recall, F1 (尤其是少数类)
```

---

## 🔧 调参常见陷阱

### 陷阱8：在测试集上调参

```python
# ❌ 错误流程
dt = DecisionTreeClassifier(max_depth=d)
dt.fit(X_train, y_train)
score = dt.score(X_test, y_test)  # 用测试集调参!
# 最终测试集评分不可信

# ✅ 正确流程
from sklearn.model_selection import cross_val_score
# 用交叉验证在训练集上调参
for d in [3, 5, 7, 10]:
    dt = DecisionTreeClassifier(max_depth=d)
    cv_score = cross_val_score(dt, X_train, y_train, cv=5).mean()
    print(f"depth={d}, CV score={cv_score:.4f}")
# 选最佳参数后，再在测试集上评估一次
```

---

## 💡 总结：经验法则

| 场景 | 建议 |
|------|------|
| 需要可解释性 | 用决策树，限制 max_depth=5 |
| 追求稳定性 | 用随机森林，n_estimators≥100 |
| 类别不平衡 | 用 class_weight='balanced' + F1 评估 |
| 数据量小 (<1000) | 用决策树或简单随机森林 |
| 数据量大 (>100K) | 考虑 LightGBM/XGBoost |
| 特征有 ID 列 | 训练前删除 |
| 调参 | 用交叉验证，不要在测试集上调 |
