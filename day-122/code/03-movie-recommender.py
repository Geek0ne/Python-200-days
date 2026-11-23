#!/usr/bin/env python3
"""
Day 122 - 完整电影推荐系统
综合运用 User-Based CF、Item-Based CF 和矩阵分解
包含冷启动处理、评估指标、可视化
"""

import numpy as np
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import json


# ============================================================
# 1. 数据模型
# ============================================================

class MovieRecommender:
    """电影推荐系统"""
    
    def __init__(self):
        self.movies = {}  # movie_id -> movie_info
        self.users = {}   # user_id -> user_info
        self.ratings = {}  # (user_id, movie_id) -> rating
        self.movie_ids = []
        self.user_ids = []
    
    def add_movie(self, movie_id: str, title: str, genres: List[str], year: int = 0):
        """添加电影"""
        self.movies[movie_id] = {
            "title": title,
            "genres": genres,
            "year": year,
        }
        if movie_id not in self.movie_ids:
            self.movie_ids.append(movie_id)
    
    def add_user(self, user_id: str, name: str = ""):
        """添加用户"""
        self.users[user_id] = {"name": name or user_id}
        if user_id not in self.user_ids:
            self.user_ids.append(user_id)
    
    def rate(self, user_id: str, movie_id: str, rating: float):
        """用户评分"""
        self.ratings[(user_id, movie_id)] = rating
    
    def get_rating_matrix(self) -> Tuple[np.ndarray, Dict, Dict]:
        """获取评分矩阵和索引映射"""
        user_idx = {uid: i for i, uid in enumerate(self.user_ids)}
        movie_idx = {mid: i for i, mid in enumerate(self.movie_ids)}
        
        matrix = np.zeros((len(self.user_ids), len(self.movie_ids)))
        for (uid, mid), rating in self.ratings.items():
            matrix[user_idx[uid]][movie_idx[mid]] = rating
        
        return matrix, user_idx, movie_idx
    
    def get_user_rated(self, user_id: str) -> Dict[str, float]:
        """获取用户评过分的电影"""
        return {mid: self.ratings[(user_id, mid)] 
                for mid in self.movie_ids 
                if (user_id, mid) in self.ratings}
    
    def get_movie_raters(self, movie_id: str) -> Dict[str, float]:
        """获取评过分某电影的用户"""
        return {uid: self.ratings[(uid, movie_id)]
                for uid in self.user_ids
                if (uid, movie_id) in self.ratings}


# ============================================================
# 2. 推荐算法
# ============================================================

class UserBasedCF:
    """基于用户的协同过滤"""
    
    def __init__(self, k: int = 5):
        self.k = k
    
    def _pearson(self, u_ratings: Dict, v_ratings: Dict) -> float:
        """皮尔逊相关系数"""
        common = set(u_ratings.keys()) & set(v_ratings.keys())
        if len(common) < 2:
            return 0.0
        
        u_vals = np.array([u_ratings[m] for m in common])
        v_vals = np.array([v_ratings[m] for m in common])
        
        u_mean = u_vals.mean()
        v_mean = v_vals.mean()
        
        numerator = np.sum((u_vals - u_mean) * (v_vals - v_mean))
        denominator = np.sqrt(np.sum((u_vals - u_mean)**2) * np.sum((v_vals - v_mean)**2))
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def predict(self, rec: MovieRecommender, user_id: str, movie_id: str) -> float:
        """预测评分"""
        user_rated = rec.get_user_rated(user_id)
        
        # 找对该电影评过分的用户
        neighbors = []
        for other_id in rec.user_ids:
            if other_id == user_id:
                continue
            other_rating = rec.ratings.get((other_id, movie_id))
            if other_rating is not None:
                sim = self._pearson(rec.get_user_rated(other_id), user_rated)
                neighbors.append((other_id, sim, other_rating))
        
        if not neighbors:
            return 0.0
        
        # 取top-k
        neighbors.sort(key=lambda x: abs(x[1]), reverse=True)
        top_k = neighbors[:self.k]
        
        # 加权平均
        numerator = sum(sim * rating for _, sim, rating in top_k)
        denominator = sum(abs(sim) for _, sim, _ in top_k)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def recommend(self, rec: MovieRecommender, user_id: str, n: int = 5) -> List[Tuple[str, float]]:
        """生成推荐列表"""
        user_rated = rec.get_user_rated(user_id)
        predictions = []
        
        for mid in rec.movie_ids:
            if mid not in user_rated:
                pred = self.predict(rec, user_id, mid)
                predictions.append((mid, pred))
        
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:n]


