# Day 158 — WebShell 检测：实战扫描器（静态特征 + 行为关联 + 评分定级）

> Phase 10 — 网络安全开发。**实战项目**：面向真实检测场景的 WebShell 扫描器。
>
> **使用边界（重要）**：本课及仓库内样本仅用于**授权环境**（自己的服务器、靶场、
> 已获书面授权的评测环境）与**离线文件副本**。运行扫描器不会执行被扫描文件、
> 不发网络请求、不自动删除或隔离任何文件。样本集中的命令均为占位符，
> 未提供可实际执行的后门载荷，也未包含规避检测的对抗手法。

## 1. 学习目标

完成本课后，应能：

- 识别各语言（PHP / JSP / ASPX / ASP）常见的 WebShell **特征类别**：
  命令执行、动态求值、编码混淆、文件操作、网络外联、动态包含
- 理解**命中 ≠ 恶意**：特征只是复核线索，需结合行为与业务基线
- 用**加权评分**给文件定级（clean / low / medium / high / critical）
- 用**行为信号关联**（上传脚本 + 子进程 + 命令参数）判断是否需人工复核
- 理解扫描器的**局限**：误报、漏报、覆盖不全的意义，以及"无命中 ≠ 安全"

## 2. 快速开始（Python 3，Linux，无第三方依赖）

```bash
python3 days/day-158-webshell-检测/code/01-static-scanner.py --self-test
python3 days/day-158-webshell-检测/code/02-behavior-hunter.py --self-test
python3 days/day-158-webshell-检测/code/03-webshell-scanner.py --self-test
```

三个命令都应输出 `SELF-TEST OK`。

**生成实战样本集并扫描**（临时目录，结束后自动清理，只读）：

```bash
python3 days/day-158-webshell-检测/code/01-static-scanner.py --lab
```

**扫描自己的离线副本**：

```bash
python3 days/day-158-webshell-检测/code/03-webshell-scanner.py ./my-offline-copy
python3 days/day-158-webshell-检测/code/03-webshell-scanner.py ./my-offline-copy --max-files 500
python3 days/day-158-webshell-检测/code/03-webshell-scanner.py --rules   # 查看规则库
```

默认不扫描 `/var/www` 或整个系统，必须显式指定目录。单文件读取上限 1 MiB。

## 3. 规则库与评分模型

`static_scan.py` 内置 20+ 条规则，每条有：名称、正则、**权重（1–3）**、类别、覆盖语言。

| 类别 | 含义 | 示例规则 | 权重 |
|---|---|---|---|
| command | 命令执行 | `system/exec/shell_exec`、`Runtime.exec`、`Process.Start`、WScript.Shell | 3 |
| dynamic | 动态求值 | `eval/assert/create_function`、`defineClass`、`Execute` | 3 |
| encoding | 编码混淆 | `base64_decode/gzinflate/str_rot13/hex2bin` | 1–2 |
| obfuscation | 混淆手法 | `@` 错误抑制、超长变量名、`$GLOBALS[]` | 1 |
| filesystem | 文件操作后门行为 | `file_put_contents/fwrite/chmod` | 1–2 |
| network | 外联 | `fsockopen/curl_exec/socket_create` | 2 |
| input | 外部输入 | `$_GET/$_POST/$_REQUEST` | 1 |
| include | 动态包含 | `include/require` 接变量 | 1 |

**评分规则**：同一规则首次命中记权重；重复命中（混淆代码常见）从第 2 次起每次 +1，
单规则封顶 3 次。累计得分 → 风险等级：

| 得分 | 等级 |
|---|---|
| ≥8 | critical |
| ≥5 | high |
| ≥3 | medium |
| ≥1 | low |
| 0 | clean |

> 权重和阈值是教学基线，可按实际业务调整。真实产品还需结合
> 语义分析、数据流分析（危险输入是否真正到达危险调用）来压制误报。

## 4. 代码导读

