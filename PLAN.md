# 🐍 Python 强化学习 · 完整执行大纲

> **配合《Python 强化学习计划（4个月）》使用**
> 方向：网络安全 · 爬虫反爬 · 自动化运维 · 数据分析 · AI

---

## 第 1 个月：核心能力速成

### 第 1 周 · Python 基础速通

#### Day 1 — 环境搭建 + 基础语法 + 数据类型

- [ ] 1.1a 安装 Python + VS Code + 插件，Hello World
- [ ] 1.1b 交互式解释器基础，print / input
- [ ] 1.1c 注释、PEP 8 基础规范
- [ ] 1.1d 变量命名规则、基本数据类型（int/float/bool/None/str）
- [ ] 1.1e 算术运算、运算符优先级、type() / id()

#### Day 2 — 控制流 + 函数

- [ ] 1.2a if / elif / else、逻辑运算符 and/or/not
- [ ] 1.2b while 循环、break / continue
- [ ] 1.2c for 循环、range()、循环遍历
- [ ] 1.2d 函数定义、参数、返回值、文档字符串
- [ ] 1.2e 位置参数、默认参数、关键字参数、*args / **kwargs
- [ ] 1.2f 斐波那契、素数判断等练习函数

#### Day 3 — 数据结构（list/dict/set/tuple）

- [ ] 1.3a 列表创建、索引、切片、常用方法
- [ ] 1.3b 元组特性、拆包、namedtuple
- [ ] 1.3c 字典创建、get/setdefault、遍历
- [ ] 1.3d 集合创建、集合运算（并/交/差/对称差）
- [ ] 1.3e 数据去重、词频统计小练习

#### Day 4 — 推导式 + Lambda + 内置函数

- [ ] 1.4a 列表推导式（基本 + 条件过滤）
- [ ] 1.4b 字典/集合推导式、嵌套推导式
- [ ] 1.4c lambda 表达式
- [ ] 1.4d map / filter / reduce 高阶函数
- [ ] 1.4e 常用内置函数：sorted / enumerate / zip / any / all

#### Day 5 — 字符串 + 正则表达式

- [ ] 1.5a 字符串方法：split/join/replace/strip/find
- [ ] 1.5b 字符串格式化（f-string / format / %）
- [ ] 1.5c re 模块：match / search / findall
- [ ] 1.5d 元字符、字符集、量词、分组
- [ ] 1.5e 日志解析、邮箱提取小练习

#### Weekend — 项目：命令行学生管理系统

- [ ] 1.6a 项目结构设计、菜单循环框架
- [ ] 1.6b 添加/删除/修改学生信息
- [ ] 1.6c 查询/列表展示、文件持久化

---

### 第 2 周 · 网络编程 + 多线程/多进程

#### Day 1 — Socket 编程（TCP/UDP）

- [ ] 2.1a socket 模块基础、TCP 服务端创建
- [ ] 2.1b TCP 客户端连接、收发数据
- [ ] 2.1c UDP 通信（server/client）
- [ ] 2.1d 处理粘包、缓冲区

#### Day 2 — HTTP 协议 + requests 库

- [ ] 2.2a HTTP 请求/响应结构、状态码
- [ ] 2.2b requests 基本 GET/POST
- [ ] 2.2c headers / params / data 参数
- [ ] 2.2d 响应解析：text / json / content / status_code

#### Day 3 — threading 多线程基础

- [ ] 2.3a threading.Thread 创建与启动
- [ ] 2.3b 守护线程、join 等待
- [ ] 2.3c 线程安全问题、Lock / RLock
- [ ] 2.3d 线程间通信：Condition / Event

#### Day 4 — 线程锁 / 队列 / 线程池

- [ ] 2.4a queue.Queue 生产者-消费者模型
- [ ] 2.4b ThreadPoolExecutor 线程池
- [ ] 2.4c ThreadPoolExecutor 实战：多线程下载

#### Day 5 — multiprocessing + asyncio 基础

- [ ] 2.5a Process / Pool 多进程基础
- [ ] 2.5b 进程间通信：Queue / Pipe
- [ ] 2.5c asyncio 入门：async / await / 事件循环
- [ ] 2.5d asyncio.gather 并发请求
- [ ] 2.5e 线程 vs 进程 vs 协程性能对比

