#!/usr/bin/env python3
"""
Day 118 - 代码示例 3：文本分类实战
功能：完整的中文新闻文本分类流水线
依赖：pip install jieba scikit-learn numpy
"""

import jieba
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

# ═══════════════════════════════════════════════════════════════
# 第一部分：准备数据集
# ═══════════════════════════════════════════════════════════════

# 模拟中文新闻数据集（实际项目中可从数据集文件加载）
NEWS_DATA = {
    "科技": [
        "苹果公司发布新一代iPhone手机搭载最新处理器",
        "华为鸿蒙操作系统获得重大更新升级",
        "人工智能在医疗影像诊断领域取得重要突破",
        "特斯拉全自动驾驶系统正式推向市场",
        "谷歌发布最新大语言模型性能再创新高",
        "量子计算机成功实现百量子比特突破",
        "5G网络技术在智慧城市中的应用日益广泛",
        "SpaceX星舰成功完成轨道飞行测试",
        "微软宣布新一代云计算平台正式上线",
        "英伟达GPU芯片需求持续增长推动股价上涨",
        "区块链技术在供应链管理中的应用前景广阔",
        "国产芯片自主研发取得重要进展",
    ],
    "体育": [
        "中国女排在世界女排联赛中夺冠",
        "世界杯亚洲区预选赛中国队取得关键胜利",
        "姚明当选中国篮球协会新一届主席",
        "北京冬奥会场馆建设工作全面完成",
        "刘翔退役后致力于青少年田径运动推广",
        "中超足球联赛新赛季正式拉开帷幕",
        "中国游泳队在世锦赛上摘得多枚金牌",
        "NBA总决赛精彩纷呈湖人队赢得总冠军",
        "中国乒乓球队包揽世乒赛全部金牌",
        "马拉松赛事在全国各大城市蓬勃发展",
        "中国短跑选手在亚洲田径锦标赛上创佳绩",
        "奥运会筹备工作有条不紊推进中",
    ],
    "财经": [
        "中国人民银行宣布下调金融机构存款准备金率",
        "沪深两市今日大幅上涨沪指突破三千点",
        "国家出台新一轮房地产市场调控政策措施",
        "比特币价格再次突破历史最高纪录",
        "新能源汽车企业获得大额融资估值飙升",
        "外资机构持续看好A股市场增加配置",
        "央行发布最新季度货币政策执行报告",
        "科技板块股票估值水平引发市场广泛讨论",
        "国务院常务会议部署稳经济一揽子措施",
        "银保监会发布银行业监管新规",
        "上市公司年报季开启业绩分化明显",
        "人民币汇率在合理均衡水平上保持基本稳定",
    ],
    "娱乐": [
        "春节档电影票房突破百亿元创历史新高",
        "热门综艺节目收视率持续领跑同时段",
        "知名导演新作品获得国际电影节大奖",
        "网络直播带货成为新型消费模式",
        "短视频平台日活跃用户数突破新纪录",
        "国产动画电影票房口碑双丰收",
        "音乐节演出市场迎来全面复苏",
        "演员参加公益活动引发社会关注",
        "游戏行业年度盛会吸引大量玩家参与",
        "影视剧组在横店影视城紧张拍摄中",
        "网红餐厅排队现象引发热议",
        "选秀节目决赛之夜精彩纷呈",
    ],
}

# 预处理
stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
             "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会",
             "着", "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那",
             "被", "从", "把", "让", "给", "对", "与", "以", "及", "等", "但",
             "而", "如", "或", "之", "其", "已", "将", "更", "新", "为", "于",
             "中", "后", "前", "可", "能", "所", "此", "大", "小", "多", "少",
             "用", "做", "年", "月", "日", "号", "个", "次", "种", "些", "最"}


def preprocess(text):
    """分词 + 清洗"""
    words = jieba.cut(text)
    return " ".join([w for w in words if w not in stopwords and len(w.strip()) > 1])


# 构建数据集
texts = []
labels = []
for category, articles in NEWS_DATA.items():
    for article in articles:
        texts.append(article)
        labels.append(category)

# 预处理所有文本
processed_texts = [preprocess(t) for t in texts]

print("=" * 60)
print("📊 数据集概览")
print("=" * 60)
print(f"  总样本数: {len(texts)}")
print(f"  类别数量: {len(set(labels))}")
for cat in set(labels):
    count = labels.count(cat)
    print(f"    {cat}: {count} 篇")
print()

# 打印预处理示例
print("  预处理示例:")
for i in range(3):
    print(f"    原文: {texts[i]}")
    print(f"    处理: {processed_texts[i]}")
    print()


# ═══════════════════════════════════════════════════════════════
# 第二部分：模型训练与评估
# ═══════════════════════════════════════════════════════════════

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    processed_texts, labels, test_size=0.25, random_state=42, stratify=labels
)

