# Day 120 — LangChain 与 RAG 练习清单

## ✅ 今日完成清单

- [ ] 理解 LangChain 的核心概念和组件
- [ ] 掌握文档加载、分割、向量化的完整流程
- [ ] 理解 RAG 的原理和应用场景
- [ ] 运行 01-basic-rag.py，理解最小 RAG 流程
- [ ] 运行 02-rag-pipeline.py，掌握完整 Pipeline
- [ ] 运行 03-chatbot.py，体验交互式问答机器人

---

## 📝 基础练习题

### 练习 1：文档分割实验

修改 `02-rag-pipeline.py` 中的 `chunk_size` 和 `chunk_overlap` 参数，观察分割结果的变化：

```python
# 测试不同参数
params_list = [
    {"chunk_size": 100, "chunk_overlap": 10},
    {"chunk_size": 300, "chunk_overlap": 50},
    {"chunk_size": 800, "chunk_overlap": 100},
]

for params in params_list:
    splitter = RecursiveCharacterTextSplitter(**params)
    chunks = splitter.split_documents(documents)
    print(f"参数: {params}")
    print(f"  分割块数: {len(chunks)}")
    print(f"  平均块大小: {sum(len(c.page_content) for c in chunks) / len(chunks):.0f}")
```

**思考**：不同参数对检索质量有什么影响？

---

### 练习 2：不同检索策略

修改检索器的 `search_type` 和 `search_kwargs`：

```python
# 方式 1: 相似度检索
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3}
)

# 方式 2: MMR（最大边际相关性）- 平衡相关性和多样性
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 3, "fetch_k": 10}
)

# 方式 3: 阈值过滤
retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"score_threshold": 0.5}
)
```

**思考**：MMR 检索有什么优势？什么时候应该用阈值过滤？

---

### 练习 3：RAG Prompt 优化

修改 RAG 提示词模板，对比不同提示词的回答质量：

```python
# 模板 1: 简单版
prompt_v1 = ChatPromptTemplate.from_template("""
基于以下上下文回答问题：
{context}
问题：{question}
""")

# 模板 2: 带约束版
prompt_v2 = ChatPromptTemplate.from_template("""
你是一个专业的技术文档助手。

规则：
1. 仅基于提供的上下文回答
2. 如果上下文没有相关信息，说"我无法在提供的文档中找到相关信息"
3. 回答要简洁准确
4. 必要时引用文档来源

上下文：
{context}

问题：{question}
""")

# 模板 3: 带格式输出
prompt_v3 = ChatPromptTemplate.from_template("""
基于以下文档回答问题。

请按以下格式回答：
**答案**: [你的回答]
**来源**: [引用的文档部分]
**置信度**: [高/中/低]

文档内容：
{context}

问题：{question}
""")
```

---

## 🚀 进阶挑战题

### 挑战 1：自定义文档加载器

编写一个加载 Markdown 文件的自定义加载器：

```python
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document

class MarkdownLoader(BaseLoader):
    """自定义 Markdown 文档加载器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 按二级标题分割
        sections = content.split("\n## ")
        documents = []
        for i, section in enumerate(sections):
            doc = Document(
                page_content=section.strip(),
                metadata={
                    "source": self.file_path,
                    "section_index": i
                }
            )
            documents.append(doc)
        return documents
```

### 挑战 2：实现混合搜索

结合向量搜索和关键词搜索：

```python
def hybrid_search(query, vectorstore, keyword_index, top_k=3):
    """混合搜索：向量搜索 + 关键词搜索"""
    # 向量搜索
    vector_results = vectorstore.similarity_search_with_score(query, k=top_k * 2)
    
    # 关键词搜索（简化版）
    keyword_results = []
    for doc, _ in vector_results:
        if any(kw in doc.page_content for kw in query.split()):
            keyword_results.append(doc)
    
    # 合并去重
    seen = set()
    final_results = []
    for doc in vector_results[:top_k] + keyword_results[:top_k]:
        content_hash = hash(doc.page_content)
        if content_hash not in seen:
            seen.add(content_hash)
            final_results.append(doc)
    
    return final_results[:top_k]
```

### 挑战 3：添加引用溯源

实现一个带引用的 RAG 系统：

```python
def rag_with_citation(rag_chain, query):
    """带引用的 RAG 回答"""
    # 检索相关文档
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    docs = retriever.invoke(query)
    
    # 构造带引用的上下文
    context_parts = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "未知")
        context_parts.append(f"[文档{i+1}] (来源: {source})\n{doc.page_content}")
    
    context = "\n\n".join(context_parts)
    
    # 生成回答
    prompt = ChatPromptTemplate.from_template("""
基于以下文档回答问题，并在回答中使用 [文档X] 标记引用来源。

{context}

问题：{question}
""")
    
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": context, "question": query})
```

### 挑战 4：RAG 评估框架

实现一个简单的 RAG 质量评估：

```python
def evaluate_rag(questions, rag_chain, ground_truth):
    """
    评估 RAG 系统
    - questions: 测试问题列表
    - ground_truth: 标准答案
    """
    results = []
    
    for q, expected in zip(questions, ground_truth):
        # 获取回答
        answer = rag_chain.invoke(q)
        
        # 评估维度
        result = {
            "question": q,
            "expected": expected,
            "actual": answer,
            "contains_keywords": all(
                kw in answer for kw in expected.split()[:3]
            ),
            "length_ratio": len(answer) / max(len(expected), 1)
        }
        results.append(result)
    
    # 统计
    accuracy = sum(r["contains_keywords"] for r in results) / len(results)
    print(f"关键词匹配率: {accuracy:.1%}")
    
    return results
```
