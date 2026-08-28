# Day 135 - JS 逆向入门 · 练习与检查表

## ✅ 今日完成清单

- [ ] 掌握 Network 面板核心功能：Initiator / Preserve log / Copy as cURL
- [ ] 掌握 XHR 断点定位加密参数的完整流程
- [ ] 能通过"两次请求对比法"找出动态参数
- [ ] 能识别常见混淆特征（_0x 数组、eval、控制流平坦化）
- [ ] 理解字符串数组混淆的"动态执行死穴"
- [ ] 理解 AST 与正则替换的本质区别
- [ ] 掌握 subprocess 调 Node 执行摘出 JS 的落地方式

---

## 📝 练习题

### 基础

**1. 动态参数侦察**

用 `01-request-recon.py` 的思路，对一个真实公开接口（如 httpbin 模拟或任意无登录站点）连续请求 3 次，列出所有参数并标注"静态/动态"，对动态参数做长度与形态的启发式分析（MD5? 时间戳? base64?）。

**2. DevTools 实操**

打开任一电商首页（F12 -> Network -> XHR），找到商品列表接口，回答：
- 请求由哪个文件发起（看 Initiator）？
- 哪些参数是动态的？
- 用 Copy as cURL 导出并与 Python requests 请求对比结果。

### 进阶

**3. 混淆特征检测器增强**

扩展 `02-deobfuscate-basic.py` 的 `detect_obfuscation()`，增加检测：
- JSFuck 特征（`[]()!+` 密集出现）
- unicode 转义（`\u0061`）
- 端口伪装/逗号表达式（`,0,0,` 高频出现）

用自己构造的样本测试。

**4. 完整逆向落地**

把 `03-call-js-from-python.py` 改造成通用 `JsCaller` 类：
- `__init__(js_file)` 加载 JS 文件
- `call(func_name, **kwargs)` 通过 stdin/stdout JSON 协议调用任意函数
- 加缓存：相同参数不重复起 Node 进程
- 测试：一个含两个函数（genSign、genToken）的 JS 文件

### 挑战

**5. AST 初体验**

安装 Node 后 `npm i @babel/parser @babel/traverse @babel/generator`，写一个脚本：统计任意 JS 文件中 `CallExpression` 的数量，并把所有 `console.log(...)` 调用替换成空（AST 层面删除）。这是所有反混淆工具的第一块积木。

---

## 🔗 相关

- 昨日：Day 134 验证码识别
- 明日：Day 136 JS 逆向进阶（Hook 技术、堆栈回溯、补环境）
