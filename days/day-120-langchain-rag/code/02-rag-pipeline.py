"""
02-rag-pipeline.py — 完整 RAG Pipeline
演示从文件加载 → 分割 → 存储 → 检索 → 问答的完整流程

使用 FAISS 作为向量存储（本地、免费、无需数据库）

运行前确保：
  pip install langchain langchain-openai langchain-community langchain-text-splitters faiss-cpu
"""

import os
import tempfile
from pathlib import Path

from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document


# ============================================================
# 工具函数
# ============================================================

def create_sample_documents():
    """创建示例文档，模拟真实文件"""
    docs = {
        "python_basics.txt": """Python 基础知识

Python 是一种解释型、面向对象的高级编程语言。Python 的设计哲学强调代码的可读性和简洁性。

Python 的数据类型包括：整数(int)、浮点数(float)、字符串(str)、列表(list)、
字典(dict)、元组(tuple)、集合(set)等。其中列表和字典是最常用的数据结构。

Python 使用缩进来定义代码块，这与 C/Java 使用花括号不同。
缩进通常使用 4 个空格。""",

        "python_advanced.txt": """Python 高级特性

装饰器（Decorator）是 Python 的重要特性之一，它允许在不修改原函数的情况下
为函数添加新功能。装饰器本质上是一个高阶函数。

生成器（Generator）使用 yield 关键字创建，可以惰性地生成序列中的值，
在处理大数据集时特别有用，因为它不需要一次性将所有数据加载到内存中。

上下文管理器（Context Manager）通过 with 语句使用，确保资源被正确管理。
可以使用 class 或 contextlib.contextmanager 来创建。

异步编程（Async/Await）允许编写并发代码，特别适合 I/O 密集型任务。
asyncio 模块提供了事件循环和协程支持。""",

        "python_web.txt": """Python Web 开发

Django 是一个全功能的 Web 框架，提供了 ORM、模板系统、Admin 界面等功能。
适合大型项目快速开发。

Flask 是一个轻量级 Web 框架，灵活度高，适合小型项目和 API 开发。

FastAPI 是现代高性能 Web 框架，基于类型提示自动生成 API 文档，
性能接近 Go 和 Node.js。非常适合构建 RESTful API。

Web 开发中常用的设计模式包括 MVC（Model-View-Controller）、
MTV（Model-Template-View，Django 使用）和 MVVM 等。"""
    }

    # 创建临时目录存放示例文档
    tmp_dir = tempfile.mkdtemp(prefix="rag_demo_")
    for filename, content in docs.items():
        filepath = os.path.join(tmp_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return tmp_dir


# ============================================================
# Step 1: 文档加载
# ============================================================

def load_documents(doc_dir):
    """从目录加载所有 .txt 文件"""
    loader = DirectoryLoader(
        doc_dir,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()
    print(f"📄 从 {doc_dir} 加载了 {len(documents)} 个文档")
    for doc in documents:
        print(f"   - {doc.metadata['source']} ({len(doc.page_content)} 字符)")
    return documents


# ============================================================
# Step 2: 文档分割
# ============================================================

def split_documents(documents, chunk_size=300, chunk_overlap=50):
    """将文档分割成小块"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "，", " "],
        length_function=len,
    )
    chunks = splitter.split_documents(documents)
    print(f"✂️  分割为 {len(chunks)} 个文本块")
    print(f"   平均块大小: {sum(len(c.page_content) for c in chunks) / len(chunks):.0f} 字符")
    return chunks


# ============================================================
# Step 3: 向量化 + 存储
# ============================================================

def create_vectorstore(chunks, persist_dir="./rag_faiss_index"):
    """将文本块向量化并存储到 FAISS"""
    # 使用 OpenAI Embedding（实际项目中可替换为本地模型）
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # 创建 FAISS 向量存储
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # 保存到磁盘（可选，下次可直接加载）
    vectorstore.save_local(persist_dir)
    print(f"💾 向量存储完成，索引大小: {vectorstore.index.ntotal} 个向量")
    print(f"💾 已保存到: {persist_dir}")

    return vectorstore


# ============================================================
# Step 4: 构建 RAG Chain
# ============================================================

def build_rag_chain(vectorstore, llm_model="gpt-4"):
    """构建完整的 RAG Chain"""
    # 检索器
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )

    # RAG 提示词模板
    rag_prompt = ChatPromptTemplate.from_template("""
你是一个专业的 Python 技术助手。请根据以下提供的上下文信息回答问题。

要求：
1. 仅基于提供的上下文回答，不要编造信息
2. 如果上下文中没有相关信息，请明确说明
3. 回答要准确、简洁、有条理
4. 适当引用上下文中的具体内容

上下文：
{context}

问题：{question}

回答：""")

    # 格式化检索结果
    def format_docs(docs):
        formatted = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "未知")
            formatted.append(f"[文档{i+1}] (来源: {source})\n{doc.page_content}")
        return "\n\n".join(formatted)

    # 构建 LCEL Chain
    llm = ChatOpenAI(model=llm_model, temperature=0)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | rag_prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain, retriever


# ============================================================
# Step 5: 问答测试
# ============================================================

def test_qa(rag_chain):
    """测试几个问题"""
    questions = [
        "Python 装饰器是什么？有什么用途？",
        "Python 中有哪些常用的 Web 框架？各自的特点是什么？",
        "生成器和列表推导式有什么区别？",
    ]

    print("\n" + "=" * 60)
    print("🤖 RAG 问答测试")
    print("=" * 60)

    for q in questions:
        print(f"\n❓ 问题: {q}")
        print("-" * 40)
        answer = rag_chain.invoke(q)
        print(f"💬 回答: {answer}")
        print()


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 完整 RAG Pipeline 演示")
    print("=" * 60)

    # 1. 创建示例文档
    print("\n📁 Step 1: 创建示例文档...")
    doc_dir = create_sample_documents()

    # 2. 加载文档
    print("\n📂 Step 2: 加载文档...")
    documents = load_documents(doc_dir)

    # 3. 分割文档
    print("\n✂️  Step 3: 分割文档...")
    chunks = split_documents(documents)

    # 4. 创建向量存储
    print("\n💾 Step 4: 创建向量存储...")
    # 注意：这里需要有效的 OpenAI API Key
    # 如果没有，可以使用 FakeEmbeddings 做演示：
    # from langchain_community.embeddings import FakeEmbeddings
    # embeddings = FakeEmbeddings(size=384)
    try:
        vectorstore = create_vectorstore(chunks)
    except Exception as e:
        print(f"⚠️  向量化失败（可能缺少 API Key）: {e}")
        print("使用 FakeEmbeddings 继续演示流程...")
        from langchain_community.embeddings import FakeEmbeddings
        embeddings = FakeEmbeddings(size=384)
        vectorstore = FAISS.from_documents(chunks, embeddings)
        print(f"💾 向量存储完成（使用模拟 embedding）")

    # 5. 构建 RAG Chain
    print("\n🔗 Step 5: 构建 RAG Chain...")
    try:
        rag_chain, retriever = build_rag_chain(vectorstore)

        # 6. 测试问答
        test_qa(rag_chain)
    except Exception as e:
        print(f"⚠️  问答失败（可能缺少 API Key）: {e}")
        print("\n演示检索部分：")
        query = "Python 装饰器是什么？"
        retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        results = retriever.invoke(query)
        for doc in results:
            print(f"\n📄 {doc.metadata.get('source', 'N/A')}:")
            print(f"   {doc.page_content[:200]}")

    # 清理
    import shutil
    shutil.rmtree(doc_dir, ignore_errors=True)
    print("\n✅ 演示完成！")
