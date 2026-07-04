"""
Day 052 - 实战：快照与回滚系统
主题：深拷贝在实际项目中的应用
"""

import copy
from datetime import datetime
from typing import Any, Optional, List


# ============================================================
# 1. 简单快照系统
# ============================================================
print("=" * 60)
print("1. 简单快照系统")
print("=" * 60)

class SnapshotManager:
    """通用快照管理器"""

    def __init__(self, obj):
        self._obj = obj
        self._snapshots: List[dict] = []

    def save(self, name: str = ""):
        """保存当前状态的快照"""
        snapshot = {
            "name": name or f"snapshot_{len(self._snapshots) + 1}",
            "data": copy.deepcopy(self._obj),
            "timestamp": datetime.now().isoformat()
        }
        self._snapshots.append(snapshot)
        return snapshot["name"]

    def restore(self, index: int = -1) -> bool:
        """恢复到指定快照"""
        if not self._snapshots:
            print("  没有可恢复的快照")
            return False

        snapshot = self._snapshots[index]
        self._obj.__dict__.update(snapshot["data"].__dict__)
        print(f"  恢复到: {snapshot['name']} ({snapshot['timestamp']})")
        return True

    def list_snapshots(self):
        """列出所有快照"""
        for i, snap in enumerate(self._snapshots):
            print(f"  [{i}] {snap['name']} - {snap['timestamp']}")

    @property
    def count(self):
        return len(self._snapshots)


# 使用
class GameCharacter:
    def __init__(self, name, hp, mp):
        self.name = name
        self.hp = hp
        self.mp = mp
        self.inventory = []

    def __repr__(self):
        return f"GameCharacter({self.name!r}, hp={self.hp}, mp={self.mp})"


player = GameCharacter("勇者", 100, 50)
manager = SnapshotManager(player)

# 保存快照
manager.save("初始状态")
print(f"当前状态: {player}")

# 修改状态
player.hp = 80
player.mp = 30
player.inventory.append("药水")
print(f"战斗后: {player}")

manager.save("战斗后")

# 继续修改
player.hp = 20
print(f"受伤后: {player}")

# 恢复
print("\n恢复到战斗后状态:")
manager.restore(-2)
print(f"恢复后: {player}")

print(f"\n快照列表:")
manager.list_snapshots()


# ============================================================
# 2. 版本控制文档
# ============================================================
print("\n" + "=" * 60)
print("2. 版本控制文档")
print("=" * 60)

class VersionedDocument:
    """带版本控制的文档"""

    def __init__(self, title: str, content: str = ""):
        self.title = title
        self.content = content
        self._versions: List[dict] = []
        self._current_version = -1

    def edit(self, new_content: str, author: str = "anonymous"):
        """编辑文档，自动创建版本"""
        # 保存当前版本
        version = {
            "content": self.content,
            "author": author,
            "timestamp": datetime.now().isoformat(),
            "version": len(self._versions)
        }
        self._versions.append(version)
        self._current_version = len(self._versions) - 1
        self.content = new_content

    def undo(self) -> bool:
        """撤销到上一个版本"""
        if self._current_version < 0:
            print("  没有可撤销的版本")
            return False

        version = self._versions[self._current_version]
        self.content = version["content"]
        self._current_version -= 1
        print(f"  撤销到版本 {version['version']}")
        return True

    def redo(self) -> bool:
        """重做到下一个版本"""
        if self._current_version >= len(self._versions) - 1:
            print("  没有可重做的版本")
            return False

        self._current_version += 1
        version = self._versions[self._current_version]
        self.content = version["content"]
        print(f"  重做到版本 {version['version']}")
        return True

    def get_version(self, index: int) -> Optional[dict]:
        """获取指定版本的信息"""
        if 0 <= index < len(self._versions):
            return self._versions[index].copy()
        return None

    def list_versions(self):
        """列出所有版本"""
        for i, v in enumerate(self._versions):
            marker = " ← 当前" if i == self._current_version else ""
            print(f"  [v{v['version']}] {v['timestamp']} by {v['author']}{marker}")

    def __repr__(self):
        return f"VersionedDocument({self.title!r}, versions={len(self._versions)})"


# 使用
doc = VersionedDocument("API文档", "v1.0 - 初始版本")
print(f"创建文档: {doc}")
print(f"内容: {doc.content}")

doc.edit("v1.1 - 添加认证说明", "Alice")
doc.edit("v1.2 - 添加错误码说明", "Bob")
doc.edit("v1.3 - 更新示例代码", "Alice")

