# Day 140 - App 爬虫基础 练习清单

## ✅ 完成清单

- [ ] 理解 HTTPS 抓包 = 中间人攻击原理，能画出 App↔mitmproxy↔服务器 链路图
- [ ] 知道 Android 7.0+ 不信任用户证书的原因及 3 种解决方案
- [ ] 能用 mitmweb 抓到一个 HTTPS 请求并找到 sign/token 参数
- [ ] 会写 mitmproxy addon 脚本自动落盘 JSONL
- [ ] 理解"客户端加密必可逆"的原因
- [ ] 能用 jadx 搜索定位签名函数，用 Python 复现 md5 签名
- [ ] 了解 SSL Pinning 及 frida/objection 绕过思路
- [ ] 完成 3 个代码示例并跑通

## 📝 练习题

### 基础

1. **抓包链路**：写出手机通过 mitmproxy 抓 HTTPS 包时，完整的证书信任关系（谁信任谁的证书）。为什么 mitmproxy 可以同时欺骗 App 又不被服务器发现？

2. **addon 脚本**：修改 `01-mitmproxy-addon.py`，实现只保存 `Content-Type: application/json` 的响应，并且当响应里出现 `"code": 401` 时在终端打印红色警告（提示：用 `flow.response.headers.get("content-type")`）。

### 进阶

3. **签名复现**：抓包样本如下，请写出 Python 函数复现 sign 算法并验证：
   ```
   password = "abc666", timestamp = 1756598400
   md5(password) = "E10ADC3949BA59ABBE56E057F20F883E" (demo值)
   sign = MD5_UPPER( MD5_UPPER(password) + timestamp + "salt123" )
   ```
   验证方式：改变 timestamp，确认 sign 同步变化；说明为什么时间戳参与签名能防"重放攻击"。

4. **反爬对抗设计**：如果你是 App 的安全工程师，设计至少 3 层防线对抗协议模拟爬虫（提示：设备指纹、短时效 token、行为风控），并说明每层对应的破解成本。

5. **抓不到包排查**：某 App 设置代理后完全抓不到任何请求，列出你的排查步骤树（至少覆盖：证书校验/SSL Pinning、代理检测、非 HTTP 协议、双向验证 mTLS 四种可能）。
