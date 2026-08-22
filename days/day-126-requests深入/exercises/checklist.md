# Day 126 — Requests 深入：练习与检查表

## ✅ 完成清单

- [ ] 理解 Session 的原理和优势
- [ ] 掌握 Cookie 的自动/手动管理
- [ ] 能实现请求头伪装（UA、Referer）
- [ ] 掌握超时控制和重试机制
- [ ] 理解连接池的工作原理
- [ ] 完成至少 3 道练习题

---

## 📝 基础练习

### 练习 1：Session 对比测试

编写代码对比 Session 和独立请求的性能差异：

```python
import requests
import time

# 串行请求 10 次同一域名
# 使用 Session 串行请求 10 次
# 对比两者的总耗时
# 提示：连接复用会显著减少耗时
```

### 练习 2：Cookie 管理器

实现一个 Cookie 管理器类：

```python
class CookieManager:
    def __init__(self, cookie_file="cookies.json"):
        self.cookie_file = cookie_file
        self.cookies = {}

    def load(self):
        """从文件加载 cookies"""
        pass

    def save(self):
        """保存 cookies 到文件"""
        pass

    def get(self, domain, name):
        """获取指定域名的 cookie"""
        pass

    def set(self, domain, name, value):
        """设置 cookie"""
        pass

    def clear(self, domain=None):
        """清除 cookies"""
        pass
```

### 练习 3：请求头轮换

实现一个请求头轮换器，每次请求随机选择一组请求头：

```python
class HeaderRotator:
    def __init__(self):
        self.header_sets = [
            {"User-Agent": "Chrome/120...", "Accept-Language": "zh-CN"},
            {"User-Agent": "Firefox/121...", "Accept-Language": "en-US"},
            # ... 更多组合
        ]

    def get_headers(self):
        """随机返回一组请求头"""
        pass
```

---

## 🚀 进阶挑战

### 挑战 1：完整的爬虫框架

实现一个功能完整的爬虫框架：
- 自动管理 Cookie 和会话
- 请求头随机轮换
- 自动重试和退避
- 并发请求控制
- 请求日志记录
- 反爬虫检测与应对

### 挑战 2：代理 IP 池管理

实现代理 IP 池管理：
- 代理 IP 的获取和验证
- 失败自动切换代理
- 代理响应时间排序
- 代理 IP 的定时刷新

### 挑战 3：模拟登录实战

选择一个网站（如知乎、GitHub），实现：
- 获取登录页面的 CSRF Token
- 提交登录表单
- 处理验证码（简单滑块或图形验证码）
- 保持登录状态访问受保护页面

---

## 💡 思考题

1. **Session 的线程安全性**：requests.Session 是线程安全的吗？在多线程环境下应该如何使用？

2. **Cookie 与 Token**：现代 Web 应用越来越多地使用 JWT Token 而不是 Cookie，这两种方式有什么区别？

3. **反爬虫检测**：除了 User-Agent，网站还可以通过哪些特征识别爬虫？如何应对？

4. **HTTP/2 支持**：requests 库默认使用 HTTP/1.1，如何启用 HTTP/2？有什么好处？

5. **请求频率控制**：如何设计一个智能的请求频率控制器，既能快速获取数据又不被封禁？
