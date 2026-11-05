# Day 086 — NLP 基础：NLTK 与 spaCy

> 📅 日期：2026-07-28 | 🏷️ Phase 6 · 实战项目 | 🤖 项目四：聊天机器人

---

## 📋 今日目标

1. 理解 NLP（自然语言处理）的核心概念与应用
2. 掌握 NLTK 库的文本处理流程（分词、词性标注、命名实体识别）
3. 掌握 spaCy 库的工业级 NLP pipeline
4. 对比 NLTK vs spaCy 的差异与适用场景
5. 为聊天机器人项目奠定 NLP 基础

---

## 1. NLP 核心概念

### 1.1 什么是 NLP？

**NLP（Natural Language Processing，自然语言处理）** 是人工智能的一个分支，专注于让计算机理解、解释和生成人类语言。

```
人类语言 ──────────────────────────────────────> 机器理解
 "今天天气真好"  ──> [分词] ──> [标注] ──> [语义] ──> {intent: "天气查询", sentiment: "positive"}
```

### 1.2 NLP 的核心任务

| 任务 | 说明 | 示例 |
|------|------|------|
| **分词 (Tokenization)** | 将文本切分成词/子词 | `"我爱Python"` → `["我", "爱", "Python"]` |
| **词性标注 (POS Tagging)** | 标记每个词的词性 | `"我爱Python"` → `[代词, 动词, 名词]` |
| **命名实体识别 (NER)** | 识别人名、地名、组织等 | `"北京故宫"` → `[地名, 地名]` |
| **句法分析 (Parsing)** | 分析句子结构 | 主语-谓语-宾语关系 |
| **情感分析 (Sentiment)** | 判断文本情感倾向 | `"太棒了!"` → positive |
| **文本分类 (Classification)** | 将文本归入预定义类别 | 垃圾邮件检测 |

### 1.3 为什么聊天机器人需要 NLP？

```
用户输入: "帮我查一下明天北京的天气"
         ↓
┌─────────────────────────────┐
│  NLP Pipeline              │
│  ├─ 分词: [帮, 我, 查, ...] │
│  ├─ NER: 北京 → 地点        │
│  ├─ 意图识别: 天气查询       │
│  └─ 时间提取: 明天           │
└─────────────────────────────┘
         ↓
结构化指令: {intent: "weather", location: "北京", date: "明天"}
```

---

## 2. NLTK：学术级 NLP 工具包

### 2.1 NLTK 简介

**NLTK（Natural Language Toolkit）** 是 Python 最经典的 NLP 库，由宾夕法尼亚大学开发。特点是教学友好、资源丰富，适合学习 NLP 基础概念。

```python
# 安装与数据下载
# pip install nltk
import nltk
nltk.download('punkt')          # 分词模型
nltk.download('averaged_perceptron_tagger')  # 词性标注
nltk.download('maxent_ne_chunker')  # 命名实体识别
nltk.download('words')          # 英语词典
nltk.download('stopwords')      # 停用词
nltk.download('wordnet')        # 词汇语义网络
```

### 2.2 文本分词（Tokenization）

分词是 NLP 的第一步。不同语言的分词策略差异很大。

```python
from nltk.tokenize import word_tokenize, sent_tokenize

text = "Dr. Smith said: 'NLP is amazing!' Isn't it? Yes, it is."

# 句子分词
sentences = sent_tokenize(text)
# ["Dr. Smith said: 'NLP is amazing!'", "Isn't it?", "Yes, it is."]

# 词级分词
words = word_tokenize(text)
# ['Dr.', 'Smith', 'said', ':', "'NLP", 'is', 'amazing', '!', "'", "Isn't", 'it', '?', ...]
```

**中文分词注意：** NLTK 原生不支持中文分词，中文需要使用 `jieba` 或 `pkuseg`。

```python
import jieba

text = "我爱自然语言处理"
words = list(jieba.cut(text))
# ['我', '爱', '自然语言处理'] 或 ['我', '爱', '自然', '语言', '处理']
```

### 2.3 词性标注（POS Tagging）

词性标注为每个词分配语法角色（名词、动词、形容词等）。

```python
from nltk import pos_tag

words = word_tokenize("The quick brown fox jumps over the lazy dog")
tags = pos_tag(words)
# [('The', 'DT'), ('quick', 'JJ'), ('brown', 'NN'), ('fox', 'NN'), 
#  ('jumps', 'VBZ'), ('over', 'IN'), ('the', 'DT'), ('lazy', 'JJ'), ('dog', 'NN')]
```

**常用 POS 标签速查：**

| 标签 | 含义 | 示例 |
|------|------|------|
| `NN` | 名词（单数） | dog, cat |
| `NNS` | 名词（复数） | dogs, cats |
| `VB` | 动词（原形） | run, eat |
| `VBZ` | 动词（第三人称单数） | runs, eats |
| `VBD` | 动词（过去式） | ran, ate |
| `JJ` | 形容词 | quick, lazy |
| `RB` | 副词 | quickly |
| `DT` | 限定词 | the, a |
| `IN` | 介词 | in, on, over |

