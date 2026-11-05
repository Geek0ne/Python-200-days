"""
Day 105 - 阶段项目：数据分析 Pipeline
03 - 完整 Pipeline：含错误处理、日志、进度追踪

运行方式：python3 03-full-pipeline.py
输出文件：pipeline_report.json, pipeline_log.txt
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import logging
import time
from datetime import datetime
from functools import wraps

# ============================================================
# 配置日志
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('pipeline_log.txt', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Pipeline')


# ============================================================
# 装饰器：重试机制
# ============================================================
def retry(max_retries=3, delay=1):
    """自动重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"  ⚠️ 尝试 {attempt + 1}/{max_retries} 失败: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"  ❌ 最终失败: {e}")
                        raise
        return wrapper
    return decorator


# ============================================================
# 装饰器：计时
# ============================================================
def timer(func):
    """执行计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"  ⏱️ {func.__name__} 耗时: {elapsed:.2f}s")
        return result
    return wrapper


# ============================================================
# Pipeline 步骤
# ============================================================
class PipelineStep:
    """Pipeline 步骤基类"""

    def __init__(self, name):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.status = 'pending'

    def execute(self, df):
        raise NotImplementedError

    def run(self, df):
        logger.info(f"\n{'='*50}")
        logger.info(f"▶ 开始: {self.name}")
        logger.info(f"{'='*50}")

        self.start_time = datetime.now()
        self.status = 'running'

        try:
            result = self.execute(df)
            self.status = 'success'
            self.end_time = datetime.now()
            elapsed = (self.end_time - self.start_time).total_seconds()
            logger.info(f"✅ 完成: {self.name} ({elapsed:.2f}s)")
            return result
        except Exception as e:
            self.status = 'failed'
            self.end_time = datetime.now()
            logger.error(f"❌ 失败: {self.name} - {e}")
            raise


class Step_LoadData(PipelineStep):
    """步骤 1: 加载数据"""

    def __init__(self):
        super().__init__("加载数据")

    @timer
    @retry(max_retries=2)
    def execute(self, df):
        # 模拟数据生成
        np.random.seed(42)
        n = 300
        data = {
            'order_id': range(2001, 2001 + n),
            'date': pd.date_range('2024-01-01', periods=n, freq='8h'),
            'product': np.random.choice(['Laptop', 'Phone', 'Tablet', 'Headphone'], n),
            'category': np.random.choice(['Electronics', 'Accessories'], n),
            'quantity': np.random.randint(1, 6, n),
            'unit_price': np.random.choice([999, 2999, 4999, 7999], n),
            'region': np.random.choice(['East', 'South', 'North', 'West', ''], n),
            'age': np.random.choice(list(range(18, 60)) + [-5, 150, np.nan], n),
            'payment': np.random.choice(['Credit', 'Debit', 'E-wallet', ''], n),
        }
        result = pd.DataFrame(data)
        result['revenue'] = result['quantity'] * result['unit_price']

        logger.info(f"  📦 生成 {len(result)} 行数据")
        logger.info(f"  📊 缺失值: {result.isnull().sum().sum()}")
        return result


class Step_CleanData(PipelineStep):
    """步骤 2: 清洗数据"""

    def __init__(self):
        super().__init__("清洗数据")

    @timer
    def execute(self, df):
        # 去重
        before = len(df)
        df = df.drop_duplicates()
        logger.info(f"  🔄 去重: {before} → {len(df)} 行")

        # 处理缺失值
        for col in df.select_dtypes(include=[np.number]).columns:
            if df[col].isnull().any():
                median = df[col].median()
                df[col].fillna(median, inplace=True)
                logger.info(f"  🧹 {col} 缺失值 → 中位数 {median:.1f}")

        # 处理空字符串
        for col in df.select_dtypes(include='object').columns:
            empty = (df[col] == '').sum()
            if empty > 0:
                mode = df[col][df[col] != ''].mode()[0] if len(df[col][df[col] != ''].mode()) > 0 else 'Unknown'
                df[col] = df[col].replace('', mode)
                logger.info(f"  🧹 {col} 空值 → '{mode}' ({empty} 条)")

        # 异常值修复
        for col in ['age', 'unit_price', 'quantity']:
            if col in df.columns:
                Q1, Q3 = df[col].quantile([0.25, 0.75])
                IQR = Q3 - Q1
                df[col] = df[col].clip(Q1 - 3*IQR, Q3 + 3*IQR)

        # 类型转换
        df['date'] = pd.to_datetime(df['date'])
        df['category'] = df['category'].astype('category')

        logger.info(f"  ✅ 清洗后: {len(df)} 行, {len(df.columns)} 列")
        return df


class Step_Analyze(PipelineStep):
    """步骤 3: 数据分析"""

    def __init__(self):
        super().__init__("数据分析")

    @timer
    def execute(self, df):
        results = {}

        # 基本统计
        results['total_orders'] = len(df)
        results['total_revenue'] = float(df['revenue'].sum())
        results['avg_revenue'] = float(df['revenue'].mean())

        # 产品分析
        product_stats = df.groupby('product')['revenue'].agg(['sum', 'mean', 'count'])
        results['top_product'] = product_stats['sum'].idxmax()
        results['product_stats'] = product_stats.to_dict('index')

        # 区域分析
        region_stats = df.groupby('region')['revenue'].agg(['sum', 'count'])
        results['top_region'] = region_stats['sum'].idxmax()

        # 时间分析
        df['month'] = df['date'].dt.month
        monthly = df.groupby('month')['revenue'].sum()
        results['monthly_trend'] = monthly.to_dict()

        logger.info(f"  📊 Top 产品: {results['top_product']}")
        logger.info(f"  📊 Top 区域: {results['top_region']}")
        logger.info(f"  📊 总收入: ¥{results['total_revenue']:,.0f}")

        return results


class Step_Visualize(PipelineStep):
    """步骤 4: 可视化"""

    def __init__(self):
        super().__init__("可视化")

    @timer
    def execute(self, results):
        # 这里只保存分析结果的可视化
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 产品销售柱状图
        product_data = results['product_stats']
        products = list(product_data.keys())
        revenues = [v['sum'] for v in product_data.values()]
        axes[0].barh(products, revenues, color=sns.color_palette('husl', len(products)))
        axes[0].set_title('Revenue by Product')
        axes[0].set_xlabel('Revenue (¥)')

        # 月度趋势
        months = list(results['monthly_trend'].keys())
        monthly_rev = list(results['monthly_trend'].values())
        axes[1].plot(months, monthly_rev, marker='o', linewidth=2)
        axes[1].fill_between(months, monthly_rev, alpha=0.2)
        axes[1].set_title('Monthly Revenue Trend')
        axes[1].set_xlabel('Month')
        axes[1].set_ylabel('Revenue (¥)')

        plt.tight_layout()
        plt.savefig('pipeline_charts.png', dpi=100)
        plt.close()
        logger.info(f"  📈 图表已保存: pipeline_charts.png")
        return results


class Step_Export(PipelineStep):
    """步骤 5: 导出报告"""

    def __init__(self):
        super().__init__("导出报告")

    @timer
    def execute(self, results):
        # 导出 JSON
        with open('pipeline_report.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"  📄 JSON 报告: pipeline_report.json")

        # 导出摘要
        summary = f"""
