# Day 130 - Playwright 现代爬虫 完成清单与练习

## ✅ 完成清单

- [ ] 说得出 Playwright 相比 Selenium 的 5 个优势
- [ ] 会安装：pip install playwright + playwright install chromium
- [ ] 会 sync_api 的 launch / new_context / new_page 基本流程
- [ ] 理解自动等待的 actionability 检查（可见/稳定/未遮挡/启用）
- [ ] 会用 Locator 多种定位（CSS / text= / get_by_role / get_by_text）
- [ ] 知道 Locator 惰性查找与 WebElement 快照的区别
- [ ] 会用 wait_for_selector / wait_for_url / wait_for_function
- [ ] 理解 BrowserContext 隔离与并发意义
- [ ] 会用 page.route 拦截/abort/mock 请求
- [ ] 会用 evaluate 取 JS 变量 / 批量提取 DOM 数据
- [ ] 会整页截图与 tracing 录制

## 📝 练习题

### 练习 1（基础）
用 Playwright 无头模式打开 quotes.toscrape.com/js/，打印第一条名言的文本和作者（不许用 time.sleep）。

### 练习 2（进阶）
分别用 `page.locator("text=...")`、`page.get_by_text()`、`page.get_by_role()` 三种方式定位"Next"按钮并点击翻页，比较三种写法的可读性。

### 练习 3（避坑）
解释：为什么 `wait_for_load_state("networkidle")` 在某些页面会超时？应该改用什么等待方式？

### 练习 4（综合）
写一个 Playwright 爬虫抓取 quotes.toscrape.com/js/ 全站：
1. 反检测参数 + 真实 UA + 固定视口；
2. 用 `page.evaluate` 一次性提取整页数据（别逐元素循环）；
3. 翻页直到 next 消失；
4. 保存 JSON 并按作者统计 TOP5。

### 练习 5（思考）
用 `page.route()` 实现"把页面所有图片请求 abort 掉"的爬虫（提速省流量）。思考：这对爬数据有影响吗？什么情况下有？

## 🔧 调试工具速记

```bash
playwright codegen quotes.toscrape.com      # 录制操作自动生成代码
playwright show-trace trace.zip             # 回放失败现场
# 代码里 page.pause() 可打开 Inspector 单步调试
```
