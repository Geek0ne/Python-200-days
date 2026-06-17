# Day 026 — 字符串高级 完成清单

## ✅ 今日完成检查

- [ ] 理解正则表达式元字符体系（`.` `\d` `\w` `\s` 等）
- [ ] 掌握 `re.search`、`re.match`、`re.fullmatch` 的区别
- [ ] 学会使用 `re.findall` 和 `re.finditer` 提取数据
- [ ] 理解分组捕获（基本分组、命名组 `(?P<name>)`、非捕获组 `(?:)`）
- [ ] 掌握贪婪与非贪婪匹配的区别（`*` vs `*?`）
- [ ] 会使用 `re.sub` / `re.subn` 做字符串替换和脱敏
- [ ] 掌握 `re.split` 的高级分割用法
- [ ] 理解预编译 `re.compile` 的性能优势
- [ ] 了解灾难性回溯的原理与规避方法
- [ ] 会使用 `re.VERBOSE` 编写可读的正则
- [ ] 理解 ASCII → Unicode → UTF-8 的编码发展历程
- [ ] 掌握 Python 的 `str` 与 `bytes` 编码/解码模型
- [ ] 会处理常见的编码错误（`encode`/`decode` 参数）
- [ ] 能编写日志解析器从文本中提取结构化数据

---

## 📝 练习题

### 基础题

**1. 邮箱验证器**

写一个函数 `validate_emails(text)`，从一段文本中提取所有合法的邮箱地址。

```python
def validate_emails(text: str) -> list[str]:
    """提取文本中所有合法邮箱地址"""
    # 你的代码
    pass

# 测试
text = "联系: admin@example.com, 或 support@公司.com, 或 invalid@@com"
print(validate_emails(text))
# 预期: ['admin@example.com', 'support@公司.com']
```

**2. 手机号提取与格式化**

写一个函数提取字符串中的手机号，并将号码格式化为 `138 **** 5678` 形式。

```python
def extract_and_format_phones(text: str) -> list[str]:
    """提取手机号并格式化为 138 **** 5678 形式"""
    # 你的代码
    pass

# 测试
text = "张三:13812345678, 李四: 15987654321, 王五: 010-12345678"
# 注意：010-12345678 是座机，不应提取
print(extract_and_format_phones(text))
# 预期: ['138 **** 5678', '159 **** 4321']
```

**3. 编码转换器**

写一个函数 `safe_convert(data, from_enc, to_enc)`，安全地将 bytes 从一种编码转换为另一种。

```python
def safe_convert(data: bytes, from_enc: str, to_enc: str) -> bytes:
    """安全地 bytes 编码转换"""
    # 你的代码
    pass

# 测试 — GBK 转 UTF-8
gbk_bytes = '你好世界'.encode('gbk')
utf8_bytes = safe_convert(gbk_bytes, 'gbk', 'utf-8')
print(f"结果: {utf8_bytes}")
print(f"还原: {utf8_bytes.decode('utf-8')}")
```

### 进阶题

**4. 日志分析工具（完整版）**

基于本日实战中的日志解析器，增加以下功能：

```python
def analyze_logs(log_lines: list[str]) -> dict:
    """
    对日志进行全面分析，返回包含以下信息的字典：
    - status_code_distribution: {code: count}
    - hourly_traffic: {hour: count}  # 按小时统计请求量
    - top_endpoints: [(path, count)]  # 访问最多的路径 TOP 5
    - error_rate: float  # 4xx/5xx 错误率
    - avg_response_size: float
    - unique_ips: int  # 不同 IP 数量
    """
    pass
```

**5. 智能搜索高亮器**

写一个函数，输入文本和搜索关键词（支持正则语法），返回高亮后的文本：

```python
def highlight_search(text: str, keyword: str) -> str:
    """
    在文本中高亮所有匹配关键词的部分。
    返回的文本中用 **匹配内容** 包裹匹配部分。
    示例：
    text = "Python 是一种编程语言，Python 很容易学。"
    keyword = "Python"
    → "**Python** 是一种编程语言，**Python** 很容易学。"
    """
    pass
```

---

## 📚 扩展阅读

- [Python re 官方文档](https://docs.python.org/3/library/re.html)
- [regex101.com — 在线正则测试器](https://regex101.com/)
- [Python Unicode 官方指南](https://docs.python.org/3/howto/unicode.html)
- [Regular-Expressions.info — 灾难性回溯](https://www.regular-expressions.info/catastrophic.html)

---

## 🎯 反思

- 今天学到的内容中，哪个概念最让你感到"原来如此"？
- 你以前是否踩过正则贪婪匹配的坑？
- 对于编码问题，Python 3 的 `str`/`bytes` 分离带来了哪些便利和困扰？
- 日志解析器还有哪些可以扩展的功能点？
