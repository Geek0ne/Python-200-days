"""
Day 105 - 阶段项目：数据分析 Pipeline
02 - 数据分析与可视化模块

运行方式：python3 02-analysis-visualization.py
输出文件：analysis_charts.png
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 中文字体配置
# ============================================================
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid", palette="muted")


# ============================================================
# 模块 3: 数据分析
# ============================================================
class DataAnalysis:
    """数据分析模块"""

    def __init__(self, df):
        self.df = df
        self.insights = []

    def overview(self):
        """数据全貌扫描"""
        print("\n📊 数据全貌扫描:")
        print(f"  形状: {self.df.shape}")
        print(f"  时间范围: {self.df['date'].min().date()} ~ {self.df['date'].max().date()}")
        print(f"  总销售额: ¥{self.df['total_price'].sum():,.0f}")
        print(f"  平均客单价: ¥{self.df['total_price'].mean():,.0f}")
        print(f"  中位数客单价: ¥{self.df['total_price'].median():,.0f}")
        return self

    def analyze_by_category(self):
        """按品类分析"""
        print("\n📊 品类分析:")
        category_stats = self.df.groupby('category').agg(
            orders=('order_id', 'count'),
            total_revenue=('total_price', 'sum'),
            avg_price=('total_price', 'mean'),
            avg_quantity=('quantity', 'mean')
        ).round(2)

        category_stats['revenue_pct'] = (category_stats['total_revenue'] /
                                          category_stats['total_revenue'].sum() * 100).round(1)

        for cat, row in category_stats.sort_values('total_revenue', ascending=False).iterrows():
            print(f"  {cat}: {row['orders']} 单, ¥{row['total_revenue']:,.0f} ({row['revenue_pct']}%)")

        self.category_stats = category_stats
        return self

    def analyze_by_region(self):
        """按区域分析"""
        print("\n📊 区域分析:")
        region_stats = self.df.groupby('region').agg(
            orders=('order_id', 'count'),
            total_revenue=('total_price', 'sum'),
            avg_age=('customer_age', 'mean')
        ).round(2)

        region_stats['revenue_pct'] = (region_stats['total_revenue'] /
                                        region_stats['total_revenue'].sum() * 100).round(1)

        for reg, row in region_stats.sort_values('total_revenue', ascending=False).iterrows():
            print(f"  {reg}: {row['orders']} 单, ¥{row['total_revenue']:,.0f} ({row['revenue_pct']}%)")

        self.region_stats = region_stats
        return self

    def analyze_time_series(self):
        """时间序列分析"""
        self.df['month'] = self.df['date'].dt.month
        self.df['hour'] = self.df['date'].dt.hour
        self.df['dayofweek'] = self.df['date'].dt.dayofweek

        print("\n📊 月度趋势:")
        monthly = self.df.groupby('month')['total_price'].sum()
        for month, revenue in monthly.items():
            bar = '█' * int(revenue / monthly.max() * 25)
            print(f"  {month:2d}月: {bar} ¥{revenue:,.0f}")

        print("\n📊 时段分布:")
        hourly = self.df.groupby('hour')['order_id'].count()
        peak_hour = hourly.idxmax()
        print(f"  高峰时段: {peak_hour}:00 ({hourly[peak_hour]} 单)")

        self.monthly_stats = monthly
        self.hourly_stats = hourly
        return self

    def find_insights(self):
        """提炼关键洞察"""
        print("\n💡 关键洞察:")

        # Top 产品
        top_product = self.df.groupby('product')['total_price'].sum().idxmax()
        top_product_sales = self.df.groupby('product')['total_price'].sum().max()
        self.insights.append(f"最畅销产品: {top_product} (¥{top_product_sales:,.0f})")

        # Top 区域
        top_region = self.df.groupby('region')['total_price'].sum().idxmax()
        top_region_pct = (self.df.groupby('region')['total_price'].sum().max() /
                          self.df['total_price'].sum() * 100)
        self.insights.append(f"最大市场: {top_region} ({top_region_pct:.1f}%)")

        # 客户画像
        avg_age = self.df['customer_age'].mean()
        self.insights.append(f"核心客群: 平均年龄 {avg_age:.0f} 岁")

        for i, insight in enumerate(self.insights, 1):
            print(f"  {i}. {insight}")

        return self


# ============================================================
# 模块 4: 可视化
# ============================================================
class ReportVisualizer:
    """报告可视化模块"""

    def __init__(self, df, analysis):
        self.df = df
        self.analysis = analysis

    def generate_dashboard(self, output_path='analysis_charts.png'):
        """生成仪表盘图表"""
        fig = plt.figure(figsize=(20, 14))
        fig.suptitle('📊 E-Commerce Sales Dashboard', fontsize=18, fontweight='bold', y=0.98)

        # 图1: 品类销售额
        ax1 = fig.add_subplot(2, 3, 1)
        cat_sales = self.df.groupby('category')['total_price'].sum().sort_values(ascending=True)
        cat_sales.plot(kind='barh', ax=ax1, color=sns.color_palette('husl', len(cat_sales)))
        ax1.set_title('Revenue by Category', fontsize=13, fontweight='bold')
        ax1.set_xlabel('Revenue (¥)')

        # 图2: 区域占比饼图
        ax2 = fig.add_subplot(2, 3, 2)
        region_sales = self.df.groupby('region')['total_price'].sum()
        region_pct = region_sales / region_sales.sum() * 100
        colors = sns.color_palette('pastel', len(region_pct))
        wedges, texts, autotexts = ax2.pie(
            region_pct, labels=region_pct.index, autopct='%1.1f%%',
            colors=colors, startangle=90
        )
        ax2.set_title('Revenue by Region', fontsize=13, fontweight='bold')

        # 图3: 月度趋势
        ax3 = fig.add_subplot(2, 3, 3)
        monthly = self.df.groupby('month')['total_price'].sum()
        ax3.plot(monthly.index, monthly.values, marker='o', linewidth=2.5, color='#3498db')
        ax3.fill_between(monthly.index, monthly.values, alpha=0.15, color='#3498db')
        ax3.set_title('Monthly Revenue Trend', fontsize=13, fontweight='bold')
        ax3.set_xlabel('Month')
        ax3.set_ylabel('Revenue (¥)')
        ax3.grid(True, alpha=0.3)

        # 图4: 支付方式分布
        ax4 = fig.add_subplot(2, 3, 4)
        payment = self.df.groupby('payment_method')['total_price'].sum().sort_values()
        payment.plot(kind='barh', ax=ax4, color=sns.color_palette('coolwarm', len(payment)))
        ax4.set_title('Payment Method Revenue', fontsize=13, fontweight='bold')
        ax4.set_xlabel('Revenue (¥)')

        # 图5: 客户年龄分布
        ax5 = fig.add_subplot(2, 3, 5)
        ax5.hist(self.df['customer_age'], bins=25, edgecolor='black',
                 alpha=0.7, color='steelblue')
        mean_age = self.df['customer_age'].mean()
        ax5.axvline(mean_age, color='red', linestyle='--', linewidth=2,
                    label=f'Mean={mean_age:.0f}')
        ax5.set_title('Customer Age Distribution', fontsize=13, fontweight='bold')
        ax5.set_xlabel('Age')
        ax5.set_ylabel('Count')
        ax5.legend()

        # 图6: 产品×区域热力图
        ax6 = fig.add_subplot(2, 3, 6)
        pivot = self.df.pivot_table(values='total_price', index='product',
                                     columns='region', aggfunc='sum')
        sns.heatmap(pivot, annot=True, fmt='.0f', cmap='YlOrRd',
                    ax=ax6, cbar_kws={'shrink': 0.8}, linewidths=0.5)
        ax6.set_title('Product × Region Heatmap', fontsize=13, fontweight='bold')

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n✅ 仪表盘已保存: {output_path}")
        plt.close()
        return self


# ============================================================
# 模块 5: 报告输出
# ============================================================
class ReportExporter:
    """报告导出模块"""

    @staticmethod
    def export_json(analysis, filepath='report.json'):
        """导出 JSON 报告"""
        import json
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_orders': len(analysis.df),
            'total_revenue': float(analysis.df['total_price'].sum()),
            'avg_order_value': float(analysis.df['total_price'].mean()),
            'insights': analysis.insights,
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON 报告已导出: {filepath}")

    @staticmethod
    def export_markdown(analysis, filepath='report.md'):
        """导出 Markdown 报告"""
        lines = [
            '# 📊 Sales Analysis Report',
            f'\n> Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            '\n## Overview\n',
            f'- Total Orders: {len(analysis.df)}',
            f'- Total Revenue: ¥{analysis.df["total_price"].sum():,.0f}',
            f'- Avg Order Value: ¥{analysis.df["total_price"].mean():,.0f}',
            '\n## Key Insights\n',
        ]
        for i, insight in enumerate(analysis.insights, 1):
            lines.append(f'{i}. {insight}')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"✅ Markdown 报告已导出: {filepath}")


# ============================================================
# 主流程
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 数据分析 Pipeline - Step 3~5: 分析 + 可视化 + 报告")
    print("=" * 60)

    # 读取清洗后的数据（如果没有则重新生成）
    try:
        df = pd.read_csv('cleaned_data.csv')
        print(f"✅ 从 cleaned_data.csv 加载: {len(df)} 行")
    except FileNotFoundError:
        print("⚠️ cleaned_data.csv 不存在，重新生成示例数据...")
        np.random.seed(42)
        n = 500
        data = {
            'order_id': range(1001, 1001 + n),
            'date': pd.date_range('2024-01-01', periods=n, freq='6h'),
            'product': np.random.choice(['iPhone', 'MacBook', 'iPad', 'AirPods'], n),
            'category': np.random.choice(['手机', '电脑', '平板', '配件'], n),
            'quantity': np.random.randint(1, 5, n),
            'unit_price': np.random.choice([5999, 9999, 3999, 1299], n),
            'region': np.random.choice(['华东', '华南', '华北', '西南'], n),
            'customer_age': np.random.randint(18, 60, n),
            'payment_method': np.random.choice(['支付宝', '微信', '银行卡'], n),
        }
        df = pd.DataFrame(data)
        df['total_price'] = df['quantity'] * df['unit_price']
        df['date'] = pd.to_datetime(df['date'])

    # Step 3: 分析
    analysis = DataAnalysis(df)
    analysis.overview()
    analysis.analyze_by_category()
    analysis.analyze_by_region()
    analysis.analyze_time_series()
    analysis.find_insights()

    # Step 4: 可视化
    viz = ReportVisualizer(df, analysis)
    viz.generate_dashboard()

    # Step 5: 导出报告
    ReportExporter.export_json(analysis, 'report.json')
    ReportExporter.export_markdown(analysis, 'report.md')

    print("\n🎉 Pipeline 全部完成！")
