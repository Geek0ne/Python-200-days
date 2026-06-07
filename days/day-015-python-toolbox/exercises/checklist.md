# Python 工具箱 — 完成清单与练习题

## ✅ 完成清单

### 项目结构

- [ ] 项目目录 `days/day-015-python-toolbox/` 已创建
- [ ] `code/pytools/` 包目录结构完整
- [ ] `diagrams/README.md` 包含架构示意图
- [ ] `exercises/checklist.md` 包含检查表和练习题
- [ ] `README.md` 项目说明完整

### 文件管理工具 (`file_tools.py`)

- [ ] `batch_rename()` 支持前缀添加
- [ ] `batch_rename()` 支持后缀添加
- [ ] `batch_rename()` 支持字符串替换
- [ ] `batch_rename()` 支持序号编号模式
- [ ] `batch_rename()` 支持按扩展名过滤
- [ ] `batch_rename()` 支持 `dry_run` 模拟模式
- [ ] `batch_rename()` 正确处理文件名冲突
- [ ] `find_files()` 支持按扩展名过滤
- [ ] `find_files()` 支持按最小/最大大小过滤
- [ ] `find_files()` 支持按修改日期过滤
- [ ] `find_files()` 支持递归/非递归搜索
- [ ] `dir_size_stats()` 统计总大小
- [ ] `dir_size_stats()` 统计子目录大小分布
- [ ] `dir_size_stats()` 统计文件类型分布
- [ ] `classify_files()` 按扩展名分组
- [ ] `classify_files()` 自动创建分类目录
- [ ] `classify_files()` 处理目标文件名冲突

### 文本处理工具 (`text_tools.py`)

- [ ] `word_frequency()` 支持文件输入
- [ ] `word_frequency()` 支持字符串输入
- [ ] `word_frequency()` 支持排除停用词
- [ ] `word_frequency()` 支持自定义停用词
- [ ] `word_frequency()` 支持返回 Top-N 结果
- [ ] `word_frequency()` 同时支持中文和英文
- [ ] `analyze_csv()` 读取 CSV 文件
- [ ] `analyze_csv()` 推断列数据类型
- [ ] `analyze_csv()` 统计缺失值
- [ ] `analyze_csv()` 数值列计算均值/最值
- [ ] `search_text()` 普通字符串匹配
- [ ] `search_text()` 正则表达式匹配
- [ ] `search_text()` 支持大小写不敏感
- [ ] `search_text()` 返回行号和详细匹配信息
- [ ] `convert_text()` 大小写转换（upper/lower/title）
- [ ] `convert_text()` 换行符转换（unix/windows/old_mac）
- [ ] `convert_text()` 编码转换

### 数据统计工具 (`stats_tools.py`)

- [ ] `mean()` 计算算术平均值
- [ ] `median()` 计算中位数（奇偶处理）
- [ ] `mode()` 计算众数（支持多众数）
- [ ] `variance()` 计算方差（样本/总体）
- [ ] `std_dev()` 计算标准差（样本/总体）
- [ ] `frequency_distribution()` 直方图分箱统计
- [ ] `sort_and_dedup()` 排序并去重
- [ ] `percentiles()` 计算任意分位数（线性插值）
- [ ] `visual_histogram()` 终端字符直方图
- [ ] `summary_report()` 综合统计报告
- [ ] 所有函数都有类型注解
- [ ] 所有函数都有 docstring
- [ ] 适当的错误处理

### 主程序 (`main.py`)

- [ ] `argparse` 命令行参数解析
- [ ] `file` 子命令（rename/find/size/classify）
- [ ] `text` 子命令（freq/csv/search/convert）
- [ ] `stats` 子命令（analyze/histogram/report）
- [ ] 交互式菜单模式
- [ ] 完善的子命令帮助信息
- [ ] 友好的用户交互体验

### 代码质量

- [ ] 所有函数有类型注解
- [ ] 所有函数有文档字符串（含参数、返回值、示例）
- [ ] 异常处理（try/except + 自定义异常）
- [ ] 单一职责原则
- [ ] 模块化设计
- [ ] `__init__.py` 统一暴露 API
- [ ] 代码符合 PEP 8 风格

---

## 📝 扩展练习题

### 练习 1：给文件工具添加撤销功能

**难度：⭐⭐⭐**

为 `file_tools.py` 添加操作日志和撤销功能。

**要求：**
1. 在执行 `batch_rename()` 和 `classify_files()` 前，自动记录操作前的文件状态
2. 创建一个 `OperationLog` 类，记录每次操作的变化
3. 实现 `undo_last_operation()` 函数，撤销最后一次操作
4. 日志保存为 JSON 文件（如 `.pytools_undo_log.json`）

