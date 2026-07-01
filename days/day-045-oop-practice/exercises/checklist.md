# Day 045 - 练习清单

## 📋 学习检查表

### ORM 框架
- [ ] 理解 ORM（对象关系映射）的概念
- [ ] 掌握 Field 字段类的设计
- [ ] 理解元类（metaclass）在 ORM 中的作用
- [ ] 掌握 Model 基类的实现
- [ ] 能够使用 ORM 框架进行基本的 CRUD 操作
- [ ] 理解字段验证机制

### REST API 客户端
- [ ] 理解 REST API 的基本概念
- [ ] 掌握类封装 HTTP 请求的方法
- [ ] 理解 Session 的作用和优势
- [ ] 掌握重试机制的实现
- [ ] 能够设计业务 API 封装
- [ ] 理解错误处理的最佳实践

### 学生管理系统
- [ ] 掌握抽象基类的使用
- [ ] 理解属性装饰器（property）的应用
- [ ] 掌握组合模式的设计
- [ ] 理解多态的实际应用
- [ ] 能够设计完整的类层次结构
- [ ] 掌握数据验证和类型检查

### OOP 综合应用
- [ ] 能够根据需求选择合适的 OOP 技术
- [ ] 理解继承与组合的选择
- [ ] 掌握封装的最佳实践
- [ ] 能够设计可扩展的类结构
- [ ] 理解魔术方法的应用

---

## 🎯 练习题

### 练习 1：扩展 ORM 框架（⭐⭐）

**任务**：为 ORM 框架添加 `DateTimeField` 字段类型

**要求**：
1. 实现 `DateTimeField` 类，继承自 `Field`
2. 支持自动设置创建时间（`auto_now_add`）
3. 支持自动更新时间（`auto_now`）
4. 添加时间格式验证

**参考代码**：
```python
class DateTimeField(Field):
    def __init__(self, auto_now_add=False, auto_now=False, **kwargs):
        super().__init__(**kwargs)
        self.auto_now_add = auto_now_add
        self.auto_now = auto_now

    def validate(self, value):
        # 验证时间格式
        pass
```

---

### 练习 2：API 客户端增强（⭐⭐）

**任务**：为 REST API 客户端添加认证管理功能

**要求**：
1. 支持多种认证方式（API Key、Bearer Token、Basic Auth）
2. 实现 Token 自动刷新机制
3. 添加请求频率限制（Rate Limiting）
4. 实现请求缓存

**提示**：
- 使用策略模式实现不同认证方式
- 使用装饰器实现 Token 刷新
- 使用字典实现简单的缓存

---

### 练习 3：学生系统扩展（⭐⭐⭐）

**任务**：为学生管理系统添加成绩分析功能

**要求**：
1. 实现成绩统计类（`GradeAnalyzer`）
2. 支持计算平均分、中位数、标准差
3. 实现成绩分布统计（优秀/良好/中等/及格/不及格）
4. 生成成绩报告（文本格式）
5. 支持对比分析（班级间、学生间）

**示例输出**：
```
成绩报告 - Python一班
========================
班级平均分: 82.50
中位数: 85.00
标准差: 12.34
及格率: 80.0%
优秀率: 20.0%

成绩分布:
  优秀 (90-100): 2 人 (20%)
  良好 (80-89): 3 人 (30%)
  中等 (70-79): 2 人 (20%)
  及格 (60-69): 1 人 (10%)
  不及格 (<60): 2 人 (20%)
```

---

### 练习 4：ORM + API 集成（⭐⭐⭐）

**任务**：将 ORM 框架与 REST API 客户端集成

**要求**：
1. 实现 `RemoteModel` 类，支持远程数据同步
2. 支持本地缓存 + 远程同步
3. 实现离线模式（本地操作 + 上线同步）
4. 添加数据冲突解决策略

**架构设计**：
```
┌─────────────────────────────────────┐
│           Application              │
├─────────────────────────────────────┤
│         RemoteModel                │
│  ┌───────────┐  ┌───────────────┐  │
│  │   ORM     │  │   API Client  │  │
│  │  (Local)  │  │   (Remote)    │  │
│  └───────────┘  └───────────────┘  │
├─────────────────────────────────────┤
│         Sync Manager               │
│  ┌──────────────────────────────┐  │
│  │   Conflict Resolution        │  │
│  │   Cache Manager              │  │
│  │   Queue Manager              │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

### 练习 5：设计模式应用（⭐⭐⭐⭐）

**任务**：使用设计模式重构学生管理系统

**要求**：
1. 使用**观察者模式**实现成绩通知系统
2. 使用**策略模式**实现不同的成绩计算方式
3. 使用**工厂模式**创建不同类型的用户
4. 使用**单例模式**实现全局配置管理

**示例代码**：
```python
# 观察者模式
class GradeObserver(ABC):
    @abstractmethod
    def on_grade_added(self, student, subject, score):
        pass

class NotificationService(GradeObserver):
    def on_grade_added(self, student, subject, score):
        print(f"通知: {student.name} 的 {subject} 成绩已更新为 {score}")

# 策略模式
class GradingStrategy(ABC):
    @abstractmethod
    def calculate(self, scores: List[float]) -> float:
        pass

class AverageStrategy(GradingStrategy):
    def calculate(self, scores):
        return sum(scores) / len(scores)

class WeightedStrategy(GradingStrategy):
    def calculate(self, scores):
        # 加权平均
        pass
```

---

### 练习 6：性能优化（⭐⭐⭐⭐⭐）

**任务**：优化学生管理系统的性能

**要求**：
1. 实现数据分页加载
2. 添加查询缓存机制
3. 优化内存使用（使用 `__slots__`）
4. 实现懒加载（Lazy Loading）
5. 添加性能分析工具

**优化点**：
- 使用 `__slots__` 减少内存占用
- 实现查询结果缓存
- 使用生成器减少内存占用
- 添加性能计时装饰器

---

## ✅ 完成标准

### 基础要求
- [ ] 所有代码示例能够正常运行
- [ ] 理解每个代码示例的核心概念
- [ ] 能够解释代码的设计思路

### 进阶要求
- [ ] 完成至少 2 个练习题
- [ ] 代码能够处理边界情况
- [ ] 有适当的错误处理

### 挑战要求
- [ ] 完成至少 1 个高级练习题
- [ ] 代码符合 PEP 8 规范
- [ ] 有完整的文档字符串

---

## 📚 扩展资源

### 阅读推荐
1. **《Python 面向对象编程》** - 深入理解 OOP 概念
2. **《流畅的 Python》** - 学习 Python 高级特性
3. **《Python 设计模式》** - 掌握常见设计模式

### 在线资源
1. [Python 官方文档 - 类](https://docs.python.org/3/tutorial/classes.html)
2. [SQLAlchemy 文档](https://docs.sqlalchemy.org/) - 学习真正的 ORM 实现
3. [Requests 文档](https://docs.python-requests.org/) - 学习 HTTP 客户端设计

### 实践项目
1. 实现一个简单的博客系统（ORM + API）
2. 开发一个学生管理 Web 应用
3. 构建一个 RESTful API 服务

---

*📅 完成日期：2026-07-01*
*📖 课程进度：Day 045/100*
*🎯 阶段：Phase 3 — 面向对象编程（完成）*