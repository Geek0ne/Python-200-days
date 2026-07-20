# Day 072 练习题清单

## 练习 1：日志分析 ⭐⭐
编写一个函数，从服务器日志中提取所有 IP 地址和访问时间：
```python
log = '192.168.1.1 - - [15/Jan/2024:10:30:00] "GET /index.html"'
# 预期输出: ('192.168.1.1', '15/Jan/2024:10:30:00')
```

**要求：**
- 使用正则表达式提取
- 处理 IPv4 地址
- 提取时间戳
- 返回元组格式

## 练习 2：Markdown 链接提取 ⭐⭐
提取 Markdown 中的所有链接（文本 + URL）：
```python
md = "访问 [Python](https://python.org) 和 [GitHub](https://github.com)"
# 预期输出: [('Python', 'https://python.org'), ('GitHub', 'https://github.com')]
```

**要求：**
- 使用非贪婪匹配
- 处理嵌套括号
- 支持带标题的链接 `[text](url "title")`

## 练习 3：CSV 字段解析 ⭐⭐⭐
用正则解析 CSV 行（处理引号内的逗号）：
```python
line = 'name,age,"city, country",email'
# 预期输出: ['name', 'age', 'city, country', 'email']
```

**要求：**
- 处理引号内的逗号
- 处理转义引号 `""`
- 支持空字段
- 不能使用 csv 模块

## 练习 4：模板引擎 ⭐⭐⭐
实现一个简单的模板引擎，支持 `{{variable}}` 替换：
```python
template = "Hello {{name}}, you have {{count}} messages"
result = render(template, {"name": "Alice", "count": 5})
# 预期输出: "Hello Alice, you have 5 messages"
```

**要求：**
- 支持嵌套变量 `{{user.name}}`
- 支持默认值 `{{name|default}}`
- 处理未定义的变量
- 支持循环 `{{#items}}...{{/items}}`

## 练习 5：正则性能测试 ⭐⭐⭐⭐
编写一个脚本，测试不同正则写法的性能差异：
- 对比贪婪 vs 非贪婪的性能
- 测试不同字符类（`\d` vs `[0-9]`）的速度
- 验证灾难性回溯的存在
- 生成性能对比报告

**要求：**
- 使用 time 模块测量时间
- 多次运行取平均值
- 生成表格形式的报告
- 分析性能差异的原因

## 提交要求
- 所有练习的代码文件放在 exercises/ 目录
- 每个文件可以独立运行
- 添加必要的注释和文档字符串
- 包含测试用例和预期输出
