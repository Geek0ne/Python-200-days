# Day 146 练习与检查表 — HTTPS 与抓包

## ✅ 今日完成清单

- [ ] 能不看资料说出 TLS 1.2 握手的 4 个步骤
- [ ] 理解"非对称建立信任、对称保障速度"的分工
- [ ] 运行 `01-tls-handshake.py`，看清协商出的版本/套件/证书
- [ ] 运行 `02-cert-verification.py`，亲眼见到自签证书被拒
- [ ] 运行 `03-tls-audit.py`，读懂体检报告每一项
- [ ] 能解释 Fiddler 抓 HTTPS 的原理（MITM + 信任假根证书）

---

## 基础练习

### 1. 数一数随机数

TLS 1.2 握手里一共出现了几个随机数？它们分别由谁生成、作用是什么？

<details><summary>参考答案</summary>

3 个：客户端随机数（ClientHello）、服务器随机数（ServerHello）、预主密钥（客户端生成）。三者一起输入 KDF 导出会话密钥——即使某一个随机数质量差，整体密钥仍然难以预测。
</details>

### 2. 找证书信息

修改 `01-tls-handshake.py`，改为连接 `www.python.org`，打印 SAN 里有几个域名。为什么证书要带 SAN 而不只看 CN？

<details><summary>参考答案</summary>

SAN（Subject Alternative Name）是现代标准，一个证书可覆盖多个域名（如 `python.org` + `www.python.org`）；CN 已被浏览器废弃，匹配只看 SAN。
</details>

### 3. 判断题

"Wireshark 抓到 HTTPS 流量就能看到我的账号密码。" 对不对？为什么？

<details><summary>参考答案</summary>

不对。Wireshark 只能看到握手明文和加密后的 record；没有会话密钥（或服务器私钥 + 非 ECDHE 套件）解不开密文。
</details>