### 2.4 停用词过滤

停用词（Stop Words）是语言中高频但信息量低的词（如 "the", "is", "a"）。

```python
from nltk.corpus import stopwords

stop_words = set(stopwords.words('english'))
words = word_tokenize("The quick brown fox jumps over the lazy dog")
filtered = [w for w in words if w.lower() not in stop_words]
# ['quick', 'brown', 'fox', 'jumps', 'lazy', 'dog']
```

### 2.5 词干提取与词形还原

**词干提取（Stemming）：** 粗暴地截断词尾，速度快但可能产生非词。
**词形还原（Lemmatization）：** 基于词典还原到标准形式，准确但较慢。

```python
from nltk.stem import PorterStemmer, WordNetLemmatizer

stemmer = PorterStemmer()
lemmatizer = WordNetLemmatizer()

words = ["running", "flies", "better", "studies"]

# 词干提取
stems = [stemmer.stem(w) for w in words]
# ['run', 'fli', 'better', 'studi']

# 词形还原
lemmas = [lemmatizer.lemmatize(w) for w in words]
# ['running', 'fly', 'better', 'study']  （需指定 POS 效果更好）
```

### 2.6 命名实体识别（NER）

NER 识别人名、地名、组织名、日期等专有名词。

```python
from nltk import ne_chunk

text = "Barack Obama was born in Hawaii and worked at the White House"
words = word_tokenize(text)
tags = pos_tag(words)
tree = ne_chunk(tags)

# 遍历提取实体
for subtree in tree:
    if hasattr(subtree, 'label'):
        entity = ' '.join([word for word, tag in subtree.leaves()])
        print(f"{subtree.label()}: {entity}")
# PERSON: Barack Obama
# GPE: Hawaii
# ORGANIZATION: White House
```

---

## 3. spaCy：工业级 NLP Pipeline

### 3.1 spaCy 简介

**spaCy** 是为生产环境设计的 NLP 库。特点是速度快、准确率高、API 简洁。

```python
# 安装与模型下载
# pip install spacy
# python -m spacy download en_core_web_sm   # 英文小模型
# python -m spacy download zh_core_web_sm   # 中文小模型

import spacy
nlp = spacy.load("en_core_web_sm")  # 加载英文模型
```

### 3.2 一键完成全流程

spaCy 最大的优势：一行代码完成分词、POS、NER 等全部处理。

```python
import spacy

nlp = spacy.load("en_core_web_sm")
doc = nlp("Apple is looking at buying U.K. startup for $1 billion")

# 分词
tokens = [token.text for token in doc]
# ['Apple', 'is', 'looking', 'at', 'buying', 'U.K.', 'startup', 'for', '$', '1', 'billion']

# 词性标注
pos = [(token.text, token.pos_) for token in doc]
# [('Apple', 'PROPN'), ('is', 'AUX'), ('looking', 'VERB'), ...]

# 依存句法分析
deps = [(token.text, token.dep_, token.head.text) for token in doc]
# [('Apple', 'nsubj', 'looking'), ('is', 'aux', 'looking'), ...]

# 命名实体识别
ents = [(ent.text, ent.label_) for ent in doc.ents]
# [('Apple', 'ORG'), ('U.K.', 'GPE'), ('$1 billion', 'MONEY')]
```

### 3.3 Token 对象详解

spaCy 的每个 Token 对象都包含丰富信息：

```python
doc = nlp("Apple is looking at buying a startup")
token = doc[0]  # "Apple"

token.text      # "Apple"      - 原始文本
token.lemma_    # "apple"      - 词形还原
token.pos_      # "PROPN"      - 粗粒度词性
token.tag_      # "NNP"        - 细粒度词性
token.dep_      # "nsubj"      - 依存关系
token.morph     # Number=Sing   - 形态特征
token.is_stop   # False         - 是否停用词
token.is_alpha  # True          - 是否纯字母
token.is_punct  # False         - 是否标点
```

### 3.4 文本相似度

spaCy 内置基于词向量的相似度计算：

```python
nlp = spacy.load("en_core_web_md")  # 需要中/大模型

doc1 = nlp("I love cats")
doc2 = nlp("I adore felines")
doc3 = nlp("I hate dogs")

print(doc1.similarity(doc2))  # 0.75 (高相似度)
print(doc1.similarity(doc3))  # 0.32 (低相似度)
```

### 3.5 自定义 NER

训练自己的命名实体识别器：