#### Weekend — 项目：多线程端口扫描器

- [ ] 2.6a socket 端口连接检测逻辑
- [ ] 2.6b 多线程并发扫描 + 超时控制
- [ ] 2.6c Banner 抓取 + 服务识别
- [ ] 2.6d CLI 参数解析、结果输出格式化

---

### 第 3 周 · 数据库编程

#### Day 1 — SQLite + sqlite3

- [ ] 3.1a 连接 / 游标 / 建表
- [ ] 3.1b INSERT / SELECT / UPDATE / DELETE
- [ ] 3.1c 参数化查询防 SQL 注入

#### Day 2 — MySQL（pymysql / psycopg2）

- [ ] 3.2a pymysql 连接与 CRUD
- [ ] 3.2b 连接池思想与实践
- [ ] 3.2c ORM 概念初步

#### Day 3 — SQLAlchemy 基础

- [ ] 3.3a SQLAlchemy Engine + Session
- [ ] 3.3b ORM 模型定义、Base / Column / Type
- [ ] 3.3c CRUD 操作、filter / order_by
- [ ] 3.3d 关系映射：ForeignKey / relationship

#### Day 4 — Redis（redis-py）

- [ ] 3.4a Redis 基本数据结构：string / hash / list / set
- [ ] 3.4b 缓存应用：setex / get 过期
- [ ] 3.4c Redis 队列：lpush / brpop

#### Day 5 — 数据库安全（SQL 注入防护）

- [ ] 3.5a 拼接 SQL vs 参数化查询对比
- [ ] 3.5b ORM 自动防注入机制
- [ ] 3.5c 常见注入绕过与防护

#### Weekend — 爬虫数据存储管道

- [ ] 3.6a 数据模型设计（SQLAlchemy）
- [ ] 3.6b 抓取 → 清洗 → 结构化 → 入库全流程
- [ ] 3.6c Redis 缓存去重

---

### 第 4 周 · OOP + 工程化

#### Day 1 — 类与对象、继承/封装/多态

- [ ] 4.1a class 定义、\_\_init\_\_、self、实例化
- [ ] 4.1b 实例方法 / 类方法 / 静态方法
- [ ] 4.1c property 装饰器、封装思想
- [ ] 4.1d 继承、super()、方法重写
- [ ] 4.1e 多态、鸭子类型

#### Day 2 — 文件 I/O + logging

- [ ] 4.2a 文件读写 with 语句、read/write 模式
- [ ] 4.2b pathlib 路径操作
- [ ] 4.2c logging 基础：级别 / Handler / Formatter
- [ ] 4.2d logging 配置文件、日志轮转

#### Day 3 — 异常处理 + 上下文管理器

- [ ] 4.3a try/except/else/finally 完整结构
- [ ] 4.3b raise、自定义异常类
- [ ] 4.3c \_\_enter\_\_ / \_\_exit\_\_ 上下文管理器
- [ ] 4.3d contextlib.contextmanager

#### Day 4 — 包管理 + 虚拟环境

- [ ] 4.4a venv 虚拟环境创建与使用
- [ ] 4.4b uv / poetry 现代工具对比
- [ ] 4.4c requirements.txt、项目结构规范
- [ ] 4.4d 包导入、\_\_init\_\_.py、相对/绝对导入

#### Day 5 — 类型提示 + mypy

- [ ] 4.5a 变量/函数类型注解基础
- [ ] 4.5b typing 模块：Optional / List / Dict / Union
- [ ] 4.5c mypy 静态类型检查

#### Weekend — 项目：Web 漏洞扫描器 v1

- [ ] 4.6a 端口扫描模块（复用 Week2）
- [ ] 4.6b 目录爆破模块
- [ ] 4.6c SQL 注入检测（payload fuzz + 响应分析）
- [ ] 4.6d OOP 架构重构、日志集成

---

## 第 2 个月：数据分析 + AI/人工智能

### 第 5 周 · 数据分析核心

#### Day 1 — NumPy 基础

- [ ] 5.1a ndarray 创建、shape / dtype / ndim
- [ ] 5.1b reshape / flatten / 转置
- [ ] 5.1c 索引、切片、花式索引、布尔索引
- [ ] 5.1d 广播机制 broadcasting
- [ ] 5.1e 通用函数 ufunc、向量化计算

