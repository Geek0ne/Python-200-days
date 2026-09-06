# Day 143 — 完成清单与练习

## ✅ 今日清单

- [ ] 阅读 README.md：代理池原理、无头检测、XHR 拦截
- [ ] 运行 `code/01-proxy-pool.py`，观察评分与淘汰逻辑
- [ ] 安装 Playwright 并运行 `code/02-browser-render.py`（拦截 JSON 响应）
- [ ] 运行 `code/03-fetch-pipeline.py`，检查 raw_data.jsonl
- [ ] 回答 5 道思考题

## 📝 练习题

### 基础

1. 给 `ProxyPool.acquire()` 增加"最少使用优先"策略开关，对比两种策略在 100 次模拟取用下的分布差异。
2. 把 `check_proxy` 的验证目标换成 httpbin 的 `/delay/2`，验证超时控制是否生效。

### 进阶

3. 在 `02-browser-render.py` 中增加请求级代理：让 Playwright 的浏览器流量也走代理池（提示：`browser.launch(proxy={"server": ...})`）。
4. **页面类型分类器**：把 `looks_dynamic` 的启发式升级为基于特征计数的打分函数（框架挂载点数量、内联 script 数量、HTML 长度），输出 0~1 的"动态概率"。
5. **容错设计**：为 `pipeline()` 增加指数退避重试（最多 3 次，每次切换代理），被封 IP 自动从池中移除——写出完整实现。

## 🎯 明日预告

Day 144 — 项目 Part 2：验证码处理 + 数据清洗 + 定时调度 + 告警 + 容器化部署。
