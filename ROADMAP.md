# 🐍 Learn-Python 学习路线图

> **从零到大师的 Python 进阶之路**
> 覆盖：基础 → 进阶 → 网络安全 · 爬虫反爬 · 自动化运维 · 数据分析 · AI
>
> 每天 5~8+ commits（概念 → 图解 → 代码 → 实战 → 练习）
> 周末/假期 8~15+ commits，加速推进

---

## 📊 路线总览

```
Phase 1: Python 基础           ██████████░░░░░░░░░░   Days 001–015  ✅ Day 8 完成
Phase 2: 核心编程概念           ████████████░░░░░░░░   Days 016–030
Phase 3: 面向对象编程           ████████████████░░░░   Days 031–045
Phase 4: 高阶特性              ████████████████████░   Days 046–060
Phase 5: 标准库与生态系统       ████████████████████░   Days 061–075
Phase 6: 实战项目              █████████████████████   Days 076–090
Phase 7: 进阶与性能优化         █████████████████████   Days 091–100
Phase 8: 数据分析与AI/ML       █████████████████████   Days 101–125
Phase 9: 爬虫与反爬对抗        █████████████████████   Days 126–145
Phase 10: 网络安全开发          █████████████████████   Days 146–165
Phase 11: 自动化运维与DevOps    █████████████████████   Days 166–185
Phase 12: 综合实战             █████████████████████   Days 186–200
```

---

## Phase 1: Python 基础（Day 001–015）

### Day 001 — Hello, Python!
- Python 简介与历史
- 环境搭建（安装、IDE、交互式解释器）
- 第一个程序：Hello World
- 代码执行流程原理解析
- **实战**：搭建完整开发环境

### Day 002 — 变量与数据类型
- 变量定义与命名规则
- 动态类型 vs 静态类型原理
- 基本数据类型：int, float, str, bool, None
- `type()` 与 `id()` 函数
- **实战**：个人信息卡片输出

### Day 003 — 字符串深入
- 字符串不可变性原理
- 字符串操作：切片、拼接、格式化
- f-string、format()、%格式化
- 转义字符与原始字符串
- **实战**：文本模板引擎

### Day 004 — 数字与运算
- 整数、浮点数、复数
- 运算符优先级与结合性
- 位运算原理
- 类型转换（隐式/显式）
- **实战**：科学计算器

### Day 005 — 布尔值与条件判断
- Truthy/Falsy 值原理
- 逻辑运算符短路求值
- if/elif/else 结构与嵌套
- 三元表达式
- **实战**：猜数字游戏

### Day 006 — 列表（List）
- 列表创建与索引
- 列表可变性原理（内存角度）
- 切片的高级用法
- 列表方法详解
- **实战**：待办事项管理器

### Day 007 — 元组（Tuple）
- 元组的不可变性原理
- 元组拆包与多返回值
- 命名元组（namedtuple）
- 列表 vs 元组性能对比
- **实战**：坐标系统

### Day 008 — 字典（Dict）
- 哈希表原理与字典实现
- 字典方法与操作
- 字典推导式
- 默认字典（defaultdict）
- **实战**：词频统计器

### Day 009 — 集合（Set）
- 集合数学原理
- 集合运算：并交差补
- 集合 vs 列表性能分析
- frozenset
- **实战**：去重与数据清洗

### Day 010 — 循环（for/while）
- for 循环与迭代器原理
- range() 函数详解
- break/continue/else
- while 循环与无限循环
- **实战**：九九乘法表 + 菱形打印

### Day 011 — 函数基础
- 函数定义与调用
- 参数传递机制（值传递 vs 引用传递）
- 返回值与 None
- 文档字符串（docstring）
- **实战**：计算器函数库

### Day 012 — 函数进阶
- 默认参数陷阱（可变对象问题）
- 关键字参数与可变参数（*args, **kwargs）
- 函数注解（type hints）
- **实战**：通用数据处理器

### Day 013 — 作用域与命名空间
- LEGB 规则详解
- global 与 nonlocal
- 闭包原理
- 变量生命周期
- **实战**：计数器工厂

### Day 014 — 模块与包
- import 机制与模块搜索路径
- `__name__ == '__main__'` 原理
- 包结构与 `__init__.py`
- 相对导入与绝对导入
- **实战**：构建小型工具包

### Day 015 — 阶段项目：Python 工具箱
> 综合运用 Phase 1 所有知识
- 文件管理工具
- 文本处理工具
- 简单数据统计

