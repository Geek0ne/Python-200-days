# Day 145 — 完成清单与练习

## ✅ 今日清单

- [ ] 阅读 README.md：复盘方法论(4L/KPT)、Phase 9 知识地图、收尾文档清单
- [ ] 运行 `code/01-phase-retrospective.py`，看自动复盘报告，手工填写 4L 四栏
- [ ] 运行 `code/02-project-audit.py 126-145`，确认全阶段交付物齐全
- [ ] 回答 5 道练习题

## 📝 练习题

### 基础

1. 给 `01-phase-retrospective.py` 增加 `--min-lines` 参数：只显示有效代码行数 ≥ N 的天。
2. 给复盘报告追加"Top 3 代码量最大的天"小节。

### 进阶

3. **复盘报告分类**：把 20 天按"采集侧/对抗侧/合规侧"三类自动归类（维护一个主题→分类映射表），报告按类分组输出。
4. **债务清单**：写一个脚本扫描所有 code/*.py 中的 `TODO`/`FIXME`/`XXX` 注释，输出"技术债务清单"，统计总数。
5. **面试题**：用 3 分钟向一个没学过爬虫的人讲清楚 Day 142–144 三日项目的架构（提示：按"入口→分流→熔断→清洗→存储"顺序讲）。

## 📖 参考答案

<details><summary>点击展开</summary>

**1.** 在 `argparse` 部分加 `ap.add_argument("--min-lines", type=int, default=0)`，构建表格时过滤 `r["py_lines"] >= args.min_lines` 即可。注意过滤要放在 total 统计**之后**还是**之前**想清楚——总数字段一般应统计全部，表格才过滤。

**2.** `top3 = sorted(rows, key=lambda r: r["py_lines"], reverse=True)[:3]`，遍历拼 Markdown 列表追加到 `lines`。

**3.** 定义 `CATEGORY = {"采集": ("requests", "beautifulsoup", "scrapy", "playwright", "selenium", "storage", "app-crawler"), ...}`，对 topic 做子串匹配归组；匹配不到的落"其他"。这类"关键词路由"是配置驱动代码的典型场景。

**4.** 核心是 `rglob("*.py")` + 逐行 `re.search(r"#\s*(TODO|FIXME|XXX)", line)`，记录 (文件, 行号, 内容)。生产工具如 `ruff`、`grep -rn` 就是干这个的，先手写一遍理解原理。

**5.** 参考讲述线：这是一个"合规的增量采集管线"——入口是调度器定时触发；先查 robots 决定能不能抓；静态页走 requests、动态页走 Playwright，代理池轮换出口；一旦遇到验证码就分级熔断（换代理→暂停→告警人工介入）；抓回的脏数据经过去重、校验、归一化清洗后落盘。一句话：**合规地、稳定地、干净地把数据拿回来**。

</details>
