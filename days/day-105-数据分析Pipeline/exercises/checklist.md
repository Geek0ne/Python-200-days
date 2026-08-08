# Day 105 — 阶段项目：数据分析 Pipeline | 完成清单

## ✅ 学习完成清单

- [ ] 理解数据分析 Pipeline 的架构与设计原则
- [ ] 掌握 ETL 模式的三阶段工作流
- [ ] 学会多种数据源（CSV/API/数据库）的读取方法
- [ ] 掌握缺失值处理的决策树
- [ ] 学会异常值检测与处理（IQR/Z-score）
- [ ] 完成完整 Pipeline 项目（获取→清洗→分析→可视化→报告）
- [ ] 理解模块化、可复现、容错性设计原则

---

## 📝 练习题

### 基础题

**1. 数据清洗 Pipeline**

创建一个 `DataCleanser` 类，包含以下方法：
- `load(filepath)`: 读取 CSV 文件
- `remove_duplicates()`: 删除重复行
- `handle_missing(strategy)`: 处理缺失值
  - `strategy='mean'`: 数值用均值填充
  - `strategy='median'`: 数值用中位数填充
  - `strategy='mode'`: 分类用众数填充
  - `strategy='drop'`: 删除含缺失值的行
- `fix_outliers(columns)`: 用 IQR 方法修复异常值
- `save(filepath)`: 保存清洗后的数据

要求：使用链式调用，如 `DataCleanser().load('data.csv').remove_duplicates().save('clean.csv')`

---

**2. 数据分析报告生成器**

编写一个函数 `generate_analysis_report(df, output_format='markdown')`，自动分析传入的 DataFrame 并生成报告。

要求：
- 自动检测数值列和分类列
- 数值列输出：均值、中位数、标准差、最大/最小值
- 分类列输出：唯一值数量、Top 3 类别
- 输出格式支持 `markdown` 和 `json`
- 保存到文件 `analysis_report.{format}`

---

**3. Pipeline 步骤装饰器**

实现以下两个装饰器：
- `@step(name)`: 记录步骤开始/结束时间，输出日志
- `@retry(max_attempts=3)`: 自动重试失败的函数

测试：
```python
@step("数据加载")
@retry(max_attempts=3)
def load_data():
    # 模拟随机失败
    if np.random.random() < 0.5:
        raise ConnectionError("模拟网络错误")
    return pd.DataFrame({'a': [1, 2, 3]})
```

---

### 进阶题

**4. 增量 Pipeline**

实现一个支持增量处理的 Pipeline：
- 只处理自上次运行以来的新数据
- 维护一个状态文件 `pipeline_state.json` 记录上次处理的最后时间戳
- 支持 `--reset` 参数重新全量处理
- 支持 `--dry-run` 参数只输出计划而不实际执行

---

**5. 多数据源 Pipeline**

实现一个支持同时处理多个数据源的 Pipeline：
- 数据源 1: CSV 文件
- 数据源 2: JSON API（模拟）
- 数据源 3: 数据库查询（模拟）
- 合并三个数据源，进行统一清洗
- 生成交叉分析报告（数据源间对比）

要求：
- 使用工厂模式创建不同的数据源连接器
- 合并时处理列名冲突
- 生成数据质量对比报告

---

## 🎯 自测标准

| 指标 | 达标标准 |
|------|---------|
| 基础题 | 3 题全部实现，代码可运行 |
| 进阶题 | 2 题全部实现，包含错误处理 |
| Pipeline | 完整走通获取→清洗→分析→报告流程 |
| 代码质量 | 使用 OOP 设计，有完整注释 |
| 日志输出 | Pipeline 执行过程有清晰的日志记录 |
