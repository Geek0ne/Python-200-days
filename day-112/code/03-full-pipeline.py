"""
Day 112 — 03-full-pipeline.py
完整 ML Pipeline 实战：数据预处理 → 特征工程 → 模型选择 → 超参数调优 → 评估 → 保存

模拟场景：电信客户流失预测（Churn Prediction）

运行方式：python 03-full-pipeline.py
"""

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

from sklearn.datasets import make_classification
from sklearn.model_selection import (
    train_test_split,
    GridSearchCV,
    StratifiedKFold,
    cross_val_score,
)
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    VotingClassifier,
)
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
import joblib
import os

# ============================================================
# 1. 生成模拟数据（模拟电信客户数据）
# ============================================================
print("=" * 70)
print("1. 生成模拟数据（电信客户流失预测）")
print("=" * 70)

np.random.seed(42)
n_samples = 1000

# 生成特征
data = pd.DataFrame({
    'age': np.random.randint(18, 70, n_samples),
    'tenure_months': np.random.randint(1, 72, n_samples),
    'monthly_charges': np.random.uniform(20, 100, n_samples),
    'total_charges': np.random.uniform(100, 8000, n_samples),
    'num_support_calls': np.random.randint(0, 10, n_samples),
    'num_complaints': np.random.randint(0, 5, n_samples),
    'contract_type': np.random.choice(['Month-to-month', 'One year', 'Two year'],
                                       n_samples, p=[0.5, 0.3, 0.2]),
    'payment_method': np.random.choice(
        ['Electronic check', 'Mailed check', 'Bank transfer', 'Credit card'],
        n_samples
    ),
    'internet_service': np.random.choice(['DSL', 'Fiber optic', 'No'], n_samples,
                                          p=[0.35, 0.45, 0.2]),
    'paperless_billing': np.random.choice([0, 1], n_samples, p=[0.4, 0.6]),
})

# 生成标签（流失率约 25%）
churn_prob = (
    0.1 +
    0.3 * (data['contract_type'] == 'Month-to-month').astype(int) +
    0.15 * (data['num_support_calls'] > 5).astype(int) +
    0.1 * (data['num_complaints'] > 2).astype(int) +
    0.05 * (data['internet_service'] == 'Fiber optic').astype(int) -
    0.1 * (data['tenure_months'] > 36).astype(int)
)
churn_prob = np.clip(churn_prob, 0.05, 0.95)
data['churn'] = np.random.binomial(1, churn_prob)

# 人为制造一些缺失值（模拟真实数据）
for col in ['age', 'monthly_charges', 'total_charges']:
    mask = np.random.random(n_samples) < 0.03
    data.loc[mask, col] = np.nan

print(f"数据集大小: {data.shape}")
print(f"特征数: {data.shape[1] - 1}")
print(f"缺失值:")
print(data.isnull().sum()[data.isnull().sum() > 0])
print(f"\n类别分布:")
print(data['churn'].value_counts())
print(f"流失率: {data['churn'].mean():.2%}")

# ============================================================
# 2. 数据探索
# ============================================================
print("\n" + "=" * 70)
print("2. 数据探索")
print("=" * 70)

print("\n数值特征统计:")
print(data.describe().round(2))

print("\n类别特征分布:")
for col in data.select_dtypes(include='object').columns:
    print(f"\n{col}:")
    print(data[col].value_counts())

# ============================================================
# 3. 定义特征类型
# ============================================================
print("\n" + "=" * 70)
print("3. 定义特征类型")
print("=" * 70)

# 分离特征和标签
X = data.drop('churn', axis=1)
y = data['churn']

# 定义数值和类别特征
numeric_features = ['age', 'tenure_months', 'monthly_charges', 'total_charges',
                    'num_support_calls', 'num_complaints', 'paperless_billing']
categorical_features = ['contract_type', 'payment_method', 'internet_service']

print(f"数值特征 ({len(numeric_features)}): {numeric_features}")
print(f"类别特征 ({len(categorical_features)}): {categorical_features}")

# ============================================================
# 4. 构建预处理器（ColumnTransformer）
# ============================================================
print("\n" + "=" * 70)
print("4. 构建预处理器")
print("=" * 70)

# 数值特征处理：缺失值填充 → 缩放
numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler()),
])

# 类别特征处理：缺失值填充 → 独热编码
from sklearn.preprocessing import OneHotEncoder
categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
    ('onehot', OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore')),
])

# 组合预处理器
preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_features),
        ('cat', categorical_transformer, categorical_features),
    ],
    remainder='drop'
)

print("预处理器结构:")
print(f"  数值特征 → SimpleImputer(median) → StandardScaler")
print(f"  类别特征 → SimpleImputer(constant) → OneHotEncoder")

