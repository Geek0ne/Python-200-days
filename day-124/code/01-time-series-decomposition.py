#!/usr/bin/env python3
"""
Day 124 - 时间序列分解与平稳性检验
演示时间序列的基本分析方法
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


# ============================================================
# 1. 生成示例时间序列数据
# ============================================================

def generate_sales_data(n_days=365):
    """生成模拟的销售数据（包含趋势、季节性、噪声）"""
    np.random.seed(42)
    
    dates = pd.date_range(start='2026-01-01', periods=n_days, freq='D')
    
    # 趋势: 线性增长
    trend = np.linspace(100, 200, n_days)
    
    # 季节性: 年度周期 (365天) + 周度周期 (7天)
    yearly_season = 30 * np.sin(2 * np.pi * np.arange(n_days) / 365)
    weekly_season = 10 * np.sin(2 * np.pi * np.arange(n_days) / 7)
    
    # 噪声
    noise = np.random.normal(0, 8, n_days)
    
    # 合成
    sales = trend + yearly_season + weekly_season + noise
    sales = np.maximum(sales, 0)  # 销售额不能为负
    
    df = pd.DataFrame({
        'date': dates,
        'sales': sales
    })
    df.set_index('date', inplace=True)
    
    return df


# ============================================================
# 2. 基本统计分析
# ============================================================

def basic_analysis(df):
    """基本统计分析"""
    print("=" * 60)
    print("1. 基本统计分析")
    print("=" * 60)
    
    print(f"\n数据概览:")
    print(f"  时间范围: {df.index[0]} ~ {df.index[-1]}")
    print(f"  数据点数: {len(df)}")
    print(f"  缺失值: {df.isnull().sum()}")
    
    print(f"\n描述统计:")
    print(df['sales'].describe().to_string())
    
    print(f"\n按月统计:")
    monthly = df.resample('ME').agg(['mean', 'std', 'min', 'max'])
    print(monthly['sales'].head(6).to_string())
    
    print(f"\n按星期统计:")
    weekly = df.groupby(df.index.dayofweek)['sales'].agg(['mean', 'std'])
    weekly.index = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    print(weekly.to_string())


# ============================================================
# 3. 时间序列分解
# ============================================================

def time_series_decomposition(df):
    """时间序列分解"""
    print("\n" + "=" * 60)
    print("2. 时间序列分解")
    print("=" * 60)
    
    from statsmodels.tsa.seasonal import seasonal_decompose
    
    # 加法分解
    print("\n--- 加法分解 (Additive) ---")
    result_add = seasonal_decompose(df['sales'], model='additive', period=30)
    
    # 提取分量
    trend = result_add.trend.dropna()
    seasonal = result_add.seasonal.dropna()
    residual = result_add.resid.dropna()
    
    print(f"趋势分量范围: [{trend.min():.2f}, {trend.max():.2f}]")
    print(f"季节性分量范围: [{seasonal.min():.2f}, {seasonal.max():.2f}]")
    print(f"残差标准差: {residual.std():.2f}")
    
    # 季节性强度
    var_resid = residual.var()
    var_seasonal_plus_resid = (seasonal + residual).var()
    seasonal_strength = 1 - var_resid / var_seasonal_plus_resid
    print(f"季节性强度: {seasonal_strength:.4f} (越接近1季节性越强)")
    
    # 趋势强度
    var_trend_plus_resid = (trend + residual).var()
    trend_strength = 1 - var_resid / var_trend_plus_resid
    print(f"趋势强度: {trend_strength:.4f} (越接近1趋势越强)")
    
    # 乘法分解
    print("\n--- 乘法分解 (Multiplicative) ---")
    result_mul = seasonal_decompose(df['sales'], model='multiplicative', period=30)
    
    seasonal_mul = result_mul.seasonal.dropna()
    print(f"季节性乘数范围: [{seasonal_mul.min():.4f}, {seasonal_mul.max():.4f}]")
    print(f"季节性波动幅度: {(seasonal_mul.max() - seasonal_mul.min()) * 100:.1f}%")


# ============================================================
# 4. 平稳性检验
# ============================================================

def stationarity_test(df):
    """平稳性检验"""
    print("\n" + "=" * 60)
    print("3. 平稳性检验 (ADF Test)")
    print("=" * 60)
    
    from statsmodels.tsa.stattools import adfuller
    
    # 原始序列
    result = adfuller(df['sales'].dropna())
    print(f"\n原始序列:")
    print(f"  ADF Statistic: {result[0]:.4f}")
    print(f"  p-value: {result[1]:.4f}")
    print(f"  使用滞后阶数: {result[2]}")
    print(f"  结论: {'平稳 ✅' if result[1] < 0.05 else '非平稳 ❌'}")
    
    # 一阶差分
    diff1 = df['sales'].diff().dropna()
    result_diff1 = adfuller(diff1)
    print(f"\n一阶差分:")
    print(f"  ADF Statistic: {result_diff1[0]:.4f}")
    print(f"  p-value: {result_diff1[1]:.4f}")
    print(f"  结论: {'平稳 ✅' if result_diff1[1] < 0.05 else '非平稳 ❌'}")
    
    # 二阶差分
    diff2 = diff1.diff().dropna()
    result_diff2 = adfuller(diff2)
    print(f"\n二阶差分:")
    print(f"  ADF Statistic: {result_diff2[0]:.4f}")
    print(f"  p-value: {result_diff2[1]:.4f}")
    print(f"  结论: {'平稳 ✅' if result_diff2[1] < 0.05 else '非平稳 ❌'}")
    
    return diff1


# ============================================================
# 5. ACF / PACF 分析
# ============================================================

def acf_pacf_analysis(diff_series):
    """ACF / PACF 分析"""
    print("\n" + "=" * 60)
    print("4. ACF / PACF 分析")
    print("=" * 60)
    
    from statsmodels.tsa.stattools import acf, pacf
    
    # 计算 ACF 和 PACF
    acf_values = acf(diff_series, nlags=20)
    pacf_values = pacf(diff_series, nlags=20)
    
    # 打印 ACF
    print(f"\n自相关函数 (ACF):")
    print(f"{'滞后':>6} {'ACF值':>10} {'显著':>6}")
    print("-" * 30)
    for i in range(1, 21):
        sig = "***" if abs(acf_values[i]) > 1.96 / np.sqrt(len(diff_series)) else ""
        print(f"{i:>6} {acf_values[i]:>10.4f} {sig:>6}")
    
    # 打印 PACF
    print(f"\n偏自相关函数 (PACF):")
    print(f"{'滞后':>6} {'PACF值':>10} {'显著':>6}")
    print("-" * 30)
    for i in range(1, 21):
        sig = "***" if abs(pacf_values[i]) > 1.96 / np.sqrt(len(diff_series)) else ""
        print(f"{i:>6} {pacf_values[i]:>10.4f} {sig:>6}")
    
    # 判断
    print(f"\n--- 模型阶数判断 ---")
    
    # 找 ACF 截尾点
    sig_threshold = 1.96 / np.sqrt(len(diff_series))
    acf_cutoff = 0
    for i in range(1, len(acf_values)):
        if abs(acf_values[i]) < sig_threshold:
            acf_cutoff = i
            break
    
    # 找 PACF 截尾点
    pacf_cutoff = 0
    for i in range(1, len(pacf_values)):
        if abs(pacf_values[i]) < sig_threshold:
            pacf_cutoff = i
            break
    
    print(f"ACF 在滞后 {acf_cutoff} 处截尾")
    print(f"PACF 在滞后 {pacf_cutoff} 处截尾")
    
    if acf_cutoff > 0 and pacf_cutoff == 0:
        print("→ 建议: MA 模型 (q=1)")
    elif pacf_cutoff > 0 and acf_cutoff == 0:
        print("→ 建议: AR 模型 (p=1)")
    elif acf_cutoff > 0 and pacf_cutoff > 0:
        print("→ 建议: ARIMA 模型")


# ============================================================
# 6. 白噪声检验
# ============================================================

def white_noise_test(series):
    """Ljung-Box 白噪声检验"""
    print("\n" + "=" * 60)
    print("5. 白噪声检验 (Ljung-Box)")
    print("=" * 60)
    
    from statsmodels.stats.diagnostic import acorr_ljungbox
    
    result = acorr_ljungbox(series, lags=[10, 20], return_df=True)
    print(f"\nLjung-Box 检验:")
    print(result.to_string())
    
    print(f"\n结论:")
    for lag, row in result.iterrows():
        p_value = row['lb_pvalue']
        conclusion = "非白噪声 (有序列相关性)" if p_value < 0.05 else "白噪声 (无序列相关性)"
        print(f"  滞后 {lag}: p-value={p_value:.4f} → {conclusion}")


# ============================================================
# 7. 主函数
# ============================================================

def main():
    print("=" * 60)
    print("📈 时间序列分解与平稳性检验")
    print("=" * 60)
    
    # 生成数据
    df = generate_sales_data(365)
    
    # 1. 基本分析
    basic_analysis(df)
    
    # 2. 时间序列分解
    time_series_decomposition(df)
    
    # 3. 平稳性检验
    diff_series = stationarity_test(df)
    
    # 4. ACF/PACF
    acf_pacf_analysis(diff_series)
    
    # 5. 白噪声检验
    white_noise_test(diff_series)
    
    # 总结
    print("\n" + "=" * 60)
    print("✅ 时间序列分解与平稳性检验完成！")
    print("=" * 60)
    print("""
核心要点:
1. 时间序列 = 趋势 + 季节性 + 周期性 + 残差
2. 加法分解适用于季节性恒定，乘法分解适用于季节性随趋势增大
3. ADF 检验判断平稳性: p-value < 0.05 → 平稳
4. 差分将非平稳序列转化为平稳序列
5. ACF/PACF 图帮助确定 ARIMA 模型阶数
6. Ljung-Box 检验判断残差是否为白噪声
""")


if __name__ == "__main__":
    main()
