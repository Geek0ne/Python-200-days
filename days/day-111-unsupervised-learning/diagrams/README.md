# Day 111 图解 — K-Means 聚类与 PCA 降维

## 1. K-Means 算法流程图

```mermaid
flowchart TD
    A[开始] --> B[输入数据 X 和簇数 K]
    B --> C[随机初始化 K 个簇中心]
    C --> D{迭代开始}
    D --> E[步骤1: 分配<br/>计算每个点到各中心的距离<br/>分配到最近的簇]
    E --> F[步骤2: 更新<br/>重新计算每个簇的中心]
    F --> G{中心是否变化?}
    G -- 是 --> D
    G -- 否 --> H[输出聚类结果]
    H --> I[结束]
    
    style A fill:#e1f5fe
    style I fill:#e1f5fe
    style D fill:#fff3e0
    style G fill:#fff3e0
```

## 2. K-Means 迭代过程图解

```mermaid
flowchart LR
    subgraph 初始状态
        A1[随机3个中心] --> A2[未分组数据]
    end
    
    subgraph 第1次迭代
        B1[计算距离] --> B2[分配到最近中心]
        B2 --> B3[更新中心位置]
    end
    
    subgraph 第2次迭代
        C1[重新计算距离] --> C2[重新分配]
        C2 --> C3[再次更新中心]
    end
    
    subgraph 收敛
        D1[中心不再变化] --> D2[输出最终聚类]
    end
    
    A2 --> B1
    B3 --> C1
    C3 --> D1
    
    style A1 fill:#bbdefb
    style A2 fill:#bbdefb
    style B1 fill:#c8e6c9
    style B2 fill:#c8e6c9
    style B3 fill:#c8e6c9
    style C1 fill:#ffe0b2
    style C2 fill:#ffe0b2
    style C3 fill:#ffe0b2
    style D1 fill:#f8bbd0
    style D2 fill:#f8bbd0
```

## 3. PCA 降维原理图

```mermaid
flowchart TD
    A[原始高维数据 X<br/>n × d] --> B[步骤1: 中心化<br/>减去均值]
    B --> C[步骤2: 计算协方差矩阵<br/>C = X^T X / (n-1)]
    C --> D[步骤3: 特征值分解<br/>C v_i = λ_i v_i]
    D --> E[步骤4: 选择主成分<br/>按特征值从大到小排列]
    E --> F[步骤5: 投影<br/>Z = X W_d]
    F --> G[输出低维数据 Z<br/>n × d', 其中 d' < d]
    
    style A fill:#e1f5fe
    style G fill:#c8e6c9
    style D fill:#fff3e0
```

## 4. PCA 方差解释比例图

```mermaid
xychart-beta
    title "PCA 方差解释比例"
    x-axis "主成分" ["PC1", "PC2", "PC3", "PC4"]
    y-axis "方差解释比例" 0 --> 1
    bar [0.72, 0.18, 0.07, 0.03]
    line [0.72, 0.90, 0.97, 1.00]
```

## 5. 肘部法则示意图

```mermaid
xychart-beta
    title "肘部法则 - WCSS vs K值"
    x-axis "K值" [2, 3, 4, 5, 6, 7, 8, 9, 10]
    y-axis "WCSS" 0 --> 2000
    line [1800, 1200, 850, 820, 790, 770, 750, 740, 730]
```

## 6. 客户分群完整流程图

```mermaid
flowchart TD
    A[客户数据] --> B[数据清洗与预处理]
    B --> C[特征标准化]
    C --> D[探索性数据分析 EDA]
    D --> E{是否需要降维?}
    E -- 是 --> F[PCA 降维]
    E -- 否 --> G[直接聚类]
    F --> H[选择主成分数量]
    H --> G
    G --> I[肘部法则选择 K]
    I --> J[训练 K-Means 模型]
    J --> K[评估聚类质量]
    K --> L{质量是否满意?}
    L -- 否 --> I
    L -- 是 --> M[客户群分析]
    M --> N[制定营销策略]
    N --> O[输出分析报告]
    
    style A fill:#e1f5fe
    style O fill:#c8e6c9
    style I fill:#fff3e0
    style L fill:#fff3e0
```

## 7. K-Means vs 其他聚类算法对比

```mermaid
flowchart LR
    A[聚类算法选择] --> B{数据形状?}
    B -- 球形簇 --> C[K-Means]
    B -- 任意形状 --> D[DBSCAN]
    B -- 层次结构 --> E[层次聚类]
    B -- 高斯混合 --> F[GMM]
    
    C --> G[优点: 快速、简单<br/>缺点: 需指定K, 对噪声敏感]
    D --> H[优点: 发现任意形状<br/>缺点: 参数敏感]
    E --> I[优点: 可视化层次<br/>缺点: 计算复杂]
    F --> J[优点: 概率解释<br/>缺点: 计算复杂]
    
    style C fill:#c8e6c9
    style D fill:#fff3e0
    style E fill:#e1f5fe
    style F fill:#f8bbd0
```

## 8. PCA 降维可视化效果

```mermaid
flowchart TD
    A[原始4D数据<br/>花萼长度, 花萼宽度<br/>花瓣长度, 花瓣宽度] --> B[PCA 降维到 2D]
    B --> C[可视化结果<br/>可以看到3类明显分离]
    
    A --> D[保留特征信息 95%]
    D --> E[第一主成分: 花瓣长度为主]
    D --> F[第二主成分: 花萼宽度为主]
    
    style A fill:#e1f5fe
    style C fill:#c8e6c9
    style E fill:#fff3e0
    style F fill:#fff3e0
```

## 9. 无监督学习应用场景

```mermaid
mindmap
  root((无监督学习))
    聚类
      客户分群
      图像分割
      文档聚类
      基因表达分析
    降维
      特征提取
      数据压缩
      可视化
      噪声去除
    异常检测
      欺诈检测
      网络入侵检测
      设备故障预测
    关联规则
      购物篮分析
      推荐系统
      序列模式挖掘
```

## 10. 评估指标对比

```mermaid
flowchart TD
    A[聚类评估] --> B[内部指标<br/>无需真实标签]
    A --> C[外部指标<br/>需要真实标签]
    
    B --> B1[轮廓系数<br/>范围: -1 到 1<br/>越大越好]
    B --> B2[Calinski-Harabasz<br/>方差比准则<br/>越大越好]
    B --> B3[Davies-Bouldin<br/>簇间相似度<br/>越小越好]
    B --> B4[WCSS/Inertia<br/>簇内平方和<br/>越小越好]
    
    C --> C1[调整兰德指数<br/>范围: -1 到 1<br/>越大越好]
    C --> C2[互信息<br/>范围: 0 到 1<br/>越大越好]
    C --> C3[同质性<br/>范围: 0 到 1<br/>越大越好]
    
    style B fill:#e1f5fe
    style C fill:#c8e6c9
    style B1 fill:#bbdefb
    style B2 fill:#bbdefb
    style B3 fill:#bbdefb
    style B4 fill:#bbdefb
    style C1 fill:#a5d6a7
    style C2 fill:#a5d6a7
    style C3 fill:#a5d6a7
```