---

## Phase 2: 核心编程概念（Day 016–030）

### Day 016 — 文件 I/O
- 文件打开模式详解（r/w/a/b/+）
- 上下文管理器与 with 语句
- 文本文件 vs 二进制文件
- **实战**：日志分析器

### Day 017 — 异常处理
- try/except/finally/else 执行流
- 异常链与 raise
- 自定义异常
- **实战**：健壮的输入验证

### Day 018 — 列表推导式
- 推导式内部原理（语法糖 vs 手写循环）
- 嵌套推导式
- 生成器表达式 vs 列表推导式
- 性能对比分析
- **实战**：数据转换流水线

### Day 019 — Lambda 与函数式编程
- Lambda 表达式原理
- map/filter/reduce
- 函数式 vs 命令式编程风格
- **实战**：函数式数据处理

### Day 020 — 递归
- 递归原理（调用栈）
- 基线条件与递归条件
- 尾递归优化（Python 不支持原因）
- 递归 vs 迭代性能对比
- **实战**：文件树遍历

### Day 021 — 迭代器与可迭代对象
- 迭代器协议（`__iter__` / `__next__`）
- for 循环底层实现
- itertools 基础
- **实战**：自定义迭代器

### Day 022 — 生成器
- 生成器函数 vs 生成器表达式
- yield 关键字原理
- 生成器状态与 send()
- 协程基础概念
- **实战**：大文件逐行处理

### Day 023 — 装饰器入门
- 装饰器模式原理
- 简单装饰器实现
- functools.wraps
- **实战**：日志装饰器

### Day 024 — 装饰器进阶
- 带参数的装饰器
- 类装饰器
- 多个装饰器组合
- **实战**：缓存/重试/权限装饰器

### Day 025 — 上下文管理器
- with 语句底层原理
- 基于类的上下文管理器（`__enter__` / `__exit__`）
- contextlib 模块
- **实战**：计时器上下文、数据库连接

### Day 026 — 字符串高级
- 正则表达式入门
- re 模块详解
- 字符串编码（ASCII/Unicode/UTF-8）
- **实战**：日志解析器 + 数据提取

### Day 027 — 时间与日期
- datetime 模块
- time 模块与时间戳
- 时区处理（pytz/zoneinfo）
- **实战**：日历生成器

### Day 028 — 数据结构综合
- 栈、队列的实现
- 堆（heapq）
- bisect 模块
- **实战**：表达式求值

### Day 029 — 算法入门
- 排序算法（冒泡/选择/插入/快排/归并）
- 搜索算法（线性/二分）
- 时间复杂度与大 O 表示法
- **实战**：排序可视化

### Day 030 — 阶段项目：命令行工具
> 综合运用 Phase 1–2 知识
- argparse/click 构建 CLI
- 实用小工具集合

---

## Phase 3: 面向对象编程（Day 031–045）

### Day 031 — 类与对象
- 面向对象三大特征
- 类定义与实例化
- `__init__` 与构造过程
- **实战**：图书管理系统基础

### Day 032 — 属性与方法
- 实例属性 vs 类属性
- 实例方法/类方法/静态方法
- property 装饰器与 getter/setter
- **实战**：银行账户类

### Day 033 — 继承
- 单继承与 MRO（方法解析顺序）
- C3 线性化算法
- super() 原理
- **实战**：形状层次结构

### Day 034 — 多态与鸭子类型
- 多态概念
- 鸭子类型与 EAFP 风格
- 抽象基类（ABC）
- **实战**：插件系统

### Day 035 — 特殊方法（Magic Methods）
- `__str__` / `__repr__`
- `__len__` / `__getitem__`
- 运算符重载
- `__call__` 与可调用对象
- **实战**：自定义向量类

### Day 036 — 封装与数据隐藏
- 名称改写（Name Mangling）
- 私有属性约定
- 属性访问控制
- **实战**：安全的 API 封装

### Day 037 — 组合与聚合
- 组合 vs 继承
- 依赖注入
- 设计原则：优先组合而非继承
- **实战**：汽车-引擎-轮胎模型

### Day 038 — 设计模式（创建型）
- 单例模式
- 工厂模式
- 建造者模式
- **实战**：配置管理器

### Day 039 — 设计模式（结构型）
- 适配器模式
- 代理模式
- 装饰器模式（对比 Python 装饰器）
- **实战**：缓存代理