#### Day 2 — Pandas 基础

- [ ] 5.2a Series 创建与操作
- [ ] 5.2b DataFrame 创建（dict / CSV / Excel）
- [ ] 5.2c 数据查看：head / info / describe
- [ ] 5.2d 数据选择：loc / iloc

#### Day 3 — Pandas 进阶

- [ ] 5.3a 数据清洗：dropna / fillna / duplicated
- [ ] 5.3b 分组聚合：groupby / agg
- [ ] 5.3c 合并：merge / concat / join
- [ ] 5.3d 时间序列、resample

#### Day 4 — 数据可视化

- [ ] 5.4a Matplotlib：figure / axes / plot 基础
- [ ] 5.4b 子图、样式定制
- [ ] 5.4c 柱状图 / 饼图 / 直方图 / 散点图
- [ ] 5.4d Seaborn 统计图：box / violin / heatmap

#### Day 5 — 实战：真实数据集分析

- [ ] 5.5a 数据加载与初始探索（EDA）
- [ ] 5.5b 数据清洗与特征工程
- [ ] 5.5c 分析结论 + 可视化报告

#### Weekend — 数据分析完整项目

- [ ] 5.6a 从 CSV/API 拉取数据
- [ ] 5.6b 数据清洗 → 分析 → 可视化
- [ ] 5.6c 输出报告（图表 + 结论）

---

### 第 6 周 · 机器学习入门

#### Day 1 — ML 基础概念

- [ ] 6.1a 监督/无监督/强化学习核心概念
- [ ] 6.1b Scikit-learn 概览、数据集
- [ ] 6.1c 训练集/测试集划分 train_test_split
- [ ] 6.1d 评估指标：准确率 / 精确率 / 召回率 / F1

#### Day 2 — 线性回归 / 逻辑回归

- [ ] 6.2a 线性回归原理 + LinearRegression 实现
- [ ] 6.2b 房价预测完整流程
- [ ] 6.2c 逻辑回归原理 + LogisticRegression
- [ ] 6.2d 二分类实战

#### Day 3 — 决策树 / 随机森林

- [ ] 6.3a 决策树原理 + DecisionTreeClassifier
- [ ] 6.3b 可视化决策树、特征重要性
- [ ] 6.3c 随机森林 RandomForestClassifier
- [ ] 6.3d 与决策树对比分析

#### Day 4 — 无监督学习

- [ ] 6.4a K-Means 聚类原理 + 实现
- [ ] 6.4b 肘部法则选 K 值
- [ ] 6.4c PCA 降维原理 + 实战
- [ ] 6.4d 降维可视化高维数据

#### Day 5 — 模型调优

- [ ] 6.5a 交叉验证 cross_val_score
- [ ] 6.5b GridSearchCV 网格搜索
- [ ] 6.5c 调参前后效果对比

#### Weekend — 完整 ML Pipeline

- [ ] 6.6a 真实数据集加载与探索
- [ ] 6.6b 数据预处理 + 特征工程
- [ ] 6.6c 多模型训练对比
- [ ] 6.6d 调优 + 评估 + 结论报告

---

### 第 7 周 · 深度学习基础 PyTorch

#### Day 1 — PyTorch 基础

- [ ] 7.1a Tensor 创建、属性、运算
- [ ] 7.1b Tensor 索引切片、GPU 切换
- [ ] 7.1c Autograd 自动求导机制
- [ ] 7.1d 用 Autograd 实现梯度下降

#### Day 2 — 神经网络基础

- [ ] 7.2a nn.Module、线性层 Linear
- [ ] 7.2b 激活函数 ReLU / Sigmoid
- [ ] 7.2c 手写 2 层神经网络分类器

#### Day 3 — 训练流程

- [ ] 7.3a DataLoader / Dataset
- [ ] 7.3b Loss 函数：CrossEntropyLoss / MSELoss
- [ ] 7.3c Optimizer：SGD / Adam
- [ ] 7.3d MNIST 手写数字识别完整流程

#### Day 4 — CNN 卷积神经网络

- [ ] 7.4a 卷积层 Conv2d / 池化层 Pooling
- [ ] 7.4b CNN 结构搭建
- [ ] 7.4c CIFAR-10 图像分类

#### Day 5 — 迁移学习

