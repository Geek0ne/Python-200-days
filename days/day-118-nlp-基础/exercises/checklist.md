# Day 118 — NLP 基础 练习清单

## ✅ 学习检查表

- [ ] 理解中文分词的必要性（对比英文）
- [ ] 掌握 jieba 的三种分词模式（精确/全/搜索引擎）
- [ ] 能够添加自定义词典解决分词问题
- [ ] 理解 TF-IDF 的计算原理（TF × IDF）
- [ ] 能用 sklearn 的 TfidfVectorizer 进行文本向量化
- [ ] 理解 Word Embedding 的核心思想
- [ ] 能搭建完整的文本分类流水线
- [ ] 能分析模型的特征词（可解释性）

---

## 📝 基础练习题

### 练习 1：分词对比（⭐）

使用 jieba 对以下句子分别用精确模式、全模式、搜索引擎模式进行分词，对比结果：

```
"南京市长江大桥"
"我们在北京野生动物园"
"乒乓球拍卖完了"
```

**思考：** 为什么同一句话会有不同的分词结果？哪种模式更适合搜索场景？

---

### 练习 2：TF-IDF 手算（⭐⭐）

给定以下 3 篇文档：

| 文档 | 内容 |
|------|------|
| D1 | Python 是解释型语言 |
| D2 | Python 用于数据分析和机器学习 |
| D3 | Java 是编译型语言 |

计算 "Python" 在 D1 中的 TF-IDF 值（手算，写出计算过程）。

---

### 练习 3：分类器调参（⭐⭐）

修改 `03-text-classification.py`，尝试以下参数组合：

1. 调整 `TfidfVectorizer` 的 `max_features` 为 100、500、1000、5000
2. 调整 `ngram_range` 为 (1,1)、(1,2)、(1,3)
3. 比较不同参数下的准确率

记录结果并分析哪种配置最优。

---

## 🚀 进阶挑战题

### 挑战 1：情感分析器（⭐⭐⭐）

基于今天学到的 TF-IDF + 分类器方法，构建一个**中文情感分类器**：

1. 收集或构造正负情感各 20+ 条文本数据
2. 预处理 + TF-IDF 特征提取
3. 训练逻辑回归分类器
4. 测试新句子的情感分类

**数据示例：**
```
正面: "这部电影太精彩了，强烈推荐！"
正面: "服务态度很好，下次还来"
负面: "产品质量太差了，很失望"
负面: "等了两小时才上菜，体验极差"
```

---

### 挑战 2：关键词提取（⭐⭐⭐）

使用 TF-IDF 实现一个**关键词提取函数**：

1. 输入一段中文文本
2. 分词 + 去停用词
3. 计算 TF-IDF
4. 返回 Top-5 关键词及其权重

**扩展：** 对比 TF-IDF 关键词提取与 jieba 内置的 `jieba.analyse.extract_tags()` 的结果差异。

---

### 挑战 3：文本聚类（⭐⭐⭐⭐）

不使用标签数据，用**无监督方法**对新闻文本进行聚类：

1. 将文本转换为 TF-IDF 向量
2. 使用 KMeans 或 DBSCAN 进行聚类
3. 评估聚类效果（纯度或轮廓系数）
4. 分析每个聚类的主题特征

**提示：** 使用 `sklearn.cluster.KMeans` 和 `sklearn.metrics.silhouette_score`。

---

## 📚 参考资源

- [jieba GitHub](https://github.com/fxsjy/jieba)
- [scikit-learn TF-IDF 文档](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- [Word2Vec 原论文](https://arxiv.org/abs/1301.3781)
- [中文 NLP 常用数据集](https://github.com/aceimnorstuvwxz/Chinese-NLP-Corpus)
