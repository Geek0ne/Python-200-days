# Day 140 - App 爬虫基础

> 目标：掌握 App 爬虫的完整工作流——抓包分析、APK 反编译、协议模拟，最终实现 App 数据抓取。

---

## 一、概念解释

### 1.1 什么是 App 爬虫？

Web 爬虫抓取的是浏览器渲染的 HTML 页面，而 **App 爬虫**抓取的是手机 App 与服务器之间的通信数据。很多公司（电商、社交、短视频）把最核心的数据和功能放在 App 端，甚至 App 优先于 Web 发布功能，所以 App 爬虫是数据采集绕不开的一环。

```
Web 爬虫:  浏览器 ──HTTP──> Web 服务器        (返回 HTML/JSON)
App 爬虫:  手机App ──HTTP/HTTPS/私有协议──> API 服务器  (返回 JSON/Protobuf)
```

### 1.2 三大核心技术

| 技术 | 作用 | 对应工具 |
|------|------|----------|
| 抓包 | 观察App与服务器通信内容 | mitmproxy / Charles / Fiddler |
| 反编译 | 分析 APK 里的加密逻辑 | jadx / apktool / frida |
| 协议模拟 | 用 Python 复现 App 的请求 | requests / httpx / pycryptodome |

### 1.3 为什么 App 爬虫比 Web 爬虫更"稳定"？

- App 的 API 接口版本迭代慢，一旦逆向出参数规则，可以长期稳定使用；
- App 端的反爬主要靠**签名校验**（sign 参数），而不是 Web 端的 JS 混淆 + 风控指纹，攻防面更窄；
- 返回数据是结构化 JSON/Protobuf，无需解析 HTML。

但代价是：**逆向门槛高**，需要懂 Android、加密算法、甚至 ARM 汇编。

---

## 二、原理深入

### 2.1 抓包原理：中间人攻击（MITM）

HTTPS 抓包的本质是自己当"中间人"：

```
正常 HTTPS:
   App <───────────TLS───────────> 服务器

抓包时（中间人）:
   App <──TLS①──> mitmproxy <──TLS②──> 服务器
            ↑                ↑
      App信任mitm的证书    mitm信任服务器证书
      (需手动安装CA证书)

① App 校验 mitmproxy 的证书 → 需在手机安装 mitmproxy CA 证书
② mitmproxy 校验服务器的真证书 → 天然可信
```

**关键点**：Android 7.0+ 默认不信任用户安装的 CA 证书，所以要么：
1. 把证书装到系统目录（需要 root：`/system/etc/security/cacerts/`）；
2. 用 `apktool` 反编译 APK，修改 `AndroidManifest.xml` 加 `networkSecurityConfig` 信任用户证书后重打包；
3. 用 Android < 7.0 的模拟器。

### 2.2 抓不到包的两种情况（SSL Pinning 与 Protobuf）

**SSL Pinning（证书锁定）**：App 在代码里内置了服务器证书指纹，拒绝与 mitmproxy 握手。绕过方法：用 **Frida + objection** 一键 hook：

```bash
pip install frida-tools objection
objection -g com.example.app explore
# 进入交互式后执行：
android sslpinning disable
```

**Protobuf 二进制协议**：抓到的 body 是乱码。流程是：先从 APK 里提取 `.proto` 定义（或反编译分析），再用 `protobuf` 库解析。

### 2.3 签名参数原理（重点！）

绝大多数 App 的请求带有 `sign` 参数，典型生成逻辑：

```
sign = md5( md5(password) + timestamp + "固定盐值salt" )
```

**为什么能逆向？** 因为签名算法必须写在客户端代码里——客户端总要自己算签名，就一定会被提取出来。这是客户端加密的宿命：**加密在端上，密钥必在端上**。

逆向路径：

```
抓包发现 sign 参数
  → jadx 反编译 APK，全局搜索 "sign"
  → 定位到 Java/native 加密函数
  → 分析算法（md5/sha/aes + 拼接顺序 + 盐值）
  → Python 复现
```

### 2.4 APK 反编译基础

APK 本质是一个 ZIP 包：

```
app.apk
├── AndroidManifest.xml  # 二进制的清单文件
├── classes.dex          # Dalvik 字节码（Java/Kotlin 编译产物）
├── lib/                 # native so 库（C/C++，重点加密常在这）
├── res/                 # 资源文件
└── assets/              # 静态资源（有时藏 .proto/.js）
```

工具链分工：

| 工具 | 作用 | 产物 |
|------|------|------|
| jadx | dex → Java 源码 | 可读的 .java（首选） |
| apktool | 反编译资源 + smali | 可回编译（用于重打包） |
| frida | 运行时 hook | 动态调试（对付加固/so） |
| unidbg | 模拟执行 so | 黑盒调用 native 算法 |

**加固识别**：jadx 打开发现只有一两个类（如 `StubApp`），说明被 360/腾讯乐固/梆梆加固了，需要脱壳（frida-dexdump）后才能看到真实代码。

---

