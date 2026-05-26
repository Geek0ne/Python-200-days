#!/usr/bin/env python3
"""
Day 003 — 字符串深入：文本模板引擎实战
=================================

实战案例：构建一个简易的文本模板引擎，支持变量替换、条件渲染和循环。
综合运用字符串格式化、替换、正则、分割等操作。

可直接运行：python3 02-template-engine.py
"""

import re
from typing import Dict, Any


class TemplateEngine:
    """
    一个简易的文本模板引擎。

    支持语法：
    - {{ variable }}          — 变量替换
    - {{ variable | default }} — 带默认值
    - {% if cond %}...{% elif cond %}...{% else %}...{% endif %}
    - {% for item in list %}...{% endfor %}
    - {{ loop.index }}, {{ loop.first }}, {{ loop.last }}
    """

    def __init__(self, template: str):
        self.template = template

    def render(self, context: Dict[str, Any]) -> str:
        result = self.template
        result = self._process_loops(result, context)
        result = self._process_conditionals(result, context)
        result = self._process_variables(result, context)
        return result

    # ---------------------------------------------------------
    # 变量替换
    # ---------------------------------------------------------
    def _process_variables(self, text: str, context: Dict[str, Any]) -> str:
        def replacer(m):
            raw = m.group(1).strip()
            if "|" in raw:
                name, default = [p.strip() for p in raw.split("|", 1)]
            else:
                name, default = raw, None
            val = self._resolve(name, context)
            if val is not None:
                return str(val)
            return default if default is not None else ""
        return re.sub(r"\{\{(.*?)\}\}", replacer, text)

    def _resolve(self, path: str, ctx: dict) -> Any:
        parts = path.split(".")
        v = ctx
        for p in parts:
            if isinstance(v, dict):
                v = v.get(p)
            elif hasattr(v, p):
                v = getattr(v, p)
            elif isinstance(v, (list, tuple)) and p.lstrip("-").isdigit():
                try:
                    v = v[int(p)]
                except (IndexError, ValueError):
                    return None
            else:
                return None
            if v is None:
                return None
        return v

    # ---------------------------------------------------------
    # 条件语句
    # ---------------------------------------------------------
    def _process_conditionals(self, text: str, context: Dict[str, Any]) -> str:
        """
        处理 {% if %}...{% elif %}...{% else %}...{% endif %}
        使用整块匹配，内部用 re.split 按 elif/else 分割
        """
        # 匹配完整的 if 块（包含 elif/else）
        pattern = r"\{%\s*if\s+(.*?)\s*%\}(.*?)\{%\s*endif\s*%\}"

        def replace_block(m):
            first_cond = m.group(1).strip()
            inner = m.group(2)

            # 用 re.split 按 elif/else 标签分割 inner
            # 注意：内层嵌套中的 {% if %} 不应被匹配到，但我们只在外层分割
            splitter = re.compile(
                r"\{%\s*elif\s+(.*?)\s*%\}|\{%\s*else\s*%\}",
                flags=re.DOTALL
            )
            segments = splitter.split(inner)

            # 交替结构：body0, cond1, body1, cond2_or_None, body2, ...
            # 由于 splitter 有 2 个捕获组，会有 None 填充
            # 简化: 用 findall 来找标签位置

            # 手工法：逐段解析
            branches = [(first_cond, '')]
            idx = 0

            for token in re.finditer(
                r"\{%\s*elif\s+(.*?)\s*%\}|\{%\s*else\s*%\}",
                inner,
                flags=re.DOTALL
            ):
                # token 前的内容属于上一个分支
                body_before = inner[idx:token.start()]
                # 更新上一个分支的 body
                branches[-1] = (branches[-1][0], body_before)

                if token.lastgroup is None or token.lastgroup == '':
                    if token.group(1) is not None:  # elif
                        branches.append((token.group(1).strip(), ''))
                    else:  # else
                        branches.append((None, ''))
                idx = token.end()

            # 最后一段
            branches[-1] = (branches[-1][0], inner[idx:])

            # 求值
            for cond, body_raw in branches:
                if cond is None:
                    return self._process_conditionals(body_raw, context)
                if self._eval(cond, context):
                    return self._process_conditionals(body_raw, context)
            return ""

        prev = None
        current = text
        while current != prev:
            prev = current
            current = re.sub(pattern, replace_block, current, flags=re.DOTALL)
        return current

    def _eval(self, condition: str, ctx: dict) -> bool:
        condition = condition.strip()
        # not
        if condition.startswith("not "):
            return not bool(self._resolve(condition[4:].strip(), ctx))
        # 比较操作
        for op in [">=", "<=", "!=", "==", ">", "<"]:
            if op in condition:
                left_raw, right_raw = [p.strip() for p in condition.split(op, 1)]
                left = self._resolve(left_raw, ctx)
                if left is None:
                    left = self._coerce(left_raw)
                right = self._resolve(right_raw, ctx)
                if right is None:
                    right = self._coerce(right_raw)
                try:
                    if op == ">=": return left >= right
                    if op == "<=": return left <= right
                    if op == "!=": return left != right
                    if op == "==": return left == right
                    if op == ">":  return left > right
                    if op == "<":  return left < right
                except TypeError:
                    return False
        # 裸变量
        v = self._resolve(condition, ctx)
        return bool(v)

    @staticmethod
    def _coerce(raw: str):
        """尝试将字符串转为数字"""
        try:
            return int(raw)
        except ValueError:
            try:
                return float(raw)
            except ValueError:
                return raw.strip("\"'")

    # ---------------------------------------------------------
    # 循环语句
    # ---------------------------------------------------------
    def _process_loops(self, text: str, context: Dict[str, Any]) -> str:
        """
        处理 {% for x in list %}...{% endfor %}
        支持嵌套：在每次迭代中递归调用自身处理 body
        """
        pattern = r"\{%\s*for\s+(\w+)\s+in\s+([\w.]+)\s*%\}(.*)\{%\s*endfor\s*%\}"

        def replacer(m):
            item_var = m.group(1)
            list_path = m.group(2)
            body = m.group(3)

            iterable = self._resolve(list_path, context)
            if not isinstance(iterable, (list, tuple, set, str)):
                return ""

            items = list(iterable)
            chunks = []
            for i, item in enumerate(items):
                ctx = dict(context)
                ctx[item_var] = item
                ctx["loop"] = {
                    "index": i + 1,
                    "index0": i,
                    "first": i == 0,
                    "last": i == len(items) - 1,
                    "length": len(items),
                }
                # 递归处理 body（嵌套循环/条件/变量）
                rendered = body
                rendered = self._process_loops(rendered, ctx)
                rendered = self._process_conditionals(rendered, ctx)
                rendered = self._process_variables(rendered, ctx)
                chunks.append(rendered)
            return "".join(chunks)

        # while 循环 = 由外到内逐层展开
        prev = None
        current = text
        while current != prev:
            prev = current
            current = re.sub(pattern, replacer, current, flags=re.DOTALL)
        return current


