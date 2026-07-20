# Day 077 — 练习清单与题目

## ✅ 今日完成清单

- [ ] 理解 Scrapy 调度器的工作原理（优先级队列、去重机制）
- [ ] 掌握自定义去重过滤器的编写
- [ ] 理解 Pipeline 的执行流程和排序规则
- [ ] 实现完整的数据清洗 → 验证 → 预警 → 存储 Pipeline 链
- [ ] 了解常见陷阱：忘记 return、顺序错误、内存泄漏
- [ ] 运行 3 个代码示例，观察调度器和 Pipeline 的行为

---

## 📝 基础练习题

### 练习 1：自定义去重过滤器
**要求**：编写一个去重过滤器，要求：
- 正常基于 URL 去重
- 但忽略 URL 中的 `utm_source`、`utm_medium`、`utm_campaign` 三个追踪参数
- 测试以下 URL，验证去重效果：
  ```
  https://example.com/page?utm_source=google&page=1
  https://example.com/page?utm_source=facebook&page=1  # 应被过滤
  https://example.com/page?utm_source=google&page=2    # 应通过（不同 page）
  ```

**预期输出**：
```
✅ 通过: https://example.com/page?utm_source=google&page=1
⛔ 过滤: https://example.com/page?utm_source=facebook&page=1
✅ 通过: https://example.com/page?utm_source=google&page=2
```

---

### 练习 2：Pipeline 执行顺序
**要求**：给定三个 Pipeline，编写正确的 `ITEM_PIPELINES` 配置：
- `StorePipeline`：存储到数据库
- `CleanPipeline`：清洗数据（去除空格、标准化价格）
- `NotifyPipeline`：发送通知

**要求输出**：
```
1. 先清洗
2. 再存储
3. 最后通知（因为通知应该发送已清洗的数据）
```

写出 `ITEM_PIPELINES` 的配置代码。

---

### 练习 3：DropItem 练习
**要求**：编写一个 `ValidatePipeline`，丢弃以下不合规数据：
- `price` 为负数
- `name` 长度小于 2
- `url` 不以 `http` 开头

测试数据：
```python
test_items = [
    {'name': 'Good Product', 'price': 99.9, 'url': 'https://example.com/1'},
    {'name': 'X', 'price': 50, 'url': 'https://example.com/2'},      # 丢弃
    {'name': 'Bad Price', 'price': -10, 'url': 'https://example.com/3'},  # 丢弃
    {'name': 'No URL', 'price': 100, 'url': 'ftp://example.com/4'},  # 丢弃
]
```

---

## 🔥 进阶挑战题

### 挑战 1：带限速的调度器
**要求**：在 `SimpleScheduler` 基础上添加限速功能：
- 每秒最多发送 N 个请求（可配置）
- 超出限制时，请求进入等待队列
- 到达时间窗口后自动出队

**提示**：使用 `time.time()` 和滑动窗口算法。

---

### 挑战 2：Pipeline 链中断恢复
**要求**：设计一个支持断点续传的 Pipeline：
- 处理到一半时模拟进程中断
- 记录已处理的 Item ID
- 重启后跳过已处理的 Item

**提示**：用一个简单的 JSON 文件记录已处理 ID。

---

### 挑战 3：并发 Pipeline 性能测试
**要求**：
- 创建 3 个不同的 Pipeline（清洗、验证、存储）
- 分别测试：顺序执行 vs 模拟并发执行的性能差异
- 用 10000 条数据进行测试
- 输出执行时间对比

---

## 📋 参考答案提示

### 练习 1 提示
```python
import hashlib
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

IGNORE_PARAMS = {'utm_source', 'utm_medium', 'utm_campaign'}

def fingerprint(url):
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    for p in IGNORE_PARAMS:
        params.pop(p, None)
    sorted_query = urlencode(sorted(params.items()), doseq=True)
    clean = urlunparse(parsed._replace(query=sorted_query))
    return hashlib.sha1(clean.encode()).hexdigest()
```

### 练习 2 提示
```python
ITEM_PIPELINES = {
    'myproject.pipelines.CleanPipeline': 100,
    'myproject.pipelines.StorePipeline': 200,
    'myproject.pipelines.NotifyPipeline': 300,
}
```

### 练习 3 提示
```python
from scrapy.exceptions import DropItem

def validate(item):
    if item.get('price', 0) < 0:
        raise DropItem("价格为负数")
    if len(item.get('name', '')) < 2:
        raise DropItem("名称过短")
    if not item.get('url', '').startswith('http'):
        raise DropItem("URL 格式无效")
    return item
```
