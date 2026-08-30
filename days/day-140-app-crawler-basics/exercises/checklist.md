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

