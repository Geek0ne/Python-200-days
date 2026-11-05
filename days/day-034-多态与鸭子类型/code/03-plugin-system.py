"""
Day 034 — 多态与鸭子类型：实战案例
====================================

实战：插件系统 —— 一个完整的、支持优先级和依赖的插件框架
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any
import time


# ====================================
# 1. 插件抽象基类
# ====================================

class PluginPriority:
    """插件优先级常量"""
    LOWEST = 0
    LOW = 25
    NORMAL = 50
    HIGH = 75
    HIGHEST = 100
    SYSTEM = 200  # 系统级插件


class PluginBase(ABC):
    """插件基类 —— 定义插件接口契约"""

    @property
    @abstractmethod
    def name(self) -> str:
        """插件唯一名称"""
        pass

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        """执行优先级（数值越大越先执行）"""
        return PluginPriority.NORMAL

    @property
    def dependencies(self) -> List[str]:
        """依赖的其他插件名称列表"""
        return []

    def initialize(self) -> None:
        """插件初始化 —— 预留钩子"""
        pass

    @abstractmethod
    def process(self, data: Any) -> Any:
        """处理数据 —— 插件核心逻辑"""
        pass

    def cleanup(self) -> None:
        """插件清理 —— 预留钩子"""
        pass


# ====================================
# 2. 插件元数据类
# ====================================

class PluginMeta:
    """插件元数据"""

    def __init__(self, plugin: PluginBase):
        self.plugin = plugin
        self.name = plugin.name
        self.version = plugin.version
        self.priority = plugin.priority
        self.dependencies = plugin.dependencies
        self.initialized = False
        self.execution_count = 0
        self.total_time = 0.0
        self.errors: List[str] = []

    def __repr__(self) -> str:
        return (f"PluginMeta({self.name} v{self.version}, "
                f"priority={self.priority}, "
                f"executed={self.execution_count} times)")


# ====================================
# 3. 插件管理器
# ====================================

class PluginManager:
    """插件管理器 —— 管理插件的注册、加载、执行"""

    def __init__(self):
        self._plugins: Dict[str, PluginMeta] = {}
        self._execution_order: List[str] = []

    # ── 注册与加载 ──

    def register(self, plugin: PluginBase) -> None:
        """注册一个插件"""
        if not isinstance(plugin, PluginBase):
            raise TypeError(f"{type(plugin).__name__} 不是 PluginBase 的子类")

        if plugin.name in self._plugins:
            raise ValueError(f"插件 '{plugin.name}' 已注册")

        self._plugins[plugin.name] = PluginMeta(plugin)
        self._rebuild_order()
        print(f"  ✅ 插件 '{plugin.name}' v{plugin.version} 已注册")

    def unregister(self, name: str) -> None:
        """卸载一个插件"""
        if name not in self._plugins:
            raise KeyError(f"插件 '{name}' 未注册")

        # 检查是否有其他插件依赖它
        dependent = self._find_dependents(name)
        if dependent:
            raise RuntimeError(
                f"无法卸载 '{name}'，以下插件依赖它: {dependent}"
            )

        meta = self._plugins[name]
        if meta.initialized:
            meta.plugin.cleanup()

        del self._plugins[name]
        self._rebuild_order()
        print(f"  ❌ 插件 '{name}' 已卸载")

    def load(self, name: str) -> None:
        """加载（初始化）一个插件"""
        if name not in self._plugins:
            raise KeyError(f"插件 '{name}' 未注册")

        meta = self._plugins[name]
        if meta.initialized:
            print(f"  ℹ️  插件 '{name}' 已初始化，跳过")
            return

        # 先加载依赖
        for dep in meta.plugin.dependencies:
            if dep not in self._plugins:
                raise RuntimeError(
                    f"依赖插件 '{dep}' 未注册，无法加载 '{name}'"
                )
            self.load(dep)

        meta.plugin.initialize()
        meta.initialized = True
        print(f"  🔌 插件 '{name}' 已初始化")

    def load_all(self) -> None:
        """加载所有插件"""
        for name in self._execution_order:
            self.load(name)

    # ── 执行 ──

    def execute(self, data: Any) -> Dict[str, Any]:
        """按优先级顺序执行所有插件"""
        results: Dict[str, Any] = {}

        for name in self._execution_order:
            meta = self._plugins[name]

            if not meta.initialized:
                print(f"  ⚠️  插件 '{name}' 未初始化，跳过")
                continue

            start = time.perf_counter()
            try:
                result = meta.plugin.process(data)
                meta.execution_count += 1
                meta.total_time += time.perf_counter() - start
                results[name] = result
                print(f"  ✅ [{name}] 执行成功: {result}")
            except Exception as e:
                meta.errors.append(str(e))
                results[name] = f"错误: {e}"
                print(f"  ❌ [{name}] 执行失败: {e}")

        return results

    def execute_single(self, name: str, data: Any) -> Any:
        """执行单个插件"""
        if name not in self._plugins:
            raise KeyError(f"插件 '{name}' 未注册")

        meta = self._plugins[name]
        if not meta.initialized:
            raise RuntimeError(f"插件 '{name}' 未初始化")

        return meta.plugin.process(data)

    # ── 查询 ──

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        if name in self._plugins:
            return self._plugins[name].plugin
        return None

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def get_execution_order(self) -> List[str]:
        return self._execution_order.copy()

    def get_stats(self) -> Dict[str, Any]:
        """获取插件系统统计信息"""
        return {
            "total_plugins": len(self._plugins),
            "initialized": sum(1 for m in self._plugins.values() if m.initialized),
            "total_executions": sum(m.execution_count for m in self._plugins.values()),
            "plugins": {
                name: {
                    "version": meta.version,
                    "priority": meta.priority,
                    "executions": meta.execution_count,
                    "total_time_ms": round(meta.total_time * 1000, 2),
                    "errors": len(meta.errors),
                }
                for name, meta in self._plugins.items()
            }
        }

    # ── 内部方法 ──

    def _rebuild_order(self) -> None:
        """重新计算执行顺序（按优先级降序 + 依赖拓扑排序）"""
        # 拓扑排序（处理依赖）
        visited: Set[str] = set()
        order: List[str] = []

        def dfs(name: str) -> None:
            if name in visited:
                return
            visited.add(name)

            meta = self._plugins[name]
            for dep in meta.plugin.dependencies:
                if dep in self._plugins:
                    dfs(dep)

            order.append(name)

        for name in sorted(
            self._plugins.keys(),
            key=lambda n: self._plugins[n].priority,
            reverse=True
        ):
            dfs(name)

        # 按优先级在组内排序
        self._execution_order = sorted(
            order,
            key=lambda n: self._plugins[n].priority,
            reverse=True
        )

    def _find_dependents(self, name: str) -> List[str]:
        """查找依赖指定插件的其他插件"""
        dependents = []
        for meta in self._plugins.values():
            if name in meta.plugin.dependencies:
                dependents.append(meta.name)
        return dependents


# ====================================
# 4. 具体插件实现
# ====================================

class TrimPlugin(PluginBase):
    """去除首尾空白"""

    @property
    def name(self) -> str:
        return "trim"

    @property
    def priority(self) -> int:
        return PluginPriority.HIGHEST  # 最先执行

    def process(self, data: Any) -> Any:
        if isinstance(data, str):
            return data.strip()
        return data


class CleanPlugin(PluginBase):
    """清理多余空白"""

    @property
    def name(self) -> str:
        return "clean"

    @property
    def priority(self) -> int:
        return PluginPriority.HIGH

    @property
    def dependencies(self) -> List[str]:
        return ["trim"]  # 依赖 trim 先执行

    def process(self, data: Any) -> Any:
        if isinstance(data, str):
            import re
            return re.sub(r'\s+', ' ', data)
        return data


class UpperCasePlugin(PluginBase):
    """转大写"""

    @property
    def name(self) -> str:
        return "uppercase"

    @property
    def priority(self) -> int:
        return PluginPriority.NORMAL

    @property
    def dependencies(self) -> List[str]:
        return ["clean"]

    def process(self, data: Any) -> Any:
        if isinstance(data, str):
            return data.upper()
        return data


class StatPlugin(PluginBase):
    """文本统计分析"""

    @property
    def name(self) -> str:
        return "stats"

    @property
    def priority(self) -> int:
        return PluginPriority.LOW

    def initialize(self) -> None:
        self._word_counts: Dict[str, int] = {}

    def process(self, data: Any) -> Any:
        if isinstance(data, str):
            words = data.split()
            for word in words:
                word_clean = word.strip('.,!?;:()[]{}"\'')
                if word_clean:
                    self._word_counts[word_clean] = \
                        self._word_counts.get(word_clean, 0) + 1
            return {
                "chars": len(data),
                "words": len(words),
                "unique_words": len(self._word_counts),
                "word_freq": dict(sorted(
                    self._word_counts.items(),
                    key=lambda x: -x[1]
                )[:5])
            }
        return data


class ReversePlugin(PluginBase):
    """反转文本"""

    @property
    def name(self) -> str:
        return "reverse"

    @property
    def priority(self) -> int:
        return PluginPriority.LOWEST

    def process(self, data: Any) -> Any:
        if isinstance(data, str):
            return data[::-1]
        return data


# ====================================
# 5. 演示
# ====================================

def demo():
    print("=" * 60)
    print("🔌 Python 插件系统实战演示")
    print("=" * 60)

    manager = PluginManager()

    # 注册插件
    print("\n📦 注册插件:")
    manager.register(TrimPlugin())
    manager.register(CleanPlugin())
    manager.register(UpperCasePlugin())
    manager.register(StatPlugin())
    manager.register(ReversePlugin())

    # 查看执行顺序
    print(f"\n📋 执行顺序: {manager.get_execution_order()}")

    # 加载所有插件
    print("\n🔌 加载插件:")
    manager.load_all()

    # 执行处理
    print(f"\n⚡ 执行处理:")
    text = "   Hello   World   from   Python   Plugin   System!   "
    print(f"   输入: '{text}'")

    results = manager.execute(text)

    # 查看最终结果（取最后一个插件的输出）
    final_plugin = manager.get_execution_order()[-1]
    print(f"\n🏁 最终结果 (来自 '{final_plugin}'):")
    print(f"   {results[final_plugin]}")

    # 统计信息
    print(f"\n📊 插件系统统计:")
    stats = manager.get_stats()
    print(f"   总插件数: {stats['total_plugins']}")
    print(f"   已初始化: {stats['initialized']}")
    print(f"   总执行次数: {stats['total_executions']}")

    # 测试卸载
    print(f"\n🗑️ 卸载插件测试:")
    try:
        manager.unregister("trim")  # 应该失败，因为 clean 依赖它
    except RuntimeError as e:
        print(f"   预期错误: {e}")

    # 先卸载 dependents
    manager.unregister("reverse")
    print(f"   当前插件: {manager.list_plugins()}")

    print("\n" + "=" * 60)
    print("✅ 插件系统演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
