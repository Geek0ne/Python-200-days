# Day 120 — LangChain 与 RAG

> **阶段**：Phase 7 — 进阶与性能优化  
> **主题**：LangChain 核心组件、文档加载/分割/向量化、RAG 问答系统  
> **实战目标**：构建本地文档问答机器人

---

## 📋 目录

1. [LangChain 是什么](#1-langchain-是什么)
2. [核心组件详解](#2-核心组件详解)
3. [文档加载](#3-文档加载)
4. [文档分割策略](#4-文档分割策略)
5. [向量化与向量存储](#5-向量化与向量存储)
6. [RAG 原理与流程](#6-rag-原理与流程)
7. [API 速查表](#7-api-速查表)
8. [图解：RAG 完整流程](#8-图解rag-完整流程)
9. [实战：本地文档问答机器人](#9-实战本地文档问答机器人)
10. [思考题](#10-思考题)

---

## 1. LangChain 是什么

### 1.1 核心定义

LangChain 是一个用于构建 **LLM 驱动应用**的开源框架。它提供了一套标准化的接口和组件，帮助开发者将大语言模型（LLM）与外部数据源、工具和工作流集成在一起。

### 1.2 为什么需要 LangChain？

直接调用 OpenAI API 很简单，但当你需要：
- 让 LLM **基于你自己的文档**回答问题（RAG）
- 将多个 LLM 调用**串联成工作流**（Chain）
- 让 LLM **使用外部工具**（Agent）
- 管理提示词模板、对话历史、向量数据库**等基础设施**

手动实现这些非常繁琐。LangChain 把这些常见模式抽象成了可复用的组件。

### 1.3 LangChain 的核心价值

```
┌─────────────────────────────────────────────────┐
│              LangChain 生态                       │
├──────────┬──────────┬──────────┬────────────────┤
│ langchain│langchain │langchain │  LangSmith     │
│  核心库  │  community│ text     │ (可观测性)     │
│          │ (社区集成)│ splitters│                │
└──────────┴──────────┴──────────┴────────────────┘
     │            │           │           │
  LLM包装     向量数据库    文档处理    调试追踪
```

---

## 2. 核心组件详解

### 2.1 Models（模型）

LangChain 通过统一接口包装不同 LLM：

```python
from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama

# OpenAI
llm = ChatOpenAI(model="gpt-4", temperature=0.7)

# 本地 Ollama
llm = Ollama(model="qwen2.5:7b")
```

**为什么要抽象？** 统一接口意味着你可以轻松切换模型提供商，只需改一行代码。

### 2.2 Prompts（提示词模板）

将提示词参数化，避免硬编码：

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的{role}，请用{language}回答。"),
    ("human", "{question}")
])

# 生成实际提示词
messages = prompt.invoke({
    "role": "Python 讲师",
    "language": "中文",
    "question": "什么是装饰器？"
})
```

### 2.3 Chains（链）

将组件串联成流水线（管道）：

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 构建 LCEL 链（推荐的现代写法）
chain = prompt | llm | StrOutputParser()

# 一行调用完成完整流程
result = chain.invoke({
    "role": "Python 讲师",
    "language": "中文",
    "question": "什么是装饰器？"
})
```

**LCEL（LangChain Expression Language）**：使用 `|` 管道语法将组件串联，类似 Unix 管道，简洁直观。

### 2.4 Retrievers（检索器）

从向量数据库中检索相关文档片段：

```python
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4}  # 返回最相关的 4 个片段
)

docs = retriever.invoke("什么是装饰器？")
```

### 2.5 Loaders（加载器）

从各种数据源加载文档：

```python
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    CSVLoader,
    WebBaseLoader
)

# 加载文本文件
loader = TextLoader("data.txt", encoding="utf-8")

# 加载 PDF
loader = PyPDFLoader("document.pdf")

# 加载网页
loader = WebBaseLoader("https://example.com/article")
```

### 2.6 Text Splitters（文本分割器）

将长文档分割成适合向量化的小片段：

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       # 每块最多 500 字符
    chunk_overlap=50,     # 相邻块重叠 50 字符
    separators=["\n\n", "\n", "。", "！", "？", "，", " "]
)
```

---

## 3. 文档加载

### 3.1 支持的数据源

| 数据源 | Loader 类 | 安装命令 |
|--------|-----------|----------|
| 纯文本 | `TextLoader` | `langchain-community` |
| PDF | `PyPDFLoader` | `pip install pypdf` |
| Word | `Docx2txtLoader` | `pip install docx2txt` |
| CSV | `CSVLoader` | 内置 |
| Markdown | `UnstructuredMarkdownLoader` | `pip install unstructured` |
| 网页 | `WebBaseLoader` | 内置 |
| JSON | `JSONLoader` | 内置 |
| 数据库 | `SQLDatabaseLoader` | `langchain-community` |

### 3.2 实际使用

```python
from langchain_community.document_loaders import PyPDFLoader

# 加载 PDF（每页是一个 Document）
loader = PyPDFLoader("paper.pdf")
docs = loader.load()

print(f"总页数: {len(docs)}")
print(f"第一页内容: {docs[0].page_content[:200]}")
print(f"元数据: {docs[0].metadata}")
# metadata 包含: source（文件路径）、page（页码）
```

---

## 4. 文档分割策略

### 4.1 为什么要分割？

LLM 有上下文窗口限制，向量模型也有输入长度限制。长文档需要切成小块才能有效检索。

### 4.2 分割策略对比

#### RecursiveCharacterTextSplitter（推荐）

```
分割顺序：段落 → 换行 → 句号 → 感叹号 → 逗号 → 空格

原始文本:
┌──────────────────────────────────────────┐
│ 第一段落第一句话。第一段落第二句话。       │
│                                           │
│ 第二段落第一句话。第二段落第二句话。       │
└──────────────────────────────────────────┘
              ↓ 按 chunk_size=50 分割
┌─────────────────┐ ┌─────────────────┐
│ 第一段落第一句话 │ │ 第一段落第二句话 │  ← 重叠区
│ 。第一段落第二句 │ │ 。第二段落第一句 │
└─────────────────┘ └─────────────────┘
```

#### CharacterTextSplitter

按固定字符分隔符分割，简单粗暴：

```python
from langchain_text_splitters import CharacterTextSplitter

splitter = CharacterTextSplitter(
    separator="\n",
    chunk_size=500,
    chunk_overlap=50
)
```

#### TokenTextSplitter

按 token 数量分割（适合精确控制 API 调用成本）：

```python
from langchain_text_splitters import TokenTextSplitter

splitter = TokenTextSplitter(
    encoding_name="cl100k_base",  # GPT-4 的 tokenizer
    chunk_size=100,               # 100 tokens
    chunk_overlap=20
)
```

### 4.3 分割参数选择指南

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `chunk_size` | 300-1000 | 太小丢失上下文，太大噪声多 |
| `chunk_overlap` | chunk_size 的 10%-20% | 保证边界处语义连续 |
| `separators` | `["\n\n", "\n", "。", " "]` | 优先按段落分割 |

---

## 5. 向量化与向量存储

### 5.1 什么是向量化？

将文本转换为高维数值向量（embedding），使得语义相似的文本在向量空间中距离更近。

```
"Python 装饰器"  ──→  [0.23, -0.45, 0.67, ..., 0.12]  (1536 维)
"装饰器语法"     ──→  [0.21, -0.42, 0.69, ..., 0.15]  (距离近!)
"猫是可爱的"     ──→  [-0.89, 0.34, -0.12, ..., 0.78]  (距离远)
```

### 5.2 Embedding 模型选择

```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

# OpenAI（云端，1536/3072 维）
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# HuggingFace（本地免费）
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",  # 中文优化
    model_kwargs={"device": "cpu"}
)
```

### 5.3 向量存储

| 存储方案 | 特点 | 适用场景 |
|----------|------|----------|
| FAISS | 本地，Facebook 出品 | 开发测试、中小数据量 |
| Chroma | 本地，轻量简洁 | 原型开发 |
| Milvus | 分布式，高性能 | 生产环境大数据量 |
| Weaviate | 内置混合搜索 | 需要关键词+语义混合搜索 |
| Pinecone | 全托管云服务 | 不想自运维 |

**本教程使用 Chroma**（本地、零配置、适合学习）：

```python
from langchain_chroma import Chroma

# 创建向量存储（自动向量化并存储）
vectorstore = Chroma.from_documents(
    documents=docs,
    embedding=embeddings,
    persist_directory="./chroma_db"  # 持久化到磁盘
)

# 查询
results = vectorstore.similarity_search("装饰器", k=3)
```

---

## 6. RAG 原理与流程

### 6.1 什么是 RAG？

**RAG（Retrieval-Augmented Generation）** = 检索增强生成

核心思想：让 LLM **先检索相关文档，再基于检索结果生成回答**，而不是仅靠自身知识。

### 6.2 为什么需要 RAG？

| 问题 | 无 RAG | 有 RAG |
|------|--------|--------|
| 知识过时 | LLM 训练数据截止到某日期 | 可查询最新文档 |
| 幻觉 | 编造不存在的信息 | 基于真实文档回答 |
| 私有数据 | LLM 不知道公司内部文档 | 可接入私有知识库 |
| 可溯源 | 无法验证回答依据 | 引用具体文档来源 |

### 6.3 RAG 完整流程

```
                    ┌──────────────────────┐
                    │  用户提问              │
                    │ "Python 装饰器是什么？" │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ ① 查询向量化          │
                    │ Embedding("装饰器")   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ ② 向量检索            │
                    │ 在向量数据库中找到     │
                    │ 最相关的文档片段       │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ ③ 构造增强提示词       │
                    │ "基于以下文档回答：    │
                    │  [检索到的文档片段]    │
                    │  问题：装饰器是什么？" │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ ④ LLM 生成回答        │
                    │ 基于检索结果生成答案   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ ⑤ 返回回答             │
                    │ "装饰器是Python中用于  │
                    │  修改函数行为的语法..." │
                    └──────────────────────┘
```

### 6.4 RAG 的关键环节

**检索质量**是 RAG 的核心瓶颈：
- chunk_size 太小 → 丢失上下文
- chunk_size 太大 → 检索精度下降
- 向量模型不匹配 → 语义理解差
- 重排（Reranking）可以二次优化检索结果

---

## 7. API 速查表

### 7.1 文档加载

```python
from langchain_community.document_loaders import TextLoader, PyPDFLoader

loader = TextLoader("file.txt", encoding="utf-8")
docs = loader.load()  # → List[Document]
```

### 7.2 文档分割

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)  # → List[Document]
```

### 7.3 向量存储

```python
from langchain_chroma import Chroma

# 创建
vs = Chroma.from_documents(docs, embeddings, persist_directory="./db")

# 查询
results = vs.similarity_search(query, k=4)

# 带分数的查询
results = vs.similarity_search_with_score(query, k=4)
```

### 7.4 LLM 调用

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="gpt-4")
prompt = ChatPromptTemplate.from_template("...")
chain = prompt | llm | StrOutputParser()
answer = chain.invoke({"question": "..."})
```

### 7.5 RAG Chain（经典写法）

```python
from langchain.chains import RetrievalQA

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",  # 将所有检索结果拼接后一次性传给 LLM
    retriever=retriever,
    return_source_documents=True
)

result = qa_chain.invoke("什么是装饰器？")
print(result["result"])
print(result["source_documents"])
```

### 7.6 RAG Chain（LCEL 写法，推荐）

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# RAG 提示词模板
rag_prompt = ChatPromptTemplate.from_template("""
基于以下上下文回答问题。如果上下文中没有相关信息，请说明你不确定。

上下文：
{context}

问题：{question}

回答：""")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
    | StrOutputParser()
)

answer = rag_chain.invoke("什么是装饰器？")
```

---

## 8. 图解：RAG 完整流程

### 8.1 索引阶段（离线）

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  原始文档     │     │  文档分割     │     │  向量化 + 存储   │
│  (PDF/网页/  │ ──→ │  (Splitter)  │ ──→ │  (Embedding +   │
│   文本)      │     │  chunk_1      │     │   VectorStore)  │
│             │     │  chunk_2      │     │                 │
│             │     │  ...          │     │  ┌───┐ ┌───┐   │
│             │     │  chunk_n      │     │  │v_1│ │v_2│   │
└─────────────┘     └──────────────┘     │  └───┘ └───┘   │
                                         │  ┌───┐ ┌───┐   │
                                         │  │v_3│ │v_4│   │
                                         │  └───┘ └───┘   │
                                         └─────────────────┘
```

### 8.2 查询阶段（在线）

```
用户问题 ──→ Embedding ──→ 向量相似度搜索 ──→ Top-K 文档片段
                                                   │
                                                   ▼
                                              Prompt 组装
                                          "基于以下内容：
                                           [片段1]
                                           [片段2]
                                           回答问题：..."
                                                   │
                                                   ▼
                                              LLM 生成回答
                                                   │
                                                   ▼
                                              返回给用户
```

---

## 9. 实战：本地文档问答机器人

### 9.1 项目结构

```
day-120-langchain-rag/
├── code/
│   ├── 01-basic-rag.py      # 基础 RAG 流程
│   ├── 02-rag-pipeline.py   # 完整 RAG Pipeline
│   └── 03-chatbot.py        # 本地文档问答机器人
├── README.md
├── diagrams/
│   └── README.md
└── exercises/
    └── checklist.md
```

### 9.2 安装依赖

```bash
pip install langchain langchain-openai langchain-community langchain-chroma \
            langchain-text-splitters pypdf
```

### 9.3 代码文件说明

- **01-basic-rag.py**：最小可运行的 RAG 示例，理解核心流程
- **02-rag-pipeline.py**：完整的 RAG Pipeline，包含加载、分割、存储、检索、问答
- **03-chatbot.py**：交互式问答机器人，支持多轮对话

运行方式：
```bash
cd days/day-120-langchain-rag/code
python3 01-basic-rag.py
```

---

## 10. 思考题

1. **chunk_size 如何影响检索质量？** 太小和太大分别会带来什么问题？如果你的知识库中既有短的 FAQ 又有长的技术文档，应该如何设置？

2. **RAG vs Fine-tuning**：什么场景下应该用 RAG，什么场景下应该用微调？两者可以结合使用吗？

3. **向量检索的局限性**：纯向量检索有什么不足？什么是混合搜索（Hybrid Search）？为什么生产环境通常使用混合搜索？

4. **幻觉问题**：即使使用了 RAG，LLM 仍然可能产生幻觉（编造信息）。你可以采取哪些额外措施来减少幻觉？

5. **评估指标**：如何评估一个 RAG 系统的质量？有哪些常用的评估维度（如检索准确率、回答相关性等）？
