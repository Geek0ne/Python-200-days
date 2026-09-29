"""
Day 119 - API 速查与对比
========================
OpenAI / DeepSeek / 通义千问 / 文心一言 API 对比速查
"""

import os


# ─── 各平台 API 对比 ───

API_COMPARISON = """
╔══════════════════════════════════════════════════════════════════╗
║                    大模型 API 平台对比速查表                      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  平台        base_url                    模型                    ║
║  ─────────  ──────────────────────────  ──────────────────────  ║
║  OpenAI     https://api.openai.com/v1   gpt-4o, gpt-4o-mini    ║
║  DeepSeek   https://api.deepseek.com/v1 deepseek-chat,         ║
║                                        deepseek-coder           ║
║  通义千问    https://dashscope.aliyuncs  qwen-turbo, qwen-plus  ║
║             .com/compatible-mode/v1                              ║
║  文心一言    https://aip.baidubce.com     ernie-3.5, ernie-4.0   ║
║                                                                  ║
║  💡 OpenAI SDK 兼容所有平台，只需改 base_url！                    ║
╚══════════════════════════════════════════════════════════════════╝
"""


# ─── OpenAI SDK 通用调用模板 ───

CODE_TEMPLATE = '''
import openai

# ═══ 通用调用模板（适用于所有兼容平台）═══

client = openai.OpenAI(
    api_key="your-api-key",
    base_url="{base_url}"  # 改这里切换平台
)

# 基础调用
response = client.chat.completions.create(
    model="{model}",
    messages=[
        {{"role": "system", "content": "你是一个助手"}},
        {{"role": "user", "content": "你好"}}
    ],
    temperature=0.7,
    max_tokens=1000
)

print(response.choices[0].message.content)
'''


# ─── 各平台配置 ───

PLATFORMS = {
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "env_key": "OPENAI_API_KEY",
        "note": "最强大，但价格最高"
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "note": "性价比最高，完全兼容 OpenAI SDK"
    },
    "通义千问": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-turbo",
        "env_key": "DASHSCOPE_API_KEY",
        "note": "阿里云出品，中文优化好"
    },
    "文心一言": {
        "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",
        "model": "ernie-3.5-8k",
        "env_key": "QIANFAN_API_KEY",
        "note": "百度出品，需要注意 API 格式差异"
    }
}


def print_platform_configs():
    """打印各平台配置"""
    print(API_COMPARISON)
    
    for name, config in PLATFORMS.items():
        print(f"\n{'─' * 50}")
        print(f"📌 {name}")
        print(f"  base_url:  {config['base_url']}")
        print(f"  model:     {config['model']}")
        print(f"  env_key:   {config['env_key']}")
        print(f"  特点:      {config['note']}")
        
        # 生成代码模板
        code = CODE_TEMPLATE.format(
            base_url=config["base_url"],
            model=config["model"]
        )
        print(f"\n  代码示例:")
        for line in code.strip().split('\n'):
            print(f"    {line}")


# ─── 参数速查 ───

def print_params_cheatsheet():
    """参数速查表"""
    print("\n" + "=" * 60)
    print("📊 参数速查表")
    print("=" * 60)
    
    params = [
        ("temperature", "0-2", "0.7", "随机性。0=确定性输出，1=创造性，2=最随机"),
        ("max_tokens", "1-∞", "1000", "最大输出 token 数。注意成本控制"),
        ("top_p", "0-1", "1.0", "核采样。0.1=只看前10%概率的token"),
        ("frequency_penalty", "0-2", "0", "惩罚已出现的词，防止重复"),
        ("presence_penalty", "0-2", "0", "惩罚新话题，鼓励深入讨论"),
        ("stop", "list", "None", "停止序列。遇到则停止生成"),
        ("stream", "bool", "False", "流式输出。True=逐token返回"),
    ]
    
    print(f"\n  {'参数名':<20} {'范围':<10} {'默认':<8} {'说明'}")
    print(f"  {'─'*20} {'─'*10} {'─'*8} {'─'*30}")
    for name, range_, default, desc in params:
        print(f"  {name:<20} {range_:<10} {default:<8} {desc}")


# ─── 快速选择指南 ───

def print_selection_guide():
    """场景选择指南"""
    print("\n" + "=" * 60)
    print("🎯 场景选择指南")
    print("=" * 60)
    
    scenarios = [
        ("学习/练手", "DeepSeek", "便宜，兼容 OpenAI SDK"),
        ("生产环境", "OpenAI GPT-4o", "最稳定，生态最完善"),
        ("中文场景", "通义千问/DeepSeek", "中文优化好"),
        ("代码生成", "DeepSeek Coder/GPT-4o", "代码能力强"),
        ("批量处理", "DeepSeek", "成本低，速度快"),
        ("高精度任务", "GPT-4o", "推理能力最强"),
    ]
    
    print(f"\n  {'场景':<15} {'推荐平台':<20} {'原因'}")
    print(f"  {'─'*15} {'─'*20} {'─'*25}")
    for scene, platform, reason in scenarios:
        print(f"  {scene:<15} {platform:<20} {reason}")


if __name__ == "__main__":
    print("Day 119 - API 速查与对比\n")
    
    print_platform_configs()
    print_params_cheatsheet()
    print_selection_guide()
    
    print("\n" + "=" * 60)
    print("💡 快速开始：")
    print("   pip install openai")
    print("   export DEEPSEEK_API_KEY='your-key'")
    print("   python3 05-api-cheatsheet.py")
    print("=" * 60)