📊 Pipeline 执行摘要
{'='*40}
执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
总订单数: {results['total_orders']}
总销售额: ¥{results['total_revenue']:,.0f}
平均客单价: ¥{results['avg_revenue']:,.0f}
最畅销产品: {results['top_product']}
最大市场: {results['top_region']}
{'='*40}
"""
        with open('pipeline_summary.txt', 'w') as f:
            f.write(summary)
        logger.info(f"  📄 摘要: pipeline_summary.txt")

        return results


# ============================================================
# Pipeline 编排器
# ============================================================
class DataPipeline:
    """数据分析 Pipeline 编排器"""

    def __init__(self):
        self.steps = []
        self.results = {}
        self.step_history = []

    def add_step(self, step):
        self.steps.append(step)
        return self

    def run(self, initial_data=None):
        logger.info("🚀 " + "=" * 48)
        logger.info("🚀  数据分析 Pipeline 开始执行")
        logger.info("🚀 " + "=" * 48)

        start_time = time.time()
        data = initial_data

        for step in self.steps:
            try:
                data = step.run(data)
                self.step_history.append({
                    'name': step.name,
                    'status': step.status,
                    'duration': (step.end_time - step.start_time).total_seconds()
                })
            except Exception as e:
                logger.error(f"Pipeline 在 [{step.name}] 步骤中断: {e}")
                self.step_history.append({
                    'name': step.name,
                    'status': 'failed',
                    'error': str(e)
                })
                break

        total_time = time.time() - start_time

        logger.info(f"\n{'='*50}")
        logger.info(f"📊 Pipeline 执行报告")
        logger.info(f"{'='*50}")
        logger.info(f"总耗时: {total_time:.2f}s")
        logger.info(f"成功步骤: {sum(1 for s in self.step_history if s['status'] == 'success')}/{len(self.steps)}")

        for s in self.step_history:
            status_icon = '✅' if s['status'] == 'success' else '❌'
            logger.info(f"  {status_icon} {s['name']}: {s.get('duration', 0):.2f}s")

        return data


# ============================================================
# 主流程
# ============================================================
if __name__ == '__main__':
    # 构建 Pipeline
    pipeline = DataPipeline()
    pipeline.add_step(Step_LoadData())
    pipeline.add_step(Step_CleanData())
    pipeline.add_step(Step_Analyze())
    pipeline.add_step(Step_Visualize())
    pipeline.add_step(Step_Export())

    # 执行
    results = pipeline.run()

    logger.info("\n🎉 Pipeline 全部执行完成！")
