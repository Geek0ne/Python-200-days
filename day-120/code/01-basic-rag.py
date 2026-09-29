"""
01-basic-rag.py — 最小可运行的 RAG 示例
展示 RAG 的核心流程：加载 → 分割 → 向量化 → 检索 → 生成

运行前确保：
  pip install langchain langchain-openai langchain-community langchain-text-splitters
  
如果不想用 OpenAI API，可以将 llm 替换为本地 Ollama：
  pip install langchain-ollama
"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ============================================================
# 1. 准备示例文档
# ============================================================
# 在真实场景中，这些文档来自文件加载器
documents_content = [
    "Python 装饰器是一种设计模式，用于在不修改原函数代码的前提下，为函数添加额外功能。"
    "装饰器本质上是一个接受函数作为参数的高阶函数，返回一个新的函数。"
    "Python 3 引入了 @ 语法糖来简化装饰器的使用。"
    "例如：@property 装饰器可以将方法转换为属性访问。"
    "再如：@staticmethod 和 @classmethod 是 Python 内置的装饰器。",

    "Python 生成器是一种特殊的迭代器，使用 yield 关键字返回值。"
    "与普通函数不同，生成器函数在每次调用 yield 时会暂停执行，保留当前状态。"
    "下次调用 next() 时从上次暂停的位置继续。"
    "生成器的优势在于惰性求值，不需要一次性将所有数据加载到内存中。"
    "列表推导式 [x**2 for x in range(1000000)] 会占用大量内存，"
    "而生成器表达式 (x**2 for x in range(1000000)) 几乎不占内存。",

    "Python 上下文管理器通过 __enter__ 和 __right__ 方法管理资源。"
    "with 语句保证资源在使用后被正确释放，即使发生异常。"
    "使用 contextlib.contextmanager 装饰器可以更方便地创建上下文管理器。"
    "常见用途：文件操作、数据库连接、线程锁等。"
    "上下文管理器的核心价值是保证资源的确定性释放。",

    "Python 异步编程通过 asyncio 模块实现协程。"
    "async/await 语法让异步代码看起来像同步代码一样清晰。"
    "协程在遇到 I/O 等待时会自动让出控制权，让其他协程运行。"
    "asyncio.gather() 可以并发执行多个协程。"
    "异步编程特别适合 I/O 密集型任务，如网络请求、文件操作等。"
]

# 模拟 Document 对象
from langchain_core.documents import Document

docs = [
    Document(page_content=text, metadata={"source": f"doc_{i}.txt"})
    for i, text in enumerate(documents_content)
]

print(f"📄 加载了 {len(docs)} 个文档片段")

# ============================================================
# 2. 文档分割
# ============================================================
splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,       # 每块最多 200 字符
    chunk_overlap=30,     # 相邻块重叠 30 字符
    separators=["\n\n", "\n", "。", "！", "？", "，", " "]
)

chunks = splitter.split_documents(docs)
print(f"✂️  分割为 {len(chunks)} 个文本块")

# ============================================================
# 3. 向量化存储（使用 FAISS，本地免费）
# ============================================================
# 使用随机维度的简单 embedding（仅用于演示流程）
# 实际生产中应使用真正的 embedding 模型

# 方案 A：使用 OpenAI Embedding（需要 API Key）
# embeddings = OpenAIEmbeddings()
# vectorstore = FAISS.from_documents(chunks, embeddings)

# 方案 B：使用本地简单向量（仅演示流程，不涉及真实语义）
from langchain_community.embeddings import FakeEmbeddings
embeddings = FakeEmbeddings(size=384)  # 模拟 384 维向量
vectorstore = FAISS.from_documents(chunks, embeddings)

print(f"💾 向量存储完成，共 {vectorstore.index.ntotal} 个向量")

# ============================================================
# 4. 检索
# ============================================================
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 2}  # 返回最相关的 2 个片段
)

query = "Python 装饰器是什么？"
retrieved_docs = retriever.invoke(query)

print(f"\n🔍 查询: {query}")
print(f"📋 检索到 {len(retrieved_docs)} 个相关片段:")
for i, doc in enumerate(retrieved_docs):
    print(f"\n--- 片段 {i+1} (来源: {doc.metadata['source']}) ---")
    print(doc.page_content[:150])

# ============================================================
# 5. 生成回答
# ============================================================
# 注意：由于使用了 FakeEmbeddings，检索结果可能是随机的
# 真实场景中，向量检索会返回语义相关的内容

llm = ChatOpenAI(model="gpt-4", temperature=0)

rag_prompt = ChatPromptTemplate.from_template("""
你是一个专业的 Python 技术助手。基于以下上下文回答问题。
如果上下文中没有相关信息，请如实说明你不确定。

上下文：
{context}

问题：{question}

请用中文回答：""")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
    | StrOutputParser()
)

print("\n🤖 正在生成回答...")
answer = rag_chain.invoke(query)
print(f"\n💬 回答:\n{answer}")

# ============================================================
# 流程总结
# ============================================================
print("\n" + "=" * 60)
print("✅ RAG 核心流程:")
print("   1. 加载文档 → Document 对象列表")
print("   2. 分割文档 → 文本块列表")
print("   3. 向量化   → 向量存储（FAISS/Chroma）")
print("   4. 检索     → 根据查询找到相关文档")
print("   5. 生成     → 将检索结果 + 问题 → LLM → 回答")
print("=" * 60)
