"""
Day 086 - 聊天机器人意图识别实战
使用 spaCy 构建一个简单的意图识别系统
运行前需安装: pip install spacy && python -m spacy download en_core_web_sm
"""
import spacy
from typing import Dict, List, Optional

# ========================================
# 意图识别器
# ========================================
class IntentRecognizer:
    """
    基于规则 + NLP 的意图识别器
    
    工作流程:
    1. 使用 spaCy 对文本进行分词和 NER
    2. 基于关键词匹配确定意图
    3. 使用 NER 提取关键实体
    """
    
    def __init__(self, model: str = "en_core_web_sm"):
        """初始化识别器，加载 spaCy 模型"""
        try:
            self.nlp = spacy.load(model)
        except OSError:
            print(f"❌ 模型 {model} 未安装，请运行:")
            print(f"   python -m spacy download {model}")
            raise
        
        # 意图定义：意图名 → 关键词列表
        self.intent_keywords = {
            "greeting": ["hello", "hi", "hey", "good morning", "good afternoon", 
                        "good evening", "greetings", "howdy"],
            "farewell": ["bye", "goodbye", "see you", "take care", "farewell"],
            "weather": ["weather", "temperature", "rain", "sunny", "cloudy", 
                       "forecast", "cold", "hot", "warm"],
            "time": ["time", "clock", "hour", "minute", "what time"],
            "search": ["search", "find", "look for", "google", "query"],
            "help": ["help", "assist", "support", "what can you do"],
        }
        
        # 实体类型映射：用于提取关键信息
        self.entity_types = {
            "GPE": "location",      # 地理政治实体（国家、城市）
            "LOC": "location",      # 地理位置
            "ORG": "organization",  # 组织机构
            "PERSON": "person",     # 人名
            "DATE": "date",         # 日期
            "TIME": "time",         # 时间
            "MONEY": "amount",      # 金额
        }
    
    def _extract_intent(self, tokens: set) -> str:
        """基于关键词匹配提取意图"""
        for intent, keywords in self.intent_keywords.items():
            # 检查 tokens 中是否包含任何关键词
            if tokens & set(keywords):
                return intent
        return "unknown"
    
    def _extract_entities(self, doc) -> Dict[str, str]:
        """提取并归类命名实体"""
        entities = {}
        for ent in doc.ents:
            label = self.entity_types.get(ent.label_, ent.label_.lower())
            if label not in entities:
                entities[label] = ent.text
            else:
                # 多个同类实体用逗号分隔
                entities[label] += f", {ent.text}"
        return entities
    
    def recognize(self, text: str) -> Dict:
        """
        识别用户输入的意图和实体
        
        Args:
            text: 用户输入的文本
            
        Returns:
            包含 intent、entities、tokens 的字典
        """
        # 使用 spaCy 处理文本
        doc = self.nlp(text.lower())
        
        # 提取 token 集合
        tokens = set(token.text for token in doc if not token.is_punct)
        
        # 识别意图
        intent = self._extract_intent(tokens)
        
        # 提取实体
        entities = self._extract_entities(doc)
        
        return {
            "intent": intent,
            "entities": entities,
            "tokens": list(tokens),
            "original_text": text,
        }
    
    def batch_recognize(self, texts: List[str]) -> List[Dict]:
        """批量识别多个文本"""
        return [self.recognize(text) for text in texts]


# ========================================
# 响应生成器
# ========================================
class ResponseGenerator:
    """根据意图生成响应"""
    
    def __init__(self):
        self.responses = {
            "greeting": "你好！有什么我可以帮助你的吗？ 😊",
            "farewell": "再见！祝你有美好的一天！ 👋",
            "weather": "让我帮你查询天气信息...",
            "time": "现在是 {time}。⏰",
            "search": "正在为你搜索相关信息...",
            "help": "我可以帮你查询天气、时间、搜索信息等。请告诉我你需要什么！",
            "unknown": "抱歉，我没有理解你的意思。你能再说一次吗？ 🤔",
        }
    
    def generate(self, intent: str, entities: Dict) -> str:
        """根据意图和实体生成响应"""
        response = self.responses.get(intent, self.responses["unknown"])
        
        # 替换响应中的占位符
        if "{time}" in response and "time" in entities:
            response = response.replace("{time}", entities["time"])
        
        return response


# ========================================
# 聊天机器人
# ========================================
class ChatBot:
    """简单的聊天机器人"""
    
    def __init__(self):
        self.recognizer = IntentRecognizer()
        self.responder = ResponseGenerator()
        self.history = []  # 对话历史
    
    def chat(self, user_input: str) -> str:
        """处理用户输入并返回响应"""
        # 识别意图
        result = self.recognizer.recognize(user_input)
        
        # 生成响应
        response = self.responder.generate(result["intent"], result["entities"])
        
        # 记录对话历史
        self.history.append({
            "user": user_input,
            "bot": response,
            "intent": result["intent"],
            "entities": result["entities"],
        })
        
        return response
    
    def print_history(self):
        """打印对话历史"""
        print("\n📝 对话历史:")
        print("-" * 50)
        for i, entry in enumerate(self.history, 1):
            print(f"[{i}] User: {entry['user']}")
            print(f"    Bot:  {entry['bot']}")
            print(f"    Intent: {entry['intent']}, Entities: {entry['entities']}")
            print()


# ========================================
# 主程序
# ========================================
def main():
    print("=" * 60)
    print("🤖 聊天机器人意图识别演示")
    print("=" * 60)
    
    # 创建聊天机器人
    bot = ChatBot()
    
    # 测试用例
    test_inputs = [
        "Hello!",
        "What's the weather in Beijing?",
        "What time is it now?",
        "Search for Python tutorials",
        "Goodbye!",
        "Can you help me with something?",
        "今天天气怎么样",  # 中文（会被处理为未知意图）
    ]
    
    print("\n📋 测试用例:")
    print("-" * 60)
    
    for text in test_inputs:
        response = bot.chat(text)
        
        # 获取识别结果
        result = bot.recognizer.recognize(text)
        
        print(f"\n👤 User: {text}")
        print(f"🤖 Bot:  {response}")
        print(f"   📊 Intent: {result['intent']}")
        if result['entities']:
            print(f"   🏷️  Entities: {result['entities']}")
    
    # 打印对话历史
    bot.print_history()
    
    # ========================================
    # 交互模式
    # ========================================
    print("=" * 60)
    print("💡 交互模式 (输入 'quit' 退出)")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 再见！")
                break
            
            if not user_input:
                continue
            
            response = bot.chat(user_input)
            print(f"🤖 Bot: {response}")
            
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break


if __name__ == "__main__":
    main()