# ============================================================
# 用例
# ============================================================

def ex01_basic():
    print("=" * 60)
    print("示例 1：基础变量替换")
    print("=" * 60)
    t = TemplateEngine("Hello, {{ name }}! You are {{ age }} years old.")
    print(t.render({"name": "Alice", "age": 25})); print()

def ex02_default():
    print("=" * 60)
    print("示例 2：默认值")
    print("=" * 60)
    t = TemplateEngine("Hello {{ name | Guest }}! Score: {{ score | 0 }}.")
    print(t.render({"name": "Bob"})); print()

def ex03_if_elif_else():
    print("=" * 60)
    print("示例 3：if / elif / else")
    print("=" * 60)
    tmpl = "{% if score >= 90 %}Excellent ({{ score }})!" \
           "{% elif score >= 60 %}Passed ({{ score }})." \
           "{% else %}Failed ({{ score }}).{% endif %}"
    t = TemplateEngine(tmpl)
    for s in [95, 72, 45]:
        print(f"  score={s} → {t.render({'score': s})}")
    print()

def ex04_boolean():
    print("=" * 60)
    print("示例 4：布尔条件 & not")
    print("=" * 60)
    t = TemplateEngine("{% if show %}Welcome {{ n }}!{% else %}Goodbye {{ n }}!{% endif %}")
    print(f"  show=True  → {t.render({'n':'Alice','show':True})}")
    print(f"  show=False → {t.render({'n':'Alice','show':False})}")

    t2 = TemplateEngine("{% if not admin %}Denied.{% else %}Welcome {{ n }}!{% endif %}")
    print(f"  not admin  → {t2.render({'n':'A','admin':False})}")
    print(f"  admin      → {t2.render({'n':'A','admin':True})}")
    print()

