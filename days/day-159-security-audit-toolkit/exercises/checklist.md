# Day 159 — 完成清单与练习题（安全审计工具）

> 全部操作在**授权环境**进行：只审计你自己拥有或已获书面授权的目录。
> 工具箱是只读的：不修改文件、不发网络请求、不尝试利用任何"疑似漏洞"。

## 一、完成清单（先跑通，再做题）

- [ ] `python3 code/01-scanner-core.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 code/02-report-builder.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 code/03-audit-toolkit.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 code/03-audit-toolkit.py rules` → 打印 13 条规则
- [ ] `python3 code/03-audit-toolkit.py lab` → 生成演示报告，退出码 3
- [ ] `python3 code/03-audit-toolkit.py lab --format json > /tmp/r.json` 后能读懂 summary/coverage 两段
- [ ] `python3 code/03-audit-toolkit.py report /tmp/r.json` → 由 JSON 重新渲染 Markdown
- [ ] 能口述：严重度（impact）与置信度（certainty）为什么要分开
- [ ] 能口述：`Coverage.complete == False` 时为什么不能说"未发现问题"
- [ ] 能口述：baseline 抑制项为什么必须单独计数并在报告中列出

## 二、基础练习

1. **加一条规则**：在 `audit_core.local_rules()` 中新增规则
   `docker_socket_mount`，匹配 `docker.sock`（severity=high，confidence=medium），
   写出它的 `why` 与 `remediation`，并在 `01-scanner-core.py` 的样本里加一个命中文件。
   要求：`--self-test` 仍然通过，且新规则的 triage 分档符合矩阵。

2. **读懂 triage 分档**：列出 15 种组合里哪些落到 P0、哪些落到 P3，
   并解释为什么 `critical + low` 与 `high + high` 同为 P0。

3. **覆盖缺口实验**：在临时目录里造 4 个文件，分别触发
   `too_large` / `binary` / `not_utf8` / `symlink` 四类跳过，
   运行 `scan_path` 后打印 `coverage.gaps`，确认 4 类都出现。

4. **门禁语义**：用 `--fail-on critical` 和 `--fail-on low` 各跑一次 `lab`，
   比较退出码差异，并说明 `--fail-on low` 在真实 CI 中会带来什么后果。

## 三、进阶挑战

5. **报告 diff**：把 `lab` 生成的 JSON 存两份（修改前后各一份），
   写 30 行脚本比较两次扫描：新增命中 / 已消失命中 / 抑制项变化，
   输出一段 Markdown diff。**为什么要做这个**：审计的价值一半在"变化"，
   只看单次快照无法回答"我们是在变好还是变坏"。

6. **误报治理**：`docs/notes.md` 里的 `password = "example-value"` 会持续命中。
   设计一个降噪方案（延伸名白名单 / 注释块识别 / baseline），
   并说明该方案会不会把**真实的**凭据藏在文档里也一起放过——如何缓解。

7. **baseline 腐化测试**：把 baseline 里的一条抑制项对应的代码删掉，
   观察报告输出：抑制项计数与"仍然存在的抑制"是否还准确？
   如果不准确，说明你的 baseline 维护机制缺了什么。

8. **权限边界**：给工具箱加一个 `--deny-dirs` 参数（默认包含 `/proc`、`/sys`、`/dev`），
   写测试证明即使目标目录里存在这些软链接，也不会越界读取。

9. **供应链规则的真实数据**：为 `unpinned_dependency` 构造一个 20 行的
   `requirements.txt`（含 `==` / `>=` / 无版本 / 注释 / 空行 / 环境标记），
   统计命中与漏报，说明为什么正则匹配依赖清单必然存在漏报。

## 四、验收命令

```bash
cd ~/code/Learn-Python
python3 days/day-159-security-audit-toolkit/code/01-scanner-core.py --self-test
python3 days/day-159-security-audit-toolkit/code/02-report-builder.py --self-test
python3 days/day-159-security-audit-toolkit/code/03-audit-toolkit.py --self-test
python3 days/day-159-security-audit-toolkit/code/03-audit-toolkit.py rules
python3 days/day-159-security-audit-toolkit/code/03-audit-toolkit.py lab
```

前三条必须输出 `SELF-TEST OK`；`lab` 的退出码应为 3（命中达到 high 阈值）。

## 五、思考题（写在笔记里）

- 命中项里 `docs/notes.md` 的误报和真实私钥命中，**在报告里看起来同样"严重"**。
  这对"用命中数考核团队"的做法意味着什么？
- 如果审计工具允许写操作（自动修 chmod、自动删密钥），
  什么样的故障会从"漏报"升级成"生产事故"？
- 本次 13 条规则全部是"模式匹配"。哪一类真实风险它**结构上**看不见？
  （提示：数据流、运行时行为、权限关系、依赖的实际版本内容）
- 工具箱能帮你完成"发现问题"。**处置**（限流、轮换、下线）需要哪些
  你在本次代码里刻意**没有**实现的权限？为什么刻意不做？