### Day 040 — 设计模式（行为型）
- 观察者模式
- 策略模式
- 命令模式
- **实战**：事件系统

### Day 041 — SOLID 原则
- SOLID 五大原则详解
- Python 中的实际应用
- 设计原则 vs 设计模式
- **实战**：重构糟糕的代码

### Day 042 — 类型提示与检查
- typing 模块详解
- 泛型与 TypeVar
- 运行时类型检查（pydantic）
- **实战**：类型安全的 API

### Day 043 — 数据类（dataclass）
- dataclass 原理
- field() 与高级配置
- 与 namedtuple/普通类的对比
- **实战**：配置管理系统

### Day 044 — 枚举与常量
- Enum 与 IntEnum
- 枚举成员与唯一性
- auto() 与自定义值
- **实战**：状态机

### Day 045 — 阶段项目：面向对象实战
> 综合运用 Phase 3 知识
- 简易 ORM 框架
- REST API 客户端封装

---

## Phase 4: 高阶特性（Day 046–060）

### Day 046 — 元类（Metaclass）
- 类也是对象
- type() 动态创建类
- 自定义元类
- **实战**：ORM 字段验证

### Day 047 — 描述符（Descriptor）
- 描述符协议
- `__get__` / `__set__` / `__delete__`
- property 底层实现
- **实战**：类型校验描述符

### Day 048 — 混入（Mixin）
- Mixin 设计模式
- 多重继承与 Mixin
- Mixin 最佳实践
- **实战**：序列化 Mixin、日志 Mixin

### Day 049 — 抽象基类（ABC）
- ABCMeta 与 register()
- 虚拟子类
- 自定义抽象基类
- **实战**：可迭代集合框架

### Day 050 — 槽（\_\_slots\_\_）
- `__slots__` 内存优化原理
- `__slots__` vs 普通类性能对比
- 与继承的关系
- **实战**：百万级数据对象优化

### Day 051 — 弱引用（weakref）
- 弱引用原理
- 循环引用与垃圾回收
- WeakSet/WeakValueDictionary
- **实战**：对象缓存与回调

### Day 052 — 深拷贝与浅拷贝
- 拷贝机制原理
- copy 模块详解
- 自定义拷贝行为（`__copy__` / `__deepcopy__`）
- **实战**：快照与回滚

### Day 053 — 内存管理与垃圾回收
- 引用计数原理
- 标记-清除与分代回收
- gc 模块详解
- 内存泄漏排查
- **实战**：内存分析工具

### Day 054 — 并发入门：线程
- GIL 原理与影响
- threading 模块
- 线程安全与锁
- **实战**：并发下载器

### Day 055 — 并发进阶：进程
- multiprocessing 模块
- 进程间通信（Queue/Pipe）
- 进程池（Pool）
- **实战**：CPU 密集型计算加速

### Day 056 — 异步编程（asyncio）
- 事件循环原理
- async/await 关键字
- Task/Future/Coroutine
- **实战**：异步 Web 爬虫

### Day 057 — asyncio 进阶
- 异步上下文管理器
- 异步迭代器与生成器
- aiohttp 实战
- **实战**：异步 API 调用

### Day 058 — 并发模型对比
- 线程 vs 进程 vs 协程
- 各自适用场景与性能瓶颈
- 不同 GIL 策略
- **实战**：三种模型基准测试

### Day 059 — C 扩展与性能优化
- Cython 入门
- ctypes 与 CFFI
- Numba JIT 编译
- **实战**：数值计算加速

### Day 060 — 阶段项目：高性能计算
> 综合运用 Phase 4 知识
- 并发数据爬虫
- 高性能图像处理

---

## Phase 5: 标准库与生态系统（Day 061–075）

### Day 061 — 文件与路径操作
- os 模块
- pathlib（现代方式）
- shutil 高级文件操作
- **实战**：文件同步工具

### Day 062 — 数据序列化
- JSON 序列化（json 模块）
- pickle/msgpack
- YAML 配置
- **实战**：配置文件解析器

### Day 063 — CSV 与 Excel
- csv 模块
- openpyxl/xlrd
- pandas 基础读取
- **实战**：报表生成器

### Day 064 — 网络请求
- urllib vs requests
- HTTP 协议基础
- Session/Cookie 管理
- **实战**：天气预报 CLI

### Day 065 — Web 框架入门
- Flask 基础
- 路由、模板、静态文件
- 请求与响应
- **实战**：个人博客

