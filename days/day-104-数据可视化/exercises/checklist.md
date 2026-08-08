# Day 104 — 数据可视化 | 完成清单

## ✅ 学习完成清单

- [ ] 理解 Matplotlib Figure/Axes 双层对象模型
- [ ] 掌握折线图、柱状图、散点图的绑制方法
- [ ] 掌握饼图、直方图、箱线图的绑制方法
- [ ] 了解 Seaborn 的核心优势与使用场景
- [ ] 学会使用 boxplot/violin/heatmap/pairplot
- [ ] 理解多子图布局技巧
- [ ] 完成完整 EDA 报告实战

---

## 📝 练习题

### 基础题

**1. 绘制温度折线图**

使用下面的数据，绘制过去 7 天的温度变化折线图，包含趋势线和数据标注：

```python
days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
temps = [22, 24, 19, 26, 28, 25, 23]
```

要求：
- 标题："Weekly Temperature"
- 标注每天的最高/最低温度
- 添加网格线
- 保存为 `temperature.png`

---

**2. 绘制柱状图 + 数值标注**

使用以下数据绘制编程语言使用率柱状图：

```python
languages = ['Python', 'JavaScript', 'Java', 'C++', 'TypeScript']
usage = [48.2, 35.4, 30.5, 22.1, 18.8]
```

要求：
- 每个柱子上方标注百分比
- 使用不同颜色
- 添加 Y 轴标签 "Percentage (%)"
- 保存为 `language_usage.png`

---

**3. 散点图相关性分析**

生成 100 个随机点，模拟"广告支出 vs 销售额"的关系：

```python
np.random.seed(42)
ad_spend = np.random.uniform(10, 100, 100)
sales = ad_spend * 2.5 + np.random.normal(0, 15, 100)
```

要求：
- 绘制散点图
- 添加趋势线（线性回归）
- 计算并显示相关系数
- 保存为 `ad_sales.png`

---

### 进阶题

**4. Seaborn 多图对比**

使用 `tips` 数据集，创建 2x2 的子图网格：
- 左上：`total_bill` 的直方图
- 右上：`day` 与 `total_bill` 的 boxplot
- 左下：`total_bill` vs `tip` 的散点图（按 `smoker` 着色）
- 右下：数值特征的 heatmap

要求：
- 使用 `plt.subplots(2, 2)`
- 每个子图都有标题
- 整体使用 `plt.suptitle()`
- 保存为 `tips_analysis.png`

---

**5. EDA 报告增强**

基于 Day 104 的 `03-eda-report.py`，增加以下分析：
- 添加 `family_size` 与 `survived` 的交叉表分析
- 用 Seaborn `catplot` 创建性别 × 船舱等级的生存率 faceted 图
- 对缺失值处理前后做对比分析（填充中位数 vs 填充众数）
- 输出完整分析报告到文本文件 `titanic_report.txt`

---

## 🎯 自测标准

| 指标 | 达标标准 |
|------|---------|
| 基础题 | 3 题全部正确，图表美观 |
| 进阶题 | 2 题全部正确，包含完整注释 |
| 图表质量 | 标题、标签、图例齐全，无中文乱码 |
| 代码规范 | 使用面向对象接口，有完整注释 |