### `01-static-scanner.py` — 真实特征样本集

`SAMPLES` 中包含 7 个文件：正常业务页面（`clean.php`）、文档（`docs.txt`，
会误报——它只是提到 API 名称）、简单命令执行、多层混淆（base64 + gzinflate +
错误抑制 + 超长变量）、ASP / JSP / ASPX 三种后门骨架。

注意 `docs.txt`：它命中了多个规则但只是**普通文档**。这演示了静态特征的固有问题——
**命中是复核线索，不是恶意结论**。

### `02-behavior-hunter.py` — 行为信号关联

输入是合成审计事件（模拟 Web 日志），按 `(host, instance)` 分组累计信号分：

| 信号 | 分值 | 必要字段 |
|---|---|---|
| upload_script_write（上传目录写脚本） | 3 | host, instance, request |
| child_start（启动子进程） | 2 | host, instance |
| cmd_arg_shell（命令参数带 shell） | 2 | host, instance |
| suspicious_ua / many_failed_auth / upload_then_delete | 1–2 | host 等 |

总分 ≥4 触发 `review_required`。`instance` 必须是**进程启动标识**
（启动时间+身份），不能用可复用的 PID。`--no-window` 模拟时间窗口信息缺失，
此时拒绝下任何结论（直接标记 `time_window_unknown`）——**信息不全时不下结论**。

### `03-webshell-scanner.py` — 完整 CLI

| 参数 | 作用 |
|---|---|
| `target` | 要扫描的本地目录（必填，除非 --self-test/--rules） |
| `--max-files` | 文件遍历上限（默认 1000） |
| `--rules` | 打印规则库 |
| `--self-test` | 自测 |

JSON 输出结构：

| 字段 | 含义 |
|---|---|
| `files` | 每个文件的状态、命中、得分、等级、规则摘要 |
| `summary.top_findings` | 高危/严重文件中按分数排序的前 20 个 |
| `truncated` / `walk_errors` | 是否覆盖不全（必须如实报告） |
| `notice` | 使用边界提醒 |

**退出码**：0 = 所有列出的文件成功扫描（即使命中）；2 = 参数错误或覆盖不全。
**0 不代表安全认证**。

## 5. 实战检测流程（结合本扫描器）

1. **证据保全**：先对目标目录做哈希快照（或直接复制离线副本），记录采集时间与来源。
2. **静态扫描**：运行 `03-webshell-scanner.py`，优先查看 `high/critical` 文件。
3. **人工复核**：打开命中文件，确认特征是否在注释/文档/合法依赖里；
   危险调用是否真的接收外部输入（数据流分析）；**不要运行可疑文件验证**。
4. **行为关联**：把同一时间窗内的上传、进程、访问事件喂给 `02-behavior-hunter.py`，
   确认是否同一主机、同一进程启动标识下多个信号叠加。
5. **响应**：按组织流程限制服务、轮换凭据、排查入口；删除/下线由负责人决定。
6. **复测**：修复后重跑扫描确认基线，并检查日志覆盖是否完整。

## 6. 局限与自测覆盖

**自测覆盖**：正常代码低分级、文档误报低分级、命令执行与混淆样本正确识别、
四语言各自特征命中、评分与分级一致、跨主机/跨实例不误关联、字段缺失报错、
时间窗缺失不下结论、只读性（哈希前后一致）、超大文件/非法编码跳过、JSON 可序列化。

**未覆盖（生产化前必须补齐）**：真实恶意样本检出率（需要授权样本集）、
语义/数据流分析、压缩包与图片马展开、编码归一化、生产日志采集与时间窗口切分、
误报率评测。**未覆盖项必须保留在报告中，不得按"零告警"隐藏。**

## 7. 后续练习

见 [练习清单](exercises/checklist.md) 和 [原理图](diagrams/README.md)。
练习要求用正常代码建立标签集、计算误报率/召回率、做数据流与行为关联分析——
全部在授权环境与离线副本上进行。