### Day 066 — Flask 进阶
- 数据库集成（SQLAlchemy）
- 用户认证
- RESTful API
- **实战**：TODO API

### Day 067 — FastAPI 入门
- FastAPI 特性与优势
- Pydantic 模型
- 自动文档生成
- **实战**：图书管理 API

### Day 068 — 数据库基础
- SQLite3 模块
- SQL 基础
- 连接池与事务
- **实战**：通讯录管理系统

### Day 069 — ORM 深入（SQLAlchemy）
- ORM 原理
- 模型定义与关系映射
- 查询 API 与高级用法
- **实战**：电商数据模型

### Day 070 — 测试基础
- unittest 框架
- pytest 实战
- Mock 与 Fixture
- 测试覆盖率
- **实战**：API 测试套件

### Day 071 — 日志与调试
- logging 模块详解
- 日志级别与配置
- pdb 调试器
- **实战**：生产级日志配置

### Day 072 — 正则表达式深入
- 正则引擎原理（NFA vs DFA）
- 前瞻/后顾断言
- 贪婪 vs 非贪婪
- **实战**：HTML 解析器

### Day 073 — 包管理
- pip 与 requirements.txt
- Poetry/PDM 现代包管理
- 虚拟环境原理（venv/conda）
- **实战**：发布自己的包到 PyPI

### Day 074 — 配置与环境
- 环境变量管理（python-dotenv）
- 配置库对比（PyYAML/toml/configparser）
- 环境隔离原理
- **实战**：多环境部署配置

### Day 075 — 阶段项目：全栈实战
> 综合运用 Phase 1–5 知识
- REST API 后端
- 数据库集成
- 测试与部署

---

## Phase 6: 实战项目（Day 076–090）

### Day 076–078 — 项目一：Web 爬虫系统
- Scrapy 框架
- 请求调度与去重
- 数据管道（Pipeline）
- 反爬策略应对
- **产出**：电商价格监控系统

### Day 079–081 — 项目二：数据分析仪表盘
- NumPy 基础
- Pandas 数据分析
- Matplotlib/Plotly 可视化
- **产出**：股票数据分析看板

### Day 082–084 — 项目三：自动化运维工具
- Fabric/Paramiko
- 远程执行与部署
- 监控告警系统
- **产出**：服务器巡检工具

### Day 085–087 — 项目四：聊天机器人
- WebSocket 通信
- NLP 基础（NLTK/spaCy）
- 状态机对话管理
- **产出**：客服聊天机器人

### Day 088–090 — 项目五：Python 游戏
- Pygame 框架
- 游戏循环与事件
- 碰撞检测与动画
- **产出**：飞机大战 / 贪吃蛇

---

## Phase 7: 进阶与性能优化（Day 091–100）

### Day 091 — 性能剖析
- cProfile 与 line_profiler
- 性能瓶颈定位
- memory_profiler
- **实战**：优化真实代码

### Day 092 — 代码优化技巧
- 数据结构选择优化
- 循环优化与向量化
- 懒加载与缓存
- **实战**：将慢代码提速 10 倍

### Day 093 — 网络编程深入
- socket 编程
- 异步网络框架
- HTTP/2 与 HTTP/3
- **实战**：自定义协议服务器

### Day 094 — 安全编程
- 输入验证与注入防护
- 密码学基础（hashlib/cryptography）
- 安全最佳实践
- **实战**：安全认证系统

### Day 095 — 函数式编程深入
- functools 模块详解
- 惰性求值与柯里化
- 不可变数据结构（pyrsistent）
- **实战**：函数式数据处理管道

### Day 096 — AST 与代码分析
- 抽象语法树（ast 模块）
- 代码生成与变换
- 静态分析工具实现
- **实战**：自定义 Linter

### Day 097 — 领域特定语言（DSL）
- DSL 设计模式
- Python 元编程构建 DSL
- **实战**：配置 DSL、规则引擎

### Day 098 — Python 内部机制
- Python 字节码（dis 模块）
- CPython 虚拟机结构
- PyObject 与类型系统
- **实战**：字节码分析器

### Day 099 — 扩展 Python
- Cython 深入
- Pybind11
- 嵌入 Python 到 C++
- **实战**：Python + C++ 混合编程

### Day 100 — 阶段里程碑：知识体系梳理
- 回顾 1-100 天知识图谱
- 查漏补缺
- 选择后续深耕方向

