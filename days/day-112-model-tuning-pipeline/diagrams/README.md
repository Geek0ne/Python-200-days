# Day 112 — 图解：模型调优与 Pipeline

> 使用 Mermaid 图解核心概念，帮助理解数据流动和算法流程

---

## 1. K-Fold 交叉验证数据划分

```mermaid
flowchart TB
    subgraph 数据集
        D["完整数据集 (500 样本)"]
    end

    subgraph "K=5 划分"
        F1["Fold 1\n100 样本"]
        F2["Fold 2\n100 样本"]
        F3["Fold 3\n100 样本"]
        F4["Fold 4\n100 样本"]
        F5["Fold 5\n100 样本"]
    end

    subgraph "交叉验证过程"
        R1["轮次1: 验证=Fold1\n训练=Fold2,3,4,5\n得分: 0.92"]
        R2["轮次2: 验证=Fold2\n训练=Fold1,3,4,5\n得分: 0.89"]
        R3["轮次3: 验证=Fold3\n训练=Fold1,2,4,5\n得分: 0.91"]
        R4["轮次4: 验证=Fold4\n训练=Fold1,2,3,5\n得分: 0.90"]
        R5["轮次5: 验证=Fold5\n训练=Fold1,2,3,4\n得分: 0.93"]
    end

    subgraph "最终结果"
        AVG["平均得分\n(0.92+0.89+0.91+0.90+0.93)/5\n= 0.91 ± 0.03"]
    end

    D --> F1 & F2 & F3 & F4 & F5
    F1 --> R1
    F2 --> R2
    F3 --> R3
    F4 --> R4
    F5 --> R5
    R1 & R2 & R3 & R4 & R5 --> AVG

    style D fill:#e1f5fe
    style AVG fill:#c8e6c9
```

---

## 2. Stratified K-Fold vs 普通 K-Fold

```mermaid
flowchart LR
    subgraph 原始数据分布
        O["总数据: 正类30%\n负类70%"]
    end

    subgraph "普通 K-Fold (可能不均匀)"
        KF1["Fold1: 正类40%\n负类60%"]
        KF2["Fold2: 正类20%\n负类80%"]
        KF3["Fold3: 正类30%\n负类70%"]
    end

    subgraph "Stratified K-Fold (保持比例)"
        SF1["Fold1: 正类30%\n负类70%"]
        SF2["Fold2: 正类30%\n负类70%"]
        SF3["Fold3: 正类30%\n负类70%"]
    end

    O --> KF1 & KF2 & KF3
    O --> SF1 & SF2 & SF3

    style O fill:#fff3e0
    style SF1 fill:#c8e6c9
    style SF2 fill:#c8e6c9
    style SF3 fill:#c8e6c9
```

---

## 3. GridSearchCV 搜索过程

```mermaid
flowchart TB
    subgraph "搜索空间"
        P1["C = [0.1, 1, 10]"]
        P2["gamma = [0.01, 0.1]"]
    end

    subgraph "组合生成 (3×2=6种)"
        C1["C=0.1, γ=0.01"]
        C2["C=0.1, γ=0.1"]
        C3["C=1, γ=0.01"]
        C4["C=1, γ=0.1"]
        C5["C=10, γ=0.01"]
        C6["C=10, γ=0.1"]
    end

    subgraph "交叉验证评估"
        CV1["组合1: 5折CV\n平均AUC=0.85"]
        CV2["组合2: 5折CV\n平均AUC=0.88"]
        CV3["组合3: 5折CV\n平均AUC=0.91"]
        CV4["组合4: 5折CV\n平均AUC=0.90"]
        CV5["组合5: 5折CV\n平均AUC=0.89"]
        CV6["组合6: 5折CV\n平均AUC=0.87"]
    end

    subgraph "结果"
        BEST["🏆 最佳: C=1, γ=0.01\nAUC=0.91"]
    end

    P1 & P2 --> C1 & C2 & C3 & C4 & C5 & C6
    C1 --> CV1
    C2 --> CV2
    C3 --> CV3
    C4 --> CV4
    C5 --> CV5
    C6 --> CV6
    CV1 & CV2 & CV3 & CV4 & CV5 & CV6 --> BEST

    style BEST fill:#ffeb3b
```

---

## 4. Pipeline 数据流

