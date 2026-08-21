#!/usr/bin/env python3
"""
Day 124 - ARIMA 时间序列预测
演示 ARIMA 模型的完整建模流程
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


# ============================================================
# 1. 生成示例数据
# ============================================================

def generate_data(n_days=500):
    """生成模拟的时间序列数据"""
    np.random.seed(42)
    
    dates = pd.date_range(start='2025-01-01', periods=n_days, freq='D')
    
    # 趋势
    trend = np.linspace(100, 180, n_days)
    
    # 季节性
    seasonal = 25 * np.sin(2 * np.pi * np.arange(n_days) / 365)
    weekly = 8 * np.sin(2 * np.pi * np.arange(n_days) / 7)
    
    # 自相关噪声 (AR(1) 过程)
    noise = np.zeros(n_days)
    noise[0] = np.random.normal(0, 5)
    for i in range(1, n_days):
        noise[i] = 0.7 * noise[i-1] + np.random.normal(0, 3)
    
    sales = trend + seasonal + weekly + noise
    sales = np.maximum(sales, 0)
    
    df = pd.DataFrame({'date': dates, 'sales': sales})
    df.set_index('date', inplace=True)
    
    return df


# ============================================================
# 2. 数据预处理
# ============================================================

def preprocess(df):
    """数据预处理"""
    print("=" * 60)
    print("1. 数据预处理")
    print("=" * 60)
    
    # 检查缺失值
    missing = df.isnull().sum()
    print(f"缺失值: {missing['sales']}")
    
    # 如果有缺失值，用前向填充
    if missing['sales'] > 0:
        df['sales'] = df['sales'].fillna(method='ffill')
        print(f"已用前向填充处理缺失值")
    
    # 划分训练集/测试集
    train_size = int(len(df) * 0.8)
    train = df.iloc[:train_size]
    test = df.iloc[train_size:]
    
    print(f"训练集: {train.index[0]} ~ {train.index[-1]} ({len(train)} 天)")
    print(f"测试集: {test.index[0]} ~ {test.index[-1]} ({len(test)} 天)")
    
    return train, test


# ============================================================
# 3. 平稳性检验与差分
# ============================================================

def check_stationarity(train):
    """平稳性检验"""
    print("\n" + "=" * 60)
    print("2. 平稳性检验")
    print("=" * 60)
    
    from statsmodels.tsa.stattools import adfuller
    
    result = adfuller(train['sales'].dropna())
    print(f"\n原始序列 ADF 检验:")
    print(f"  ADF Statistic: {result[0]:.4f}")
    print(f"  p-value: {result[1]:.4f}")
    
    is_stationary = result[1] < 0.05
    print(f"  结论: {'平稳 ✅' if is_stationary else '非平稳 ❌'}")
    
    if not is_stationary:
        # 一阶差分
        diff = train['sales'].diff().dropna()
        result_diff = adfuller(diff)
        print(f"\n一阶差分 ADF 检验:")
        print(f"  ADF Statistic: {result_diff[0]:.4f}")
        print(f"  p-value: {result_diff[1]:.4f}")
        print(f"  结论: {'平稳 ✅' if result_diff[1] < 0.05 else '非平稳 ❌'}")
        return 1
    else:
        return 0


# ============================================================
# 4. 自动定阶 (Auto ARIMA)
# ============================================================

def auto_arima(train, test):
    """使用 pmdarima 自动选择 ARIMA 参数"""
    print("\n" + "=" * 60)
    print("3. 自动定阶 (Auto ARIMA)")
    print("=" * 60)
    
    try:
        from pmdarima import auto_arima
        
        stepwise_fit = auto_arima(
            train['sales'],
            start_p=0, start_q=0,
            max_p=5, max_q=5,
            m=7,  # 周度季节性
            d=None,  # 自动确定差分阶数
            seasonal=True,
            start_P=0, start_Q=0,
            max_P=2, max_Q=2,
            D=None,
            trace=True,
            error_action='ignore',
            suppress_warnings=True,
            stepwise=True
        )
        
        print(f"\n最优参数: {stepwise_fit.order}")
        print(f"季节性参数: {stepwise_fit.seasonal_order}")
        print(f"AIC: {stepwise_fit.aic():.2f}")
        print(f"BIC: {stepwise_fit.bic():.2f}")
        
        return stepwise_fit
    
    except ImportError:
        print("⚠️  pmdarima 未安装，使用默认参数")
        print("安装命令: pip install pmdarima")
        
        # 手动设置参数
        from statsmodels.tsa.arima.model import ARIMA
        model = ARIMA(train['sales'], order=(1, 1, 1))
        return model.fit()


# ============================================================
# 5. ARIMA 手动建模
# ============================================================

def manual_arima(train, test):
    """手动 ARIMA 建模"""
    print("\n" + "=" * 60)
    print("4. 手动 ARIMA 建模")
    print("=" * 60)
    
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.stats.diagnostic import acorr_ljungbox
    
    # 尝试不同参数
    best_aic = float('inf')
    best_order = None
    best_model = None
    
    print("\n网格搜索最佳参数:")
    print(f"{'(p,d,q)':>12} {'AIC':>12} {'BIC':>12}")
    print("-" * 40)
    
    for p in range(3):
        for d in range(2):
            for q in range(3):
                try:
                    model = ARIMA(train['sales'], order=(p, d, q))
                    fitted = model.fit()
                    
                    if fitted.aic < best_aic:
                        best_aic = fitted.aic
                        best_order = (p, d, q)
                        best_model = fitted
                    
                    print(f"({p},{d},{q}){'':>8} {fitted.aic():>12.2f} {fitted.bic():>12.2f}")
                except:
                    continue
    
    print(f"\n✅ 最优参数: {best_order}, AIC: {best_aic:.2f}")
    
    # 模型摘要
    print(f"\n模型摘要:")
    print(best_model.summary().as_text()[:2000])
    
    # 残差检验
    print(f"\n残差 Ljung-Box 检验:")
    residuals = best_model.resid
    lb_result = acorr_ljungbox(residuals, lags=[10], return_df=True)
    print(lb_result.to_string())
    
    p_value = lb_result['lb_pvalue'].values[0]
    print(f"结论: 残差{'是' if p_value > 0.05 else '不是'}白噪声 (p={p_value:.4f})")
    
    return best_model, best_order


# ============================================================
# 6. 预测与评估
# ============================================================

def forecast_and_evaluate(model, train, test, order):
    """预测与评估"""
    print("\n" + "=" * 60)
    print("5. 预测与评估")
    print("=" * 60)
    
    from statsmodels.tsa.arima.model import ARIMA
    
    # 动态预测
    predictions = []
    history = list(train['sales'])
    
    for t in range(len(test)):
        model_fit = ARIMA(history, order=order).fit()
        yhat = model_fit.forecast(steps=1)[0]
        predictions.append(yhat)
        history.append(test['sales'].iloc[t])
    
    predictions = np.array(predictions)
    actuals = test['sales'].values
    
    # 计算指标
    mae = np.mean(np.abs(actuals - predictions))
    mse = np.mean((actuals - predictions) ** 2)
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs((actuals - predictions) / actuals)) * 100
    
    print(f"\n预测评估指标:")
    print(f"  MAE:  {mae:.4f}")
    print(f"  MSE:  {mse:.4f}")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  MAPE: {mape:.2f}%")
    
    # 展示部分预测结果
    print(f"\n预测结果对比 (前10天):")
    print(f"{'日期':>12} {'实际值':>10} {'预测值':>10} {'误差':>10}")
    print("-" * 48)
    for i in range(min(10, len(test))):
        date = test.index[i].strftime('%Y-%m-%d')
        actual = actuals[i]
        pred = predictions[i]
        error = actual - pred
        print(f"{date:>12} {actual:>10.2f} {pred:>10.2f} {error:>10.2f}")
    
    return predictions, {'mae': mae, 'mse': mse, 'rmse': rmse, 'mape': mape}


# ============================================================
# 7. 未来预测
# ============================================================

def future_forecast(model, df, order, steps=30):
    """预测未来"""
    print("\n" + "=" * 60)
    print("6. 未来预测")
    print("=" * 60)
    
    from statsmodels.tsa.arima.model import ARIMA
    
    # 用全部数据拟合
    full_model = ARIMA(df['sales'], order=order).fit()
    
    # 预测未来
    forecast_result = full_model.get_forecast(steps=steps)
    forecast_mean = forecast_result.predicted_mean
    forecast_ci = forecast_result.conf_int(alpha=0.05)
    
    print(f"\n未来 {steps} 天预测:")
    print(f"{'日期':>12} {'预测值':>10} {'95%下界':>10} {'95%上界':>10}")
    print("-" * 48)
    
    for i in range(min(10, steps)):
        date = forecast_mean.index[i].strftime('%Y-%m-%d')
        pred = forecast_mean.iloc[i]
        lower = forecast_ci.iloc[i, 0]
        upper = forecast_ci.iloc[i, 1]
        print(f"{date:>12} {pred:>10.2f} {lower:>10.2f} {upper:>10.2f}")
    
    if steps > 10:
        print(f"  ... (还有 {steps-10} 天)")
    
    return forecast_mean, forecast_ci


# ============================================================
# 8. 主函数
# ============================================================

def main():
    print("=" * 60)
    print("📈 ARIMA 时间序列预测")
    print("=" * 60)
    
    # 生成数据
    df = generate_data(500)
    
    # 预处理
    train, test = preprocess(df)
    
    # 平稳性检验
    d = check_stationarity(train)
    print(f"建议差分阶数 d={d}")
    
    # 手动建模
    model, order = manual_arima(train, test)
    
    # 预测评估
    predictions, metrics = forecast_and_evaluate(model, train, test, order)
    
    # 未来预测
    forecast_mean, forecast_ci = future_forecast(model, df, order, steps=30)
    
    # 总结
    print("\n" + "=" * 60)
    print("✅ ARIMA 时间序列预测完成！")
    print("=" * 60)
    print(f"""
最终模型: ARIMA{order}
评估指标:
  MAE:  {metrics['mae']:.4f}
  RMSE: {metrics['rmse']:.4f}
  MAPE: {metrics['mape']:.2f}%

核心要点:
1. ARIMA(p,d,q) 中 p=自回归阶数, d=差分阶数, q=移动平均阶数
2. ADF 检验判断平稳性，差分使序列平稳
3. ACF/PACF 图帮助确定 p 和 q
4. AIC/BIC 用于模型选择（越小越好）
5. 残差应为白噪声（Ljung-Box 检验 p>0.05）
6. 动态预测逐步更新历史数据，更准确
""")


if __name__ == "__main__":
    main()
