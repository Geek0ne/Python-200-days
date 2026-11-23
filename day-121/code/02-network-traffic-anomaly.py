"""
Day 121 - 网络流量异常检测
============================
模拟网络流量数据，使用 Isolation Forest 检测异常流量
包括：DDoS攻击、端口扫描、异常连接模式
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix

# ============================================================
# 1. 模拟网络流量数据
# ============================================================

np.random.seed(42)

def generate_normal_traffic(n=1000):
    """生成正常网络流量数据"""
    return pd.DataFrame({
        'src_port': np.random.choice(range(1024, 65535), n),
        'dst_port': np.random.choice([80, 443, 22, 3306, 5432, 8080], n,
                                      p=[0.4, 0.3, 0.1, 0.1, 0.05, 0.05]),
        'protocol': np.random.choice([6, 17, 1], n, p=[0.7, 0.25, 0.05]),  # TCP/UDP/ICMP
        'packets': np.random.lognormal(mean=2, sigma=1, size=n).astype(int) + 1,
        'bytes': np.random.lognormal(mean=8, sigma=2, size=n).astype(int) + 64,
        'duration': np.random.exponential(scale=30, size=n),  # 秒
        'syn_count': np.random.poisson(lam=0.5, size=n),      # SYN包数量
        'fin_count': np.random.poisson(lam=0.8, size=n),      # FIN包数量
        'rst_count': np.random.poisson(lam=0.1, size=n),      # RST包数量
        'label': 0  # 0=正常
    })

def generate_ddos_attack(n=50):
    """模拟DDoS攻击流量：大量小包、高SYN、短连接"""
    return pd.DataFrame({
        'src_port': np.random.choice(range(1024, 65535), n),
        'dst_port': np.random.choice([80, 443], n),           # 只打HTTP/HTTPS
        'protocol': np.full(n, 6),                             # 全TCP
        'packets': np.random.poisson(lam=2, size=n) + 1,      # 少量包
        'bytes': np.random.normal(loc=64, scale=10, size=n).astype(int).clip(40),  # 小包
        'duration': np.random.exponential(scale=0.5, size=n),  # 极短连接
        'syn_count': np.random.poisson(lam=15, size=n),        # 高SYN
        'fin_count': np.random.poisson(lam=0.1, size=n),       # 几乎无FIN
        'rst_count': np.random.poisson(lam=0.2, size=n),       # 有RST
        'label': 1  # 1=异常
    })

def generate_port_scan(n=30):
    """模拟端口扫描：同一源IP连接大量不同端口"""
    return pd.DataFrame({
        'src_port': np.full(n, np.random.randint(40000, 60000)),
        'dst_port': np.random.choice(range(1, 65535), n),      # 随机目标端口
        'protocol': np.full(n, 6),
        'packets': np.random.poisson(lam=1, size=n) + 1,
        'bytes': np.random.normal(loc=40, scale=5, size=n).astype(int).clip(20),
        'duration': np.random.exponential(scale=0.1, size=n),  # 极快
        'syn_count': np.random.poisson(lam=3, size=n),
        'fin_count': np.random.poisson(lam=0.1, size=n),
        'rst_count': np.random.poisson(lam=1, size=n),
        'label': 1
    })

# 生成数据
print("📊 生成模拟网络流量数据...")
normal = generate_normal_traffic(1000)
ddos = generate_ddos_attack(50)
scan = generate_port_scan(30)

df = pd.concat([normal, ddos, scan], ignore_index=True)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # 打乱顺序

print(f"  正常流量: {len(normal)} 条")
print(f"  DDoS攻击: {len(ddos)} 条")
print(f"  端口扫描: {len(scan)} 条")
print(f"  总计: {len(df)} 条")

# ============================================================
# 2. 特征工程
# ============================================================

print("\n🔧 特征工程...")

# 衍生特征
df['byte_per_packet'] = df['bytes'] / df['packets']
df['syn_ratio'] = df['syn_count'] / (df['packets'] + 1)
df['fin_ratio'] = df['fin_count'] / (df['packets'] + 1)
df['rst_ratio'] = df['rst_count'] / (df['packets'] + 1)
df['bytes_per_second'] = df['bytes'] / (df['duration'] + 0.01)

# 选择特征列
feature_cols = [
    'packets', 'bytes', 'duration', 'syn_count', 'fin_count', 'rst_count',
    'byte_per_packet', 'syn_ratio', 'fin_ratio', 'rst_ratio', 'bytes_per_second'
]

X = df[feature_cols].values
y_true = df['label'].values

# 标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

print(f"  特征数量: {len(feature_cols)}")
print(f"  样本数量: {len(X_scaled)}")

# ============================================================
# 3. 训练 Isolation Forest
# ============================================================

print("\n🌲 训练 Isolation Forest...")

clf = IsolationForest(
    n_estimators=200,
    max_samples=256,
    contamination=0.07,  # 约80/1080 ≈ 7.4%
    random_state=42,
    n_jobs=-1
)
clf.fit(X_scaled)

# 预测
y_pred = clf.predict(X_scaled)
# 转换标签：1→0(正常), -1→1(异常) 以匹配 y_true
y_pred_binary = (y_pred == -1).astype(int)

# ============================================================
# 4. 评估结果
# ============================================================

print("\n📈 评估结果:")
print("=" * 50)
print(classification_report(y_true, y_pred_binary,
                          target_names=['正常', '异常']))

print("混淆矩阵:")
cm = confusion_matrix(y_true, y_pred_binary)
print(f"  真负例(TN): {cm[0][0]}  |  假正例(FP): {cm[0][1]}")
print(f"  假负例(FN): {cm[1][0]}  |  真正例(TP): {cm[1][1]}")

# 异常分数分析
scores = clf.decision_function(X_scaled)
print(f"\n异常分数统计:")
print(f"  正常样本均分: {scores[y_true == 0].mean():.4f}")
print(f"  异常样本均分: {scores[y_true == 1].mean():.4f}")

# ============================================================
# 5. 按攻击类型分析
# ============================================================

print("\n🔍 按攻击类型分析:")
attack_types = {
    'DDoS攻击': df[df['label'] == 1].iloc[:len(ddos)],
    '端口扫描': df[df['label'] == 1].iloc[len(ddos):]
}

for name, attack_df in attack_types.items():
    attack_scores = scores[attack_df.index]
    print(f"\n  {name}:")
    print(f"    平均异常分数: {attack_scores.mean():.4f}")
    print(f"    检出率: {(y_pred_binary[attack_df.index] == 1).mean():.1%}")

# ============================================================
# 6. 实时检测模拟
# ============================================================

print("\n⏱️  实时检测模拟（模拟10条新流量）:")

new_traffic = pd.DataFrame({
    'src_port': [54321, 12345, 44444, 9999, 55555, 11111, 22222, 33333, 44444, 55555],
    'dst_port': [80, 80, 22, 443, 80, 8080, 3306, 80, 80, 443],
    'protocol': [6, 6, 6, 6, 6, 17, 6, 6, 6, 6],
    'packets': [10, 2, 50, 8, 2, 100, 5, 1, 2, 15],
    'bytes': [5000, 80, 2000, 3000, 64, 8000, 500, 40, 60, 6000],
    'duration': [5, 0.3, 30, 2, 0.1, 60, 1, 0.05, 0.2, 8],
    'syn_count': [1, 5, 2, 1, 20, 0, 1, 8, 15, 1],
    'fin_count': [1, 0, 1, 1, 0, 0, 1, 0, 0, 1],
    'rst_count': [0, 0, 0, 0, 3, 0, 0, 2, 1, 0],
})

# 衍生特征
new_traffic['byte_per_packet'] = new_traffic['bytes'] / new_traffic['packets']
new_traffic['syn_ratio'] = new_traffic['syn_count'] / (new_traffic['packets'] + 1)
new_traffic['fin_ratio'] = new_traffic['fin_count'] / (new_traffic['packets'] + 1)
new_traffic['rst_ratio'] = new_traffic['rst_count'] / (new_traffic['packets'] + 1)
new_traffic['bytes_per_second'] = new_traffic['bytes'] / (new_traffic['duration'] + 0.01)

X_new = scaler.transform(new_traffic[feature_cols].values)
pred_new = clf.predict(X_new)
score_new = clf.decision_function(X_new)

for i in range(len(new_traffic)):
    status = "🔴 异常" if pred_new[i] == -1 else "🟢 正常"
    print(f"  连接{i+1}: dst_port={new_traffic.iloc[i]['dst_port']}, "
          f"packets={new_traffic.iloc[i]['packets']}, "
          f"score={score_new[i]:.4f} → {status}")

print("\n💡 关键要点：")
print("  1. 特征工程是异常检测的关键：原始数据+衍生特征")
print("  2. DDoS特征：高SYN比、低FIN比、短持续时间、小包")
print("  3. 端口扫描特征：大量不同目标端口、RST响应多")
print("  4. 标准化对 Isolation Forest 影响不大，但对其他方法重要")
print("  5. 实时场景需要滑动窗口 + 模型定期更新")
