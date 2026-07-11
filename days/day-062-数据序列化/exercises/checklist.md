# Day 062 — 数据序列化：练习与检查表

## ✅ 今日完成清单

- [ ] 理解序列化的概念与核心目的
- [ ] 掌握 json 模块的 dumps/loads/dump/load 方法
- [ ] 能处理自定义类型的 JSON 编码/解码
- [ ] 理解 pickle 的适用场景与安全风险
- [ ] 了解 msgpack 的跨语言二进制序列化
- [ ] 掌握 YAML 配置文件的基本使用
- [ ] 理解三种序列化方案的优缺点对比
- [ ] 完成实战：配置文件解析器

---

## 📝 练习题

### 基础题

#### 题 1：JSON 序列化实操

有一个字典数据，包含学生的考试成绩：

```python
student_data = {
    "name": "小明",
    "scores": {"math": 95, "english": 88, "science": 92},
    "graduated": False
}
```

要求：
1. 将其序列化为 JSON 字符串，缩进 2 格，保留中文
2. 从 JSON 字符串反序列化回 Python 对象
3. 证明反序列化后的 `graduated` 是 `bool` 类型而不是字符串

#### 题 2：文件读写

将上面 `student_data` 写入文件 `student.json`，然后读取出来，打印 `name` 和 `math` 成绩。

#### 题 3：YAML 配置文件

编写一个 YAML 配置文件来描述以下内容（使用锚点避免重复）：
- 三个环境：`development`、`staging`、`production`
- 公共配置：`timeout: 30`, `retries: 3`, `debug: false`
- development 覆盖 `debug: true`、`host: localhost`
- production 覆盖 `timeout: 60`、`host: api.example.com`

---

### 进阶题

#### 题 4：自定义 JSON 编码器

有一个数据包含 `Decimal` 和 `datetime` 类型：

```python
from decimal import Decimal
from datetime import datetime

order = {
    "order_id": "ORD-2026-001",
    "total": Decimal("199.99"),
    "created_at": datetime.now(),
    "items": ["Python 进阶书", "数据结构导论"]
}
```

编写一个自定义 JSON 编码器，能将上述数据序列化，并且反序列化时恢复原始类型。

#### 题 5：配置合并与优先级

实现一个 `ConfigMerger` 类，支持三层配置合并：

```
默认配置 (default) ← 文件配置 (file) ← 命令行配置 (cli)
```

合并规则：
- 上层覆盖下层（CLI > File > Default）
- 字典类型递归合并
- 支持点号路径设置（如 `set("database.host", "value")`）

示例：
```python
default = {"app": {"debug": False, "port": 3000}}
file_cfg = {"app": {"port": 8080, "workers": 4}}
cli_cfg = {"app": {"debug": True}}

merger = ConfigMerger(default, file_cfg, cli_cfg)
# 结果应为: {"app": {"debug": True, "port": 8080, "workers": 4}}
```

---

## 💡 挑战题

编写一个函数 `auto_serialize(data, output_path)`，能根据 `output_path` 的文件扩展名自动选择序列化格式（支持 .json、.yaml、.pkl、.msgpack），将 `data` 序列化写入文件。然后编写对应的 `auto_deserialize(input_path)` 从文件读取反序列化。

要求：
1. 自动检测格式
2. 错误处理完善
3. 支持 Python 标准类型 + datetime
4. 如果格式不支持当前数据类型，给出明确的错误提示

---

## 📚 参考资料

- [Python json 文档](https://docs.python.org/3/library/json.html)
- [Python pickle 文档](https://docs.python.org/3/library/pickle.html)
- [PyYAML 文档](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [msgpack-python](https://github.com/msgpack/msgpack-python)
