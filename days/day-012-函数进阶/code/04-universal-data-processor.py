#!/usr/bin/env python3
"""
04-universal-data-processor.py — 通用数据处理器

综合运用 Day 012 所有进阶函数特性的完整实战项目：
  - 默认参数陷阱（None 安全模式）
  - *args / **kwargs（可变参数传递）
  - 函数作为参数（预处理回调）
  - Type Hints（完整类型注解）
  - 仅限关键字参数

运行: python3 04-universal-data-processor.py
"""

import time
import math
from typing import List, Union, Optional, Callable, Dict, Any, Tuple


# ============================================================
# 1. 通用数据处理器类
# ============================================================

class DataProcessor:
    """
    通用数据处理器

    综合运用 Day 012 的进阶函数特性:
    - 核心方法使用 *args 接收任意数量数据
    - 预处理函数作为参数传入（回调函数）
    - 配置参数通过 **kwargs 传入
    - 缓存字典使用 None 模式避免默认参数陷阱
    - 完整类型注解
    """

    def __init__(self, name: str = "default"):
        """
        初始化处理器

        Args:
            name: 处理器名称
        """
        self.name = name
        # 缓存字典 — 使用实例属性而非默认参数
        self._cache: dict[str, Any] = {}
        self._call_count: int = 0

    def process(
        self,
        *data: Union[int, float],
        preprocess: Optional[Callable] = None,
        agg_method: str = "sum",
        use_cache: bool = True,
        **options: Any,
    ) -> dict[str, Any]:
        """
        核心处理方法 — 接收任意数量的数据并处理

        Args:
            *data: 要处理的数据（可变位置参数）
            preprocess: 可选的预处理函数（回调）
            agg_method: 聚合方法（sum/mean/max/min）
            use_cache: 是否使用缓存
            **options: 其他配置选项

        Returns:
            处理结果字典

        Raises:
            ValueError: 当 agg_method 不支持时
        """
        self._call_count += 1

        # 步骤 1：应用预处理函数
        if preprocess is not None:
            processed = [preprocess(x) for x in data]
        else:
            processed = list(data)

        if not processed:
            return {
                "processor": self.name,
                "method": agg_method,
                "data_count": 0,
                "result": None,
                "call_count": self._call_count,
                "timestamp": time.time(),
            }

        # 步骤 2：缓存检查
        if use_cache:
            cache_key = self._make_cache_key(processed, agg_method)
            if cache_key in self._cache:
                options.get("verbose") and print(
                    f"[{self.name}] 缓存命中: {cache_key}"
                )
                return self._cache[cache_key]

        # 步骤 3：聚合计算
        result_value = self._aggregate(processed, agg_method)

        result = {
            "processor": self.name,
            "method": agg_method,
            "data_count": len(processed),
            "result": result_value,
            "call_count": self._call_count,
            "timestamp": time.time(),
        }

        # 步骤 4：缓存结果
        if use_cache:
            cache_key = self._make_cache_key(processed, agg_method)
            self._cache[cache_key] = result

        # 步骤 5：额外处理（通过 **options 控制）
        if options.get("verbose"):
            print(f"[{self.name}] 处理完成: {agg_method}，共 {len(processed)} 条数据")

        if options.get("format_result"):
            result["formatted"] = self._format_result(result_value, options.get("format_result"))

        return result

    def batch_process(
        self,
        datasets: list[tuple],
        *,
        preprocess: Optional[Callable] = None,
        agg_methods: list[str] = None,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """
        批量处理多个数据集

        Args:
            datasets: 数据集列表，每个元素是 (name, *values)
            preprocess: 预处理函数
            agg_methods: 批量聚合方法列表
            verbose: 是否输出详细信息

        Returns:
            所有处理结果的汇总字典

        示例:
            processor.batch_process([
                ("数学", 85, 92, 78),
                ("英语", 88, 95),
            ])
        """
        if agg_methods is None:
            agg_methods = ["sum", "mean", "max", "min"]

        results: dict[str, Any] = {}

        for item in datasets:
            name = item[0]
            values = item[1:]  # 解包：第一个是名称，其余是数据

            if verbose:
                print(f"\n▶ 处理数据集: {name} (共 {len(values)} 个值)")

            for method in agg_methods:
                result = self.process(
                    *values,
                    preprocess=preprocess,
                    agg_method=method,
                    use_cache=True,
                    verbose=verbose,
                )
                key = f"{name}_{method}"
                results[key] = result

        return results

    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取处理器统计信息"""
        return {
            "name": self.name,
            "cache_size": len(self._cache),
            "call_count": self._call_count,
        }

    # ---- 辅助方法 ----

    def _make_cache_key(self, data: list, method: str) -> str:
        """生成缓存键"""
        return f"{method}_{hash(tuple(round(x, 10) if isinstance(x, float) else x for x in data))}"

    def _aggregate(self, data: list[Union[int, float]], method: str) -> Union[int, float, None]:
        """执行聚合计算"""
        if method == "sum":
            return sum(data)
        elif method == "mean":
            return sum(data) / len(data)
        elif method == "max":
            return max(data)
        elif method == "min":
            return min(data)
        elif method == "product":
            return math.prod(data)
        elif method == "std":
            mean = sum(data) / len(data)
            variance = sum((x - mean) ** 2 for x in data) / len(data)
            return math.sqrt(variance)
        else:
            raise ValueError(f"不支持的聚合方法: {method}")

    @staticmethod
    def _format_result(value: Union[int, float], fmt: str) -> str:
        """格式化结果值"""
        if fmt == "percent":
            return f"{value * 100:.2f}%"
        elif fmt == "currency":
            return f"¥{value:,.2f}"
        elif fmt == "decimal2":
            return f"{value:.2f}"
        return str(value)


# ============================================================
# 2. 预处理函数（回调函数示例）
# ============================================================

def square(x: Union[int, float]) -> Union[int, float]:
    """预处理：平方"""
    return x * x


def cube(x: Union[int, float]) -> Union[int, float]:
    """预处理：立方"""
    return x * x * x


def normalize(x: Union[int, float]) -> float:
    """预处理：归一化到 [0, 1]（假设数据均为正数）"""
    # 使用 sigmoid 函数将任意值映射到 (0, 1)
    return 1.0 / (1.0 + math.exp(-x))


def clip(min_val: float, max_val: float) -> Callable:
    """
    预处理工厂：生成一个截断函数

    Args:
        min_val: 最小值
        max_val: 最大值

    Returns:
        截断函数

    演示高阶函数——返回一个闭包
    """
    def _clip(x: Union[int, float]) -> Union[int, float]:
        return max(min_val, min(max_val, x))
    return _clip


def log_transform(x: Union[int, float]) -> float:
    """预处理：对数变换"""
    if x <= 0:
        return 0.0
    return math.log1p(x)  # log(1 + x)，避免 log(0)


# ============================================================
# 3. 使用演示
# ============================================================

def demo_basic():
    """基本使用演示"""
    print("=" * 60)
    print("🔰 基本使用演示")
    print("=" * 60)

    processor = DataProcessor("demo")

    # 1️⃣ 直接处理几个数字
    result = processor.process(1, 2, 3, 4, 5)
    print(f"\n1. 基本求和: {result['result']}")

    # 2️⃣ 自定义聚合方法
    result = processor.process(1, 2, 3, 4, 5, agg_method="mean")
    print(f"2. 平均值: {result['result']}")

    # 3️⃣ 应用预处理回调
    result = processor.process(1, 2, 3, preprocess=square, agg_method="sum")
    print(f"3. 平方后求和 (1²+2²+3²): {result['result']}")

    # 4️⃣ 缓存验证（第二次调用从缓存读取）
    result2 = processor.process(1, 2, 3, preprocess=square, agg_method="sum")
    print(f"4. 缓存验证: {result2['result']} (调用次数: {result2['call_count']})")

    # 5️⃣ 通过 **options 传额外配置
    result = processor.process(
        10, 20, 30,
        agg_method="mean",
        verbose=True,
        format_result="currency",
    )
    print(f"5. 格式化输出: {result.get('formatted', 'N/A')}")


def demo_multi_aggregate():
    """多种聚合方法演示"""
    print("\n" + "=" * 60)
    print("📊 多种聚合方法演示")
    print("=" * 60)

    processor = DataProcessor("aggregate")

    data = (85, 92, 78, 95, 88, 76, 91, 84)

    for method in ["sum", "mean", "max", "min", "product", "std"]:
        result = processor.process(*data, agg_method=method)
        print(f"  {method:>8}: {result['result']}")


def demo_preprocess_functions():
    """预处理函数（回调）演示"""
    print("\n" + "=" * 60)
    print("🔄 预处理函数（回调）演示")
    print("=" * 60)

    processor = DataProcessor("preprocess")
    data = (1, 2, 3, 4, 5)

    preprocessors = [
        ("无预处理", None),
        ("平方", square),
        ("立方", cube),
        ("归一化 (sigmoid)", normalize),
        ("对数变换", log_transform),
        ("截断 [2, 4]", clip(2, 4)),
    ]

    for name, func in preprocessors:
        result = processor.process(*data, preprocess=func, agg_method="sum")
        print(f"  {name:>15}: sum = {result['result']:.4f}")


def demo_batch():
    """批量处理演示"""
    print("\n" + "=" * 60)
    print("🗂️  批量处理演示")
    print("=" * 60)

    processor = DataProcessor("batch")

    datasets = [
        ("数学成绩", 85, 92, 78, 95, 88),
        ("英语成绩", 90, 85, 88, 92, 87),
        ("物理成绩", 76, 82, 91, 88, 79),
    ]

    results = processor.batch_process(
        datasets,
        agg_methods=["sum", "mean", "max"],
        verbose=False,
    )

    print(f"{'科目':<12} {'总分':>8} {'平均分':>8} {'最高分':>8}")
    print("-" * 40)
    for subj, *_ in datasets:
        sum_key = f"{subj}_sum"
        mean_key = f"{subj}_mean"
        max_key = f"{subj}_max"
        print(f"{subj:<12} {results[sum_key]['result']:>8.0f} "
              f"{results[mean_key]['result']:>8.1f} {results[max_key]['result']:>8.0f}")

    # 显示缓存信息
    stats = processor.get_stats()
    print(f"\n缓存大小: {stats['cache_size']} 条目")
    print(f"总调用次数: {stats['call_count']}")


def demo_real_world_scenario():
    """真实场景模拟：销售数据分析"""
    print("\n" + "=" * 60)
    print("🏪 真实场景模拟：销售数据分析")
    print("=" * 60)

    processor = DataProcessor("sales")

    # 模拟销售数据（金额，单位：元）
    sales_data = (299, 450, 128, 890, 345, 670, 199, 550, 888, 320)

    print("原始销售数据（元）:")
    print(f"  {sales_data}")

    # 1. 统计汇总
    total = processor.process(*sales_data, agg_method="sum",
                              format_result="currency")
    avg = processor.process(*sales_data, agg_method="mean")
    best = processor.process(*sales_data, agg_method="max")
    worst = processor.process(*sales_data, agg_method="min")

    print(f"\n📈 销售统计:")
    print(f"  总销售额:     {total['formatted']}")
    print(f"  平均每单:     ¥{avg['result']:,.2f}")
    print(f"  最高单笔:     ¥{best['result']:,.2f}")
    print(f"  最低单笔:     ¥{worst['result']:,.2f}")

    # 2. 使用截断预处理处理异常值（比如总经理认为单笔超过 500 的去重分析）
    trimmed = processor.process(*sales_data, preprocess=clip(100, 500),
                                agg_method="sum", format_result="currency")
    print(f"\n🔧 价格截断后 (100~500):")
    print(f"  截断后总额:   {trimmed['formatted']}")

    # 3. 对数变换分析（处理数据偏态）
    log_result = processor.process(*sales_data, preprocess=log_transform,
                                   agg_method="mean")
    print(f"\n📐 对数变换后均值: {log_result['result']:.4f} "
          f"(原均值: {avg['result']:.2f})")

    # 4. 标准差分析（数据波动性）
    std_result = processor.process(*sales_data, agg_method="std")
    print(f"\n📊 标准差: ¥{std_result['result']:,.2f}")
    cv = std_result['result'] / avg['result']
    print(f"  变异系数: {cv:.2%} ({'波动大' if cv > 0.5 else '波动可接受'})")


# ============================================================
# 4. 架构总览图
# ============================================================

def print_architecture():
    """输出处理器架构总览"""
    arch = """
┌─────────────────────────────────────────────────────────────┐
│                  通用数据处理器 (DataProcessor)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  调用示例:                                                    │
│  processor.process(*data, preprocess=fn, agg_method="sum",   │
│                    use_cache=True, verbose=True, ...)        │
│                                                              │
│  执行流程:                                                    │
│                                                              │
│  *data ──────────────────────────────────────────────────┐   │
│    │                                                      │   │
│    ▼                                                      │   │
│  ┌─────────────────────────────────────────┐              │   │
│  │  ① 预处理 (preprocess 回调函数)          │              │   │
│  │     square / cube / normalize / clip / ... │            │   │
│  └──────────────┬──────────────────────────┘              │   │
│                 ▼                                         │   │
│  ┌─────────────────────────────────────────┐              │   │
│  │  ② 缓存检查                              │              │   │
│  │     use_cache=True → 查 cache 字典       │              │   │
│  │     命中 → 直接返回缓存结果               │              │   │
│  └──────────────┬──────────────────────────┘              │   │
│                 ▼ (未命中)                                │   │
│  ┌─────────────────────────────────────────┐              │   │
│  │  ③ 聚合计算 (agg_method)                 │              │   │
│  │     sum / mean / max / min / product / std │           │   │
│  └──────────────┬──────────────────────────┘              │   │
│                 ▼                                         │   │
│  ┌─────────────────────────────────────────┐              │   │
│  │  ④ 缓存结果 (use_cache=True → 存入 cache) │            │   │
│  └──────────────┬──────────────────────────┘              │   │
│                 ▼                                         │   │
│  ┌─────────────────────────────────────────┐              │   │
│  │  ⑤ 额外处理 (**options 控制)              │              │   │
│  │     verbose=True → 打印日志               │              │   │
│  │     format_result → 格式化输出            │              │   │
│  └──────────────┬──────────────────────────┘              │   │
│                 ▼                                         │   │
│           返回结果字典                                      │   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  涉及 Day 012 知识点:                                       │
│  • *data: 可变位置参数                                      │
│  • preprocess=None: None 模式避免默认参数陷阱               │
│  • **options: 可变关键字参数                                │
│  • Callable 回调函数: 函数作为参数                          │
│  • agg_method: 仅限关键字参数的替代设计                     │
│  • 完整类型注解: 参数 + 返回值                              │
│  • clip() 工厂函数: 闭包（返回函数）                       │
└─────────────────────────────────────────────────────────────┘
"""
    print(arch)


# ============================================================
# 5. 主程序入口
# ============================================================

def main():
    print("🐍 Day 012 函数进阶 — 实战：通用数据处理器\n")

    print_architecture()
    demo_basic()
    demo_multi_aggregate()
    demo_preprocess_functions()
    demo_batch()
    demo_real_world_scenario()

    print("\n" + "=" * 60)
    print("✅ 所有演示完成！")
    print("=" * 60)
    print(f"\n知识点覆盖清单:")
    print(f"  ✅ *args — 接收任意数量数据")
    print(f"  ✅ **kwargs — 传递配置选项")
    print(f"  ✅ 回调函数 — 预处理作为参数")
    print(f"  ✅ None 模式 — 避免默认参数陷阱")
    print(f"  ✅ Type Hints — 完整类型注解")
    print(f"  ✅ 高阶函数 — 预处理工厂")
    print(f"  ✅ 缓存 — 性能优化")


if __name__ == "__main__":
    main()
