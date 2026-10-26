# Day 197 完成清单与练习

> 所有命令都在本目录（`days/day-197-面试准备/`）下执行。
> 脚本零第三方依赖，Python 3.10+ 即可；本课实测环境是 Python 3.12.3 / Linux / 4 vCPU。

---

## ✅ 今日完成清单

- [ ] 能不看笔记说出 9 类算法模板的「识别信号 + 不变量 + 复杂度」
- [ ] 能手写 `lower_bound`，并解释为什么用左闭右开
- [ ] 能说清 GIL 对 CPU 密集 / IO 密集的不同影响，并给出实测数字
- [ ] 能解释引用计数与分代 GC 的分工
- [ ] 能区分可迭代对象 / 迭代器 / 生成器
- [ ] 能说出装饰器本质与 `functools.wraps` 的作用
- [ ] 能解释可变默认参数为什么共享，正确写法是什么
- [ ] 能画出 C3 MRO 顺序，并解释为什么
- [ ] 能用 STAR 讲一个项目，且至少包含 2 个数字
- [ ] 能说出本课评分器的 4 个维度、权重和已知局限
- [ ] 跑通 4 个脚本的 `--self-test`
- [ ] 跑通一次基准，并解释「线程为什么比顺序还慢」

---

## 一、基础练习（每题 10–20 分钟）

### 练习 1：手写 lower_bound 的三种边界

不运行代码，先在纸上写出下面三种调用的返回值，再跑脚本验证：

```python
lower_bound([1, 3, 3, 5], 0)   # ?
lower_bound([1, 3, 3, 5], 3)   # ?
lower_bound([1, 3, 3, 5], 6)   # ?
lower_bound([], 1)             # ?
```

要求：写出 `lo/hi` 每一步的变化，而不是只写答案。

验证：

```bash
python3 code/01-algorithm-templates.py --demo lower_bound
python3 code/01-algorithm-templates.py --self-test
```

### 练习 2：把「两数之和」改成「返回所有不重复的数对」

输入 `nums = [1, 1, 2, 2, 3, 3], target = 4`，期望输出 `[(1, 3), (2, 2)]`（顺序不限）。

要求：
- 先用哈希做，再想能不能排序 + 双指针；
- 说明为什么哈希版需要额外去重，而排序版天然不重复；
- 写出时间复杂度。

### 练习 3：给滑动窗口加一个「最多替换 k 个字符」的变体

给定字符串 `s` 和整数 `k`，求「最多替换 k 个字符后，最长的全相同子串」长度。
（提示：窗口内 `长度 - 出现最多的字符次数 <= k`。）

要求：先写暴力 O(n²)，再改滑动窗口，并用 `assert` 对比两者在 200 组随机小数据上结果一致。

### 练习 4：用本课评分器评自己的三条回答

选三题：`py-gil`、`algo-binary`、`proj-star`。先不看标准答案，各写 100–300 字，
存成 `answer1.txt` / `answer2.txt` / `answer3.txt`，然后：

```bash
python3 code/03-mock-interview-scorer.py --question py-gil --answer-file answer1.txt
python3 code/03-mock-interview-scorer.py --question algo-binary --answer-file answer2.txt
python3 code/03-mock-interview-scorer.py --question proj-star --answer-file answer3.txt
```

要求：
- 记录每题的四个维度分数；
- 只改「最低的那个维度」，重写一遍再评分；
- 观察总分变化，判断改法是否有效。

### 练习 5：解释一次「线程比顺序还慢」

跑：

```bash
python3 code/04-concurrency-and-memory.py --bench
```

用不超过 150 字解释：为什么 CPU 密集场景下 `threads_s` 可能大于 `sequential_s`？
要求至少提到：GIL、线程切换、缓存的局部性。

---

## 二、进阶挑战（每题 30–60 分钟）

### 挑战 1：给评分器加一个「反堆砌」检测

现状：长段落堆关键词可能骗过覆盖分。设计一个不依赖外部库的检测器，要求：

- 输入一段回答，输出 0–1 的「信息密度」；
- 至少能区分「重复同一句 3 次」和「三个不同要点」；
- 给出你的阈值依据（在 5 条以上样本上试）。

提示：相邻二元组去重率、句子长度方差、unique token 比例，任选其一，但要解释为什么。

### 挑战 2：把题库扩展成「追问树」

当前 `follow_ups` 只是列表。改成树：

```json
{"q": "...", "follow_ups": [{"q": "...", "follow_ups": []}]}
```

要求：
- 评分器能按「主问题 → 追问 1 → 追问 2」逐层提问；
- 每层单独计分，并给出「主问题会但追问不会」的诊断；
- 保持 `--self-test` 可离线运行。

### 挑战 3：用 `multiprocessing` 手写进程池，替代 `ProcessPoolExecutor`

要求：
- 4 个 worker 进程，通过 `Queue` 分发任务、收集结果；
- 支持任务异常回传，不能让 worker 静默死掉；
- 在 4 个 20M 筛法任务上对比 `ProcessPoolExecutor` 的耗时；
- 解释 `fork` 与 `spawn` 启动方式对耗时的影响。

### 挑战 4：写一份「项目深挖 20 问」并自答

基于你真实做过的一个项目，列出面试官可能追问的 20 个问题，覆盖：

- 需求与约束（为什么做、不做什么）
- 方案与备选（为什么选 A 不选 B）
- 数据与指标（怎么测、口径是什么）
- 故障与边界（最坏情况、如何回滚）
- 反思（重做会改什么）

每题写 3 句以内的回答，再用评分器的 `--answer-text` 批量跑一遍，记录最低分的 3 题。

---

## 三、验收命令（复制即可）

```bash
cd days/day-197-面试准备

# 1. 四个脚本自检（离线，约 2 秒）
python3 code/01-algorithm-templates.py --self-test
python3 code/02-python-interview-facts.py --self-test
python3 code/03-mock-interview-scorer.py --self-test
python3 code/04-concurrency-and-memory.py --self-test

# 2. 真实基准（约 5 秒；数值随机器负载变化）
python3 code/04-concurrency-and-memory.py --bench

# 3. 评分器校准（应输出准确率 100%，间隔 > 0）
python3 code/03-mock-interview-scorer.py --calibrate

# 4. 题库清单
python3 code/03-mock-interview-scorer.py --list
```

预期：四条自检末尾都是 `✅ ... 项断言全部通过`。

---

## 四、今日复盘（写完再关电脑）

1. 我今天新学到的、能一句话讲清的结论是：______
2. 我原来理解错的一个点是：______
3. 我能用数字证明的一个结论是：______
4. 明天（Day 198 开源贡献）我要带着什么问题去学：______
