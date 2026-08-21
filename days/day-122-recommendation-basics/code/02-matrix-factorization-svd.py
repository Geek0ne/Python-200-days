#!/usr/bin/env python3
"""
Day 122 - 矩阵分解 SVD
演示 SVD 和 ALS 矩阵分解在推荐系统中的应用
"""

import numpy as np
from collections import defaultdict


# ============================================================
# 1. 构造评分矩阵
# ============================================================

movies = ["泰坦尼克号", "盗梦空间", "战狼2", "流浪地球", "你好李焕英", "疯狂动物城"]
users = ["Alice", "Bob", "Charlie", "David", "Eve"]

ratings = np.array([
    [5, 4, 0, 0, 1, 3],
    [0, 5, 4, 4, 0, 0],
    [4, 0, 5, 3, 2, 0],
    [3, 0, 0, 5, 4, 2],
    [0, 3, 0, 0, 5, 4],
])

print("评分矩阵:")
for i, user in enumerate(users):
    print(f"  {user}: {ratings[i]}")


# ============================================================
# 2. SVD 奇异值分解
# ============================================================

print("\n" + "=" * 60)
print("SVD 奇异值分解")
print("=" * 60)

# 对评分矩阵做 SVD (先填充0为均值，避免奇异值退化)
# 实际应用中会用更复杂的填充策略
rating_mean = ratings[ratings > 0].mean()
ratings_filled = ratings.copy()
ratings_filled[ratings_filled == 0] = rating_mean

U, sigma, Vt = np.linalg.svd(ratings_filled, full_matrices=False)

print(f"\n原始矩阵形状: {ratings.shape}")
print(f"U 形状: {U.shape}")
print(f"sigma 形状: {sigma.shape}")
print(f"Vt 形状: {Vt.shape}")
print(f"\n奇异值: {sigma}")
print(f"奇异值占比: {sigma / sigma.sum() * 100}")

# 选择前 k 个奇异值进行降维
k = 2  # 2个隐因子
U_k = U[:, :k]
sigma_k = np.diag(sigma[:k])
Vt_k = Vt[:k, :]

# 重构评分矩阵
R_approx = U_k @ sigma_k @ Vt_k

print(f"\n降维后的矩阵形状: k={k}")
print(f"\n重构后的预测评分矩阵:")
print(f"{'':>12}", end="")
for m in movies:
    print(f"{m:>10}", end="")
print()
for i, user in enumerate(users):
    print(f"{user:>12}", end="")
    for j in range(len(movies)):
        print(f"{R_approx[i][j]:>10.2f}", end="")
    print()


# ============================================================
# 3. ALS (交替最小二乘法) 矩阵分解
# ============================================================

print("\n" + "=" * 60)
print("ALS 交替最小二乘法")
print("=" * 60)


class ALSMatrixFactorization:
    """
    ALS (Alternating Least Squares) 矩阵分解
    
    通过交替固定 P 和 Q 来优化目标函数:
    min Σ (rᵤᵢ - pᵤ·qᵢ)² + λ(||pᵤ||² + ||qᵢ||²)
    """
    
    def __init__(self, n_factors=2, n_epochs=50, lr=0.01, reg=0.1):
        """
        参数:
            n_factors: 隐因子数量
            n_epochs: 迭代次数
            lr: 学习率 (SGD模式)
            reg: 正则化系数
        """
        self.n_factors = n_factors
        self.n_epochs = n_epochs
        self.reg = reg
        self.P = None  # 用户特征矩阵
        self.Q = None  # 物品特征矩阵
        self.b_u = None  # 用户偏置
        self.b_i = None  # 物品偏置
        self.b = 0  # 全局偏置
    
    def fit(self, ratings_matrix):
        """训练 ALS 模型"""
        n_users, n_items = ratings_matrix.shape
        
        # 初始化
        self.P = np.random.normal(0, 0.1, (n_users, self.n_factors))
        self.Q = np.random.normal(0, 0.1, (n_items, self.n_factors))
        self.b_u = np.zeros(n_users)
        self.b_i = np.zeros(n_items)
        self.b = ratings_matrix[ratings_matrix > 0].mean()
        
        # 记录训练误差
        self.history = []
        
        for epoch in range(self.n_epochs):
            # 固定 Q，更新 P
            for u in range(n_users):
                rated_items = np.where(ratings_matrix[u] > 0)[0]
                if len(rated_items) == 0:
                    continue
                
                Q_rated = self.Q[rated_items]
                r_rated = ratings_matrix[u, rated_items] - self.b - self.b_u[u] - self.b_i[rated_items]
                
                # 闭式解
                A = Q_rated.T @ Q_rated + self.reg * np.eye(self.n_factors)
                b = Q_rated.T @ r_rated
                self.P[u] = np.linalg.solve(A, b)
            
            # 固定 P，更新 Q
            for i in range(n_items):
                rated_users = np.where(ratings_matrix[:, i] > 0)[0]
                if len(rated_users) == 0:
                    continue
                
                P_rated = self.P[rated_users]
                r_rated = ratings_matrix[rated_users, i] - self.b - self.b_u[rated_users] - self.b_i[i]
                
                A = P_rated.T @ P_rated + self.reg * np.eye(self.n_factors)
                b = P_rated.T @ r_rated
                self.Q[i] = np.linalg.solve(A, b)
            
            # 计算 RMSE
            pred = self.predict_all()
            mask = ratings_matrix > 0
            rmse = np.sqrt(np.mean((ratings_matrix[mask] - pred[mask]) ** 2))
            self.history.append(rmse)
            
            if (epoch + 1) % 10 == 0:
                print(f"  Epoch {epoch+1:>3}: RMSE = {rmse:.4f}")
    
    def predict(self, user_idx, item_idx):
        """预测单个评分"""
        return (self.b + self.b_u[user_idx] + self.b_i[item_idx] +
                np.dot(self.P[user_idx], self.Q[item_idx]))
    
    def predict_all(self):
        """预测所有评分"""
        return self.b + self.b_u[:, None] + self.b_i[None, :] + self.P @ self.Q.T


