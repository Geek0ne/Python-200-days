#!/usr/bin/env python3
"""
Day 122 - 协同过滤基础
演示 User-Based 和 Item-Based 协同过滤的核心算法
"""

import numpy as np
from collections import defaultdict


# ============================================================
# 1. 构造示例评分数据
# ============================================================
# 用户-物品评分矩阵
# 行: 用户, 列: 物品
# 0 表示未评分

movies = ["泰坦尼克号", "盗梦空间", "战狼2", "流浪地球", "你好李焕英", "疯狂动物城"]
users = ["Alice", "Bob", "Charlie", "David", "Eve"]

# 评分矩阵 (5个用户 × 6部电影)
ratings = np.array([
    [5, 4, 0, 0, 1, 3],   # Alice: 喜欢泰坦尼克号、盗梦空间
    [0, 5, 4, 4, 0, 0],   # Bob: 喜欢盗梦空间、战狼2、流浪地球
    [4, 0, 5, 3, 2, 0],   # Charlie: 喜欢泰坦尼克号、战狼2
    [3, 0, 0, 5, 4, 2],   # David: 喜欢流浪地球、你好李焕英
    [0, 3, 0, 0, 5, 4],   # Eve: 喜欢你好李焕英、疯狂动物城
])

print("=" * 60)
print("用户-物品评分矩阵")
print("=" * 60)
print(f"{'':>12}", end="")
for m in movies:
    print(f"{m:>10}", end="")
print()
for i, user in enumerate(users):
    print(f"{user:>12}", end="")
    for j in range(len(movies)):
        val = ratings[i][j]
        print(f"{val:>10}", end="" if val != 0 else "        -")
    print()


# ============================================================
# 2. 相似度计算
# ============================================================

def cosine_similarity(u, v):
    """计算两个向量的余弦相似度"""
    dot = np.dot(u, v)
    norm_u = np.linalg.norm(u)
    norm_v = np.linalg.norm(v)
    if norm_u == 0 or norm_v == 0:
        return 0.0
    return dot / (norm_u * norm_v)


def pearson_correlation(u, v):
    """计算皮尔逊相关系数（考虑用户评分偏差）"""
    # 只考虑两者都评了分的物品
    mask = (u != 0) & (v != 0)
    if mask.sum() == 0:
        return 0.0
    u_rated = u[mask]
    v_rated = v[mask]
    u_mean = u_rated.mean()
    v_mean = v_rated.mean()
    
    numerator = np.sum((u_rated - u_mean) * (v_rated - v_mean))
    denominator = np.sqrt(np.sum((u_rated - u_mean)**2) * np.sum((v_rated - v_mean)**2))
    
    if denominator == 0:
        return 0.0
    return numerator / denominator


# 计算用户之间的相似度矩阵
n_users = len(users)
user_sim_matrix = np.zeros((n_users, n_users))

print("\n" + "=" * 60)
print("用户相似度矩阵 (皮尔逊相关系数)")
print("=" * 60)

for i in range(n_users):
    for j in range(n_users):
        user_sim_matrix[i][j] = pearson_correlation(ratings[i], ratings[j])

print(f"{'':>12}", end="")
for user in users:
    print(f"{user:>10}", end="")
print()
for i, user in enumerate(users):
    print(f"{user:>12}", end="")
    for j in range(n_users):
        print(f"{user_sim_matrix[i][j]:>10.3f}", end="")
    print()


# ============================================================
# 3. User-Based 协同过滤
# ============================================================

def predict_user_based(ratings, user_sim_matrix, target_user_idx, target_item_idx, k=3):
    """
    User-Based CF: 基于用户的协同过滤预测评分
    
    参数:
        ratings: 评分矩阵
        user_sim_matrix: 用户相似度矩阵
        target_user_idx: 目标用户索引
        target_item_idx: 目标物品索引
        k: 选择最相似的k个用户
    """
    # 找到对该物品评过分的用户
    rated_users = []
    for u in range(len(ratings)):
        if u != target_user_idx and ratings[u][target_item_idx] != 0:
            sim = user_sim_matrix[target_user_idx][u]
            rated_users.append((u, sim, ratings[u][target_item_idx]))
    
    if not rated_users:
        return 0.0
    
    # 按相似度排序，取top-k
    rated_users.sort(key=lambda x: x[1], reverse=True)
    top_k = rated_users[:k]
    
    # 加权平均预测评分
    numerator = sum(sim * rating for _, sim, rating in top_k)
    denominator = sum(abs(sim) for _, sim, _ in top_k)
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator


# 为 Alice 预测对《战狼2》的评分
target_user = 0  # Alice
target_item = 2  # 战狼2
pred = predict_user_based(ratings, user_sim_matrix, target_user, target_item, k=3)
print(f"\nUser-Based CF: {users[target_user]} 对 《{movies[target_item]}》 的预测评分: {pred:.2f}")


