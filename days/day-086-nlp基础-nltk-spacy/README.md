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

**参考答案**

因为**意图决定了「需要哪些实体」**。先知道用户想干什么（订机票 / 查天气 / 查订单），才知道该提取什么信息：订机票关心「出发地、目的地、日期」，查天气关心「城市、日期」。意图是「框架」，实体是往框架里填的「值」，所以逻辑上先定框架再填值。

如果反过来——先盲目提取所有实体再判断意图，会有几个问题：

- **做无用功**：把句子里所有人名、地名、时间都抽出来，但当前意图可能根本用不到其中大部分，浪费算力。
- **角色无法归位**：同一个实体在不同意图下含义不同。「北京」在订机票里可能是出发地或目的地，在查天气里只是查询城市；没有意图作上下文，就不知道该把它放进哪个槽位。
- **可能被无关实体误导**：一堆噪声实体反而干扰意图判断。

- 小例子：「帮我订明天去北京的机票」→ 先识别意图＝订机票 → 才知道要填 `date=明天`、`destination=北京`。若先做 NER 只得到「明天(DATE)、北京(GPE)」，仍不知道北京是出发还是目的。

💡 提示：实际系统常是「迭代式」的——先粗判意图、按意图提取槽位，若发现槽位冲突再回头修正意图。但「意图优先」这个主线不变，Day 087 的槽位填充正是它的体现。
2. **spaCy 的依存句法分析对聊天机器人有什么实际价值？** 举一个具体应用场景。

**参考答案**

依存句法分析（dependency parsing）会标出每个词的**中心词（head）**和**语法关系（dep）**，比如「谁是谁的主语 / 宾语 / 修饰语」。它的价值在于让机器人从「关键词匹配」升级到「理解句子结构」，搞清楚**谁对谁做了什么**，从而正确处理否定、修改、并列等复杂表达。

一个具体场景——**改签指令的槽位定位**：

用户说「把北京到上海的机票改成后天」。关键词匹配只能看到「北京、上海、后天」几个词，却不知道该怎么组合。依存分析能看出：谓语是「改」，「机票」是它的宾语，「北京到上海」是修饰机票的定语，「后天」是新的日期补语。于是机器人准确地知道：要修改的是「北京→上海」这张机票的 `date` 槽位，新值为「后天」，而不是新建一个订单。

其他常见价值：

- **否定识别**：「我不想去北京」中 `neg`（否定）关系修饰「去」，避免把「北京」误当成目的地。
- **并列拆分**：「订机票并且查天气」通过并列关系拆成两个意图。
- **疑问/焦点**：判断用户问的是时间、地点还是价格。

- 小例子：spaCy 里 `token.dep_` 给出 `nsubj`（名词性主语）、`dobj`（直接宾语）、`neg`（否定）等标签，`token.head` 指向中心词，组合起来就是句子的「骨架」。
3. **如果要构建一个中文聊天机器人，你会如何组合 jieba + spaCy？** 需要注意哪些兼容性问题？

**参考答案**

分工思路：**jieba 负责中文分词**（spaCy 中文模型的分词可控性较弱），**spaCy 负责后续 pipeline**（词性、NER、依存）并提供统一的 `Doc` 接口。常见组合方式有三种：

- **方案 A（最省事）**：直接用 spaCy 中文模型 `zh_core_web_sm`，它内部已集成分词，`nlp(text)` 一步到位。缺点是分词粒度不好干预。
- **方案 B（更可控）**：自定义 spaCy 的 tokenizer，把 `jieba.cut` 接到 pipeline 最前面的分词阶段，后面仍用 spaCy 的 POS/NER。需要写一个 Tokenizer 适配函数。
- **方案 C（混合）**：jieba 分词 + `jieba.posseg` 词性 + 规则/自定义 NER，spaCy 只用于英文或相似度计算。

需要特别注意的兼容性问题：

- **分词粒度不一致**：jieba 与 spaCy 中文模型切分不同，导致实体的字符偏移 `(start, end)` 对不上。NER 标注必须基于**实际 token 边界**。
- **字符偏移守恒**：spaCy 的 `Doc` 要求「所有 token 拼起来 == 原文（含空白）」。自定义分词时若丢了空格或字符，实体 span 就会错位。
- **词性标签体系不同**：jieba 用 ICTCLAS 标签（`n`/`v`/`ns`），spaCy 用 Universal POS（`NOUN`/`VERB`/`PROPN`），混用要做映射。
- **依赖与模型下载**：`pip install jieba`；`python -m spacy download zh_core_web_sm`。jieba 首次加载词典较慢，spaCy 中文模型体积较大。