---

## Phase 8: 数据分析与 AI/ML（Day 101–125）

> 从数据分析到机器学习、深度学习、大模型应用

### Day 101 — NumPy 核心
- ndarray 创建、shape/dtype/ndim
- 广播机制 (broadcasting)
- 通用函数 ufunc、向量化计算
- 线性代数基础：linalg
- **实战**：矩阵运算与性能对比

### Day 102 — Pandas 核心
- Series/DataFrame 创建与操作
- 数据查看：head/info/describe
- 数据选择：loc/iloc/布尔索引
- **实战**：加载 CSV 数据探索

### Day 103 — Pandas 进阶
- 数据清洗：dropna/fillna/duplicated
- 分组聚合：groupby/agg/transform
- 合并连接：merge/concat/join
- 时间序列：resample/rolling
- **实战**：电商销售数据分析

### Day 104 — 数据可视化
- Matplotlib：figure/axes/plot 定制
- 柱状图/饼图/直方图/散点图/箱线图
- Seaborn：box/violin/heatmap/pairplot
- **实战**：数据探索性分析报告

### Day 105 — 阶段项目：数据分析 Pipeline
- 从 API/CSV 拉取数据
- 清洗 → 分析 → 可视化
- 输出完整分析报告

### Day 106 — 机器学习基础
- 监督/无监督/强化学习概念
- Scikit-learn 概览
- 数据集拆分 train_test_split
- 评估指标：准确率/精确率/召回率/F1
- **实战**：完整 ML 流程初体验

### Day 107 — 线性回归
- 线性回归原理与假设
- LinearRegression 实现
- 评估：MSE/R²
- **实战**：房价预测

### Day 108 — 逻辑回归与分类
- 逻辑回归原理
- LogisticRegression + 多分类
- 混淆矩阵与 ROC 曲线
- **实战**：二分类任务

### Day 109 — 决策树与随机森林
- 决策树原理（信息增益/基尼系数）
- 可视化决策树
- 随机森林 Bagging 集成
- 特征重要性分析
- **实战**：信用风险评估

### Day 110 — SVM 与 KNN
- SVM 原理（间隔/核技巧）
- KNN 原理与 K 值选择
- 不同算法对比
- **实战**：手写数字识别

### Day 111 — 无监督学习
- K-Means 聚类原理
- 肘部法则选 K
- PCA 降维原理与可视化
- **实战**：客户分群

### Day 112 — 模型调优与 Pipeline
- 交叉验证 cross_val_score
- 网格搜索 GridSearchCV
- 特征工程与 Pipeline
- 保存与加载模型（joblib）
- **实战**：完整的 ML Pipeline

### Day 113 — PyTorch 基础
- Tensor 创建与运算
- GPU 切换（cuda）
- Autograd 自动求导
- 用 Autograd 实现梯度下降
- **实战**：线性回归手动实现

### Day 114 — 神经网络入门
- nn.Module 与线性层
- 激活函数：ReLU/Sigmoid/Tanh
- 损失函数：CrossEntropyLoss/MSELoss
- 优化器：SGD/Adam
- **实战**：手写 2 层网络分类器

### Day 115 — 训练流程
- DataLoader/Dataset 数据加载
- 完整训练循环
- 模型保存与加载
- **实战**：MNIST 手写数字识别

### Day 116 — CNN 卷积神经网络
- 卷积层 Conv2d/池化层原理
- CNN 结构设计
- **实战**：CIFAR-10 图像分类

### Day 117 — 迁移学习
- 预训练模型（ResNet/VGG）
- 微调（fine-tuning）
- 特征提取 vs 微调
- **实战**：自定义图片分类

### Day 118 — NLP 基础
- 分词（jieba）
- TF-IDF 文本表示
- Word Embedding 概念
- **实战**：文本分类

### Day 119 — 大模型 API 调用
- OpenAI/DeepSeek API 调用
- Prompt Engineering 技巧
- Function Calling
- **实战**：智能助手

### Day 120 — LangChain 与 RAG
- LangChain 核心组件
- 文档加载、分割与向量化
- RAG 问答系统
- **实战**：本地文档问答机器人

### Day 121 — 异常检测与安全交叉
- Isolation Forest 异常检测
- 网络流量异常检测实战
- **实战**：日志异常检测器

### Day 122 — 推荐系统基础
- 协同过滤原理
- 基于物品/用户的推荐
- **实战**：电影推荐系统

