# Day 200 代码说明

四个脚本全部零第三方依赖、可离线自证。Python 3.10+（`X | None` 注解、`dataclass`、
`str.removeprefix`）。**02 需要真实的 git 历史**，浅克隆会直接报错而不是给出错误结论。

## 四件套的关系

```text
01-skill-audit.py      能力证据   → audit.json  ┐
02-learning-loop.py    系统瓶颈   → loop.json   ├→ 04-growth-roadmap.py
03-tech-radar.py       技术资产   → radar.json  ┘      → graduation.md
仓库真实文件（04 自己扫）                              → roadmap-90d.md
                                                       → summary.json
```

01/02/03 互相独立，可以单独跑、单独看。04 是唯一的消费者：缺哪份输入就在报告里
标「缺失」，不会替你编数字。

## 运行顺序

```bash
cd days/day-200-持续成长路径/code

# 0. 先离线自证（4 个脚本共 93 条断言，不联网、不依赖本仓库）
python 01-skill-audit.py --self-test
python 02-learning-loop.py --self-test
python 03-tech-radar.py --self-test
python 04-growth-roadmap.py --self-test

# 1. 能力：把「我感觉会」换成可数的文件痕迹
python 01-skill-audit.py
python 01-skill-audit.py --ratings self-rating.example.json
python 01-skill-audit.py --ratings my-rating.json --scale 5
python 01-skill-audit.py --json /tmp/day200/audit.json --markdown /tmp/day200/audit.md

# 2. 系统：从 git 历史反推学习回路哪一环被饿死
python 02-learning-loop.py --top 10
python 02-learning-loop.py --json /tmp/day200/loop.json --markdown /tmp/day200/loop.md

# 3. 资产：ast 静态扫描 import，生成技术雷达
python 03-tech-radar.py
python 03-tech-radar.py --ring Hold
python 03-tech-radar.py --json /tmp/day200/radar.json --markdown /tmp/day200/radar.md

# 4. 合成：三份测量 + 仓库统计 → 毕业总结与 90 天路线图
python 04-growth-roadmap.py \
  --audit /tmp/day200/audit.json \
  --loop  /tmp/day200/loop.json \
  --radar /tmp/day200/radar.json \
  --out   /tmp/day200/毕业交付
```

Windows 上把 `python3` 换成 `python`；旧课脚本若报 `UnicodeEncodeError`，加 `-X utf8`。

## 一次真实运行能看到什么（2026-11，Windows 11 · Python 3.12）

| 指标 | 值 | 来源 |
|---|---:|---|
| 离线断言总数 | 93（20 + 29 + 24 + 20） | 四个 `--self-test` |
| 扫描课程数 | 200 | 01 / 04 |
| git 提交数（已忽略 merge） | 1,478 | 02 |
| 活跃天数 / 日历跨度 | 125 / 170 天 | 02 |
| 实践 : 输出 : 反馈 | 653 : 740 : 19 | 02 |
| 反馈延迟中位（全部 / 剔除批量） | 85 / 55.0 天 | 02 |
| 从未被针对性回访的课 | 152 门（全部口径 0 门） | 02 |
| 解析 .py（失败数） | 737（0） | 03 |
| import 归类 | 标准库 3308 · 第三方 798 · 本地 70 | 03 |
| 标准库占比 | 79.2% | 03 |
| 第三方包 / 窄面包 | 78 / 56 | 03 |
| 雷达四环 | Adopt 5 · Trial 17 · Assess 53 · Hold 3 | 03 |
| requirements 条目 | 5（钉死 4 · 范围 1 · 未约束 0） | 03 |
| .py 总行数 | 208,445 | 04 |
| mermaid 图 | 528 | 04 |
| 四件套完整度 | 200/200 | 04 |

> 数字会随仓库演进而变化，读法不变；`mermaid` 统计每课目录下所有 `.md`。
> 每个数字怎么解读，见主 README 第五节。

### 03 的 737 与 04 的 740 为什么不同

不是 bug，是口径：

- **03 只扫 `days/*/code/**/*.py`**（要判断第三方依赖，`deploy/` 与练习答案不在射程内）
- **04 扫 `days/*/**/*.py`**（要统计交付体量）

