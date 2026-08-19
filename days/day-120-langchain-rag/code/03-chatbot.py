"""
03-chatbot.py — 本地文档问答机器人（交互式）
支持多轮对话，基于本地文档进行问答

功能特点：
1. 加载本地目录下的文档
2. 构建向量索引
3. 支持交互式多轮问答
4. 显示检索到的参考文档来源
5. 支持对话历史上下文

运行前确保：
  pip install langchain langchain-openai langchain-community langchain-text-splitters faiss-cpu
"""

import os
import sys
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage


# ============================================================
# 配置
# ============================================================

class ChatConfig:
    """机器人配置"""
    # 文档目录（默认当前目录下的 sample_docs/）
    DOC_DIR = "./sample_docs"

    # 向量存储目录
    FAISS_DIR = "./chatbot_faiss_index"

    # 分割参数
    CHUNK_SIZE = 400
    CHUNK_OVERLAP = 60

    # 检索参数
    TOP_K = 3

    # LLM 配置
    LLM_MODEL = "gpt-4"
    TEMPERATURE = 0.3  # 问答场景用较低温度

    # 系统提示词
    SYSTEM_PROMPT = """你是一个智能文档助手。根据提供的文档上下文回答用户的问题。

规则：
1. 基于文档内容回答，不要编造信息
2. 如果文档中没有相关信息，诚实说明
3. 回答简洁准确，必要时引用文档来源
4. 可以进行多轮对话，记住之前的上下文"""


# ============================================================
# 示例文档创建
# ============================================================

def create_sample_docs():
    """创建示例文档目录"""
    doc_dir = Path(ChatConfig.DOC_DIR)
    doc_dir.mkdir(exist_ok=True)

    docs = {
        "getting_started.txt": """# Python 快速入门

## 环境安装
1. 访问 python.org 下载最新版本
2. 安装时勾选 "Add Python to PATH"
3. 打开终端输入 `python --version` 验证安装

## 第一个程序
创建文件 hello.py:
```python
print("Hello, World!")
```
运行: `python hello.py`

## 变量与数据类型
Python 是动态类型语言，不需要声明变量类型:
```python
name = "Alice"      # 字符串
age = 25            # 整数
height = 1.68       # 浮点数
is_student = True   # 布尔值
```

## 基本运算
```python
# 算术运算
print(10 + 3)   # 13
print(10 - 3)   # 7
print(10 * 3)   # 30
print(10 / 3)   # 3.333...
print(10 // 3)  # 3 (整除)
print(10 % 3)   # 1 (取余)
print(10 ** 3)  # 1000 (幂运算)

# 字符串拼接
greeting = "Hello" + " " + "World"
print(greeting)  # Hello World
```""",

        "data_structures.txt": """# Python 数据结构

## 列表 (List)
有序、可变的序列:
```python
fruits = ["apple", "banana", "cherry"]
fruits.append("date")        # 添加元素
fruits.remove("banana")      # 删除元素
print(fruits[0])             # apple (索引访问)
print(fruits[1:3])           # ['banana', 'cherry'] (切片)
```

## 字典 (Dict)
键值对集合:
```python
person = {
    "name": "Alice",
    "age": 25,
    "city": "Beijing"
}
print(person["name"])        # Alice
person["email"] = "a@b.com" # 添加键值对
del person["age"]            # 删除键值对
```

## 元组 (Tuple)
有序、不可变的序列:
```python
colors = ("red", "green", "blue")
print(colors[0])             # red
# colors[0] = "yellow"       # ❌ 报错！元组不可变
```

## 集合 (Set)
无序、不重复的元素集合:
```python
numbers = {1, 2, 3, 3, 4}   # 自动去重
print(numbers)               # {1, 2, 3, 4}
numbers.add(5)
numbers.discard(2)
```

## 选择合适的数据结构
| 需求 | 数据结构 |
|------|----------|
| 有序集合 | list |
| 快速查找 | dict |
| 不可变数据 | tuple |
| 去重 | set |
""",

        "control_flow.txt": """# Python 控制流

## 条件语句
```python
age = 18

if age >= 18:
    print("成年人")
elif age >= 12:
    print("青少年")
else:
    print("儿童")
```

## for 循环
```python
# 遍历列表
for fruit in ["apple", "banana", "cherry"]:
    print(fruit)

# 使用 range
for i in range(5):
    print(i)  # 0, 1, 2, 3, 4

# 带索引遍历
for index, fruit in enumerate(["apple", "banana"]):
    print(f"{index}: {fruit}")
```

## while 循环
```python
count = 0
while count < 5:
    print(count)
    count += 1
```

## 列表推导式
```python
# 基本语法: [expression for item in iterable if condition]
squares = [x**2 for x in range(10)]
even_squares = [x**2 for x in range(10) if x % 2 == 0]
print(squares)       # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
print(even_squares)  # [0, 4, 16, 36, 64]
```

## 异常处理
```python
try:
    result = 10 / 0
except ZeroDivisionError:
    print("除以零错误")
except Exception as e:
    print(f"其他错误: {e}")
finally:
    print("总是执行")
```
"""
    }

    for filename, content in docs.items():
        filepath = doc_dir / filename
        if not filepath.exists():
            filepath.write_text(content, encoding="utf-8")
            print(f"  📝 创建: {filename}")

    return doc_dir


# ============================================================
# 文档处理
# ============================================================