**提示：**
- 在执行重命名前，记录 `(原名, 新名)` 映射
- 撤销时反转这个映射
- 注意撤销操作的顺序（后执行的先撤销）

**示例：**
```python
from pytools.file_tools import batch_rename, undo_last_operation

# 执行重命名
batch_rename("/tmp/files", prefix="new_", ext=".txt")
# 后悔了，撤销
undo_last_operation("/tmp/files")
```

---

### 练习 2：给文本工具添加敏感词过滤

**难度：⭐⭐**

为 `text_tools.py` 添加敏感词过滤功能。

**要求：**
1. 实现 `filter_sensitive_words(text, word_list, replacement="***")` 函数
2. 支持从文件加载敏感词列表
3. 大小写不敏感匹配
4. 支持中文敏感词

**扩展思考：**
- 如何防止绕过（如 "敏-感-词" 中间加符号）？
- 如何实现分级过滤（警告 vs 阻止）？
- 如何处理长文本的性能？

**示例：**
```python
from pytools.text_tools import filter_sensitive_words

text = "This is a badword in this sentence."
result = filter_sensitive_words(text, ["badword"], replacement="[FILTERED]")
print(result)  # "This is a [FILTERED] in this sentence."
```

---

### 练习 3：用 stats_tools 分析成绩单 CSV

**难度：⭐⭐**

使用 `stats_tools.py` 的成绩单分析脚本。

**要求：**
1. 创建一个学生成绩 CSV 文件（包含姓名、语文、数学、英语、总分列）
2. 读取 CSV 并对每科成绩进行统计
3. 输出每科的均值、中位数、标准差、最高分、最低分
4. 找出总分前 3 名和后 3 名的学生

**示例 CSV (`scores.csv`)：**
```csv
姓名,语文,数学,英语
张三,85,92,78
李四,90,88,95
王五,78,85,82
...
```

**输出示例：**
```
=== 成绩分析报告 ===
科目: 语文
  均值: 83.5
  中位数: 84.0
  标准差: 7.2
  最高分: 98
  最低分: 62

总分排名:
  🥇 李四 - 273 分
  🥈 赵六 - 265 分
  🥉 张三 - 255 分
...
```

---

### 练习 4：实现一个 JSON 配置文件系统

**难度：⭐⭐⭐**

为 `pytools` 添加配置文件支持。

**要求：**
1. 创建一个 `config.py` 模块
2. 支持从 YAML 或 JSON 文件加载配置
3. 配置项包括：
   - 停用词文件路径
   - 文件分类映射表（可自定义）
   - 默认统计参数（如分箱数量）
   - 日志级别和输出格式
4. 各工具模块使用配置中的默认值

**示例配置 (`pytools_config.json`)：**
```json
{
    "text_tools": {
        "stopwords_file": "~/.pytools/stopwords.txt",
        "default_top_n": 30
    },
    "file_tools": {
        "custom_categories": {
            ".md": "docs",
            ".rst": "docs"
        }
    },
    "stats_tools": {
        "default_bins": 15
    }
}
```

---

### 练习 5：终极挑战 — 为工具箱添加 GUI 界面

**难度：⭐⭐⭐⭐⭐**

使用 Python 标准库 `tkinter` 为工具箱添加图形界面。
如果你熟悉 `PyQt5` 或 `Dear PyGui` 也可以使用。

**要求（基础级）：**
1. 主窗口包含三个选项卡（文件管理、文本处理、数据统计）
2. 每个选项卡对应一个功能模块
3. 文件管理：目录选择 + 操作参数输入 + 结果展示
4. 文本处理：文件选择 + 操作选择 + 结果预览
5. 数据统计：数据输入 + 统计结果显示

**要求（进阶级）：**
1. 文件拖放支持
2. 实时预览重命名结果
3. 词频统计结果以柱状图显示
4. 进度条显示长操作进度
5. 支持多线程（避免界面卡死）

**提示：**
```python
# 基础 tkinter 框架
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class PytoolsGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Python 工具箱")
        self.root.geometry("800x600")
        # ... 构建 UI

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = PytoolsGUI()
    app.run()
```

---

## 💪 自我挑战

完成以上 5 道练习题后，试着把这些功能集成到 `main.py` 中，
让用户可以通过交互菜单选择使用这些扩展功能。

复习至此，你应该已经掌握了 Python 的基础语法和核心数据结构，
可以自信地说：「**我了解 Python 基础了！**」🚀

接下来进入 Phase 2：面向对象编程！