print("=" * 60)
print("🔧 模型训练与对比")
print("=" * 60)

# 定义多个分类器
classifiers = {
    "朴素贝叶斯": Pipeline([
        ("tfidf", TfidfVectorizer(max_features=3000, ngram_range=(1, 2))),
        ("clf", MultinomialNB(alpha=0.1))
    ]),
    "逻辑回归": Pipeline([
        ("tfidf", TfidfVectorizer(max_features=3000, ngram_range=(1, 2))),
        ("clf", LogisticRegression(C=1.0, max_iter=1000, solver='lbfgs', multi_class='multinomial'))
    ]),
    "SVM": Pipeline([
        ("tfidf", TfidfVectorizer(max_features=3000, ngram_range=(1, 2))),
        ("clf", LinearSVC(C=1.0, max_iter=2000))
    ]),
}

results = {}
for name, clf in classifiers.items():
    # 训练
    clf.fit(X_train, y_train)

    # 预测
    y_pred = clf.predict(X_test)

    # 评估
    from sklearn.metrics import accuracy_score
    acc = accuracy_score(y_test, y_pred)
    results[name] = acc

    print(f"\n  {name}:")
    print(f"    准确率: {acc:.2%}")
    print(f"    详细报告:")
    report = classification_report(y_test, y_pred, zero_division=0, output_dict=True)
    for cat in set(y_test):
        if cat in report:
            p = report[cat]['precision']
            r = report[cat]['recall']
            f1 = report[cat]['f1-score']
            print(f"      {cat:4s}: P={p:.2%} R={r:.2%} F1={f1:.2%}")

print(f"\n  📈 模型对比:")
for name, acc in sorted(results.items(), key=lambda x: x[1], reverse=True):
    bar = "█" * int(acc * 40)
    print(f"    {name:8s}: {acc:.2%} {bar}")


# ═══════════════════════════════════════════════════════════════
# 第三部分：交叉验证
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("🔄 交叉验证（5-fold）")
print("=" * 60)

best_name = max(results, key=results.get)
best_clf = classifiers[best_name]

cv_scores = cross_val_score(best_clf, processed_texts, labels, cv=5, scoring='accuracy')
print(f"  最佳模型: {best_name}")
print(f"  5 折交叉验证准确率:")
for i, score in enumerate(cv_scores):
    print(f"    折 {i+1}: {score:.2%}")
print(f"    平均: {cv_scores.mean():.2%} (+/- {cv_scores.std() * 2:.2%})")


# ═══════════════════════════════════════════════════════════════
# 第四部分：新文本预测
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("🔮 新文本预测")
print("=" * 60)

new_texts = [
    "研究人员开发出新型电池技术大幅提高能量密度",
    "世界杯足球赛决赛将在今晚举行球迷热情高涨",
    "央行宣布下调存款准备金率释放流动性",
    "暑期档电影票房持续走高观众观影热情不减",
    "自动驾驶出租车在多个城市开始试运营",
    "奥运会游泳比赛中国选手打破亚洲纪录",
]

best_clf.fit(processed_texts, labels)  # 用全部数据重新训练

for text in new_texts:
    processed = preprocess(text)
    pred = best_clf.predict([processed])[0]

    # 获取概率（如果分类器支持）
    if hasattr(best_clf.named_steps['clf'], 'predict_proba'):
        proba = best_clf.predict_proba([processed])[0]
        classes = best_clf.classes_
        proba_info = ", ".join([f"{c}:{p:.0%}" for c, p in sorted(zip(classes, proba), key=lambda x: -x[1])])
        print(f"\n  📰 {text}")
        print(f"    → 分类: {pred} | 概率: {proba_info}")
    else:
        print(f"\n  📰 {text}")
        print(f"    → 分类: {pred}")


# ═══════════════════════════════════════════════════════════════
# 第五部分：特征词分析（可解释性）
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("📝 各类别最重要的特征词")
print("=" * 60)

# 使用逻辑回归（支持 coef_）
lr_pipeline = classifiers["逻辑回归"]
lr_pipeline.fit(processed_texts, labels)
feature_names = lr_pipeline.named_steps['tfidf'].get_feature_names_out()
clf = lr_pipeline.named_steps['clf']

for i, category in enumerate(clf.classes_):
    coef = clf.coef_[i]
    top_indices = coef.argsort()[-8:][::-1]
    top_words = [feature_names[idx] for idx in top_indices]
    print(f"\n  {category}类核心词:")
    for idx in top_indices:
        word = feature_names[idx]
        weight = coef[idx]
        bar = "█" * int(abs(weight) * 5)
        print(f"    {word:8s} 权重={weight:.4f} {bar}")
