#!/usr/bin/env python3
"""
Day 124 - Prophet 时间序列预测
演示 Facebook Prophet 模型的使用
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


# ============================================================
# 1. 生成示例数据
# ============================================================

def generate_data(n_days=730):
    """生成模拟的销售数据（2年）"""
    np.random.seed(42)
    
    dates = pd.date_range(start='2024-01-01', periods=n_days, freq='D')
    
    # 趋势: 非线性增长
    trend = 100 + 0.15 * np.arange(n_days) + 0.0001 * np.arange(n_days)**2
    
    # 年度季节性
    yearly = 30 * np.sin(2 * np.pi * np.arange(n_days) / 365)
    
    # 周度季节性
    weekly = np.where(dates.dayofweek >= 5, -15, 10)  # 周末低，工作日高
    
    # 节假日效应 (模拟双11)
    holiday_effect = np.zeros(n_days)
    for i, d in enumerate(dates):
        if d.month == 11 and 10 <= d.day <= 12:  # 双11
            holiday_effect[i] = 80
        elif d.month == 12 and 25 == d.day:  # 圣诞
            holiday_effect[i] = 40
    
    # 噪声
    noise = np.random.normal(0, 5, n_days)
    
    sales = trend + yearly + weekly + holiday_effect + noise
    sales = np.maximum(sales, 0)
    
    df = pd.DataFrame({'date': dates, 'sales': sales})
    
    return df


# ============================================================
# 2. Prophet 基础使用
# ============================================================

def prophet_basic(df):
    """Prophet 基础使用"""
    print("=" * 60)
    print("1. Prophet 基础使用")
    print("=" * 60)
    
    try:
        from prophet import Prophet
        
        # Prophet 要求列名为 ds 和 y
        prophet_df = df.rename(columns={'date': 'ds', 'sales': 'y'})
        
        # 创建模型
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,  # 趋势灵活性
            seasonality_prior_scale=10.0,  # 季节性灵活性
        )
        
        # 训练
        model.fit(prophet_df)
        
        print(f"模型训练完成")
        print(f"趋势变化点: {len(model.changepoints)} 个")
        print(f"变化点位置: {[d.strftime('%Y-%m-%d') for d in model.changepoints[:5]]}...")
        
        return model, prophet_df
    
    except ImportError:
        print("⚠️  Prophet 未安装，跳过")
        print("安装命令: pip install prophet")
        return None, None


# ============================================================
# 3. Prophet 预测
# ============================================================

def prophet_forecast(model, prophet_df, periods=90):
    """Prophet 预测"""
    print("\n" + "=" * 60)
    print("2. Prophet 预测")
    print("=" * 60)
    
    if model is None:
        return
    
    # 创建未来日期
    future = model.make_future_dataframe(periods=periods)
    print(f"预测未来 {periods} 天")
    
    # 预测
    forecast = model.predict(future)
    
    # 展示预测结果
    print(f"\n预测结果 (最后10天):")
    print(f"{'日期':>12} {'预测值':>10} {'下界':>10} {'上界':>10}")
    print("-" * 48)
    
    tail = forecast.tail(periods).head(10)
    for _, row in tail.iterrows():
        date = row['ds'].strftime('%Y-%m-%d')
        yhat = row['yhat']
        lower = row['yhat_lower']
        upper = row['yhat_upper']
        print(f"{date:>12} {yhat:>10.2f} {lower:>10.2f} {upper:>10.2f}")
    
    # 预测分量
    print(f"\n预测分量 (最后预测日):")
    last = forecast.iloc[-1]
    print(f"  趋势 (trend): {last['trend']:.2f}")
    if 'yearly' in forecast.columns:
        print(f"  年度季节性: {last['yearly']:.2f}")
    if 'weekly' in forecast.columns:
        print(f"  周度季节性: {last['weekly']:.2f}")
    
    return forecast


# ============================================================
# 4. Prophet 交叉验证
# ============================================================

def prophet_cross_validation(model):
    """Prophet 交叉验证"""
    print("\n" + "=" * 60)
    print("3. Prophet 交叉验证")
    print("=" * 60)
    
    try:
        from prophet.diagnostics import cross_validation, performance_metrics
        
        # 交叉验证
        # 初始训练期: 365天
        # 预测期: 30天
        # 滑动窗口: 30天
        print("执行交叉验证 (这可能需要一些时间)...")
        
        cv_results = cross_validation(
            model, 
            initial='365 days',
            period='30 days',
            horizon='30 days'
        )
        
        # 性能指标
        metrics = performance_metrics(cv_results)
        
        print(f"\n交叉验证性能指标:")
        print(f"{'指标':>12} {'均值':>10} {'标准差':>10}")
        print("-" * 36)
        
        for metric in ['mae', 'mse', 'rmse', 'mape']:
            if metric in metrics.columns:
                mean_val = metrics[metric].mean()
                std_val = metrics[metric].std()
                print(f"{metric:>12} {mean_val:>10.4f} {std_val:>10.4f}")
        
        return metrics
    
    except Exception as e:
        print(f"交叉验证出错: {e}")
        return None


# ============================================================
# 5. Prophet 节假日效应
# ============================================================

def prophet_holidays(df):
    """Prophet 节假日效应"""
    print("\n" + "=" * 60)
    print("4. Prophet 节假日效应")
    print("=" * 60)
    
    try:
        from prophet import Prophet
        
        # 定义中国节假日
        holidays = pd.DataFrame({
            'holiday': 'double11',
            'ds': pd.to_datetime(['2024-11-11', '2025-11-11', '2026-11-11']),
            'lower_window': -2,  # 前2天开始
            'upper_window': 2,   # 后2天结束
        })
        
        # 添加更多节假日
        holidays = pd.concat([
            holidays,
            pd.DataFrame({
                'holiday': 'christmas',
                'ds': pd.to_datetime(['2024-12-25', '2025-12-25', '2026-12-25']),
                'lower_window': 0,
                'upper_window': 1,
            }),
            pd.DataFrame({
                'holiday': 'newyear',
                'ds': pd.to_datetime(['2025-01-01', '2026-01-01', '2027-01-01']),
                'lower_window': -1,
                'upper_window': 1,
            }),
        ], ignore_index=True)
        
        print(f"定义了 {len(holidays)} 个节假日:")
        print(holidays.to_string(index=False))
        
        # Prophet 模型
        prophet_df = df.rename(columns={'date': 'ds', 'sales': 'y'})
        
        model = Prophet(
            holidays=holidays,
            yearly_seasonality=True,
            weekly_seasonality=True,
        )
        model.fit(prophet_df)
        
        # 查看节假日效应
        forecast = model.predict(model.make_future_dataframe(periods=30))
        
        if 'double11' in forecast.columns:
            holiday_effect = forecast['double11'].mean()
            print(f"\n双11 平均效应: {holiday_effect:.2f}")
        
        return model
    
    except ImportError:
        print("⚠️  Prophet 未安装，跳过")
        return None


# ============================================================
# 6. Prophet vs ARIMA 对比
# ============================================================

def compare_models(df):
    """Prophet vs ARIMA 对比"""
    print("\n" + "=" * 60)
    print("5. Prophet vs ARIMA 对比")
    print("=" * 60)
    
    prophet_df = df.rename(columns={'date': 'ds', 'sales': 'y'})
    
    # 划分训练集/测试集
    train_size = int(len(df) * 0.8)
    train = prophet_df.iloc[:train_size]
    test = prophet_df.iloc[train_size:]
    
    results = {}
    
    # Prophet
    try:
        from prophet import Prophet
        
        model_p = Prophet(yearly_seasonality=True, weekly_seasonality=True)
        model_p.fit(train)
        
        future = model_p.make_future_dataframe(periods=len(test))
        forecast_p = model_p.predict(future)
        
        pred_p = forecast_p.iloc[-len(test):]['yhat'].values
        actual = test['y'].values
        
        mae_p = np.mean(np.abs(actual - pred_p))
        rmse_p = np.sqrt(np.mean((actual - pred_p) ** 2))
        mape_p = np.mean(np.abs((actual - pred_p) / actual)) * 100
        
        results['Prophet'] = {'mae': mae_p, 'rmse': rmse_p, 'mape': mape_p}
        
    except ImportError:
        pass
    
    # ARIMA
    try:
        from statsmodels.tsa.arima.model import ARIMA
        
        model_a = ARIMA(train['y'].values, order=(1, 1, 1))
        fitted_a = model_a.fit()
        
        pred_a = fitted_a.forecast(steps=len(test))
        
        mae_a = np.mean(np.abs(actual - pred_a))
        rmse_a = np.sqrt(np.mean((actual - pred_a) ** 2))
        mape_a = np.mean(np.abs((actual - pred_a) / actual)) * 100
        
        results['ARIMA'] = {'mae': mae_a, 'rmse': rmse_a, 'mape': mape_a}
    
    except Exception:
        pass
    
    # 对比
    if results:
        print(f"\n{'模型':>10} {'MAE':>10} {'RMSE':>10} {'MAPE(%)':>10}")
        print("-" * 45)
        for name, metrics in results.items():
            print(f"{name:>10} {metrics['mae']:>10.4f} {metrics['rmse']:>10.4f} {metrics['mape']:>10.2f}")
        
        best = min(results.items(), key=lambda x: x[1]['rmse'])
        print(f"\n🏆 RMSE 最优模型: {best[0]}")
    
    return results


# ============================================================
# 7. 主函数
# ============================================================

def main():
    print("=" * 60)
    print("📈 Prophet 时间序列预测")
    print("=" * 60)
    
    # 生成数据
    df = generate_data(730)
    print(f"数据概览: {df['date'].min()} ~ {df['date'].max()}, 共 {len(df)} 天")
    print(f"销售范围: [{df['sales'].min():.2f}, {df['sales'].max():.2f}]")
    
    # 1. 基础使用
    model, prophet_df = prophet_basic(df)
    
    # 2. 预测
    forecast = prophet_forecast(model, prophet_df, periods=90)
    
    # 3. 交叉验证
    cv_metrics = prophet_cross_validation(model)
    
    # 4. 节假日效应
    model_holiday = prophet_holidays(df)
    
    # 5. 模型对比
    compare_models(df)
    
    # 总结
    print("\n" + "=" * 60)
    print("✅ Prophet 时间序列预测完成！")
    print("=" * 60)
    print("""
核心要点:
1. Prophet 适合具有强季节性、趋势变化点的时间序列
2. 自动处理缺失值、异常值
3. 支持节假日效应建模
4. 交叉验证评估模型泛化能力
5. 比 ARIMA 更易用，调参更少
6. 适合业务场景的快速预测

Prophet 核心参数:
- changepoint_prior_scale: 趋势灵活性 (越大越灵活)
- seasonality_prior_scale: 季节性强度
- holidays_prior_scale: 节假日效应强度
""")


if __name__ == "__main__":
    main()