- [ ] 7.5a 预加载模型 torchvision.models
- [ ] 7.5b ResNet / VGG 预训练模型
- [ ] 7.5c 微调 fine-tuning 自定义分类

#### Weekend — 自定义图片分类器

- [ ] 7.6a 数据集准备与预处理
- [ ] 7.6b 模型选择与训练
- [ ] 7.6c 评估 + 预测演示

---

### 第 8 周 · AI 延伸 + 数据+安全交叉

#### Day 1 — NLP 基础

- [ ] 8.1a jieba 分词基础
- [ ] 8.1b TF-IDF 词向量、文本分类

#### Day 2 — 大模型 API 调用

- [ ] 8.2a OpenAI / DeepSeek API 调用
- [ ] 8.2b Prompt Engineering 技巧
- [ ] 8.2c Function Calling 函数调用

#### Day 3 — LangChain 基础

- [ ] 8.3a LangChain 核心组件：LLM / Prompt / Chain
- [ ] 8.3b 文档加载与分割
- [ ] 8.3c RAG 问答系统搭建

#### Day 4 — 异常检测

- [ ] 8.4a Isolation Forest 原理
- [ ] 8.4b 网络流量异常检测实战

#### Day 5 — 数据+爬虫：自动分类

- [ ] 8.5a 爬取内容自动归类 Pipeline
- [ ] 8.5b NLP + 爬虫结合实战

#### Weekend — AI 版日志异常检测器

- [ ] 8.6a 日志数据预处理
- [ ] 8.6b ML 模型训练 + 调优
- [ ] 8.6c 异常告警 + 可视化

---

## 第 3 个月：爬虫与反爬 + 网络安全

### 第 9 周 · 爬虫核心

#### Day 1 — Requests 深入

- [ ] 9.1a Session 会话保持
- [ ] 9.1b Cookie 处理（手动 + 自动）
- [ ] 9.1c Headers 伪装（UA / Referer）
- [ ] 9.1d 模拟登录实战

#### Day 2 — BeautifulSoup / lxml 解析

- [ ] 9.2a BeautifulSoup 基本使用
- [ ] 9.2b find / find_all / CSS 选择器
- [ ] 9.2c lxml XPath 解析
- [ ] 9.2d 数据提取 + 结构化输出

#### Day 3 — Scrapy 框架

- [ ] 9.3a Scrapy 项目创建 + Spider
- [ ] 9.3b Item + Pipeline 数据流
- [ ] 9.3c Middleware 中间件
- [ ] 9.3d 跑通完整 Scrapy 爬虫

#### Day 4 — 动态渲染（Selenium + Playwright）

- [ ] 9.4a Selenium WebDriver 基础
- [ ] 9.4b 元素定位、等待策略
- [ ] 9.4c Playwright 基础
- [ ] 9.4d 抓取 JS 动态渲染页面

#### Day 5 — 爬虫策略

- [ ] 9.5a URL 去重（set / Bloom Filter）
- [ ] 9.5b 断点续爬（requests 中断恢复）
- [ ] 9.5c 限速与礼貌爬取

#### Weekend — 动态网站爬取入库

- [ ] 9.6a 目标分析 + 爬虫编写
- [ ] 9.6b Selenium/PW 渲染抓取
- [ ] 9.6c 数据清洗 + 数据库存储

---

### 第 10 周 · 反爬对抗

#### Day 1 — UA + IP 代理池

- [ ] 10.1a UA 随机切换
- [ ] 10.1b 免费/付费代理获取
- [ ] 10.1c 代理验证 + 可用性检测
- [ ] 10.1d 代理池搭建

#### Day 2 — Headers 伪装 + Cookie

- [ ] 10.2a 完整浏览器 Headers 伪造
- [ ] 10.2b Cookie 池管理
- [ ] 10.2c 绕过简单反爬检测

#### Day 3 — 验证码识别

- [ ] 10.3a tesserocr / ddddocr 基础
- [ ] 10.3b 图形验证码处理流程
- [ ] 10.3c 滑块验证码识别思路

#### Day 4 — JS 加密参数逆向

- [ ] 10.4a 浏览器 DevTools Network 分析
- [ ] 10.4b JS 断点调试、参数定位
- [ ] 10.4c Python 模拟加密参数生成

#### Day 5 — 浏览器指纹规避

