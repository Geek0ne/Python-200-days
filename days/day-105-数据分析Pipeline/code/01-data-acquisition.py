"""
Day 105 - 阶段项目：数据分析 Pipeline
01 - 数据获取与清洗模块

运行方式：python3 01-data-acquisition.py
输出文件：cleaned_data.csv
"""
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 模块 1: 数据获取
# ============================================================
class DataAcquisition:
    """数据获取模块 - 支持多种数据源"""

    @staticmethod
    def from_csv(filepath, **kwargs):
        """从 CSV 文件读取"""
        try:
            df = pd.read_csv(filepath, **kwargs)
            print(f"✅ CSV 加载成功: {len(df)} 行, {len(df.columns)} 列")
            return df
        except FileNotFoundError:
            print(f"❌ 文件不存在: {filepath}")
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ CSV 读取失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def from_api(url, params=None):
        """从 API 获取数据（示例：模拟）"""
        # 实际项目中使用 requests
        # import requests
        # response = requests.get(url, params=params)
        # return pd.DataFrame(response.json())

        # 模拟数据
        np.random.seed(42)
        n = 200
        data = {
            'id': range(1, n + 1),
            'name': [f'Product_{i}' for i in range(1, n + 1)],
            'price': np.random.uniform(10, 500, n).round(2),
            'category': np.random.choice(['A', 'B', 'C', 'D'], n),
            'sales': np.random.randint(0, 1000, n),
        }
        df = pd.DataFrame(data)
        print(f"✅ API 数据模拟: {len(df)} 行")
        return df

    @staticmethod
    def generate_sample_data(n=500):
        """生成示例脏数据（用于教学演示）"""
        np.random.seed(42)
        data = {
            'order_id': range(1001, 1001 + n),
            'date': pd.date_range('2024-01-01', periods=n, freq='6h'),
            'product': np.random.choice(['iPhone', 'MacBook', 'iPad', 'AirPods'], n),
            'price': np.random.uniform(100, 10000, n).round(2),
            'quantity': np.random.randint(1, 10, n),
            'city': np.random.choice(['北京', '上海', '广州', '深圳', '杭州', ''], n),
            'age': np.random.choice(list(range(15, 70)) + [-1, 200, np.nan], n),
        }
        df = pd.DataFrame(data)

        # 注入脏数据
        dirty = np.random.choice(n, 30, replace=False)
        df.loc[dirty[:8], 'price'] = np.nan
        df.loc[dirty[8:15], 'city'] = ''
        df = pd.concat([df, df.iloc[:5]])  # 重复行

        print(f"📦 生成示例数据: {len(df)} 行（含脏数据）")
        return df


# ============================================================
# 模块 2: 数据清洗
# ============================================================
class DataCleansing:
    """数据清洗模块"""

    def __init__(self, df):
        self.df = df.copy()
        self.log = []

    def remove_duplicates(self):
        """删除重复行"""
        before = len(self.df)
        self.df.drop_duplicates(inplace=True)
        removed = before - len(self.df)
        self.log.append(f"去重: 删除 {removed} 行重复数据")
        print(f"  🔄 去重: {before} → {len(self.df)} 行")
        return self

    def handle_missing(self, strategy='auto'):
        """处理缺失值"""
        missing = self.df.isnull().sum()
        missing_cols = missing[missing > 0]

        for col in missing_cols.index:
            if self.df[col].dtype in ['float64', 'int64']:
                fill_value = self.df[col].median()
                self.df[col].fillna(fill_value, inplace=True)
                self.log.append(f"缺失值填充: {col} → 中位数 {fill_value:.2f}")
            else:
                fill_value = self.df[col].mode()[0] if not self.df[col].mode().empty else 'Unknown'
                self.df[col].fillna(fill_value, inplace=True)
                self.log.append(f"缺失值填充: {col} → 众数 '{fill_value}'")

        # 处理空字符串
        for col in self.df.select_dtypes(include='object').columns:
            empty_count = (self.df[col] == '').sum()
            if empty_count > 0:
                self.df[col].replace('', np.nan, inplace=True)
                mode_val = self.df[col].mode()[0] if not self.df[col].mode().empty else 'Unknown'
                self.df[col].fillna(mode_val, inplace=True)
                self.log.append(f"空字符串填充: {col} → '{mode_val}' ({empty_count} 条)")

        print(f"  🧹 缺失值处理完成: {len(self.df.columns)} 列已检查")
        return self

    def fix_outliers(self, columns=None):
        """修复异常值"""
        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns

        for col in columns:
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 3 * IQR
            upper = Q3 + 3 * IQR

            outliers = ((self.df[col] < lower) | (self.df[col] > upper)).sum()
            self.df[col] = self.df[col].clip(lower=lower, upper=upper)
            if outliers > 0:
                self.log.append(f"异常值修复: {col} → clip [{lower:.1f}, {upper:.1f}] ({outliers} 条)")

        print(f"  📏 异常值检查完成")
        return self

    def convert_types(self, type_map=None):
        """类型转换"""
        if type_map is None:
            type_map = {}
            for col in self.df.select_dtypes(include='object').columns:
                if 'date' in col.lower():
                    type_map[col] = 'datetime'
                elif self.df[col].nunique() < 20:
                    type_map[col] = 'category'

        for col, dtype in type_map.items():
            if dtype == 'datetime':
                self.df[col] = pd.to_datetime(self.df[col], errors='coerce')
            elif dtype == 'category':
                self.df[col] = self.df[col].astype('category')
            self.log.append(f"类型转换: {col} → {dtype}")

        print(f"  🔄 类型转换完成: {len(type_map)} 列")
        return self

    def get_result(self):
        """获取清洗结果"""
        print(f"\n📋 清洗日志:")
        for entry in self.log:
            print(f"  • {entry}")
        return self.df


# ============================================================
# 主流程
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 数据分析 Pipeline - Step 1 & 2: 获取与清洗")
    print("=" * 60)

    # Step 1: 获取数据
    acquisition = DataAcquisition()
    df = acquisition.generate_sample_data(n=500)

    print(f"\n📊 原始数据:")
    print(f"  形状: {df.shape}")
    print(f"  缺失值:\n{df.isnull().sum()[df.isnull().sum() > 0]}")

    # Step 2: 清洗数据
    print("\n" + "=" * 60)
    print("🧹 开始清洗...")
    print("=" * 60)

    cleaner = DataCleansing(df)
    cleaned_df = (cleaner
                  .remove_duplicates()
                  .handle_missing()
                  .fix_outliers()
                  .convert_types()
                  .get_result())

    # 保存清洗结果
    cleaned_df.to_csv('cleaned_data.csv', index=False)
    print(f"\n✅ 清洗后数据保存至 cleaned_data.csv")
    print(f"  形状: {cleaned_df.shape}")
    print(f"  缺失值: {cleaned_df.isnull().sum().sum()}")