# 测试预处理器
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

preprocessor.fit(X_train)
X_train_processed = preprocessor.transform(X_train)
X_test_processed = preprocessor.transform(X_test)

print(f"\n处理后特征数: {X_train_processed.shape[1]}")
print(f"训练集: {X_train_processed.shape}, 测试集: {X_test_processed.shape}")

# ============================================================
# 5. 构建完整 Pipeline
# ============================================================
print("\n" + "=" * 70)
print("5. 构建完整 Pipeline")
print("=" * 70)

# Pipeline 1: Logistic Regression
pipeline_lr = Pipeline([
    ('preprocessor', preprocessor),
    ('feature_selection', SelectKBest(f_classif, k='all')),
    ('classifier', LogisticRegression(max_iter=1000, random_state=42))
])

# Pipeline 2: Random Forest（不需要缩放，但预处理器仍然有用）
pipeline_rf = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
])

# Pipeline 3: Gradient Boosting
pipeline_gb = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', GradientBoostingClassifier(n_estimators=100, random_state=42))
])

# Pipeline 4: SVM + PCA
pipeline_svm = Pipeline([
    ('preprocessor', preprocessor),
    ('pca', PCA(n_components=0.95, random_state=42)),
    ('classifier', SVC(probability=True, random_state=42))
])

pipelines = {
    'Logistic Regression': pipeline_lr,
    'Random Forest': pipeline_rf,
    'Gradient Boosting': pipeline_gb,
    'SVM + PCA': pipeline_svm,
}

print("已构建 4 个 Pipeline:")
for name, pipe in pipelines.items():
    print(f"  - {name}")

# ============================================================
# 6. 基线评估（未调参）
# ============================================================
print("\n" + "=" * 70)
print("6. 基线评估（未调参）")
print("=" * 70)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print(f"{'模型':<25} {'CV均值':>8} {'CV标准差':>8}")
print("-" * 45)

for name, pipe in pipelines.items():
    scores = cross_val_score(pipe, X_train, y_train, cv=cv, scoring='roc_auc')
    print(f"{name:<25} {scores.mean():>8.4f} {scores.std()*2:>8.4f}")

# ============================================================
# 7. 超参数调优（GridSearchCV）
# ============================================================
print("\n" + "=" * 70)
print("7. 超参数调优")
print("=" * 70)

# 对最佳候选模型进行调优
param_grids = {
    'Logistic Regression': {
        'classifier__C': [0.01, 0.1, 1, 10],
        'classifier__penalty': ['l1', 'l2'],
        'classifier__solver': ['liblinear'],
    },
    'Random Forest': {
        'classifier__n_estimators': [100, 200],
        'classifier__max_depth': [5, 10, 20, None],
        'classifier__min_samples_split': [2, 5],
    },
    'Gradient Boosting': {
        'classifier__n_estimators': [100, 200],
        'classifier__max_depth': [3, 5, 7],
        'classifier__learning_rate': [0.01, 0.1, 0.2],
    },
}

best_models = {}

for name in ['Logistic Regression', 'Random Forest', 'Gradient Boosting']:
    print(f"\n正在调优: {name}...")
    gs = GridSearchCV(
        estimator=pipelines[name],
        param_grid=param_grids[name],
        cv=cv,
        scoring='roc_auc',
        n_jobs=-1,
        verbose=0,
    )
    gs.fit(X_train, y_train)

    best_models[name] = gs.best_estimator_
    test_score = gs.score(X_test, y_test)

    print(f"  最佳参数: {gs.best_params_}")
    print(f"  最佳CV得分: {gs.best_score_:.4f}")
    print(f"  测试集得分: {test_score:.4f}")

# ============================================================
# 8. 模型评估与比较
# ============================================================
print("\n" + "=" * 70)
print("8. 模型评估与比较")
print("=" * 70)

print(f"\n{'模型':<25} {'测试集AUC':>10}")
print("-" * 38)

best_auc = 0
best_model_name = ""

for name, model in best_models.items():
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"{name:<25} {auc:>10.4f}")
    if auc > best_auc:
        best_auc = auc
        best_model_name = name

print(f"\n🏆 最佳模型: {best_model_name} (AUC: {best_auc:.4f})")

# 详细分类报告
print(f"\n{'='*70}")
print(f"最佳模型详细评估: {best_model_name}")
print(f"{'='*70}")

best_model = best_models[best_model_name]
y_pred = best_model.predict(X_test)

print("\n分类报告:")
print(classification_report(y_test, y_pred, target_names=['未流失', '流失']))

