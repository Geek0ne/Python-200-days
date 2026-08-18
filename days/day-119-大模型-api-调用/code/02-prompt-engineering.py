"""
Day 119 - Prompt Engineering 进阶技巧
=====================================
演示 6 大核心 Prompt 技巧，对比不同 Prompt 的效果差异
"""

import os
import json
import openai

client = openai.OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "your-key-here"),
    base_url="https://api.deepseek.com/v1"
)


# ─── 1. 角色设定（Role Prompting）───
def demo_role_prompting():
    """
    角色设定让模型锁定知识领域和表达风格。
    
    原理：LLM 在训练时学习了各种角色的表达模式，
    指定角色相当于激活对应的知识子集。
    """
    question = "如何优化 Python 代码性能？"
    
    # 没有角色设定
    prompt_naive = question
    
    # 有角色设定
    prompt_expert = (
        "你是一位有 15 年经验的 Python 性能优化专家，"
        "曾为多家大型互联网公司优化过核心系统。"
        f"\n\n问题：{question}\n\n"
        "请从底层原理出发，给出 3 个最有效的优化策略，"
        "每个策略附带代码示例和性能对比数据。"
    )
    
    print("=" * 60)
    print("1. 角色设定对比")
    print("=" * 60)
    
    print("\n【无角色设定】")
    print(f"Prompt: {prompt_naive}")
    # response = client.chat.completions.create(...)
    print("→ 输出：泛泛而谈，缺乏深度\n")
    
    print("【有角色设定】")
    print(f"Prompt: {prompt_expert[:100]}...")
    print("→ 输出：专业、有深度、带数据支撑\n")


# ─── 2. Few-Shot 示例 ───
def demo_few_shot():
    """
    Few-Shot = 提供几个输入-输出示例，让模型学习模式。
    
    原理：Transformer 的 in-context learning 能力，
    模型能从 few-shot 示例中"学习"任务模式。
    """
    # 差：没有示例
    bad_prompt = "分析这段代码的情感倾向"
    
    # 好：有示例
    good_prompt = """分析用户评论的情感倾向，输出 JSON 格式。

示例 1:
评论: "这个产品太棒了，超出预期！"
输出: {"sentiment": "positive", "confidence": 0.95, "keywords": ["棒", "超出预期"]}

示例 2:
评论: "一般般，没什么特别的"
输出: {"sentiment": "neutral", "confidence": 0.7, "keywords": ["一般般"]}

示例 3:
评论: "质量很差，浪费钱"
输出: {"sentiment": "negative", "confidence": 0.9, "keywords": ["质量差", "浪费"]}

现在分析:
评论: "物流很快，包装精美，但价格偏贵"
输出:"""
    
    print("=" * 60)
    print("2. Few-Shot 示例对比")
    print("=" * 60)
    print(f"\n【好的 Few-Shot Prompt】\n{good_prompt}")
    print("\n→ 模型能精确学习输出格式和判断标准")


# ─── 3. 链式思考（Chain of Thought）───
def demo_chain_of_thought():
    """
    CoT 让模型逐步推理，减少跳跃式错误。
    
    原理：大模型的"思考"是自回归的，
    逐步输出推理过程等于为后续步骤提供更多上下文。
    """
    problem = "一个水池有两个进水管，A管每小时进水3吨，B管每小时进水5吨。同时开两管，4小时能进多少水？"
    
    # 差：直接回答
    prompt_direct = f"回答以下问题：{problem}"
    
    # 好：引导逐步思考
    prompt_cot = f"""请一步步思考并解答以下问题：

{problem}

解题步骤：
1. 理解题意：找出关键信息
2. 列出已知条件
3. 建立数学关系
4. 计算过程
5. 验证答案
6. 给出最终结论"""

    print("=" * 60)
    print("3. 链式思考对比")
    print("=" * 60)
    print(f"\n【CoT Prompt】\n{prompt_cot}")


# ─── 4. 结构化输出 ───
def demo_structured_output():
    """
    明确输出格式，便于程序解析。
    
    原理：给模型明确的格式约束，减少自由发挥的空间。
    JSON 模式 + 示例 = 最可靠的结构化输出方案。
    """
    prompt = """分析以下代码片段，以 JSON 格式输出：

```python
def divide(a, b):
    return a / b
```

输出格式要求（严格遵守）：
{
    "function_name": "函数名",
    "description": "功能描述（一句话）",
    "issues": [
        {"type": "问题类型", "severity": "high/medium/low", "description": "问题描述"}
    ],
    "suggestions": ["改进建议1", "改进建议2"]
}"""

    print("=" * 60)
    print("4. 结构化输出示例")
    print("=" * 60)
    print(f"\n{prompt}")
    print("\n→ 程序可以直接解析 JSON 结果")