```mermaid
flowchart LR
    subgraph "原始数据"
        RAW["X_raw\n(含缺失值、\n不同类型特征)"]
    end

    subgraph "Pipeline 步骤"
        S1["步骤1: 预处理器\n(ColumnTransformer)"]
        S2["步骤2: 特征工程\n(PCA/特征选择)"]
        S3["步骤3: 模型\n(分类器)"]
    end

    subgraph "数据变化"
        D1["X_imputed\n(缺失值已填充)"]
        D2["X_scaled\n(数值已标准化)"]
        D3["X_encoded\n(类别已编码)"]
        D4["X_combined\n(所有特征合并)"]
        D5["X_reduced\n(降维后特征)"]
        D6["y_pred\n(预测结果)"]
    end

    RAW -->|"fit_transform / transform"| S1
    S1 -->|"输出"| D1
    D1 --> D2 --> D3 --> D4
    D4 -->|"fit_transform / transform"| S2
    S2 -->|"输出"| D5
    D5 -->|"fit / predict"| S3
    S3 -->|"输出"| D6

    style RAW fill:#e1f5fe
    style D6 fill:#c8e6c9
```

---

## 5. 完整 ML Pipeline 工作流

```mermaid
flowchart TB
    subgraph "1. 数据准备"
        A1["加载数据"]
        A2["探索性分析"]
        A3["划分训练/测试集"]
    end

    subgraph "2. 构建 Pipeline"
        B1["预处理器\n(ColumnTransformer)"]
        B2["特征工程\n(PCA/SelectKBest)"]
        B3["基础模型\n(LR/SVM/RF)"]
    end

    subgraph "3. 模型调优"
        C1["定义参数网格"]
        C2["GridSearchCV\n(交叉验证+搜索)"]
        C3["选择最佳模型"]
    end

    subgraph "4. 评估"
        D1["测试集评估"]
        D2["分类报告"]
        D3["混淆矩阵"]
        D4["ROC曲线"]
    end

    subgraph "5. 部署"
        E1["保存Pipeline\n(joblib.dump)"]
        E2["加载模型\n(joblib.load)"]
        E3["生产预测"]
    end

    A1 --> A2 --> A3
    A3 --> B1 --> B2 --> B3
    B3 --> C1 --> C2 --> C3
    C3 --> D1 --> D2 & D3 & D4
    D1 --> E1 --> E2 --> E3

    style A1 fill:#e1f5fe
    style C2 fill:#fff3e0
    style E1 fill:#c8e6c9
```

---

## 6. 数据泄露 vs 正确做法

```mermaid
flowchart TB
    subgraph "❌ 数据泄露 (错误)"
        W1["全部数据"]
        W2["scaler.fit_transform(全部)"]
        W3["划分训练/测试"]
        W4["模型训练"]
        W5["⚠️ 测试集信息已泄露到训练集!"]
    end

    subgraph "✅ 正确做法"
        R1["全部数据"]
        R2["划分训练/测试集"]
        R3["scaler.fit_transform(训练集)"]
        R4["scaler.transform(测试集)"]
        R5["模型训练 & 评估"]
    end

    subgraph "✅ Pipeline 做法 (最佳)"
        P1["Pipeline.fit(训练集)"]
        P2["Pipeline.predict(测试集)"]
        P3["✅ 自动防止数据泄露"]
    end

    W1 --> W2 --> W3 --> W4 --> W5
    R1 --> R2 --> R3 --> R4 --> R5
    P1 --> P2 --> P3

    style W5 fill:#ffcdd2
    style R5 fill:#c8e6c9
    style P3 fill:#c8e6c9
```

---

## 7. 模型保存与加载流程

```mermaid
flowchart LR
    subgraph "训练阶段"
        T1["加载数据"]
        T2["构建Pipeline"]
        T3["训练模型\npipeline.fit()"]
        T4["joblib.dump()\n保存到文件"]
    end

    subgraph "部署阶段"
        D1["joblib.load()\n加载模型"]
        D2["接收新数据"]
        D3["pipeline.predict()\n直接预测"]
        D4["返回结果"]
    end

    T1 --> T2 --> T3 --> T4
    T4 -.->|"model.pkl"| D1
    D1 --> D2 --> D3 --> D4

    style T4 fill:#fff3e0
    style D1 fill:#e1f5fe
```

---

## 📝 图解说明

以上 Mermaid 图解覆盖了 Day 112 的核心概念：

1. **K-Fold 交叉验证** — 数据如何被划分和重复使用
2. **Stratified vs 普通 K-Fold** — 类别比例保持的重要性
3. **GridSearchCV** — 超参数搜索的穷举过程
4. **Pipeline 数据流** — 数据在各步骤中的变化
5. **完整 ML 工作流** — 从数据到部署的全流程
6. **数据泄露** — 正确 vs 错误的做法对比
7. **模型持久化** — 训练与部署的衔接

> 💡 可以将这些代码复制到 [Mermaid Live Editor](https://mermaid.live/) 中查看可视化效果。