差的 3 个文件是：

```text
days/day-018-推导式/exercises/solutions.py
days/day-190-定时巡检与变更告警/deploy/app/sink.py
days/day-190-定时巡检与变更告警/deploy/app/worker.py
```

## 参数约定

| 参数 | 默认 | 说明 |
|---|---|---|
| `--root` | 从脚本位置向上找含 `days/` 的目录 | 也可用 `LEARN_PYTHON_ROOT` 覆盖 |
| `--scale` | 100 | 01 的自评分制，只接受 5 或 100 |
| `--top` | 5 | 02 打磨度榜单长度 |
| `--ring` | 全部 | 03 只显示某一环 |
| `--json` / `--markdown` | 不导出 | 01/02/03 的双视图导出 |
| `--out` | 必填才写盘 | 04 的输出目录 |

### 模块常量（都是产品判断，不是统计结论，改之前先想清楚）

| 常量 | 值 | 所在 | 含义 |
|---|---:|---|---|
| `LEVELS` 权重 | 1 / 2 / 3 / 4 | 01 | 读过 / 跑过 / 自证过 / 交付过 |
| `CALIBRATION_BAND` | 15 | 01 | 校准差在 ±15 内算「基本一致」（含边界） |
| `STARVED` | 实践 20% · 输出 15% · 反馈 5% | 02 | 低于此比例判为饿死 |
| `BULK_THRESHOLD` | 20 | 02 | 一次提交触及 ≥20 课即视为批量，另算一套口径 |
| `ADOPT_MIN_DAYS` / `ADOPT_MIN_SPAN` | 8 课 / 30 天 | 03 | 进 Adopt 需同时满足 |
| `TRIAL_MIN_DAYS` | 3 | 03 | 进 Trial 的课数下限 |
| `HOLD_MAX_DAYS` | 2 | 03 | 窄面上限，且必须有标准库替代 |
| `REQUIRED` | 4 项 | 04 | README / code / exercises/checklist.md / diagrams/README.md |

## 已知边界

- **01 的证据分只统计仓库痕迹，不等于真实能力**。你在别处写过的代码它看不见；
  反过来，仓库里有 `--self-test` 也不代表你真的理解那一课。它测的是「可举证的最低量」。
- **01 的维度→Day 区间是硬编码的**（`DIMENSIONS`），依据是根 README 的 12 阶段表。
  课程重排后必须同步改，否则会静默算错。
- **02 测不到「输入」**。git 里没有「我读了什么」，所以四阶段里输入永远显示「不可观测」，
  不是 0。把不可观测当成 0 是本课最想拦住的错误。
- **02 依赖 Conventional Commits**。不规范的 message 归「其他」（本仓库 47 条），
  不猜。如果你自己的仓库不用这套前缀，先改 `STAGE_OF` 再用。
- **03 用 `ast.parse`，从不 import 或执行任何被扫描的文件**。所以它看得见
  `import tools`，但看不见 `importlib.import_module(name)` 这种动态导入。
- **03 的 import 名 ≠ 发行包名**：`PIL`→pillow、`sklearn`→scikit-learn、
  `yaml`→PyYAML、`cv2`→opencv-python。雷达按 import 名统计，装包时别照抄。
- **03 的「标准库替代」不是等价替换**。`bs4 → html.parser` 少了 CSS 选择器与容错修复，
  `jwt → hmac+hashlib` 少了声明校验与过期处理。报告里每条都写了代价。
- **04 的里程碑是缺口驱动的模板，不是排期承诺**。周投入、交付物、验收、放弃条件
  四项齐全，但「30 天」只是节拍器，真实工期要你自己按周投入折算。
- **04 缺输入时不编数字**，会在 `summary.json` 的 `missing_inputs` 里列出来。
  一份没有 01/02/03 输入的毕业总结，只能证明仓库有多大，不能证明你学到了什么。

## 清理

```bash
rm -rf /tmp/day200          # Windows: rmdir /s /q "%TEMP%\day200"
```

四个脚本都只读仓库，唯一写盘动作是 `--json` / `--markdown` / `--out` 指定的路径。