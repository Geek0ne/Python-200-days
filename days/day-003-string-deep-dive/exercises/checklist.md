# Day 003 — 字符串深入：练习与检查清单

> ✅ 完成一项就勾一项，跟踪你的学习进度

---

## 今日完成清单

- [ ] **概念理解**
  - [ ] 理解字符串不可变性的含义
  - [ ] 理解字符串驻留（interning）机制
  - [ ] 理解为什么 `+` 拼接大量字符串效率低
  - [ ] 理解 f-string 的编译时优化机制

- [ ] **切片操作**
  - [ ] 掌握 `str[start:stop:step]` 完整语法
  - [ ] 掌握负数索引的使用
  - [ ] 掌握 `[::-1]` 反转字符串
  - [ ] 理解左闭右开规则的原理

- [ ] **字符串格式化**
  - [ ] 理解三种格式化方式的区别
  - [ ] 掌握 f-string 基础用法
  - [ ] 掌握 f-string 格式控制（对齐、精度、填充）
  - [ ] 了解 `str.format()` 的位置参数和关键字参数

- [ ] **转义字符**
  - [ ] 掌握常用转义序列（`\n`, `\t`, `\\`, `\'`）
  - [ ] 掌握 Unicode 转义（`\u`, `\U`, `\N{}`）
  - [ ] 理解原始字符串的使用场景
  - [ ] 理解三引号多行字符串

- [ ] **内置方法**
  - [ ] 掌握 `.split()` 和 `.join()` 的使用
  - [ ] 掌握 `.strip()` 系列方法
  - [ ] 掌握 `.find()`, `.replace()`, `.count()`
  - [ ] 了解判断方法（`.isalpha()`, `.isdigit()` 等）

- [ ] **实战项目**
  - [ ] 运行 `01-string-fundamentals.py` 理解所有概念
  - [ ] 运行 `02-template-engine.py` 理解模板引擎
  - [ ] 完成下面至少 3 道练习题

---

## 练习题

### 练习 1：密码强度检测器

编写一个函数 `check_password_strength(password: str)`，根据以下规则给密码打分：

| 条件 | 加分 |
|------|------|
| 长度 >= 8 | +1 |
| 包含大写字母 | +1 |
| 包含小写字母 | +1 |
| 包含数字 | +1 |
| 包含特殊字符（`!@#$%^&*`） | +1 |

返回分数（0-5）和评价（"弱"/"中等"/"强"）。

**提示**：用 `any()` + 推导式判断字符类别。

```python
def check_password_strength(password: str) -> tuple:
    score = 0
    # 你的代码
    
    return score, rating
```

### 练习 2：字符串压缩

实现 `compress_string(s: str) -> str`，对连续重复字符进行压缩：

```
"aaabbc"    → "a3b2c1"
"abcd"      → "a1b1c1d1"
"aabbaa"    → "a2b2a2"
```

**条件**：只能遍历字符串一次（O(n) 时间复杂度）。

### 练习 3：URL 解析器

实现 `parse_url(url: str) -> dict`，将 URL 解析为以下格式：

```python
parse_url("https://user:pass@example.com:8080/path/to/page?q=hello&lang=zh#section")
# 返回:
# {
#     "protocol": "https",
#     "username": "user",
#     "password": "pass",
#     "hostname": "example.com",
#     "port": "8080",
#     "path": "/path/to/page",
#     "query": {"q": "hello", "lang": "zh"},
#     "fragment": "section"
# }
```

**要求**：只使用字符串方法（`.split()`, `.partition()`, `.find()` 等），**不能使用** `urllib.parse`。

### 练习 4：驼峰命名转换

实现两个函数：

```python
camel_to_snake("helloWorld")      # "hello_world"
camel_to_snake("XMLParser")       # "xml_parser"（注意连续大写）

snake_to_camel("hello_world")     # "helloWorld"
snake_to_camel("xml_parser")      # "xmlParser"
```

**提示**：用正则或遍历字符串构建。

### 练习 5：文本对齐工具

实现 `justify(text: str, width: int) -> str`：

- 将文本按指定宽度两端对齐
- 单词间均匀插入空格
- 最后一行左对齐
- 如果某单词长度超过宽度，直接原样输出

```python
justify("The quick brown fox jumps over the lazy dog.", 16)
# 输出:
# "The  quick brown"
# "fox  jumps  over"
# "the   lazy dog."
```

---

## 参考答案提示

> 先自己尝试，实在卡住了再参考提示

<details>
<summary>练习 1 提示</summary>

```python
def check_password_strength(password: str) -> tuple:
    score = 0
    if len(password) >= 8: score += 1
    if any(c.isupper() for c in password): score += 1
    if any(c.islower() for c in password): score += 1
    if any(c.isdigit() for c in password): score += 1
    if any(c in "!@#$%^&*" for c in password): score += 1
    
    ratings = {0: "极弱", 1: "弱", 2: "弱", 3: "中等", 4: "强", 5: "极强"}
    return score, ratings[score]
```
</details>

<details>
<summary>练习 2 提示</summary>

遍历字符串，记录当前字符和计数。当前后字符不同时，输出 `字符+计数` 并重置。
</details>