print(f"\n版本历史:")
doc.list_versions()

print(f"\n当前内容: {doc.content}")

doc.undo()
print(f"撤销后: {doc.content}")

doc.undo()
print(f"再次撤销: {doc.content}")


# ============================================================
# 3. 配置热重载
# ============================================================
print("\n" + "=" * 60)
print("3. 配置热重载")
print("=" * 60)

class ConfigManager:
    """配置管理器，支持热重载"""

    def __init__(self, config: dict):
        self._config = copy.deepcopy(config)
        self._backup = copy.deepcopy(config)
        self._history: List[dict] = []

    def update(self, updates: dict, validate: bool = True):
        """更新配置"""
        # 保存历史
        self._history.append({
            "config": copy.deepcopy(self._config),
            "timestamp": datetime.now().isoformat()
        })

        # 应用更新
        self._config.update(updates)

        # 验证配置
        if validate and not self._validate():
            print("  ⚠️ 配置验证失败，回滚到上一版本")
            self.rollback()
            return False

        print(f"  ✅ 配置已更新: {list(updates.keys())}")
        return True

    def rollback(self) -> bool:
        """回滚到上一版本"""
        if not self._history:
            print("  没有可回滚的历史")
            return False

        prev = self._history.pop()
        self._config = prev["config"]
        print(f"  ⏪ 回滚到: {prev['timestamp']}")
        return True

    def reset(self):
        """重置为初始配置"""
        self._config = copy.deepcopy(self._backup)
        self._history.clear()
        print("  🔄 配置已重置为初始值")

    def _validate(self) -> bool:
        """简单的配置验证"""
        required = ["host", "port"]
        return all(k in self._config for k in required)

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def __repr__(self):
        return f"ConfigManager({self._config})"


# 使用
initial_config = {
    "host": "localhost",
    "port": 5432,
    "debug": False,
    "timeout": 30
}

manager = ConfigManager(initial_config)
print(f"初始配置: {manager}")

# 更新配置
manager.update({"debug": True, "timeout": 60})
print(f"更新后: {manager}")

# 尝试无效更新
manager.update({"host": None})  # 验证失败
print(f"无效更新后: {manager}")  # 应该回滚了

# 手动回滚
manager.update({"debug": False})
manager.rollback()
print(f"手动回滚后: {manager}")


# ============================================================
# 4. 状态机快照
# ============================================================
print("\n" + "=" * 60)
print("4. 状态机快照")
print("=" * 60)

class StateMachine:
    """带快照的状态机"""

    def __init__(self, initial_state: str):
        self.state = initial_state
        self._snapshots: List[dict] = []
        self._transitions = {}

    def add_transition(self, from_state: str, to_state: str, event: str):
        """添加状态转换规则"""
        if from_state not in self._transitions:
            self._transitions[from_state] = {}
        self._transitions[from_state][event] = to_state

    def trigger(self, event: str) -> bool:
        """触发事件"""
        if self.state not in self._transitions:
            print(f"  ❌ 状态 {self.state} 没有转换规则")
            return False

        if event not in self._transitions[self.state]:
            print(f"  ❌ 事件 {event} 在状态 {self.state} 无效")
            return False

        # 保存快照
        self._snapshots.append({
            "state": self.state,
            "timestamp": datetime.now().isoformat()
        })

        old_state = self.state
        self.state = self._transitions[self.state][event]
        print(f"  {old_state} --({event})--> {self.state}")
        return True

    def undo(self) -> bool:
        """撤销到上一个状态"""
        if not self._snapshots:
            print("  没有可撤销的状态")
            return False

        snapshot = self._snapshots.pop()
        self.state = snapshot["state"]
        print(f"  ⏪ 回滚到状态: {self.state}")
        return True

    def __repr__(self):
        return f"StateMachine(state={self.state!r})"


# 使用
fsm = StateMachine("idle")

# 添加转换规则
fsm.add_transition("idle", "running", "start")
fsm.add_transition("running", "paused", "pause")
fsm.add_transition("paused", "running", "resume")
fsm.add_transition("running", "idle", "stop")
fsm.add_transition("paused", "idle", "stop")

print(f"初始状态: {fsm}")

fsm.trigger("start")
fsm.trigger("pause")
fsm.trigger("resume")
fsm.trigger("stop")

print(f"\n撤销操作:")
fsm.undo()  # 回到 running
fsm.undo()  # 回到 paused
print(f"当前状态: {fsm}")