def ex05_loop():
    print("=" * 60)
    print("示例 5：循环遍历")
    print("=" * 60)
    tmpl = "Shopping:\n{% for item in items %}{{ loop.index }}. {{ item }}" \
           "{% if loop.last %} (last!){% endif %}\n{% endfor %}"
    t = TemplateEngine(tmpl)
    print(t.render({"items": ["Apples", "Bananas", "Milk"]})); print()

def ex06_nested_loop():
    print("=" * 60)
    print("示例 6：嵌套循环（点号路径）")
    print("=" * 60)
    tmpl = """Teams:
{% for t in teams %}
  {{ t.name }}:
  {% for m in t.members %}- {{ m }}
  {% endfor %}{% endfor %}"""
    t = TemplateEngine(tmpl)
    print(t.render({"teams": [
        {"name": "Alpha", "members": ["A", "B"]},
        {"name": "Beta", "members": ["C", "D", "E"]},
    ]})); print()

def ex07_nested():
    print("=" * 60)
    print("示例 7：嵌套对象 + 默认值")
    print("=" * 60)
    t = TemplateEngine("Name: {{ u.name }}\nCity: {{ u.addr.city | N/A }}")
    print(t.render({"u": {"name": "Alice", "addr": {"city": "BJ"}}}))
    print()

def ex08_report():
    print("=" * 60)
    print("示例 8：综合 — 成绩报告单")
    print("=" * 60)
    tmpl = """
==================================
         成绩报告单
==================================
姓名: {{ stu.name }}
班级: {{ stu.class_name | 未知 }}
{% for sub in subjects %}
  {% if sub.score >= 90 %}  ✅ {{ sub.name }}: {{ sub.score }} (优秀)
  {% elif sub.score >= 75 %}  👍 {{ sub.name }}: {{ sub.score }} (良好)
  {% elif sub.score >= 60 %}  👌 {{ sub.name }}: {{ sub.score }} (及格)
  {% else %}  ❌ {{ sub.name }}: {{ sub.score }} (不及格)
  {% endif %}{% endfor %}
{% if total %}总分: {{ total }} | 平均: {{ avg|0 }}
  {% if avg >= 85 %}🎉 优秀!
  {% elif avg >= 70 %}👍 良好
  {% elif avg >= 60 %}👌 及格
  {% else %}💪 加油
  {% endif %}{% endif %}
日期: {{ date | 未知 }}"""
    subs = [{"name": "语文", "score": 88}, {"name": "数学", "score": 95},
            {"name": "英语", "score": 72}, {"name": "物理", "score": 58}]
    total = sum(s["score"] for s in subs)
    avg = total / len(subs)
    t = TemplateEngine(tmpl)
    print(t.render({"stu": {"name": "张三", "class_name": "高三(1)班"},
                    "subjects": subs, "total": total, "avg": avg,
                    "date": "2024-05-27"}))


if __name__ == "__main__":
    ex01_basic()
    ex02_default()
    ex03_if_elif_else()
    ex04_boolean()
    ex05_loop()
    ex06_nested_loop()
    ex07_nested()
    ex08_report()
    print("=" * 60)
    print("✅ 所有示例运行完成！")
    print("=" * 60)
