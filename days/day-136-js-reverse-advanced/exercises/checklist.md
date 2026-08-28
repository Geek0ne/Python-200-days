# Day 136 - JS 逆向进阶 · 练习与检查表

## ✅ 今日完成清单

- [ ] 理解 Hook 的"备份原函数 -> 替换 -> 插桩 -> 原样返回"四步模型
- [ ] 能手写 `btoa` / `JSON.parse` / `XMLHttpRequest.send` 的 Hook 脚本
- [ ] 理解为什么 Hook 必须在目标脚本之前执行（闭包引用问题）
- [ ] 会用 XHR 断点 + Call Stack 回溯定位加密核心函数
- [ ] 理解补环境的本质：伪造 window/document/navigator 让 JS 以为在浏览器
- [ ] 理解"漏补属性 -> 静默走错分支"这个最隐蔽的坑，会用 Proxy 日志兜底
- [ ] 掌握无头浏览器取签名的完整流程（addScriptToEvaluateOnNewDocument + execute_script）

---

## 📝 练习题

### 基础

**1. Hook 模板改写**

把 `code/01-hook-basic.py` 的 `hook_function` 改造为"条件 Hook"：只有当入参包含 `"sign"` 关键字时才打印日志并触发断点，其余调用静默放行。思考：这解决了什么实际问题？（提示：高频函数全量打印会淹没日志）

**2. 调用栈阅读**

运行 `code/02-stack-trace.py` 的 A 部分，按输出回答：
- 调用链里哪一层是"加密核心"？
- 如果 `build_params` 和 `send_request` 都是混淆名 `_0x1a2b`，你还能靠什么信息定位？（提示：Scope 变量值）

### 进阶

**3. 补环境完整性校验器**

给 `code/02-stack-trace.py` 的 `Env` 类增加 `diff(real_env: dict)` 方法：传入真实浏览器的属性快照（可手写），输出"已补但值不一致 / 真实有但漏补 / 补了多余属性"三类差异报告。

**4. Hook 时机实验**

设计一个最小 HTML 实验：页面脚本第一行就把 `var _origBtoa = window.btoa` 存入闭包并一直用 `_origBtoa`。验证：Hook 注入晚于该脚本时必然失效；再把注入提前到 `document_start`，观察 Hook 是否生效（本例中仍失效，为什么？如何补救？提示：改 Hook `Function.prototype` 层面或拦截更底层）。

**5. 签名方案选型**

针对以下三种站点，分别选择"Python 复现 / Node 补环境 / 无头浏览器"并说明理由：
- a) 签名是纯 MD5(固定盐+参数)，无环境检测
- b) 签名读取 `navigator.plugins` 长度与 `document.createElement('canvas')` 指纹
- c) 签名每 10 分钟由服务端下发一段新 JS 动态生成，且 JS 带 VMP 虚拟机壳
