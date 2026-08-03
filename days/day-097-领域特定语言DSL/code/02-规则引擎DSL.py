"""
Day 097 - 进阶 DSL：规则引擎

学习要点：
1. 用装饰器 + 链式调用构建规则引擎 DSL
2. 条件与动作的解耦
3. 规则优先级与冲突解决
"""

from dataclasses import dataclass, field
from typing import Callable, Any, Optional
from enum import Enum


# ============================================================
# 规则优先级
# ============================================================

class Priority(Enum):
    LOW = 1
    MEDIUM = 5
    HIGH = 10
    CRITICAL = 100


# ============================================================
# 核心：规则类
# ============================================================

@dataclass
class Rule:
    """一条规则 = 条件 + 动作"""
    name: str
    condition: Callable[[dict], bool]
    action: Callable[[dict], Any]
    priority: Priority = Priority.MEDIUM
    enabled: bool = True
    
    def matches(self, context: dict) -> bool:
        if not self.enabled:
            return False
        try:
            return self.condition(context)
        except Exception as e:
            print(f"  ⚠️ 规则 [{self.name}] 条件执行出错: {e}")
            return False
    
    def execute(self, context: dict) -> Any:
        return self.action(context)


# ============================================================
# 规则引擎
# ============================================================

class RuleEngine:
    """规则引擎 DSL"""
    
    def __init__(self):
        self.rules: list[Rule] = []
    
    def add_rule(self, name: str, priority: Priority = Priority.MEDIUM):
        """
        装饰器 DSL：定义规则
        
        @engine.add_rule("年龄验证", priority=Priority.HIGH)
        def age_check(ctx):
            return ctx.get("age", 0) >= 18
        age_check.action = lambda ctx: "通过"
        """
        def decorator(func):
            rule = Rule(
                name=name,
                condition=func,
                action=lambda ctx: f"规则 [{name}] 触发",
                priority=priority
            )
            self.rules.append(rule)
            # 保留原函数并添加 action 属性
            func.rule = rule
            func.action = rule.action  # 默认 action
            return func
        return decorator
    
    def when(self, condition: Callable):
        """
        链式调用 DSL：定义条件 → 动作
        
        engine.when(lambda ctx: ctx["score"] > 90) \
              .then(lambda ctx: "优秀")
        """
        return _RuleBuilder(self, condition)
    
    def evaluate(self, context: dict) -> list[dict]:
        """评估所有规则，按优先级排序"""
        results = []
        
        # 找到匹配的规则
        matched = [r for r in self.rules if r.matches(context)]
        
        # 按优先级排序（高优先级先执行）
        matched.sort(key=lambda r: r.priority.value, reverse=True)
        
        for rule in matched:
            result = rule.execute(context)
            results.append({
                "rule": rule.name,
                "priority": rule.priority.name,
                "result": result
            })
            print(f"  ✅ [{rule.priority.name}] {rule.name} → {result}")
        
        return results


class _RuleBuilder:
    """规则构建器：支持 when().then() 链式调用"""
    
    def __init__(self, engine: RuleEngine, condition):
        self._engine = engine
        self._condition = condition
    
    def then(self, action: Callable):
        """定义动作并注册规则"""
        rule = Rule(
            name=f"auto_rule_{len(self._engine.rules)}",
            condition=self._condition,
            action=action,
            priority=Priority.MEDIUM
        )
        self._engine.rules.append(rule)
        return self._engine


# ============================================================
# DSL 使用示例
# ============================================================

print("=" * 60)
print("规则引擎 DSL 实战演示")
print("=" * 60)

engine = RuleEngine()

# ---------- 方式 1：装饰器风格 ----------

@engine.add_rule("用户等级判定", priority=Priority.HIGH)
def user_level(ctx):
    """根据积分判定用户等级"""
    score = ctx.get("score", 0)
    if score >= 1000:
        return True
    return False

# 手动设置动作
def level_action(ctx):
    return f"🏆 {ctx['name']} 升级为钻石会员 (积分: {ctx['score']})"

user_level.rule.action = level_action


@engine.add_rule("年龄验证", priority=Priority.MEDIUM)
def age_check(ctx):
    """检查是否成年"""
    return ctx.get("age", 0) >= 18

age_check.rule.action = lambda ctx: f"✅ {ctx['name']} 通过年龄验证"


@engine.add_rule("消费满减", priority=Priority.LOW)
def discount_check(ctx):
    """消费满 500 减 50"""
    return ctx.get("amount", 0) >= 500

discount_check.rule.action = lambda ctx: f"🎁 {ctx['name']} 享受满减优惠 (消费: ¥{ctx['amount']})"


# ---------- 方式 2：链式调用风格 ----------

(engine.when(lambda ctx: ctx.get("vip", False))
       .then(lambda ctx: f"👑 {ctx['name']} 为 VIP 用户，享受专属服务"))

(engine.when(lambda ctx: ctx.get("age", 0) < 18)
       .then(lambda ctx: f"🔒 {ctx['name']} 为未成年用户，限制部分内容"))


# ---------- 测试 ----------

print("\n--- 测试场景 1：VIP 用户，高积分 ---")
context1 = {"name": "Alice", "age": 25, "score": 1200, "amount": 800, "vip": True}
results1 = engine.evaluate(context1)

print("\n--- 测试场景 2：普通用户，未成年 ---")
context2 = {"name": "Bob", "age": 15, "score": 50, "amount": 100, "vip": False}
results2 = engine.evaluate(context2)

print("\n--- 测试场景 3：中等用户 ---")
context3 = {"name": "Charlie", "age": 30, "score": 300, "amount": 600, "vip": False}
results3 = engine.evaluate(context3)

print("\n" + "=" * 60)
print("DSL 设计要点")
print("=" * 60)
print("""
1. 装饰器 @engine.add_rule() → 声明式定义规则
2. 链式调用 engine.when().then() → 流畅接口
3. 优先级机制 → 控制规则执行顺序
4. 条件/动作解耦 → 规则可复用、可组合

这就是「用 Python 语法写领域特定语言」的威力！
""")