### Day 123 — 模型部署
- Flask/FastAPI 模型服务
- ONNX 模型导出
- Docker 容器化模型
- **实战**：部署 ML API

### Day 124 — 时间序列预测
- 时间序列分解
- ARIMA/Prophet 基础
- **实战**：股票/销量预测

### Day 125 — 阶段项目：综合 AI 应用
- 端到端 ML/DL 项目
- 数据→训练→评估→部署

---

## Phase 9: 爬虫与反爬对抗（Day 126–145）

### Day 126 — Requests 深入
- Session 会话保持
- Cookie 手动/自动管理
- Headers 伪装（UA/Referer）
- **实战**：模拟登录

### Day 127 — BeautifulSoup / lxml 解析
- HTML 解析原理
- find/find_all/CSS 选择器
- XPath 解析
- **实战**：提取结构化数据

### Day 128 — Scrapy 框架
- Scrapy 项目结构
- Spider/Item/Pipeline
- Middleware 中间件
- **实战**：完整爬虫流程

### Day 129 — 动态渲染（Selenium）
- Selenium WebDriver 原理
- 元素定位与等待策略
- 无头浏览器
- **实战**：抓取 JS 渲染页面

### Day 130 — Playwright 现代爬虫
- Playwright vs Selenium 对比
- 自动等待与截图
- 多浏览器支持
- **实战**：反爬网站突破

### Day 131 — 爬虫策略
- URL 去重（set/Bloom Filter）
- 断点续爬
- 限速与礼貌爬取
- **实战**：稳定大规模爬虫

### Day 132 — 代理池搭建
- 免费/付费代理获取
- 代理验证与可用性检测
- 代理池架构
- **实战**：高匿名代理池

### Day 133 — UA 与 Cookie 池
- 浏览器指纹 UA 随机化
- Cookie 持久化与轮换
- **实战**：绕过反爬检测

### Day 134 — 验证码识别
- 图形验证码处理（ddddocr）
- 滑块验证码识别思路
- OCR tesserocr 基础
- **实战**：自动化验证码处理

### Day 135 — JS 逆向入门
- 浏览器 DevTools Network 分析
- JS 混淆与反混淆基础
- AST 初步
- **实战**：定位加密参数

### Day 136 — JS 逆向进阶
- Hook 技术
- 堆栈回溯
- 补环境与 Selenium 自动化
- **实战**：逆向常见反爬参数

### Day 137 — 浏览器指纹规避
- Canvas/WebGL 指纹
- undetected-chromedriver
- 过 Cloudflare 实战
- **实战**：突破 WAF

### Day 138 — Scrapy 分布式
- Scrapy-Redis 分布式架构
- 请求调度与去重
- **实战**：分布式爬虫集群

### Day 139 — 数据存储管道
- 爬虫数据清洗与结构化
- MySQL/Redis/MongoDB 存储
- 数据质量控制
- **实战**：完整的数据管道

### Day 140 — App 爬虫基础
- 抓包（mitmproxy/Fiddler）
- 反编译 APK 基础
- 协议模拟
- **实战**：App 数据抓取

### Day 141 — 爬虫监控与告警
- 爬虫异常监控
- 任务失败重试
- 通知告警（钉钉/企微）
- **实战**：爬虫健康监控

### Day 142 — 爬虫法律与规范
- robots.txt 规范
- 数据合规与反爬法律边界
- 爬虫职业道德

### Day 143–145 — 阶段项目：全栈反爬突破系统
- 代理池 + 浏览器模拟 + JS 解析
- 验证码处理 + 数据清洗
- 定时调度 + 告警
- 容器化部署

---

## Phase 10: 网络安全开发（Day 146–165）

### Day 146 — HTTPS 与抓包
- HTTPS/TLS 握手流程
- 证书验证机制
- 抓包工具（Wireshark/Fiddler）
- **实战**：分析 HTTPS 流量

### Day 147 — 密码学基础
- hashlib 哈希（MD5/SHA256）
- 加盐哈希与 HMAC
- **实战**：文件完整性校验

### Day 148 — 对称与非对称加密
- AES 对称加密
- RSA 非对称加密
- 混合加密方案
- **实战**：安全通信工具

### Day 149 — JWT 安全
- JWT 结构（Header/Payload/Signature）
- pyjwt 生成与验证
- JWT 攻击：alg none/弱密钥
- **实战**：JWT 安全检测

