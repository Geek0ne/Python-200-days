# Day 063 — CSV 与 Excel：练习与检查表

## ✅ 今日完成清单

- [ ] 理解 CSV 格式的核心概念与使用场景
- [ ] 掌握 csv.reader / csv.writer 基础读写
- [ ] 掌握 csv.DictReader / csv.DictWriter 字典操作
- [ ] 理解方言（Dialect）系统和 Sniffer 自动检测
- [ ] 掌握 openpyxl 创建/读取 Excel 文件
- [ ] 能应用 Excel 单元格样式（字体、填充、边框）
- [ ] 能在 Excel 中添加图表
- [ ] 了解 pandas 的 CSV/Excel 读取 API
- [ ] 理解 CSV 编码陷阱（utf-8-sig BOM）
- [ ] 完成实战：报表生成器

---

## 📝 练习题

### 基础题

#### 题 1：CSV 读写练习

有一份学生成绩数据：

```csv
姓名,语文,数学,英语
张三,85,92,78
李四,90,88,95
王五,76,85,82
赵六,92,78,90
```

要求：
1. 用 `csv.DictReader` 读取数据
2. 计算每个学生的总分和平均分
3. 用 `csv.DictWriter` 将结果（含总分和平均分两列）写入新文件

#### 题 2：Excel 表格美化

使用 openpyxl 创建一个产品目录表：
- 字段：编号、产品名、价格、库存
- 添加 5 条示例数据
- 表头用蓝色背景白色字体
- 价格列用货币格式（¥#,##0.00）
- 库存 < 10 的单元格用红色高亮

#### 题 3：CSV 分隔符检测

编写一个函数 `detect_csv_format(file_path)`，使用 `csv.Sniffer` 自动检测：
1. 分隔符
2. 引号字符
3. 是否有表头
4. 换行符类型

针对以下三种格式都能正确检测：
```csv
name,age,city
Alice,30,Beijing
```
```tsv
name	age	city
Alice	30	Beijing
```
```psv
name|age|city
Alice|30|Beijing
```

---

### 进阶题

#### 题 4：大文件分块处理

有一个 100 万行的销售数据 CSV 文件（`sales.csv`），字段为：
`order_id, user_id, amount, date`

内存只有 512MB 可用，无法一次读入全部数据。

要求：编写程序分块（每块 10 万行）读取，计算：
1. 总销售额
2. 每日销售额趋势（输出到新文件）
3. 单笔最大金额的订单

#### 题 5：多 Sheet Excel 报表

使用 openpyxl 生成一个多层级的报表 Excel，包含：
- Sheet "销售日报" — 按日期的销售明细
- Sheet "月度汇总" — 按月汇总（用公式或 Python 计算）
- Sheet "人员排行" — 按销售员排名
- Sheet "图表" — 包含柱状图（月度趋势）和饼图（人员占比）

要求：从 CSV 文件输入，输出格式化的 .xlsx。

---

## 💡 挑战题

编写一个 `UniversalDataExporter` 类，支持：

```python
exporter = UniversalDataExporter(engine="pandas")  # 或 "csv" 或 "openpyxl"
```

功能：
1. `read(input_path)` — 自动识别格式并读取（CSV / XLSX / XLS）
2. `transform(operations)` — 支持过滤、分组、排序操作链
3. `write(output_path, format)` — 导出为指定格式
4. 支持 100 万行数据的分块导出
5. 自动处理编码问题

---

## 📚 参考资料

- [Python csv 官方文档](https://docs.python.org/3/library/csv.html)
- [openpyxl 文档](https://openpyxl.readthedocs.io/)
- [pandas read_csv 文档](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html)
- [pandas read_excel 文档](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html)
