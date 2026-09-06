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

---

## 进阶挑战

### 4. TLS 1.3 为什么砍掉 RSA 密钥交换？

提示：思考"服务器私钥十年后被泄露，今天的抓包还能不能被解开"。

<details><summary>参考答案</summary>

RSA 交换的预主密钥用服务器公钥加密，攻击者存下今天的密文，十年后拿到私钥即可解密——即无前向保密。ECDHE 每次会话用临时密钥对，会话结束即销毁，私钥泄露也无法回溯历史流量（Forward Secrecy）。
</details>

### 5. 动手：TLS 版本探测

写脚本分别用 `ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)` 并设置 `ctx.maximum_version = ssl.TLSVersion.TLSv1_1` 去连一个现代站点，观察报错。再用 Python 检查为什么默认上下文禁止了旧协议。

<details><summary>参考答案</summary>

现代站点/中间设备会直接握手失败或拒绝旧协议；Python 3.12 起 `ssl` 默认上下文按系统安全策略禁用 TLS<1.2（`ssl.create_default_context().minimum_version` 可查看）。结论：协议降级不是兼容，是漏洞。
</details>

### 6. 思考：ECH 要解决什么问题？

ClientHello 里的 SNI 是明文的，谁在利用这个信息？ECH（Encrypted Client Hello）如何应对？

<details><summary>参考答案</summary>

SNI 明文暴露你要访问的域名，可被运营商/防火墙用于分流与封锁。ECH 把真正的 SNI 加密后放在加密扩展里，明文位置只留一个占位域名；配合 DNS-over-HTTPS 才能完全生效。
</details>
