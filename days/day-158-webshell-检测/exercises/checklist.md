# Day 158 — 练习与验收（实战版）

> 全部练习在**授权环境**（自己的服务器/靶场/离线副本）进行。
> 只用占位载荷，不制作可部署的后门，不做规避检测的对抗研究。

## 已验证的教学程序

- [x] 三个示例的 `--self-test` 全部通过
- [x] 规则库 20+ 条，覆盖 PHP/JSP/ASPX/ASP 四类语言
- [x] 加权评分与分级（clean/low/medium/high/critical）自测通过
- [x] 行为信号按 (host, instance) 关联，跨主机/跨实例不误报
- [x] 时间窗口缺失时拒绝下结论（`--no-window`）
- [x] 只读性：扫描前后文件哈希一致；不联网、不执行、不自动删除

## 读者练习（需自行完成，不能把生成教材当作学会）

- [ ] 用正常业务代码 + 你自己收集的授权样本（靶场）建 20+ 条带标签数据集，
      记录每条规则的误报数，计算 precision/recall
- [ ] 调参：把某条规则权重改成 2，观察分级变化；说明误报与漏报的取舍
- [ ] 给 `docs.txt` 这类"文档误报"设计一个降噪方案（如跳过注释块/纯文本扩展名）
- [ ] 构造"命令执行 + 外部输入"样本，验证静态扫描无法判断数据流可达性，
      说明为什么需要人工复核
- [ ] 用合成事件验证：同主机同实例多信号叠加触发复核；只加一个弱信号不触发
- [ ] 设计时间窗口边界测试：缺失时间戳、跨时区、日志乱序时如何处理
- [ ] 为 `03-webshell-scanner.py` 添加 `--hash` 输出，记录每个文件的 SHA-256
      （证据保全用途），并验证重复扫描结果稳定
- [ ] 写一份"命中即删除"的反例说明：为什么自动化删除危险文件是错误设计

## 验收命令

在仓库根目录执行：

```bash
python3 days/day-158-webshell-检测/code/01-static-scanner.py --self-test
python3 days/day-158-webshell-检测/code/02-behavior-hunter.py --self-test
python3 days/day-158-webshell-检测/code/03-webshell-scanner.py --self-test
python3 days/day-158-webshell-检测/code/03-webshell-scanner.py --rules
```

全部应输出 `SELF-TEST OK`（`--rules` 输出规则表）。

思考题：被悄悄跳过（too_large / not_utf8 / symlink）的文件，比一个误报更危险吗？
`truncated` 或 `walk_errors` 非空时，扫描结果还能当作"无告警"吗？
本扫描器未在真实生产样本集评测，不能替代生产检测产品。
