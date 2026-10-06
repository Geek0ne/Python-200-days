# Day 176 — ELK 日志系统 · 练习与检查表

## 概念理解

- [ ] 能用自己的话解释 ELK 三件套各是什么、分别解决什么问题
- [ ] 能画出 ELK 整体架构图（至少包含 Filebeat → Logstash → ES → Kibana）
- [ ] 解释什么是倒排索引，为什么比正排索引快
- [ ] 解释 grok 模式是什么，举一个 COMBINEDAPACHELOG 的例子

## 原理深入

- [ ] Elasticsearch 一次写入的完整链路（从客户端 PUT 到返回 201）
- [ ] Elasticsearch 一次查询的完整链路（query → fetch → merge → 返回）
- [ ] 主分片和副本分片的区别，生产环境为什么至少 3 个节点
- [ ] Logstash pipeline 的内存模型：buffer、batch、workers 的关系
- [ ] 什么是 near real time？为什么默认 1 秒后才能查到刚写入的日志
- [ ] Filebeat 的 sincedb 是什么作用，关掉会怎样

## 实战操作

- [ ] 用 docker-compose 部署单节点 ELK，访问 Kibana 看到绿色健康状态
- [ ] 用 02-log-collection.py 生成 100 条测试日志并写入 ES
- [ ] 用 03-log-analysis-query.py 查状态码分布
- [ ] 用 03-log-analysis-query.py 查最近 1 小时的 5xx 错误
- [ ] 用 Kibana Discover 查一条日志，验证字段解析正确
- [ ] 用 Kibana Visualize 画一个状态码分布的柱状图
- [ ] 用 Kibana Dashboard 把图表拼成一个看板

## 代码实践

- [ ] 修改 02-log-collection.py，增加按 status 过滤输出功能
- [ ] 修改 03-log-analysis-query.py，增加按时间范围查询的功能
- [ ] 写一个脚本：自动清理 7 天前的索引（DELETE /logs-2026.09.*）
- [ ] 写一个脚本：导出今日所有 5xx 错误为 CSV 文件

## 思考题

1. 为什么 Elasticsearch 默认 1 秒后才能查到刚写入的日志？
2. 主分片和副本分片有什么区别？生产环境为什么建议至少 3 个节点？
3. Logstash 的 grok 模式匹配失败会怎样？怎么调试？
4. filter 和 must 有什么区别？什么时候用哪个更快？
5. Filebeat 和 Logstash 应该装在哪里？什么场景需要两层？
6. 索引模板的作用是什么？为什么不建议每次写入前手动建索引？
7. Kibana 的 size: 0 是什么意思？它返回什么？

## 自检

- [ ] 今天的内容全部阅读完
- [ ] 所有代码都能跑通（或至少看懂）
- [ ] 思考题能回答出 5 个以上
- [ ] 明天开始前的准备工作已就绪