# ─── 5. 约束与边界 ───
def demo_constraints():
    """
    通过约束减少幻觉，控制输出质量。
    
    原理：LLM 的训练目标是"预测下一个 token"，
    没有内置的"我不知道"机制。约束能弥补这一缺陷。
    """
    prompt = """你是一位医疗健康顾问（注意：你不是真正的医生，只提供一般性健康建议）。

回答以下问题：
"经常头痛怎么办？"

严格遵守以下约束：
- ⚠️ 首先声明"以下为一般性建议，不替代专业医疗诊断"
- 只提供常见的缓解方法
- 不要给出具体药物剂量
- 如果症状严重，明确建议就医
- 回答控制在 150 字以内
- 如果问题超出你的知识范围，说"建议咨询专业医生"

输出："""

    print("=" * 60)
    print("5. 约束与边界示例")
    print("=" * 60)
    print(f"\n{prompt}")
    print("\n→ 约束减少幻觉，保护用户安全")


# ─── 6. 分步骤指令 ───
def demo_step_by_step():
    """
    分步骤让复杂任务条理清晰。
    
    原理：分解任务降低了每一步的复杂度，
    模型更容易生成高质量的逐步输出。
    """
    prompt = """任务：审查以下 Python 代码并提供改进建议。

```python
import os
def read_config():
    f = open('config.txt')
    data = f.read()
    f.close()
    return data
```

请按以下步骤进行：
步骤 1 - 代码风格审查：检查 PEP 8 规范、命名规范
步骤 2 - 功能分析：这段代码做了什么？有没有功能缺陷？
步骤 3 - 安全检查：有没有安全隐患？
步骤 4 - 性能分析：有没有性能问题？
步骤 5 - 改进方案：提供改进后的完整代码

每个步骤单独输出，格式：[步骤X] 标题 → 分析内容"""

    print("=" * 60)
    print("6. 分步骤指令示例")
    print("=" * 60)
    print(f"\n{prompt}")
    print("\n→ 每步聚焦一个维度，全面不遗漏")


# ─── 实战：Prompt 模板系统 ───
class PromptTemplate:
    """可复用的 Prompt 模板系统"""
    
    def __init__(self, template: str, required_vars: list = None):
        self.template = template
        self.required_vars = required_vars or []
    
    def render(self, **kwargs) -> str:
        """渲染模板，替换变量"""
        # 检查必需变量
        missing = [v for v in self.required_vars if v not in kwargs]
        if missing:
            raise ValueError(f"缺少必需变量: {missing}")
        
        result = self.template
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result


# 预定义模板
TEMPLATES = {
    "translate": PromptTemplate(
        template="""你是专业翻译。请将以下{source_lang}文本翻译为{target_lang}。

要求：
- 翻译要{style}
- 保持原文的{preserve}
- 不要添加解释

原文：
{text}

翻译：""",
        required_vars=["source_lang", "target_lang", "style", "preserve", "text"]
    ),
    
    "code_review": PromptTemplate(
        template="""你是资深 {language} 代码审查员。

审查以下代码，关注：{focus_areas}

```{language}
{code}
```

输出格式：
[功能理解] 一句话描述
[问题列表] - 问题类型: 描述 (严重度)
[改进建议] 具体建议
[改进代码] 完整修复后的代码""",
        required_vars=["language", "focus_areas", "code"]
    ),
    
    "summarize": PromptTemplate(
        template="""请用 {style} 风格总结以下内容。

要求：
- 保留关键信息
- 控制在 {length} 字以内
- 使用 {format} 格式输出

原文：
{text}

总结：""",
        required_vars=["style", "length", "format", "text"]
    )
}


def demo_template_system():
    """演示 Prompt 模板系统"""
    print("\n" + "=" * 60)
    print("Prompt 模板系统演示")
    print("=" * 60)
    
    # 使用翻译模板
    prompt = TEMPLATES["translate"].render(
        source_lang="中文",
        target_lang="英文",
        style="自然流畅",
        preserve="语气和情感",
        text="人生苦短，我用 Python"
    )
    print(f"\n【翻译模板】\n{prompt}")
    
    # 使用代码审查模板
    prompt = TEMPLATES["code_review"].render(
        language="Python",
        focus_areas="安全性、性能、可读性",
        code="import os; os.system(input())"
    )
    print(f"\n【代码审查模板】\n{prompt}")


if __name__ == "__main__":
    print("Day 119 - Prompt Engineering 进阶技巧\n")
    
    # 演示各技巧（不需要 API）
    demo_role_prompting()
    demo_few_shot()
    demo_chain_of_thought()
    demo_structured_output()
    demo_constraints()
    demo_step_by_step()
    demo_template_system()
    
    print("\n" + "=" * 60)
    print("💡 实际运行：取消注释代码中的 API 调用")
    print("   export DEEPSEEK_API_KEY='your-key'")
    print("=" * 60)