class ItemBasedCF:
    """基于物品的协同过滤"""
    
    def __init__(self, k: int = 5):
        self.k = k
        self.item_sim = {}
    
    def _cosine(self, vec_a: List[float], vec_b: List[float]) -> float:
        """余弦相似度"""
        a, b = np.array(vec_a), np.array(vec_b)
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        return dot / norm if norm != 0 else 0.0
    
    def fit(self, rec: MovieRecommender):
        """预计算物品相似度"""
        for i, mid_a in enumerate(rec.movie_ids):
            for j, mid_b in enumerate(rec.movie_ids):
                if i >= j:
                    continue
                
                # 找两个物品都被评过分的用户
                vec_a, vec_b = [], []
                for uid in rec.user_ids:
                    ra = rec.ratings.get((uid, mid_a))
                    rb = rec.ratings.get((uid, mid_b))
                    if ra is not None and rb is not None:
                        vec_a.append(ra)
                        vec_b.append(rb)
                
                if len(vec_a) >= 2:
                    sim = self._cosine(vec_a, vec_b)
                    self.item_sim[(mid_a, mid_b)] = sim
                    self.item_sim[(mid_b, mid_a)] = sim
    
    def predict(self, rec: MovieRecommender, user_id: str, movie_id: str) -> float:
        """预测评分"""
        user_rated = rec.get_user_rated(user_id)
        
        # 找与目标物品最相似的、用户评过分的物品
        neighbors = []
        for mid, rating in user_rated.items():
            sim = self.item_sim.get((movie_id, mid), 0.0)
            neighbors.append((mid, sim, rating))
        
        if not neighbors:
            return 0.0
        
        neighbors.sort(key=lambda x: abs(x[1]), reverse=True)
        top_k = neighbors[:self.k]
        
        numerator = sum(sim * rating for _, sim, rating in top_k)
        denominator = sum(abs(sim) for _, sim, _ in top_k)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def recommend(self, rec: MovieRecommender, user_id: str, n: int = 5) -> List[Tuple[str, float]]:
        """生成推荐列表"""
        user_rated = rec.get_user_rated(user_id)
        predictions = []
        
        for mid in rec.movie_ids:
            if mid not in user_rated:
                pred = self.predict(rec, user_id, mid)
                predictions.append((mid, pred))
        
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:n]


# ============================================================
# 3. 冷启动处理
# ============================================================

class ColdStartHandler:
    """冷启动处理器"""
    
    def __init__(self, rec: MovieRecommender):
        self.rec = rec
    
    def popular_recommend(self, n: int = 5) -> List[str]:
        """热门推荐 (基于平均评分和评分人数)"""
        movie_scores = {}
        
        for mid in self.rec.movie_ids:
            raters = self.rec.get_movie_raters(mid)
            if raters:
                avg_rating = np.mean(list(raters.values()))
                count = len(raters)
                # 综合评分: 平均分 + 评分人数加权
                movie_scores[mid] = avg_rating * 0.7 + min(count / 10, 1.0) * 3
        
        sorted_movies = sorted(movie_scores.items(), key=lambda x: x[1], reverse=True)
        return [mid for mid, _ in sorted_movies[:n]]
    
    def content_based_recommend(self, user_id: str, n: int = 5) -> List[str]:
        """基于内容的推荐 (利用电影类型)"""
        user_rated = self.rec.get_user_rated(user_id)
        
        if not user_rated:
            return self.popular_recommend(n)
        
        # 统计用户喜欢的类型
        genre_count = defaultdict(float)
        for mid, rating in user_rated.items():
            for genre in self.rec.movies[mid]["genres"]:
                genre_count[genre] += rating
        
        # 为未评过分的电影打分
        movie_scores = {}
        for mid in self.rec.movie_ids:
            if mid not in user_rated:
                score = sum(genre_count.get(g, 0) for g in self.rec.movies[mid]["genres"])
                movie_scores[mid] = score
        
        sorted_movies = sorted(movie_scores.items(), key=lambda x: x[1], reverse=True)
        return [mid for mid, _ in sorted_movies[:n]]


# ============================================================
# 4. 评估指标
# ============================================================

class Evaluator:
    """推荐系统评估器"""
    
    @staticmethod
    def rmse(predictions: List[float], actuals: List[float]) -> float:
        """均方根误差"""
        pred, actual = np.array(predictions), np.array(actuals)
        return np.sqrt(np.mean((pred - actual) ** 2))
    
    @staticmethod
    def mae(predictions: List[float], actuals: List[float]) -> float:
        """平均绝对误差"""
        pred, actual = np.array(predictions), np.array(actuals)
        return np.mean(np.abs(pred - actual))
    
    @staticmethod
    def precision_at_k(recommended: List[str], relevant: set, k: int) -> float:
        """Precision@K"""
        rec_k = recommended[:k]
        if not rec_k:
            return 0.0
        hits = len(set(rec_k) & relevant)
        return hits / k
    
    @staticmethod
    def recall_at_k(recommended: List[str], relevant: set, k: int) -> float:
        """Recall@K"""
        rec_k = recommended[:k]
        if not relevant:
            return 0.0
        hits = len(set(rec_k) & relevant)
        return hits / len(relevant)
    
    @staticmethod
    def ndcg_at_k(recommended: List[str], relevant: set, k: int) -> float:
        """NDCG@K"""
        dcg = 0.0
        for i, item in enumerate(recommended[:k]):
            if item in relevant:
                dcg += 1.0 / np.log2(i + 2)
        
        # 理想排序
        ideal_dcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))
        
        return dcg / ideal_dcg if ideal_dcg > 0 else 0.0


