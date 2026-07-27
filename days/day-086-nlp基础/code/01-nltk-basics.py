"""
Day 086 - NLTK 基础用法示例
演示 NLTK 的核心 NLP 功能：分词、词性标注、停用词、词干提取
运行前需安装: pip install nltk && python -c "import nltk; nltk.download('all')"
"""
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk import pos_tag
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer

# ========================================
# 1. 文本分词
# ========================================
print("=" * 50)
print("1. 文本分词")
print("=" * 50)

text = "Dr. Smith said: 'NLP is amazing!' Isn't it? Yes, it is."

# 句子分词
sentences = sent_tokenize(text)
print(f"\n原文: {text}")
print(f"\n句子分词 ({len(sentences)} 句):")
for i, s in enumerate(sentences, 1):
    print(f"  [{i}] {s}")

# 词级分词
words = word_tokenize(text)
print(f"\n词级分词 ({len(words)} 词):")
print(f"  {words}")

# ========================================
# 2. 词性标注
# ========================================
print("\n" + "=" * 50)
print("2. 词性标注 (POS Tagging)")
print("=" * 50)

sentence = "The quick brown fox jumps over the lazy dog"
words = word_tokenize(sentence)
tags = pos_tag(words)

print(f"\n句子: {sentence}")
print(f"\n词性标注结果:")
for word, tag in tags:
    print(f"  {word:10s} → {tag}")

# 按词性分组
from collections import defaultdict
pos_groups = defaultdict(list)
for word, tag in tags:
    pos_groups[tag].append(word)

print(f"\n按词性分组:")
for tag, words in pos_groups.items():
    print(f"  {tag}: {words}")

# ========================================
# 3. 停用词过滤
# ========================================
print("\n" + "=" * 50)
print("3. 停用词过滤")
print("=" * 50)

stop_words = set(stopwords.words('english'))
print(f"\n英文停用词数量: {len(stop_words)}")
print(f"部分停用词: {list(stop_words)[:10]}...")

words = word_tokenize("The quick brown fox jumps over the lazy dog")
filtered = [w for w in words if w.lower() not in stop_words]

print(f"\n原始词汇: {words}")
print(f"过滤后:   {filtered}")
print(f"移除了 {len(words) - len(filtered)} 个停用词")

# ========================================
# 4. 词干提取
# ========================================
print("\n" + "=" * 50)
print("4. 词干提取 (Stemming)")
print("=" * 50)

stemmer = PorterStemmer()

test_words = ["running", "flies", "better", "studies", "happiness", "connecting"]
print(f"\n词干提取对比:")
print(f"  {'原词':15s} → {'词干':15s}")
print(f"  {'-'*15}   {'-'*15}")
for word in test_words:
    stem = stemmer.stem(word)
    marker = "  ✓" if stem != word else "  (无变化)"
    print(f"  {word:15s} → {stem:15s}{marker}")

# ========================================
# 5. 词形还原
# ========================================
print("\n" + "=" * 50)
print("5. 词形还原 (Lemmatization)")
print("=" * 50)

lemmatizer = WordNetLemmatizer()

print(f"\n词形还原对比:")
print(f"  {'原词':15s} → {'还原结果':15s}")
print(f"  {'-'*15}   {'-'*15}")

# 不指定 POS
for word in test_words:
    lemma = lemmatizer.lemmatize(word)
    marker = "  ✓" if lemma != word else "  (无变化)"
    print(f"  {word:15s} → {lemma:15s}{marker}")

# 指定 POS 更准确
print(f"\n指定 POS 的词形还原:")
pos_map = {'r': 'adv', 'v': 'verb', 'n': 'noun', 'a': 'adj'}
examples = [("better", "a"), ("running", "v"), ("flies", "n"), ("happily", "r")]
for word, pos in examples:
    lemma = lemmatizer.lemmatize(word, pos=pos)
    print(f"  {word:15s} (pos={pos}) → {lemma:15s}")

# ========================================
# 6. 词干提取 vs 词形还原
# ========================================
print("\n" + "=" * 50)
print("6. 词干提取 vs 词形还原 对比")
print("=" * 50)

comparison = ["running", "flies", "better", "studies", "ran", "was"]
print(f"\n  {'原词':12s} {'词干提取':15s} {'词形还原':15s}")
print(f"  {'-'*12} {'-'*15} {'-'*15}")
for word in comparison:
    stem = stemmer.stem(word)
    lemma = lemmatizer.lemmatize(word)
    print(f"  {word:12s} {stem:15s} {lemma:15s}")

print(f"\n总结:")
print(f"  • 词干提取: 速度快，但可能产生非词 (如 'fli', 'studi')")
print(f"  • 词形还原: 更准确，但需要词典支持，速度较慢")
print(f"  • 生产环境推荐词形还原，快速原型可用词干提取")

print("\n✅ NLTK 基础示例完成！")
