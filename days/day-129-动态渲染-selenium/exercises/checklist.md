# Day 129 - 动态渲染（Selenium） 完成清单与练习

## ✅ 完成清单

- [ ] 能说清动态渲染页面和静态页面的区别（数据从哪来）
- [ ] 理解 Python / ChromeDriver / Chrome 三者的通信关系
- [ ] 会用 8 种 find_element 定位方式，知道优先级
- [ ] 掌握显式等待 WebDriverWait + expected_conditions
- [ ] 理解隐式/显式等待不能混用的原因
- [ ] 会配置无头模式并避开窗口大小坑
- [ ] 会处理 iframe（switch_to.frame / default_content）
- [ ] 会用 execute_script 滚动页面触发懒加载
- [ ] 会用 staleness_of 处理翻页后的元素失效
- [ ] 知道 quit() 和 close() 的区别

## 📝 练习题

### 练习 1（基础）
用无头 Selenium 打开 `http://quotes.toscrape.com/js/`，等第一条名言出现后，打印页面标题和前 5 条名言的作者。

### 练习 2（进阶）
分别用 ID、CLASS_NAME、CSS_SELECTOR、XPath 四种方式定位页面上同一个元素（比如第一条名言的文本），体会不同定位器的写法差异。

### 练习 3（避坑）
解释这段代码可能出现的两种失败场景，并改成显式等待：

```python
driver.get(url)
time.sleep(3)
driver.find_element(By.ID, "search").send_keys("python")
```

### 练习 4（综合）
写一个爬虫：抓取 quotes.toscrape.com/js/ 全站名言，要求：
1. 无头模式 + 反检测参数；
2. 显式等待渲染完成；
3. 翻页时用 staleness_of 防止抓到重复数据；
4. 结果按作者分组统计数量后输出 TOP5。

### 练习 5（思考）
在 F12 Network 的 XHR 面板里观察 quotes.toscrape.com/js/ 页面加载过程：数据是页面自带的还是后续请求拿到的？如果是后者，说明你能不能绕开 Selenium 直接拿数据？