print("混淆矩阵:")
cm = confusion_matrix(y_test, y_pred)
print(f"  预测未流失  预测流失")
print(f"实际未流失  {cm[0, 0]:>6}  {cm[0, 1]:>6}")
print(f"实际流失    {cm[1, 0]:>6}  {cm[1, 1]:>6}")

# ============================================================
# 9. 特征重要性（适用于树模型）
# ============================================================
print("\n" + "=" * 70)
print("9. 特征重要性分析")
print("=" * 70)

if best_model_name in ['Random Forest', 'Gradient Boosting']:
    # 获取预处理后的特征名
    feature_names = (numeric_features +
                     list(best_model.named_steps['preprocessor']
                          .named_transformers_['cat']
                          .named_steps['onehot']
                          .get_feature_names_out(categorical_features)))

    # 获取特征重要性
    importances = best_model.named_steps['classifier'].feature_importances_

    # 排序并显示
    indices = np.argsort(importances)[::-1]
    print(f"\nTop 10 重要特征:")
    for i in range(min(10, len(indices))):
        print(f"  {i+1}. {feature_names[indices[i]]}: {importances[indices[i]]:.4f}")

# ============================================================
# 10. 模型保存与加载
# ============================================================
print("\n" + "=" * 70)
print("10. 模型保存与加载")
print("=" * 70)

# 保存最佳模型
model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
os.makedirs(model_dir, exist_ok=True)

model_path = os.path.join(model_dir, 'churn_model.pkl')
joblib.dump(best_model, model_path, compress=3)
print(f"模型已保存到: {model_path}")

# 获取文件大小
file_size = os.path.getsize(model_path) / 1024
print(f"文件大小: {file_size:.1f} KB")

# 加载模型
loaded_model = joblib.load(model_path)
print(f"模型已加载")

# 验证加载的模型
y_pred_loaded = loaded_model.predict(X_test)
y_pred_proba_loaded = loaded_model.predict_proba(X_test)[:, 1]

auc_loaded = roc_auc_score(y_test, y_pred_proba_loaded)
print(f"加载模型的AUC: {auc_loaded:.4f}")
print(f"预测结果一致: {np.array_equal(y_pred, y_pred_loaded)}")

# ============================================================
# 11. 模拟部署使用
# ============================================================
print("\n" + "=" * 70)
print("11. 模拟部署使用")
print("=" * 70)

# 模拟新客户数据
new_customers = pd.DataFrame({
    'age': [35, 55, 22],
    'tenure_months': [2, 48, 6],
    'monthly_charges': [89.5, 45.0, 95.0],
    'total_charges': [179.0, 2160.0, 570.0],
    'num_support_calls': [7, 1, 3],
    'num_complaints': [3, 0, 1],
    'contract_type': ['Month-to-month', 'Two year', 'Month-to-month'],
    'payment_method': ['Electronic check', 'Bank transfer', 'Credit card'],
    'internet_service': ['Fiber optic', 'DSL', 'Fiber optic'],
    'paperless_billing': [1, 0, 1],
})

print("新客户数据:")
print(new_customers.to_string(index=False))

# 预测
predictions = loaded_model.predict(new_customers)
probabilities = loaded_model.predict_proba(new_customers)[:, 1]

print("\n预测结果:")
for i in range(len(new_customers)):
    status = "⚠️  流失风险高" if predictions[i] == 1 else "✅ 流失风险低"
    print(f"  客户{i+1}: {status} (流失概率: {probabilities[i]:.2%})")

# ============================================================
# 12. 总结
# ============================================================
print("\n" + "=" * 70)
print("12. 项目总结")
print("=" * 70)

print(f"""
📊 项目概述:
  数据集: 模拟电信客户数据 ({n_samples} 样本, {X.shape[1]} 特征)
  任务: 客户流失预测（二分类）
  最佳模型: {best_model_name}
  最佳AUC: {best_auc:.4f}

🔧 Pipeline 结构:
  1. 预处理 (ColumnTransformer)
     - 数值: 缺失值填充 → 标准化
     - 类别: 缺失值填充 → 独热编码
  2. 特征工程 (可选: PCA, 特征选择)
  3. 模型训练

📁 输出文件:
  - 模型文件: {model_path}
  - 可直接加载用于生产部署

💡 关键收获:
  1. Pipeline 确保预处理步骤在交叉验证中正确执行
  2. ColumnTransformer 统一处理不同类型的特征
  3. GridSearchCV 系统化搜索最优超参数
  4. joblib 保存完整 Pipeline，包含所有预处理步骤
  5. 加载的模型可以直接对新数据进行预测
""")

print("✅ 完整 ML Pipeline 实战完成！")
print("🎯 这个流程可以应用于任何结构化数据的分类/回归任务。")