### Day 150 — OAuth2 与认证安全
- OAuth2 授权流程
- CSRF 攻击与防护
- SSRF 漏洞检测
- **实战**：认证系统安全审计

### Day 151 — SQL 注入原理
- SQL 注入类型
- 参数化查询防护
- ORM 自动防注入机制
- **实战**：SQL 注入检测脚本

### Day 152 — XSS 与 Web 漏洞
- XSS 反射型/存储型/DOM 型
- CSRF 攻击原理
- **实战**：XSS 检测 PoC

### Day 153 — 端口扫描进阶
- Nmap 基础命令
- python-nmap 库
- Banner 抓取与服务识别
- **实战**：自动化端口扫描器

### Day 154 — 目录扫描与指纹识别
- 字典爆破原理
- 多线程目录扫描器
- Web 指纹识别
- **实战**：资产发现工具

### Day 155 — mitmproxy 中间人
- mitmproxy 安装与使用
- 流量拦截与修改
- Addon 编写
- **实战**：自动化流量处理

### Day 156 — Scapy 数据包构造
- Scapy 基础（IP/TCP 层）
- 自定义网络包发送
- 数据包嗅探与分析
- **实战**：网络探测工具

### Day 157 — pyshark 流量分析
- PCAP 文件解析
- 协议过滤与统计
- 异常流量检测
- **实战**：流量分析器

### Day 158 — WebShell 检测
- 常见 WebShell 特征
- 静态特征扫描
- 行为检测思路
- **实战**：WebShell 扫描器

### Day 159 — 安全审计工具
- 漏洞扫描器设计
- 结果报告生成
- CLI 整合
- **实战**：审计工具箱

### Day 160 — 日志安全分析
- 日志格式标准化
- 异常登录检测
- 暴力破解识别
- **实战**：安全日志分析器

### Day 161 — 渗透测试框架
- 渗透测试流程
- 信息收集 → 漏洞检测 → 利用
- Metasploit 基础
- **实战**：自动化扫描框架

### Day 162–165 — 阶段项目：安全审计工具箱
- 端口扫描 + 目录爆破 + 指纹识别
- SQLi + XSS 检测集成
- 代理中间人 + 流量分析
- 报告生成 + Docker 部署

---

## Phase 11: 自动化运维与 DevOps（Day 166–185）

### Day 166 — 系统监控（psutil）
- CPU/内存/磁盘/网络监控
- 进程管理
- 系统信息采集
- **实战**：系统监控脚本

### Day 167 — 文件监控（watchdog）
- 文件事件监听
- 文件自动分类
- **实战**：文件变化监控工具

### Day 168 — SSH 远程管理
- paramiko SSH 连接
- 远程命令执行
- SFTP 文件传输
- **实战**：批量运维工具

### Day 169 — Fabric 批量执行
- Fabric 任务定义
- 多服务器并行执行
- 错误处理
- **实战**：批量部署脚本

### Day 170 — 定时任务
- schedule 库
- APScheduler 高级调度
- 任务持久化
- **实战**：定时备份系统

### Day 171 — 通知告警
- smtplib 邮件告警
- 企业微信/钉钉机器人
- Slack Webhook
- **实战**：多渠道告警

### Day 172 — Docker 容器化
- Docker 基础命令
- Dockerfile 编写
- 构建与运行
- **实战**：容器化 Python 应用

### Day 173 — Docker Compose
- docker-compose.yml 编写
- 多服务编排（App+Redis+DB）
- 数据卷与网络
- **实战**：全栈应用编排

### Day 174 — CI/CD（GitHub Actions）
- Workflow 基础语法
- 自动测试流程
- 自动构建与部署
- **实战**：完整的 CI/CD 管道

### Day 175 — Ansible 批量部署
- Inventory / Playbook
- 模块化任务
- Python 调用 Ansible API
- **实战**：批量部署爬虫集群

### Day 176 — ELK 日志系统
- 日志格式标准化
- Filebeat 日志采集
- Elasticsearch 存储
- Kibana 可视化
- **实战**：集中式日志平台

### Day 177 — Prometheus + Grafana
- 监控指标暴露
- Prometheus 采集
- Grafana 看板
- **实战**：应用监控看板

### Day 178 — 容器编排（K8s 入门）
- Kubernetes 核心概念
- Pod/Deployment/Service
- kubectl 基础
- **实战**：部署 Python 应用到 K8s