def load_and_split_docs(doc_dir):
    """加载并分割文档"""
    from langchain_community.document_loaders import DirectoryLoader, TextLoader

    loader = DirectoryLoader(
        str(doc_dir),
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()
    print(f"📄 加载了 {len(documents)} 个文档")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=ChatConfig.CHUNK_SIZE,
        chunk_overlap=ChatConfig.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", "，", " "]
    )
    chunks = splitter.split_documents(documents)
    print(f"✂️  分割为 {len(chunks)} 个文本块")
    return chunks


# ============================================================
# 向量存储
# ============================================================

def get_or_create_vectorstore(chunks):
    """获取或创建向量存储"""
    faiss_dir = Path(ChatConfig.FAISS_DIR)

    if faiss_dir.exists():
        print("📂 加载已有的向量索引...")
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vectorstore = FAISS.load_local(
            str(faiss_dir), embeddings, allow_dangerous_deserialization=True
        )
    else:
        print("🆕 创建新的向量索引...")
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vectorstore = FAISS.from_documents(chunks, embeddings)
        vectorstore.save_local(str(faiss_dir))
        print("💾 索引已保存")

    print(f"📊 索引大小: {vectorstore.index.ntotal} 个向量")
    return vectorstore


# ============================================================
# RAG Chain 构建
# ============================================================

def build_chat_chain(vectorstore):
    """构建支持多轮对话的 RAG Chain"""
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": ChatConfig.TOP_K}
    )

    llm = ChatOpenAI(model=ChatConfig.LLM_MODEL, temperature=ChatConfig.TEMPERATURE)

    def format_docs(docs):
        parts = []
        for i, doc in enumerate(docs):
            source = Path(doc.metadata.get("source", "未知")).name
            parts.append(f"[来源: {source}]\n{doc.page_content}")
        return "\n\n---\n\n".join(parts)

    # 带历史记录的提示词
    prompt = ChatPromptTemplate.from_messages([
        ("system", ChatConfig.SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", """
请根据以下文档上下文回答问题。

文档上下文：
{context}

问题：{question}
""")
    ])

    def contextualize_question(input_dict):
        """将用户问题与对话历史结合，生成独立的查询"""
        if not input_dict.get("chat_history"):
            return input_dict["question"]

        contextualize_prompt = ChatPromptTemplate.from_template("""
基于对话历史和用户最新的问题，生成一个独立的查询。
不要回答问题，只需要生成查询。如果问题已经是独立的，直接返回原问题。

对话历史：
{chat_history}

最新问题：{question}

独立查询：""")

        chain = contextualize_prompt | llm | StrOutputParser()
        return chain.invoke({
            "chat_history": "\n".join(
                f"{'用户' if isinstance(m, HumanMessage) else '助手'}: {m.content}"
                for m in input_dict["chat_history"]
            ),
            "question": input_dict["question"]
        })

    # 完整 Chain
    rag_chain = (
        {
            "context": RunnablePassthrough.assign(
                question=lambda x: contextualize_question(x)
            )["question"] | retriever | format_docs,
            "question": RunnablePassthrough.assign(
                question=lambda x: contextualize_question(x)
            )["question"],
            "chat_history": lambda x: x["chat_history"]
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain, retriever


# ============================================================
# 交互式聊天
# ============================================================

def run_chat(rag_chain, retriever):
    """运行交互式聊天"""
    print("\n" + "=" * 60)
    print("🤖 本地文档问答机器人")
    print("=" * 60)
    print("命令: quit/exit 退出 | clear 清空历史 | docs 查看检索结果")
    print("=" * 60)

    chat_history = []

    while True:
        try:
            user_input = input("\n👤 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not user_input:
            continue

        # 特殊命令
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break

        if user_input.lower() == "clear":
            chat_history.clear()
            print("🗑️  对话历史已清空")
            continue

        if user_input.lower() == "docs":
            query = input("输入查看检索结果的查询: ").strip() or "Python"
            results = retriever.invoke(query)
            print(f"\n📋 检索到 {len(results)} 个相关文档:")
            for i, doc in enumerate(results):
                source = Path(doc.metadata.get("source", "N/A")).name
                print(f"\n--- 文档 {i+1} ({source}) ---")
                print(doc.page_content[:300])
            continue

        # 正常问答
        try:
            answer = rag_chain.invoke({
                "question": user_input,
                "chat_history": chat_history
            })

            print(f"\n🤖 助手: {answer}")

            # 更新历史
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=answer))

            # 限制历史长度（保留最近 10 轮）
            if len(chat_history) > 20:
                chat_history = chat_history[-20:]

        except Exception as e:
            print(f"\n❌ 错误: {e}")
            print("提示: 请确保设置了有效的 OPENAI_API_KEY 环境变量")


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 本地文档问答机器人启动")
    print("=" * 60)

    # 1. 创建示例文档
    print("\n📁 Step 1: 准备文档...")
    doc_dir = create_sample_docs()

    # 2. 加载和分割
    print("\n📂 Step 2: 加载文档...")
    chunks = load_and_split_docs(doc_dir)

    # 3. 创建/加载向量存储
    print("\n💾 Step 3: 向量化...")
    try:
        vectorstore = get_or_create_vectorstore(chunks)
    except Exception as e:
        print(f"❌ 向量化失败: {e}")
        print("请确保设置了 OPENAI_API_KEY 环境变量")
        sys.exit(1)

    # 4. 构建 Chain
    print("\n🔗 Step 4: 构建 RAG Chain...")
    try:
        rag_chain, retriever = build_chat_chain(vectorstore)
    except Exception as e:
        print(f"❌ Chain 构建失败: {e}")
        sys.exit(1)

    # 5. 开始聊天
    run_chat(rag_chain, retriever)