- [ ] 10.5a undetected-chromedriver 使用
- [ ] 10.5b 指纹伪装原理
- [ ] 10.5c 过 Cloudflare 实战

#### Weekend — 代理池 + 模拟突破

- [ ] 10.6a 代理池 + undetected-chromedriver 集成
- [ ] 10.6b 目标网站突破全流程
- [ ] 10.6c 数据抓取与稳定性优化

---

### 第 11 周 · 网络安全开发

#### Day 1 — HTTPS 深入 + 抓包分析

- [ ] 11.1a HTTPS/TLS 握手流程
- [ ] 11.1b 证书验证机制
- [ ] 11.1c Fiddler / Wireshark 抓包分析

#### Day 2 — 密码学（hashlib / cryptography）

- [ ] 11.2a hashlib 哈希（MD5 / SHA256）
- [ ] 11.2b 加盐哈希、hmac
- [ ] 11.2c AES 对称加密
- [ ] 11.2d RSA 非对称加密

#### Day 3 — JWT / OAuth2 认证

- [ ] 11.3a JWT 结构（Header / Payload / Signature）
- [ ] 11.3b pyjwt 生成与验证
- [ ] 11.3c JWT 伪造攻击（alg none）
- [ ] 11.3d OAuth2 授权流程理解

#### Day 4 — Web 漏洞 PoC

- [ ] 11.4a SQLi 自动检测脚本
- [ ] 11.4b XSS 检测 PoC
- [ ] 11.4c CSRF / SSRF 检测思路

#### Day 5 — Scapy 数据包构造

- [ ] 11.5a Scapy 基础：IP / TCP 层构造
- [ ] 11.5b 自定义网络包发送与嗅探
- [ ] 11.5c DNS 查询构造

#### Weekend — SQL 注入检测器

- [ ] 11.6a Payload fuzz 生成器
- [ ] 11.6b 响应分析（错误/时间盲注）
- [ ] 11.6c 结果报告输出

---

### 第 12 周 · 安全工具 + 中间人技术

#### Day 1 — 进阶端口扫描

- [ ] 12.1a Nmap 基础命令
- [ ] 12.1b python-nmap 库调用
- [ ] 12.1c Banner 抓取 + 服务版本识别

#### Day 2 — 目录扫描 + 指纹识别

- [ ] 12.2a 字典爆破原理
- [ ] 12.2b 多线程目录扫描器
- [ ] 12.2c Web 指纹识别（headers / body 特征）

#### Day 3 — mitmproxy 代理中间人

- [ ] 12.3a mitmproxy 安装与基本使用
- [ ] 12.3b addon 编写：修改 HTTP 请求/响应
- [ ] 12.3c 流量拦截 + 自动化处理

#### Day 4 — pyshark 流量分析

- [ ] 12.4a PCAP 文件解析
- [ ] 12.4b 协议过滤、统计
- [ ] 12.4c 异常流量检测

#### Day 5 — WebShell 检测

- [ ] 12.5a 常见 WebShell 特征
- [ ] 12.5b 静态特征扫描
- [ ] 12.5c 行为检测思路

#### Weekend — 安全审计工具箱

- [ ] 12.6a 端口扫描 + 目录爆破集成
- [ ] 12.6b SQLi + XSS 检测集成
- [ ] 12.6c 指纹识别
- [ ] 12.6d 报告输出 + CLI 整合

---

## 第 4 个月：自动化运维 + DevOps + 综合实战

### 第 13 周 · 自动化运维

#### Day 1 — 系统管理

- [ ] 13.1a psutil：CPU / 内存 / 磁盘 / 网络监控
- [ ] 13.1b subprocess 执行系统命令
- [ ] 13.1c 系统信息采集脚本

#### Day 2 — 文件处理

- [ ] 13.2a glob 文件匹配
- [ ] 13.2b watchdog 文件变化监控
- [ ] 13.2c 文件自动分类器

#### Day 3 — SSH 远程管理

- [ ] 13.3a paramiko SSH 连接与命令执行
- [ ] 13.3b paramiko SFTP 文件传输
- [ ] 13.3c fabric 批量执行

#### Day 4 — 定时任务

- [ ] 13.4a schedule 库基础
- [ ] 13.4b APScheduler 高级调度
- [ ] 13.4c 定时备份脚本实战

#### Day 5 — 通知告警