### Day 179 — Terraform 基础设施
- IaC 基础设施即代码
- Terraform 基础
- **实战**：云资源管理

### Day 180 — 自动化测试
- 单元测试 pytest
- 集成测试
- 端到端测试
- 测试覆盖率
- **实战**：自动化测试套件

### Day 181 — 发布管理
- 语义化版本
- Changelog 规范
- PyPI 发布流程
- **实战**：自动化发布流水线

### Day 182–185 — 阶段项目：自动化运维平台
- 服务器监控 + 告警
- Docker + CI/CD 自动化
- 日志收集 + 可视化
- 一键部署

---

## Phase 12: 综合实战（Day 186–200）

### Day 186–190 — 综合项目 I：企业资产监控系统
> 融合：爬虫 + 安全 + 自动化 + 数据

- 爬虫模块：子域名收集、端口扫描、指纹识别
- 安全检测：SQLi + XSS 自动扫描
- 数据分析：扫描结果趋势可视化
- 自动化：定时扫描、变更检测、增量扫描
- 存储：MySQL + Redis
- 通知：企业微信/Slack 机器人
- 容器化：Docker Compose 一键部署

### Day 191–195 — 综合项目 II：AI 赋能反爬数据平台
> 融合：爬虫 + 反爬 + AI + 运维

- 爬虫引擎：代理池 + 浏览器模拟 + JS 解析
- 反爬对抗：验证码识别 + 指纹规避 + IP 轮换
- AI 增强：ML 预测反爬策略、NLP 内容归类
- 数据管道：清洗 → 结构化 → 入库
- 运维：定时调度 + 失败重试 + 日志告警
- 安全：数据加密 + API 鉴权
- Docker + CI/CD 部署

### Day 196–200 — 总复习与职业发展
- 200 天知识体系全景回顾
- 面试准备：算法 + 八股文 + 项目经验
- 开源贡献：参与 CPython / 知名项目
- 技术写作：输出技术博客
- 持续成长路径规划

---

## ⏱ 执行节奏

| 时间段 | 日均 commits | 节奏说明 |
|--------|-------------|---------|
| 工作日 | 5~8 | 每天 1 个 Day，概念+图解+代码+实战+练习 |
| 周末 | 8~15 | 1.5~2 个 Day，加速推进 |
| 小长假 | 10~13/天 | 半周~1 周内容 |
| 长假 | 12~15/天 | 1~2 周内容 |

## 📐 每日内容结构

```
days/day-XXX-topic/
├── README.md          ← 本章完整学习内容
├── concepts.md        ← 核心概念与定义
├── code/              ← 代码示例目录
│   ├── example-01.py
│   ├── example-02.py
│   └── ...
├── diagrams/          ← Mermaid / ASCII 图解
│   └── ...
└── exercises/         ← 练习题
    └── ...
```

## 📝 提交流程

```
<type>(<scope>): <描述>
```

| 类型 | 含义 |
|------|------|
| `docs(concept)` | 概念解释与定义 |
| `feat(diagram)` | 原理解析示意图 |
| `docs(example)` | 基础用法代码示例 |
| `feat(example)` | 实战案例代码 |
| `docs(exercise)` | 练习题与答案 |
| `feat` | Day 汇总 |
| `chore(progress)` | 更新学习进度 |

**示例：**
```
docs(concept): 添加列表概念解释与定义
feat(diagram): 添加列表底层原理与操作复杂度图解
docs(example): 添加列表基础用法与操作演示代码
feat(example): 添加实战案例-待办事项管理器
docs(exercise): 添加列表练习题与检查清单
chore(progress): 更新学习进度至 Day 6
```

## 📚 推荐资源

| 方向 | 资源 |
|------|------|
| Python 基础 | 《Python编程：从入门到实践》 |
| 数据结构 | 《算法图解》/ LeetCode |
| 数据分析 | 《利用Python进行数据分析》 |
| 机器学习 | 《Hands-On Machine Learning》 |
| 深度学习 | 《Dive into Deep Learning》(d2l.ai) |
| 爬虫 | 《Python3网络爬虫开发实战》(崔庆才) |
| 安全 | PortSwigger Web Security Academy |
| DevOps | Docker/K8s 官方文档 |

---

> *"The best way to learn is to build." — 动手是最好的学习方式*
> 
> 路径：`~/code/Learn-Python/` · 已学到 Day 6
