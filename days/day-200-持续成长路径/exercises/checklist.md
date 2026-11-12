# Day 200 练习题清单

> 所有命令都在仓库根目录执行。四个脚本全部支持 `--self-test`，离线、无外部服务、无第三方依赖。
> **Windows 用户注意**：默认控制台是 GBK，直接跑仓库里旧课的脚本可能报 `UnicodeEncodeError`，
> 与代码对错无关，加 `python -X utf8` 重跑即可。本课四个脚本已内置 UTF-8 兜底。
> 下文用 `python`；Linux/macOS 读者换成 `python3` 即可。

---

## 一、今日完成清单

- [ ] 读完 README 概念与原理两节，能说出「证据阶梯」四级分别对应什么文件痕迹
- [ ] 能解释为什么校准差要双向读，高估和低估的修法为什么不同
- [ ] 能解释为什么「输入」阶段在 git 里不可观测，以及为什么不能把它算成 0
- [ ] 能解释一次批量提交如何把「从未回访」从 152 门刷成 0 门
- [ ] 跑通四个脚本的 `--self-test`（应当全部 PASS，合计 93 条断言）
- [ ] 用 01 给自己打一次分，算出至少一个高估维度和一个低估维度
- [ ] 用 02 体检自己的仓库，找出被饿死的那一环
- [ ] 用 03 列出自己的 Hold 环，并说明替代方案覆盖到什么程度
- [ ] 用 04 生成毕业总结与 90 天路线图，检查每个里程碑都有放弃条件
- [ ] 清理实验现场（临时目录），确认没有改动仓库里其他课的文件

---

## 二、基础练习

### 练习 1：给自己打一次会被反驳的分

**目标**：体验「自评挂在证据上」和「凭感觉自评」的差别

```bash
cd days/day-200-持续成长路径
python code/01-skill-audit.py                                  # 先看证据分
cp code/self-rating.example.json /tmp/my-rating.json           # 换成你自己的分数
python code/01-skill-audit.py --ratings /tmp/my-rating.json
```

**要求**：

1. 先不看证据分，凭感觉给 8 个维度打分，写进 `/tmp/my-rating.json`
2. 再跑一次，记下每个维度的校准差
3. 挑出校准差最大的那个维度，回答：是我记错了，还是证据口径漏了什么？

**验收**：能说出「这个维度我高估了，因为我以为学过就等于会，但仓库里它只有 L2 痕迹」这类具体判断，
而不是「差不多挺准的」。

### 练习 2：用星级制再打一次

**目标**：理解口径换算，以及为什么工具要显式声明 scale

```bash
python code/01-skill-audit.py --ratings /tmp/my-rating.json --scale 5
```

**要求**：

1. 把分数改成 1–5 的星级
2. 对比两次输出的证据分是否一致（应当一致，变的只有自评列）
3. 故意写一个 `"不存在的维度": 4`，观察工具是报错还是静默忽略

**思考**：为什么静默忽略未知维度比报错更危险？

### 练习 3：找出你自己仓库里被饿死的一环

**目标**：把「我很努力」换成可反驳的配比

```bash
python code/02-learning-loop.py --top 10
```

**要求**：

1. 记下实践/输出/反馈三环的占比
2. 对照阈值（20% / 15% / 5%）判断哪一环被饿死
3. 看「剔除批量后」的从未回访课数，和「全部口径」差多少

**验收**：能解释为什么两个口径差这么多，以及差值说明了什么。

---

## 三、进阶挑战

### 练习 4：给证据阶梯加一级 L5

**目标**：理解「加一个等级」会如何改变整个排名

现状：L4 是「交付过」。但交付和被复用是两件事——Day 198 讲的开源贡献才是 L5。

**要求**：

1. 在 `LEVELS` 里加 `5: ("被复用过", 5)`，并把 `MAX_WEIGHT` 改成自动取最大值（已经是了，确认一下）
2. 给 L5 设计一个**可静态检测**的信号（提示：git 历史里该课目录被其他课的脚本引用过？
   或者 README 里出现外部仓库链接？先想清楚再动手）
3. 在 `self_test()` 里加夹具和断言
4. 跑 `--self-test` 必须 PASS，再跑真实仓库，对比 8 个维度的排名变化

**思考**：如果 L5 的信号设计得很难命中，会发生什么？（提示：所有维度分数一起被稀释，排名却不变——
这说明加等级不一定增加信息量。）

### 练习 5：证明「语法通过 ≠ 能跑」