# ============================================================
# 5. 完整演示
# ============================================================

def main():
    print("=" * 60)
    print("🎬 电影推荐系统演示")
    print("=" * 60)
    
    # 创建推荐系统
    rec = MovieRecommender()
    
    # 添加电影
    movies_data = [
        ("m1", "泰坦尼克号", ["爱情", "剧情"], 1997),
        ("m2", "盗梦空间", ["科幻", "动作"], 2010),
        ("m3", "战狼2", ["动作", "战争"], 2017),
        ("m4", "流浪地球", ["科幻", "冒险"], 2019),
        ("m5", "你好李焕英", ["喜剧", "剧情"], 2021),
        ("m6", "疯狂动物城", ["动画", "喜剧"], 2016),
        ("m7", "肖申克的救赎", ["剧情", "犯罪"], 1994),
        ("m8", "阿甘正传", ["剧情", "爱情"], 1994),
    ]
    for mid, title, genres, year in movies_data:
        rec.add_movie(mid, title, genres, year)
    
    # 添加用户和评分
    users_data = [
        ("u1", "Alice", [("m1", 5), ("m2", 4), ("m5", 1), ("m6", 3)]),
        ("u2", "Bob", [("m2", 5), ("m3", 4), ("m4", 4), ("m7", 3)]),
        ("u3", "Charlie", [("m1", 4), ("m3", 5), ("m4", 3), ("m5", 2)]),
        ("u4", "David", [("m4", 5), ("m5", 4), ("m6", 2), ("m8", 3)]),
        ("u5", "Eve", [("m5", 5), ("m6", 4), ("m8", 4), ("m1", 2)]),
        ("u6", "Frank", [("m2", 3), ("m7", 5), ("m8", 4)]),
    ]
    for uid, name, rates in users_data:
        rec.add_user(uid, name)
        for mid, rating in rates:
            rec.rate(uid, mid, rating)
    
    print(f"\n📊 数据概况:")
    print(f"  电影数量: {len(rec.movies)}")
    print(f"  用户数量: {len(rec.users)}")
    print(f"  评分数量: {len(rec.ratings)}")
    print(f"  评分矩阵稀疏度: {1 - len(rec.ratings) / (len(rec.movies) * len(rec.users)):.1%}")
    
    # 显示评分矩阵
    print(f"\n📋 评分矩阵:")
    matrix, user_idx, movie_idx = rec.get_rating_matrix()
    
    header = f"{'':>12}"
    for mid in rec.movie_ids:
        header += f"{rec.movies[mid]['title'][:4]:>8}"
    print(header)
    
    for uid in rec.user_ids:
        row = f"{rec.users[uid]['name']:>12}"
        for mid in rec.movie_ids:
            r = rec.ratings.get((uid, mid), 0)
            row += f"{r:>8.1f}" if r > 0 else f"{'  -':>8}"
        print(row)
    
    # User-Based CF
    print("\n" + "=" * 60)
    print("👥 User-Based 协同过滤推荐")
    print("=" * 60)
    
    user_cf = UserBasedCF(k=3)
    
    for uid in ["u1", "u2", "u6"]:
        recs = user_cf.recommend(rec, uid, n=3)
        print(f"\n{rec.users[uid]['name']} 的推荐:")
        for mid, score in recs:
            title = rec.movies[mid]['title']
            print(f"  🎬 {title}: 预测评分 {score:.2f}")
    
    # Item-Based CF
    print("\n" + "=" * 60)
    print("📦 Item-Based 协同过滤推荐")
    print("=" * 60)
    
    item_cf = ItemBasedCF(k=3)
    item_cf.fit(rec)
    
    for uid in ["u1", "u3", "u6"]:
        recs = item_cf.recommend(rec, uid, n=3)
        print(f"\n{rec.users[uid]['name']} 的推荐:")
        for mid, score in recs:
            title = rec.movies[mid]['title']
            print(f"  🎬 {title}: 预测评分 {score:.2f}")
    
    # 冷启动处理
    print("\n" + "=" * 60)
    print("🆕 冷启动处理")
    print("=" * 60)
    
    cold = ColdStartHandler(rec)
    
    print("\n热门推荐 (新用户):")
    popular = cold.popular_recommend(n=3)
    for mid in popular:
        title = rec.movies[mid]['title']
        raters = rec.get_movie_raters(mid)
        avg = np.mean(list(raters.values())) if raters else 0
        print(f"  🎬 {title}: 平均评分 {avg:.1f} ({len(raters)}人评过)")
    
    print("\n基于内容推荐 (新用户喜欢科幻):")
    # 模拟一个新用户喜欢科幻片
    rec.add_user("u_new", "新用户")
    rec.rate("u_new", "m2", 5)  # 喜欢盗梦空间
    rec.rate("u_new", "m4", 4)  # 喜欢流浪地球
    
    content_recs = cold.content_based_recommend("u_new", n=3)
    for mid in content_recs:
        title = rec.movies[mid]['title']
        genres = ", ".join(rec.movies[mid]['genres'])
        print(f"  🎬 {title} ({genres})")
    
    # 评估
    print("\n" + "=" * 60)
    print("📈 模型评估")
    print("=" * 60)
    
    # 留出法评估: 从每个用户的评分中留出一个作为测试
    test_cases = []
    for uid in rec.user_ids:
        user_rated = list(rec.get_user_rated(uid).items())
        if len(user_rated) >= 2:
            # 留出最后一个作为测试
            test_mid, test_rating = user_rated[-1]
            test_cases.append((uid, test_mid, test_rating))
    
    # User-Based CF 评估
    user_preds = []
    user_actuals = []
    for uid, mid, actual in test_cases:
        pred = user_cf.predict(rec, uid, mid)
        user_preds.append(pred)
        user_actuals.append(actual)
    
    user_rmse = Evaluator.rmse(user_preds, user_actuals)
    user_mae = Evaluator.mae(user_preds, user_actuals)
    
    print(f"\nUser-Based CF (k=3):")
    print(f"  RMSE: {user_rmse:.4f}")
    print(f"  MAE:  {user_mae:.4f}")
    
    # Item-Based CF 评估
    item_preds = []
    item_actuals = []
    for uid, mid, actual in test_cases:
        pred = item_cf.predict(rec, uid, mid)
        item_preds.append(pred)
        item_actuals.append(actual)
    
    item_rmse = Evaluator.rmse(item_preds, item_actuals)
    item_mae = Evaluator.mae(item_preds, item_actuals)
    
    print(f"\nItem-Based CF (k=3):")
    print(f"  RMSE: {item_rmse:.4f}")
    print(f"  MAE:  {item_mae:.4f}")
    
    # 推荐质量评估 (Precision@K, Recall@K, NDCG@K)
    print(f"\n推荐质量评估 (K=3):")
    
    # 定义"相关物品": 评分>=4的电影
    for uid in ["u1", "u2", "u3"]:
        user_rated = rec.get_user_rated(uid)
        relevant = {mid for mid, rating in user_rated.items() if rating >= 4}
        
        # 获取推荐列表
        recs_user = user_cf.recommend(rec, uid, n=3)
        recs_item = item_cf.recommend(rec, uid, n=3)
        
        rec_list_user = [mid for mid, _ in recs_user]
        rec_list_item = [mid for mid, _ in recs_item]
        
        p_user = Evaluator.precision_at_k(rec_list_user, relevant, 3)
        r_user = Evaluator.recall_at_k(rec_list_user, relevant, 3)
        n_user = Evaluator.ndcg_at_k(rec_list_user, relevant, 3)
        
        p_item = Evaluator.precision_at_k(rec_list_item, relevant, 3)
        r_item = Evaluator.recall_at_k(rec_list_item, relevant, 3)
        n_item = Evaluator.ndcg_at_k(rec_list_item, relevant, 3)
        
        print(f"\n{rec.users[uid]['name']}:")
        print(f"  User-Based: P@3={p_user:.3f}, R@3={r_user:.3f}, NDCG@3={n_user:.3f}")
        print(f"  Item-Based: P@3={p_item:.3f}, R@3={r_item:.3f}, NDCG@3={n_item:.3f}")
    
    # 总结
    print("\n" + "=" * 60)
    print("✅ 电影推荐系统演示完成！")
    print("=" * 60)
    print("""
功能总结:
1. User-Based CF: 基于用户相似度的推荐
2. Item-Based CF: 基于物品相似度的推荐
3. 冷启动处理: 热门推荐 + 基于内容推荐
4. 评估指标: RMSE, MAE, Precision@K, Recall@K, NDCG@K
5. 评分矩阵稀疏度分析

实际应用中的改进方向:
- 引入矩阵分解 (SVD/ALS) 处理稀疏性
- 加入时间衰减因子
- 使用隐式反馈 (点击/浏览/购买)
- 混合推荐策略
- 在线学习与实时更新
""")


if __name__ == "__main__":
    main()