# ============================================================
# 4. Item-Based 协同过滤
# ============================================================

def compute_item_similarity(ratings):
    """计算物品之间的余弦相似度"""
    n_items = ratings.shape[1]
    item_sim = np.zeros((n_items, n_items))
    
    for i in range(n_items):
        for j in range(n_items):
            # 取两个物品都被评过分的用户
            mask = (ratings[:, i] != 0) & (ratings[:, j] != 0)
            if mask.sum() == 0:
                continue
            vec_i = ratings[mask, i]
            vec_j = ratings[mask, j]
            item_sim[i][j] = cosine_similarity(vec_i, vec_j)
    
    return item_sim


def predict_item_based(ratings, item_sim_matrix, target_user_idx, target_item_idx, k=3):
    """
    Item-Based CF: 基于物品的协同过滤预测评分
    
    参数:
        ratings: 评分矩阵
        item_sim_matrix: 物品相似度矩阵
        target_user_idx: 目标用户索引
        target_item_idx: 目标物品索引
        k: 选择最相似的k个物品
    """
    # 找到目标用户评过分的物品
    rated_items = []
    for i in range(ratings.shape[1]):
        if i != target_item_idx and ratings[target_user_idx][i] != 0:
            sim = item_sim_matrix[target_item_idx][i]
            rated_items.append((i, sim, ratings[target_user_idx][i]))
    
    if not rated_items:
        return 0.0
    
    # 按相似度排序，取top-k
    rated_items.sort(key=lambda x: x[1], reverse=True)
    top_k = rated_items[:k]
    
    # 加权平均
    numerator = sum(sim * rating for _, sim, rating in top_k)
    denominator = sum(abs(sim) for _, sim, _ in top_k)
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator


item_sim_matrix = compute_item_similarity(ratings)

print("\n" + "=" * 60)
print("物品相似度矩阵 (余弦相似度)")
print("=" * 60)
print(f"{'':>12}", end="")
for m in movies:
    print(f"{m:>10}", end="")
print()
for i, m in enumerate(movies):
    print(f"{m:>12}", end="")
    for j in range(len(movies)):
        print(f"{item_sim_matrix[i][j]:>10.3f}", end="")
    print()

# 为 Alice 预测对《战狼2》的评分
pred_item = predict_item_based(ratings, item_sim_matrix, target_user, target_item, k=3)
print(f"\nItem-Based CF: {users[target_user]} 对 《{movies[target_item]}》 的预测评分: {pred_item:.2f}")


# ============================================================
# 5. 为用户生成推荐列表
# ============================================================

def recommend_user_based(ratings, user_sim_matrix, user_idx, n=3, k=3):
    """为指定用户推荐 n 个未评过分的物品"""
    unrated_items = []
    for i in range(ratings.shape[1]):
        if ratings[user_idx][i] == 0:
            pred = predict_user_based(ratings, user_sim_matrix, user_idx, i, k)
            unrated_items.append((movies[i], pred))
    
    unrated_items.sort(key=lambda x: x[1], reverse=True)
    return unrated_items[:n]


def recommend_item_based(ratings, item_sim_matrix, user_idx, n=3, k=3):
    """为指定用户推荐 n 个未评过分的物品"""
    unrated_items = []
    for i in range(ratings.shape[1]):
        if ratings[user_idx][i] == 0:
            pred = predict_item_based(ratings, item_sim_matrix, user_idx, i, k)
            unrated_items.append((movies[i], pred))
    
    unrated_items.sort(key=lambda x: x[1], reverse=True)
    return unrated_items[:n]


# 为每个用户生成推荐
print("\n" + "=" * 60)
print("推荐结果对比: User-Based vs Item-Based CF")
print("=" * 60)

for i, user in enumerate(users):
    user_recs = recommend_user_based(ratings, user_sim_matrix, i, n=2, k=3)
    item_recs = recommend_item_based(ratings, item_sim_matrix, i, n=2, k=3)
    
    print(f"\n{user} 的推荐:")
    print(f"  User-Based: {[(m, f'{s:.2f}') for m, s in user_recs]}")
    print(f"  Item-Based: {[(m, f'{s:.2f}') for m, s in item_recs]}")


# ============================================================
# 6. 运行验证
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("✅ 协同过滤基础演示完成！")
    print("=" * 60)
    print("""
核心要点:
1. User-Based CF: 找相似用户，用邻居的评分预测
2. Item-Based CF: 找相似物品，用用户对相似物品的评分预测
3. 皮尔逊相关系数 > 余弦相似度 (考虑了评分偏差)
4. k值(邻居数)是重要超参数，需要调优
5. 实际应用中需要处理稀疏性、冷启动等问题
""")
