# Day 086 — NLP 基础 · 图解

## 1. NLP 处理流程

```
┌──────────────────────────────────────────────────────────────┐
│                    NLP 处理流程                               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  原始文本                                                     │
│  "Apple is looking at buying U.K. startup"                   │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐   │
│  │  分词    │───▶│ POS标注 │───▶│   NER   │───▶│ 依存分析│   │
│  │Tokenizer│    │  Tagging │    │   NER   │    │Parsing  │   │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘   │
│       │              │              │              │          │
│       ▼              ▼              ▼              ▼          │
│  ["Apple",     {Apple:PROPN,    [{Apple:ORG,   {Apple:       │
│   "is",         is:AUX,          U.K.:GPE,      nsubj:looking│
│   "looking",   looking:VERB...}] money:$1B}]  is:aux:looking│
│   ...]                                                  ...} │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## 2. NLTK vs spaCy 架构对比

```
┌─────────────────────────────┐  ┌─────────────────────────────┐
│         NLTK                │  │         spaCy               │
├─────────────────────────────┤  ├─────────────────────────────┤
│                             │  │                             │
│  ┌───────────────────────┐  │  │  ┌───────────────────────┐  │
│  │   模块化设计           │  │  │  │   统一 Pipeline       │  │
│  │                       │  │  │  │                       │  │
│  │  • tokenize 模块      │  │  │  │  nlp(text)           │  │
│  │  • tag 模块           │  │  │  │    ├─ Tokenizer      │  │
│  │  • chunk 模块         │  │  │  │    ├─ Tagger         │  │
│  │  • stem 模块          │  │  │  │    ├─ NER            │  │
│  │  • corpus 模块        │  │  │  │    └─ Parser         │  │
│  │                       │  │  │  │                       │  │
│  │  每个模块独立使用      │  │  │  │  一行代码完成全部     │  │
│  └───────────────────────┘  │  │  └───────────────────────┘  │
│                             │  │                             │
│  速度: ★★☆☆☆               │  │  速度: ★★★★★               │
│  灵活: ★★★★★               │  │  灵活: ★★★☆☆               │
│  学习: ★★★★☆               │  │  学习: ★★★★☆               │
│  生产: ★★☆☆☆               │  │  生产: ★★★★★               │
│                             │  │                             │
└─────────────────────────────┘  └─────────────────────────────┘
```

## 3. 聊天机器人 NLP Pipeline

```
用户输入: "What's the weather in Beijing tomorrow?"
                    │
                    ▼
┌─────────────────────────────────────────┐
│           NLP Pipeline                  │
│                                         │
│  1. 分词 (Tokenization)                 │
│     ["what", "'s", "the", "weather",    │
│      "in", "beijing", "tomorrow", "?"]  │
│                                         │
│  2. 词性标注 (POS Tagging)              │
│     {weather: NN, Beijing: NNP,         │
│      tomorrow: NN}                      │
│                                         │
│  3. 命名实体识别 (NER)                  │
│     {Beijing: GPE → location}           │
│     {tomorrow: DATE → date}             │
│                                         │
│  4. 意图识别 (Intent Recognition)       │
│     匹配 "weather" → intent: weather    │
│                                         │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│           结构化输出                     │
│                                         │
│  {                                      │
│    "intent": "weather",                 │
│    "entities": {                        │
│      "location": "Beijing",             │
│      "date": "tomorrow"                 │
│    },                                   │
│    "tokens": ["weather", "beijing",     │
│               "tomorrow"]               │
│  }                                      │
│                                         │
└─────────────────────────────────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │  响应生成器      │
          │  查天气API →     │
          │  返回天气信息    │
          └─────────────────┘
```

## 4. 词干提取 vs 词形还原

```
原词          词干提取 (Stemming)     词形还原 (Lemmatization)
─────────    ─────────────────      ──────────────────────
running      run ✓                  running → run ✓
flies        fli ✗ (非词)           flies → fly ✓
better       better (无变化)        better → good ✓
studies      studi ✗ (非词)        studies → study ✓
happines     happi ✗ (非词)         happiness → happiness ✓
ran          ran (无变化)           ran → run ✓

说明:
• 词干提取: 基于规则截断，速度快，可能产生非词
• 词形还原: 基于词典，准确，需要 POS 信息辅助
```

## 5. spaCy Token 属性关系

```
                    Token 对象
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   文法属性          语义属性          状态属性
        │               │               │
   ┌────┴────┐     ┌────┴────┐     ┌────┴────┐
   │ .text   │     │ .lemma_ │     │ .is_stop│
   │ .pos_   │     │ .vector │     │ .is_alpha│
   │ .tag_   │     │ .similarity│ │ .is_punct│
   │ .dep_   │     │         │     │ .is_oov │
   │ .head   │     │         │     │         │
   │ .morph  │     │         │     │         │
   └─────────┘     └─────────┘     └─────────┘
   
   • text:     原始文本
   • lemma_:   词形还原结果
   • pos_:     粗粒度词性 (NOUN, VERB, ADJ...)
   • tag_:     细粒度词性 (NN, VBZ, JJ...)
   • dep_:     依存关系标签
   • head:     依存关系的中心词
   • morph:    形态特征 (Number=Sing, Tense=Past...)
   • is_stop:  是否停用词
   • is_alpha: 是否纯字母
   • is_punct: 是否标点
   • vector:   词向量 (需中/大模型)
```