- 小例子：「我爱自然语言处理」用 jieba 可能切成 `["我","爱","自然语言处理"]`，而 spaCy 中文模型可能切成 `["我","爱","自然","语言","处理"]`——同一个实体「自然语言处理」的 span 完全不同，标注数据不能直接通用。

⚠️ 注意：自定义 tokenizer 时务必保留原文空白映射（spaCy 用 `spaces` 标记每个 token 后是否有空格），否则 `doc.ents` 的字符区间会整体错位。
4. **NLTK 的 `ne_chunk` 和 spaCy 的 NER 各有什么优缺点？** 在什么场景下你会选择其中一个？

**参考答案**

两者定位不同：NLTK 偏**学术/教学**，spaCy 偏**工业/生产**。

**NLTK `ne_chunk`：**

- 优点：教学友好、可解释（先词性标注再基于规则/最大熵切块），能看到树结构；资源轻量，适合英文小实验。
- 缺点：准确率偏低、速度较慢；要手动串「分词 → 词性标注 → ne_chunk」三步；实体类型有限（PERSON/GPE/ORGANIZATION 等）；对中文几乎不支持。

**spaCy NER：**

- 优点：工业级、准确率高、速度快（Cython 优化）；一行 `nlp(text)` 完成全流程；预训练模型丰富（含中文）；实体类型多（DATE/MONEY/PRODUCT…）；支持微调训练，与 pipeline 无缝衔接。
- 缺点：模型体积大；内部偏「黑盒」不易解释；自定义训练需要标注数据和算力；依赖模型下载。

**怎么选**：学习原理、英文演示、资源受限 → NLTK；生产部署、中文、大规模、要高准确率 → spaCy。

- 小例子：同一句「Apple buys U.K. startup for $1 billion」，spaCy 直接给出 `ORG/GPE/MONEY`；NLTK 要走三步，且常常漏掉 `MONEY` 这类实体。

💡 提示：NLTK 新版本需要下载 `punkt_tab`、`averaged_perceptron_tagger_eng` 等数据，旧教程里的下载名（如 `punkt`、`averaged_perceptron_tagger`）在新版可能失效——这是常见的版本差异坑。
5. **情感分析在客服聊天机器人中可以如何应用？** 除了判断正负面，还能做什么？

**参考答案**

最基础的用法是判断用户情绪的正/负/中：一旦检测到负面，就优先安抚、升级工单或转人工。但情感分析在客服里能做的远不止「贴个正负标签」：

- **情绪强度分级**：区分「轻微不满」和「暴怒」，对应不同优先级与话术，避免一刀切。
- **细粒度情绪识别**：愤怒 / 焦虑 / 失望 / 满意 / 感激，针对性回应（焦虑→给确定性，愤怒→先道歉）。
- **方面级情感（aspect-based）**：同一句话里「对物流满意、对质量不满」，精准定位是哪个环节出问题。
- **实时预警与路由**：连续负面或极端情绪触发人工介入；负面情绪高的会话排队优先处理。
- **质检与满意度评估**：会话结束后自动打分，评估客服/机器人表现，统计某产品或时段的负面比例反哺改进。
- **共情回复生成**：根据情绪调整语气，让回复更有人情味。

- 小例子：用户「这什么破东西，气死我了！」→ 判定为强负面/愤怒 → 机器人先道歉安抚、把会话标记为高优先级、并主动提供「转人工」入口。

⚠️ 注意：反讽和否定（如「真是太『好』了」）极易误判，纯词典/简单模型不够，需结合上下文与更强的情感模型。

---

## 📚 扩展阅读

- [spaCy 官方文档](https://spacy.io/usage)
- [NLTK 官方文档](https://www.nltk.org/)
- [spaCy 中文模型](https://spacy.io/models/zh)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/) — 下一步：BERT/GPT 级别 NLP

---

> ⏭️ **明天预告：Day 087 — 状态机对话管理**
