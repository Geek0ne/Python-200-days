# Day 086 — NLP 基础：NLTK 与 spaCy · 练习清单

## ✅ 今日完成清单

- [ ] 理解 NLP 的核心概念与应用场景
- [ ] 掌握 NLTK 的分词、词性标注、停用词过滤
- [ ] 掌握 NLTK 的词干提取与词形还原
- [ ] 掌握 spaCy 的一键 NLP pipeline
- [ ] 理解 spaCy Token 对象的属性
- [ ] 了解 NLTK vs spaCy 的差异与选择
- [ ] 完成代码示例运行
- [ ] 完成以下练习题

---

## 📝 基础练习题

### 练习 1：中文分词对比

使用 `jieba` 对以下文本进行分词，观察不同分词模式的结果：

```python
import jieba

text = "南京市长江大桥欢迎你"
# 1. 精确模式
print(list(jieba.cut(text)))
# 2. 全模式
print(list(jieba.cut(text, cut_all=True)))
# 3. 搜索引擎模式
print(list(jieba.cut_for_search(text)))
```

**思考：** 为什么精确模式会把"南京市"和"长江大桥"分开？如果想正确分词该怎么做？

---

### 练习 2：POS 标签分析

对以下句子进行词性标注，并统计每种词性的出现次数：

```python
from nltk import pos_tag
from nltk.tokenize import word_tokenize
from collections import Counter

text = "The quick brown fox jumps over the lazy dog while the cat sleeps peacefully"
words = word_tokenize(text)
tags = pos_tag(words)

# 统计词性
pos_counts = Counter(tag for word, tag in tags)
print(pos_counts)
```

**问题：**
1. 这个句子中有多少个名词（NN/NNS）？多少个动词（VB/VBZ）？
2. `JJ` 和 `RB` 分别代表什么？各出现了几次？

---

### 练习 3：spaCy NER 提取

使用 spaCy 从以下文本中提取所有命名实体，并按类型分组：

```python
import spacy
from collections import defaultdict

nlp = spacy.load("en_core_web_sm")
text = """Elon Musk founded SpaceX in 2002. The company is headquartered in Hawthorne, California.
Tesla, another company led by Musk, is based in Austin, Texas. Musk was born in South Africa."""

doc = nlp(text)
entities_by_type = defaultdict(list)

for ent in doc.ents:
    entities_by_type[ent.label_].append(ent.text)

for label, entities in entities_by_type.items():
    print(f"{label}: {entities}")
```

**问题：** 识别出的所有 `ORG` 类型实体有哪些？`GPE` 类型呢？

---

## 🚀 进阶挑战题

### 挑战 1：情感词典构建

构建一个简单的情感词典，并计算句子的情感分数：

```python
positive_words = {"good", "great", "excellent", "amazing", "wonderful", "love", "happy"}
negative_words = {"bad", "terrible", "awful", "horrible", "hate", "sad", "angry"}

def sentiment_score(text):
    from nltk.tokenize import word_tokenize
    words = set(word_tokenize(text.lower()))
    pos = len(words & positive_words)
    neg = len(words & negative_words)
    return pos - neg  # 正数=积极, 负数=消极

# 测试
print(sentiment_score("I love this amazing product"))   # 期望: 正数
print(sentiment_score("This is terrible and horrible"))  # 期望: 负数
```

**扩展：** 如何处理否定词（如 "not good"）？如何处理程度词（如 "very good"）？

---

### 挑战 2：文本预处理 Pipeline

构建一个完整的文本预处理 pipeline，包括：小写化 → 分词 → 停用词过滤 → 词形还原：

```python
import spacy

def preprocess(text):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text.lower())
    
    tokens = [
        token.lemma_        # 词形还原
        for token in doc
        if not token.is_stop   # 过滤停用词
        and not token.is_punct  # 过滤标点
        and token.is_alpha     # 只保留字母
    ]
    return tokens

# 测试
text = "The cats are running quickly through the beautiful garden"
print(preprocess(text))
# 期望: ['cat', 'run', 'quickly', 'beautiful', 'garden']
```

---

### 挑战 3：简易关键词提取

基于 TF（词频）提取文本关键词：

```python
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from collections import Counter

def extract_keywords(text, top_n=5):
    stop_words = set(stopwords.words('english'))
    words = [
        w.lower() for w in word_tokenize(text)
        if w.isalpha() and w.lower() not in stop_words
    ]
    freq = Counter(words)
    return freq.most_common(top_n)

text = """
Python is a powerful programming language. Python is used for web development,
data science, machine learning, and automation. Many developers love Python
because Python is easy to learn and Python has a large community.
"""

print(extract_keywords(text))
# 期望: [('python', 4), ('programming', 1), ...]
```

**扩展：** 如何改进这个关键词提取算法？（提示：考虑 TF-IDF）

---

## 📊 练习检查

完成后自查：
- [ ] 能否解释 NLP 的 6 个核心任务？
- [ ] 能否用 NLTK 完成分词、POS、NER 的基本操作？
- [ ] 能否用 spaCy 一行代码完成全流程处理？
- [ ] 能否说出 NLTK 和 spaCy 的主要区别？
- [ ] 能否构建一个简单的意图识别系统？