- [ ] 13.5a smtplib 邮件告警
- [ ] 13.5b 企业微信/钉钉机器人
- [ ] 13.5c Slack Webhook 通知

#### Weekend — 服务器健康监控 + 告警

- [ ] 13.6a 监控指标采集
- [ ] 13.6b 阈值判定 + 异常检测
- [ ] 13.6c 多渠道告警推送
- [ ] 13.6d 定时调度 + 日志

---

### 第 14 周 · DevOps 基础

#### Day 1 — Docker 容器化

- [ ] 14.1a Docker 基础命令（run / ps / images / exec）
- [ ] 14.1b Dockerfile 编写
- [ ] 14.1c 爬虫/安全工具容器化

#### Day 2 — Docker Compose

- [ ] 14.2a docker-compose.yml 编写
- [ ] 14.2b 多服务编排：App + Redis + DB
- [ ] 14.2c 数据卷与网络配置

#### Day 3 — CI/CD（GitHub Actions）

- [ ] 14.3a GitHub Actions 工作流基础
- [ ] 14.3b 自动测试 workflow
- [ ] 14.3c 自动构建 + 部署

#### Day 4 — Ansible 批量部署

- [ ] 14.4a Ansible 基础：inventory / playbook
- [ ] 14.4b 用 Python 调用 Ansible API
- [ ] 14.4c 批量部署爬虫/安全工具

#### Day 5 — 日志采集（ELK 基础）

- [ ] 14.5a 日志格式标准化
- [ ] 14.5b Filebeat 日志采集
- [ ] 14.5c Elasticsearch + Kibana 基础

#### Weekend — 自动化部署爬虫集群

- [ ] 14.6a Docker Compose 编排
- [ ] 14.6b CI/CD 自动化测试+发布
- [ ] 14.6c 批量部署 + 日志收集

---

### 第 15 周 · 综合项目 I — 企业资产监控系统

- [ ] 15.1 项目设计文档 + 架构图
- [ ] 15.2 爬虫模块：子域名收集
- [ ] 15.3 爬虫模块：端口扫描 + 指纹识别
- [ ] 15.4 安全检测：SQLi + XSS 扫描模块
- [ ] 15.5 定时调度：APScheduler 每日扫描
- [ ] 15.6 数据存储：MySQL + Redis 方案
- [ ] 15.7 数据分析：扫描趋势可视化（Matplotlib）
- [ ] 15.8 自动化：变更检测 + 增量扫描
- [ ] 15.9 通知模块：企业微信/Slack 机器人
- [ ] 15.10 容器化：Docker Compose 一键部署
- [ ] 15.11 测试 + 错误处理优化
- [ ] 15.12 README 文档 + 部署说明

---

### 第 16 周 · 综合项目 II — AI 赋能反爬数据平台

- [ ] 16.1 项目设计文档 + 架构图
- [ ] 16.2 爬虫引擎：代理池 + 浏览器模拟 + JS 解析
- [ ] 16.3 反爬对抗模块：验证码识别（CNN）
- [ ] 16.4 反爬对抗模块：指纹规避 + IP 轮换
- [ ] 16.5 AI：ML 预测反爬策略（响应特征分类）
- [ ] 16.6 AI：NLP 自动提取 + 归类页面内容
- [ ] 16.7 AI：异常检测识别反爬升级
- [ ] 16.8 数据管道：清洗 → 结构化 → 入库
- [ ] 16.9 运维：定时调度 + 失败重试 + 日志
- [ ] 16.10 安全：数据加密 + API 鉴权
- [ ] 16.11 Docker Compose 编排
- [ ] 16.12 CI/CD 自动化
- [ ] 16.13 README 文档 + 架构说明

---

---

## 提交规范

```
<type>(<week>): <简短描述>
```

| 类型 | 含义 |
|------|------|
| `feat` | 新功能 / 新知识点代码 |
| `docs` | 笔记 / 注释 / README |
| `test` | 测试用例 |
| `fix` | 修复 |
| `refactor` | 重构优化 |
| `chore` | 环境配置 |

**示例：**
```
feat(week1): add list comprehensions with condition filtering
- 基本列表推导式 [x for x in range(10)]
- 条件过滤 [x for x in range(10) if x % 2 == 0]
- 嵌套推导式
```

---