**目标**：亲手复现本课最重要的那个缺陷

```bash
# CI 只做语法编译，这一步会全绿
python -W error::SyntaxWarning -m compileall -q days/day-018-推导式/code

# 但实跑立刻崩
python days/day-018-推导式/code/01-comprehension-basics.py
```

**要求**：

1. 确认第一条命令退出码 0，第二条抛 `ModuleNotFoundError: No module named 'tools'`
2. 数一数 day-018 下有多少个文件受影响（含 `exercises/solutions.py`）
3. 写一个 20 行的冒烟脚本：遍历 `days/*/code/*.py`，逐个 `python <file>`，
   收集失败清单，超时 10 秒就跳过（有的脚本会起服务）
4. 用你的冒烟脚本扫全仓库，看看还有多少课是「语法绿、运行红」

**验收**：交一份失败清单，每行含课号、文件名、异常类型。
**注意**：不要顺手去修别的课——那是里程碑 1 的任务，今天只负责把它测出来。

### 练习 6：把毕业总结写成可发表文章

**目标**：完整走一遍 Day 196→200 的闭环

**步骤**：

1. 跑完整流水线，生成 `graduation.md` 与 `roadmap-90d.md`
2. 用 Day 199 的体检器检查毕业总结：
   `python -X utf8 ../day-199-技术写作/code/01-article-lint.py /tmp/day200/毕业交付/graduation.md`
3. 修掉所有 error 与 warning（提示：表格多、代码块少，W108 可能会响）
4. 给路线图里每个里程碑补一句「我为什么选它而不是别的」——生成器给的是缺口，理由要你自己写

**检查点（自评）**：

- [ ] 每个数字都能指回一条命令
- [ ] 「这份总结不能证明什么」那一节没有被删掉
- [ ] 三个里程碑都有放弃条件，且条件是可判定的（不是「如果感觉不对」）
- [ ] 一个不在场的人能照着验收你的交付物

---

## 四、验收命令（一条条跑，全部应通过）

```bash
cd days/day-200-持续成长路径

# 1) 四个脚本离线自证（20 + 29 + 24 + 20 = 93 条断言）
python code/01-skill-audit.py --self-test
python code/02-learning-loop.py --self-test
python code/03-tech-radar.py --self-test
python code/04-growth-roadmap.py --self-test

# 2) 真实仓库流水线
mkdir -p /tmp/day200
python code/01-skill-audit.py --ratings code/self-rating.example.json --json /tmp/day200/audit.json
python code/02-learning-loop.py --json /tmp/day200/loop.json
python code/03-tech-radar.py --json /tmp/day200/radar.json
python code/04-growth-roadmap.py --out /tmp/day200/毕业交付 \
    --audit /tmp/day200/audit.json --loop /tmp/day200/loop.json --radar /tmp/day200/radar.json

# 3) 产物应当齐全，且四件套完整度是 200/200
ls /tmp/day200/毕业交付
# 期望：graduation.md  roadmap-90d.md  summary.json

# 4) 语法编译（与 CI 同口径）
python -W error::SyntaxWarning -m compileall -q code

# 5) 清理
rm -rf /tmp/day200
```

**预期**：四个 `SELF-TEST PASS`；04 输出「四件套完整 200/200」；
`graduation.md` 里的 mermaid 图数与 04 控制台打印的一致；`compileall` 退出码 0。

**Windows 清理**：`rm -rf /tmp/day200` 在 Git Bash 下可用；
PowerShell 用 `Remove-Item -Recurse -Force $env:TEMP\day200`。

---

## 五、自测失败时的排查顺序

1. **先怀疑夹具和口径**：本课开发时真的发生过——把含边界的 75 分当成低分、
   把字符串「无（标准库没有…）」当成有替代（见 README 翻车记录）
2. **再看口径**：是不是把「批量提交」和「针对性修正」混在一起算了
3. **再看编码**：Windows 下 `UnicodeEncodeError` 不是逻辑错，是控制台编码，加 `-X utf8` 即可
4. **最后看边界**：空仓库、浅克隆（`git fetch --unshallow`）、缺 JSON 输入、单课维度

---

## 六、毕业之后

这份清单的最后一项不是练习，是一个决定：

> 从明天起，没有人给你出题了。
> 你打算用什么代替「目录里的 Day N」？

如果答案是「再看看有什么新课」，那 Day 200 就白学了。
正确答案应当长这样：**每周跑一次 02，每月跑一次 01，让缺口告诉你下一课是什么。**