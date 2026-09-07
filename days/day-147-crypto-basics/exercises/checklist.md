# Day 147 练习与检查表 — 密码学基础

## ✅ 完成清单

- [ ] 理解哈希函数四大性质（确定性 / 单向性 / 抗碰撞性 / 雪崩效应）
- [ ] 能说出 MD5 / SHA-1 / SHA-256 的安全性现状与适用场景
- [ ] 掌握 `hashlib` 的 update() 增量哈希与流式大文件处理
- [ ] 理解裸哈希存密码的三宗罪（彩虹表 / 高速爆破 / 相同密码同摘要）
- [ ] 会用 `pbkdf2_hmac` + 随机盐实现密码哈希存储与校验
- [ ] 理解 HMAC 与 `sha256(key+msg)` 的区别（长度扩展攻击）
- [ ] 记住校验摘要必须用 `hmac.compare_digest`（时序攻击）
- [ ] 跑通 code/03 文件完整性校验工具的全部 4 个子命令

## 📝 练习题

### 基础

**1. 实现一个 `sha256_tree` 函数**：给定任意目录，返回一个形如
`{"相对路径": "sha256十六进制"}` 的字典（提示：`os.walk` + 分块读取）。

**2. 修改 `02-password-hashing.py`**：把迭代次数从 100_000 提升到 600_000，
用 `time.perf_counter` 对比两次校验耗时，并回答：这对正常登录用户和
暴力破解者分别意味着什么？

### 进阶

**3. 实现防篡改配置文件**：写一对函数
`save_config(cfg: dict, path: str, key: bytes)` / `load_config(path: str, key: bytes) -> dict | None`。
要求：保存时把 JSON + HMAC 签名一起写入；加载时先验签，失败返回 None；
测试篡改文件中任意一个字符后 load 返回 None。

**4. 说明并验证长度扩展攻击的存在**：阅读 `hashlib` 文档，解释为什么
`hashlib.sha256(key + msg).hexdigest()` 不能当 MAC 用（画出 Merkle–Damgård
结构中的中间状态转移即可，不要求实现攻击）。再用
`hmac.new(key, msg, hashlib.sha256)` 写一个对照示例说明 HMAC 免疫此攻击。

### 挑战

**5. 给 03 工具加"并行哈希"**：用 `concurrent.futures.ThreadPoolExecutor`
对目录中多个文件并行计算 SHA-256（哈希是 CPU 密集，可尝试 ProcessPoolExecutor
对比谁更快），并思考：单个大文件能否并行计算哈希？为什么？（从链式结构角度回答）