```python
from spacy.training import Example
import spacy

# 准备训练数据
TRAIN_DATA = [
    ("华为发布新手机", {"entities": [(0, 2, "ORG"), (4, 8, "PRODUCT")]}),
    ("我在北京工作", {"entities": [(2, 4, "LOC")]}),
]

nlp = spacy.blank("zh")  # 创建空白中文模型
ner = nlp.add_pipe("ner")
ner.add_label("ORG")
ner.add_label("PRODUCT")
ner.add_label("LOC")

# 训练循环（简化版）
optimizer = nlp.begin_training()
for i in range(20):
    for text, annotations in TRAIN_DATA:
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, annotations)
        nlp.update([example], sgd=optimizer)
```

---

## 4. NLTK vs spaCy 对比

| 特性 | NLTK | spaCy |
|------|------|-------|
| **定位** | 学术/教学 | 生产/工业 |
| **速度** | 较慢 | 快（Cython 优化） |
| **API 设计** | 模块化、灵活 | 统一、简洁 |
| **模型大小** | 资源文件丰富 | 预训练模型打包 |
| **中文支持** | 需额外工具 | 有中文模型 |
| **社区活跃度** | 成熟但缓慢 | 活跃、更新快 |
| **适合场景** | 学习原理、原型开发 | 生产部署、大规模处理 |

**选择建议：**
- 🎓 学习 NLP 概念 → NLTK
- 🏭 生产环境部署 → spaCy
- 🔬 研究实验 → 两者结合使用

---

## 5. 实战：聊天机器人意图识别

```python
"""
聊天机器人意图识别模块
使用 spaCy 进行基本的意图分类和实体提取
"""
import spacy

class IntentRecognizer:
    """基于规则的意图识别器"""
    
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        # 意图关键词映射
        self.intent_keywords = {
            "greeting": ["hello", "hi", "hey", "good morning"],
            "weather": ["weather", "temperature", "rain", "sunny"],
            "time": ["time", "clock", "hour", "minute"],
            "goodbye": ["bye", "goodbye", "see you"],
        }
    
    def recognize(self, text: str) -> dict:
        """识别用户输入的意图和实体"""
        doc = self.nlp(text.lower())
        
        # 提取实体
        entities = {}
        for ent in doc.ents:
            entities[ent.label_] = ent.text
        
        # 匹配意图
        intent = "unknown"
        tokens = set([token.text for token in doc])
        
        for intent_name, keywords in self.intent_keywords.items():
            if tokens & set(keywords):
                intent = intent_name
                break
        
        return {
            "intent": intent,
            "entities": entities,
            "tokens": [token.text for token in doc]
        }

# 使用示例
recognizer = IntentRecognizer()
tests = [
    "Hello, how are you?",
    "What's the weather in Beijing?",
    "What time is it?",
    "Goodbye!",
]
for text in tests:
    result = recognizer.recognize(text)
    print(f"Input: {text}")
    print(f"  → Intent: {result['intent']}, Entities: {result['entities']}")
    print()
```

---

## 6. 常见陷阱与避坑

### 陷阱 1：中文分词用错工具

```python
# ❌ 错误：用 NLTK 分中文
from nltk.tokenize import word_tokenize
word_tokenize("我爱Python")  # 可能报错或分词不准

# ✅ 正确：用 jieba 分中文
import jieba
list(jieba.cut("我爱Python"))  # ['我', '爱', 'Python']
```

### 陷阱 2：spaCy 模型未下载

```python
# ❌ 会报 OSError: [E050]
nlp = spacy.load("en_core_web_sm")

# ✅ 先下载模型
# python -m spacy download en_core_web_sm
```

### 陷阱 3：忽略大小写

```python
# ❌ 大小写敏感导致漏匹配
if "hello" in text:  # "Hello" 匹配不到

# ✅ 统一转小写
if "hello" in text.lower():
```

### 陷阱 4：词干提取 vs 词形还原混淆

```python
# ❌ 词干提取可能产生非词
stemmer.stem("better")  # "better" (没变，有时会变成 "bett")

# ✅ 词形还原更准确
lemmatizer.lemmatize("better", pos='a')  # "good"
```

---

## 7. 思考题

1. **为什么聊天机器人需要先做意图识别，再做实体提取？** 如果反过来会怎样？
2. **spaCy 的依存句法分析对聊天机器人有什么实际价值？** 举一个具体应用场景。
3. **如果要构建一个中文聊天机器人，你会如何组合 jieba + spaCy？** 需要注意哪些兼容性问题？
4. **NLTK 的 `ne_chunk` 和 spaCy 的 NER 各有什么优缺点？** 在什么场景下你会选择其中一个？
5. **情感分析在客服聊天机器人中可以如何应用？** 除了判断正负面，还能做什么？

---

## 📚 扩展阅读

- [spaCy 官方文档](https://spacy.io/usage)
- [NLTK 官方文档](https://www.nltk.org/)
- [spaCy 中文模型](https://spacy.io/models/zh)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/) — 下一步：BERT/GPT 级别 NLP

---

> ⏭️ **明天预告：Day 087 — 状态机对话管理**