# 训练 ALS 模型
print("\n训练 ALS 模型:")
als = ALSMatrixFactorization(n_factors=2, n_epochs=50, reg=0.1)
als.fit(ratings)

print(f"\n最终 RMSE: {als.history[-1]:.4f}")

# 预测结果
print(f"\nALS 预测评分矩阵:")
print(f"{'':>12}", end="")
for m in movies:
    print(f"{m:>10}", end="")
print()
for i, user in enumerate(users):
    print(f"{user:>12}", end="")
    for j in range(len(movies)):
        original = ratings[i][j]
        predicted = als.predict(i, j)
        if original == 0:
            print(f"  {predicted:>7.2f}*", end="")
        else:
            print(f"  {predicted:>7.2f} ", end="")
    print()
print("  (* = 预测值)")


# ============================================================
# 4. 隐因子解释
# ============================================================

print("\n" + "=" * 60)
print("隐因子解释")
print("=" * 60)

print("\n用户特征矩阵 P (每个用户的隐因子向量):")
print(f"{'':>12}", end="")
for k_idx in range(als.n_factors):
    print(f"  隐因子{k_idx+1:>8}", end="")
print()
for i, user in enumerate(users):
    print(f"{user:>12}", end="")
    for k_idx in range(als.n_factors):
        print(f"{als.P[i][k_idx]:>10.3f}", end="")
    print()

print("\n物品特征矩阵 Q (每个物品的隐因子向量):")
print(f"{'':>12}", end="")
for k_idx in range(als.n_factors):
    print(f"  隐因子{k_idx+1:>8}", end="")
print()
for j, movie in enumerate(movies):
    print(f"{movie:>12}", end="")
    for k_idx in range(als.n_factors):
        print(f"{als.Q[j][k_idx]:>10.3f}", end="")
    print()

# 隐因子语义分析
print("\n隐因子语义分析 (基于向量方向):")
factor_names = ["因子1", "因子2"]

# 找出每个因子中得分最高的用户和物品
for f in range(als.n_factors):
    top_user_idx = np.argmax(als.P[:, f])
    top_item_idx = np.argmax(als.Q[:, f])
    print(f"  {factor_names[f]}: 最高用户={users[top_user_idx]}({als.P[top_user_idx][f]:.3f}), "
          f"最高物品={movies[top_item_idx]}({als.Q[top_item_idx][f]:.3f})")


# ============================================================
# 5. 生成推荐
# ============================================================

print("\n" + "=" * 60)
print("ALS 推荐结果")
print("=" * 60)

for i, user in enumerate(users):
    # 找出未评过分的物品
    unrated = []
    for j in range(len(movies)):
        if ratings[i][j] == 0:
            pred = als.predict(i, j)
            unrated.append((movies[j], pred))
    
    unrated.sort(key=lambda x: x[1], reverse=True)
    
    if unrated:
        print(f"\n{user} 的推荐 (未看过):")
        for movie, score in unrated[:3]:
            print(f"  {movie}: 预测评分 {score:.2f}")


# ============================================================
# 6. ALS vs SVD 对比
# ============================================================

print("\n" + "=" * 60)
print("ALS vs SVD 对比")
print("=" * 60)

# SVD 预测
svd_pred = R_approx

# ALS 预测
als_pred = als.predict_all()

# 只比较非零项
mask = ratings > 0
svd_rmse = np.sqrt(np.mean((ratings[mask] - svd_pred[mask]) ** 2))
als_rmse = np.sqrt(np.mean((ratings[mask] - als_pred[mask]) ** 2))

print(f"\n在训练数据上的 RMSE:")
print(f"  SVD (k={k}): {svd_rmse:.4f}")
print(f"  ALS (k={als.n_factors}): {als_rmse:.4f}")
print(f"\n结论: {'ALS' if als_rmse < svd_rmse else 'SVD'} 在此数据集上表现更优")


# ============================================================
# 7. 运行验证
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("✅ 矩阵分解 SVD 演示完成！")
    print("=" * 60)
    print("""
核心要点:
1. SVD 将评分矩阵分解为 U × Σ × Vᵀ
2. 截断 SVD 只保留前 k 个奇异值实现降维
3. ALS 通过交替优化 P 和 Q 来训练矩阵分解模型
4. 隐因子 (latent factor) 代表潜在的用户兴趣维度
5. 矩阵分解能有效处理稀疏数据，是推荐系统的核心算法
""")
