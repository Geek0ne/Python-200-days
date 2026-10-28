# Day 199 练习与验收清单 — 技术写作

> 所有命令都在仓库根目录执行。三个教学脚本 + 一个夹具都支持 `--self-test`，
> 离线、无外部服务、无第三方依赖。

---

## 一、今日完成清单

- [ ] 读完 `README.md` 的概念与原理两节，能说出"可复现性契约"的五个字段
- [ ] 能解释为什么体检器必须跳过代码围栏内的内容
- [ ] 能解释为什么"输出可复现"和"计时可信"是两个独立判定
- [ ] 跑通四个脚本的 `--self-test`（应当全部 PASS）
- [ ] 用体检器给自己写过的一篇文章打分，并至少修掉 2 个 warning
- [ ] 用实验卡片给自己的一条命令生成一张卡片，检查哈希是否稳定
- [ ] 用静态站构建器发布一篇文章，curl 验证返回 200
- [ ] 清理实验现场（端口、临时目录）

---

## 二、基础练习

### 练习 1：让体检器给你的旧文打分

**目标**：把规则用在真实文本上，感受误报与真问题

```bash
cd days/day-199-技术写作
# 换成你自己电脑上的任意 markdown 文件
python3 code/01-article-lint.py ../../README.md
```

**要求**：

1. 记下评分和每条 finding 的行号
2. 对每条 finding 判断：真问题 / 误报 / 可接受
3. 至少修掉 2 条真问题，重跑确认分数上升

**验收**：能说出"这条 warning 为什么在这篇文章里不适用"，而不是一律照改。

### 练习 2：写一条新规则

**目标**：理解规则的成本——加上去容易，收得住难

在 `01-article-lint.py` 里加一条：**H2 标题超过 40 字报 warning**（W109）。

**要求**：

1. 在 `lint()` 的标题分支里加判断
2. 在 `self_test()` 里加一条夹具和一个断言
3. 跑 `--self-test`，必须 PASS
4. 用 `--strict` 跑 `article/post.md`，看是否引入新问题

**思考**：为什么"标题过长"是 warning 而不是 error？

### 练习 3：手工验证实验卡片的判定

**目标**：确认"输出不稳定"是真判定，不是随机出错

```bash
cd days/day-199-技术写作
python3 code/02-repro-card.py --repeat 4 -- python3 -c "import random; print(random.random())"
python3 code/02-repro-card.py --repeat 4 -- python3 -c "print(42)"
```

**要求**：

1. 第一条应当报"输出不稳定"
2. 第二条应当报"输出可复现"
3. 两条的退出码分别是多少？为什么这样设计？

---

## 三、进阶挑战

### 练习 4：给静态站加一个"上一篇 / 下一篇"

**目标**：理解构建器里数据流的位置

现状：`build_site()` 已经按日期倒序拿到 `articles` 列表，但 `build_article()` 是
独立渲染的，拿不到邻居。

**要求**：

1. 改成两阶段：先渲染正文片段，再注入 prev/next 导航
2. 导航链接必须指向真实存在的 slug
3. 自测里加一条断言：第一篇没有 prev、最后一篇没有 next

**提示**：不要在 `build_article()` 里读文件系统——那会让它难以测试。

### 练习 5：把一次真实测量写成 300 字短文

**目标**：完整走一遍"实验 → 卡片 → 文章 → 体检"的闭环

**步骤**：

1. 用 `02-repro-card.py` 测两段你熟悉的代码（例如 `list.append` 循环 vs 列表推导），
   `--repeat 7`
2. 写出短文，必须包含：结论先行的一段、环境与样本量、真实输出块、一个适用边界
3. 用 `01-article-lint.py --strict` 检查，必须 0 error 0 warning
4. 用 `03-article-build.py` 构建，curl 确认 200

**检查点（自评）**：

- [ ] 结论能用一句话说清，且没有"显然"
- [ ] 数字带环境、重复次数、统计量（median 还是 mean）
- [ ] 写明了这个结论在什么情况下不成立
- [ ] 读者能只靠文章复现你的命令

---

## 四、验收命令（一条条跑，全部应通过）

```bash
cd days/day-199-技术写作

# 1) 四个脚本离线自证
python3 code/01-article-lint.py --self-test
python3 code/02-repro-card.py --self-test
python3 code/03-article-build.py --self-test
python3 code/04-make-corpus.py /tmp/corpus-check --self-test

# 2) 分数应当是 65 和 100
python3 code/01-article-lint.py article/draft-with-issues.md; echo "exit=$?"
python3 code/01-article-lint.py article/post.md; echo "exit=$?"

# 3) 构建产物应当包含 index/post/feed/.nojekyll
python3 code/03-article-build.py article --out /tmp/day199-check
ls /tmp/day199-check

# 4) 清理
rm -rf /tmp/day199-check /tmp/corpus-check
```

**预期**：`draft` 退出码 1、`post` 退出码 0；构建输出 2 篇文章；
`ls` 里能看到 `feed.xml` 与 `.nojekyll`。

---

## 五、自测失败时的排查顺序

1. **先怀疑夹具**：规则没错，是样例写错了（今天真的发生过，见 README 翻车 1）
2. 再看规则的作用域：是不是把代码块里的内容也查了
3. 最后看边界：空文件、单个 H1、无代码块
