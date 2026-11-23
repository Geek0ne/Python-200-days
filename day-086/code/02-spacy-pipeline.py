"""
Day 086 - spaCy Pipeline 用法示例
演示 spaCy 的一站式 NLP 处理：分词、POS、NER、依存分析
运行前需安装: pip install spacy && python -m spacy download en_core_web_sm
"""
import spacy

# ========================================
# 1. 加载模型与基本处理
# ========================================
print("=" * 50)
print("1. spaCy 基本处理")
print("=" * 50)

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("❌ 请先下载模型: python -m spacy download en_core_web_sm")
    exit(1)

text = "Apple is looking at buying U.K. startup for $1 billion"
doc = nlp(text)

print(f"\n原文: {text}")
print(f"分词结果: {[token.text for token in doc]}")

# ========================================
# 2. Token 属性详解
# ========================================
print("\n" + "=" * 50)
print("2. Token 属性详解")
print("=" * 50)

print(f"\n{'Token':12s} {'Lemma':12s} {'POS':6s} {'Tag':6s} {'Dep':8s} {'Stop'}")
print("-" * 60)

for token in doc:
    print(f"{token.text:12s} {token.lemma_:12s} {token.pos_:6s} {token.tag_:6s} {token.dep_:8s} {token.is_stop}")

# ========================================
# 3. 命名实体识别 (NER)
# ========================================
print("\n" + "=" * 50)
print("3. 命名实体识别 (NER)")
print("=" * 50)

print(f"\n发现 {len(doc.ents)} 个命名实体:")
for ent in doc.ents:
    print(f"  {ent.text:20s} → {ent.label_:10s} ({spacy.explain(ent.label_)})")

# 实体类型统计
from collections import Counter
label_counts = Counter(ent.label_ for ent in doc.ents)
print(f"\n实体类型统计:")
for label, count in label_counts.most_common():
    print(f"  {label}: {count}")

# ========================================
# 4. 依存句法分析
# ========================================
print("\n" + "=" * 50)
print("4. 依存句法分析")
print("=" * 50)

print(f"\n依存关系:")
for token in doc:
    if token.dep_ != "punct":  # 跳过标点
        print(f"  {token.text:12s} --{token.dep_:10s}--> {token.head.text}")

# 找主语和谓语
print(f"\n句子结构:")
for token in doc:
    if token.dep_ == "nsubj":
        print(f"  主语: {token.text}")
    if token.dep_ == "ROOT":
        print(f"  谓语: {token.text}")

# ========================================
# 5. 句子分割
# ========================================
print("\n" + "=" * 50)
print("5. 句子分割")
print("=" * 50)

multi_text = "Apple is looking at buying U.K. startup. The deal is worth $1 billion. Tim Cook confirmed the news."
doc2 = nlp(multi_text)

print(f"\n原文: {multi_text}")
print(f"\n分割为 {len(list(doc2.sents))} 个句子:")
for i, sent in enumerate(doc2.sents, 1):
    print(f"  [{i}] {sent.text}")

# ========================================
# 6. 文本相似度
# ========================================
print("\n" + "=" * 50)
print("6. 文本相似度")
print("=" * 50)

# 注意: 相似度需要词向量，小模型可能不支持
try:
    nlp_md = spacy.load("en_core_web_md")
    
    pairs = [
        ("I love cats", "I adore felines"),
        ("I love cats", "I hate dogs"),
        ("The weather is nice", "It's a beautiful day"),
    ]
    
    print(f"\n文本相似度对比:")
    for text1, text2 in pairs:
        doc1 = nlp_md(text1)
        doc2 = nlp_md(text2)
        sim = doc1.similarity(doc2)
        bar = "█" * int(sim * 20)
        print(f"  '{text1}' vs '{text2}'")
        print(f"    相似度: {sim:.3f} {bar}")
except OSError:
    print("\n⚠️ 文本相似度需要 en_core_web_md 模型")
    print("   运行: python -m spacy download en_core_web_md")

# ========================================
# 7. 自定义 NLP Pipeline
# ========================================
print("\n" + "=" * 50)
print("7. 自定义 Pipeline 组件")
print("=" * 50)

# 查看当前 pipeline
print(f"\n默认 Pipeline 组件:")
for pipe_name in nlp.pipe_names:
    print(f"  • {pipe_name}")

# 添加自定义组件
from spacy.language import Language

@Language.component("custom_length_filter")
def custom_length_filter(doc):
    """过滤掉长度为1的token（标点除外）"""
    # 这里只是演示，实际使用需谨慎
    return doc

# 添加到 pipeline
# nlp.add_pipe("custom_length_filter", last=True)
print(f"\n💡 可通过 nlp.add_pipe() 添加自定义组件")
print(f"   例如: 文本清洗、实体链接、情感分析等")

# ========================================
# 8. 批量处理
# ========================================
print("\n" + "=" * 50)
print("8. 批量处理 (nlp.pipe)")
print("=" * 50)

texts = [
    "Google was founded in 1998",
    "Microsoft is based in Redmond",
    "Apple released new iPhone",
]

# 使用 nlp.pipe 批量处理（比逐条处理更高效）
docs = list(nlp.pipe(texts))

print(f"\n批量处理 {len(texts)} 条文本:")
for doc, text in zip(docs, texts):
    entities = [f"{ent.text}({ent.label_})" for ent in doc.ents]
    print(f"  '{text}'")
    print(f"    实体: {entities}")

print("\n✅ spaCy Pipeline 示例完成！")
print(f"\n💡 提示: spaCy 的优势在于:")
print(f"   • 一行代码完成全流程 (分词→POS→NER→依存)")
print(f"   • Token 对象包含丰富信息")
print(f"   • 批量处理效率高")
print(f"   • 支持自定义 Pipeline 组件")
