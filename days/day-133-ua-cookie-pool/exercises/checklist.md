# Day 133 - UA 与 Cookie 池 · 练习与检查表

## ✅ 今日完成清单

- [ ] 理解 UA 在反爬检测中的作用（第一道防线 + 交叉验证）
- [ ] 掌握"会话身份一致性"原则（UA + 头模板 + Cookie 整体绑定）
- [ ] 理解 Cookie 池状态机：fresh -> active -> dead
- [ ] 掌握 `requests.Session` 的 Cookie 自动管理与持久化
- [ ] 能用加权随机实现更真实的 UA 分布
- [ ] 理解 Cookie 池与 IP 代理池绑定的原因
- [ ] 了解 TLS 指纹（JA3）等更高层检测的存在

---

## 📝 练习题

### 基础

**1. 加权 UA 池**

给一个 `[(ua, weight), ...]` 列表，实现 `pick_ua()` 函数：按权重随机返回 UA（不用 `random.choices`，手写累积权重法）。再用 `collections.Counter` 验证 10000 次抽样的分布是否接近权重比。

**2. Cookie 持久化**

写一个函数 `save_cookies(session, path)` 和 `load_cookies(path) -> RequestsCookieJar`，用 `pickle` 实现会话 Cookie 的落盘与恢复。要求：加载后用 `httpbin.org/cookies` 验证 Cookie 仍然生效。

### 进阶

**3. 简易 Cookie 池类**

实现 `CookiePool` 类，要求：
- 内部用 SQLite（表字段：cookie, status, fail_count, last_used）
- `get()`：随机取一个 `active/fresh` 状态的 Cookie，并置为 active
- `report(cookie, ok)`：成功则 fail_count 清零；失败则 +1，连续失败 3 次置为 dead
- `refill(n)`：从 `httpbin.org` 获取 n 个游客 Cookie 补充进池
- 写 10 行测试代码模拟"成功率 70%"的随机反馈，观察池子状态流转

**4. 绑定身份的会话管理器**

实现 `IdentityManager`：每个身份 = (UA 模板, proxy, cookie) 三元组，`acquire()` 返回一个完整配置的 `requests.Session`，`release(session, ok)` 回收并统计。要求同一个身份在未被标记失败前，proxy 与 cookie 不会被拆开给别的会话使用。

### 挑战

**5. 指纹一致性思考实现**

写一个 `fingerprint_check(headers_dict)` 函数：检查 UA 与 `sec-ch-ua-platform`、`Accept-Language`、`Referer` 的一致性（如 UA 声称 Windows 但 platform 是 macOS 则报警）。用它扫描你的 UA 池生成的 100 组随机请求头，统计报警率并修复模板。

---

## 🔗 相关

- 昨日：Day 132 代理池（IP 层）
- 明日：Day 134 验证码识别（Cookie 失效后的应对）
