# 推导式快速参考卡

## 语法速查

| 类型 | 语法 | 返回 |
|------|------|------|
| 列表推导式 | `[expr for x in iterable]` | `list` |
| 字典推导式 | `{k: v for x in iterable}` | `dict` |
| 集合推导式 | `{expr for x in iterable}` | `set` |
| 生成器表达式 | `(expr for x in iterable)` | `generator` |

## 条件语法

```python
# 过滤（可选元素）
[expr for x in iterable if condition]

# 三元表达式（所有元素都输出，但值不同）
[expr_true if condition else expr_false for x in iterable]
```

## 嵌套展开规则

```python
# 推导式
[expr for a in A for b in B if cond]

# 等价于
for a in A:
    for b in B:
        if cond:
            result.append(expr)
```

## 推荐场景速查

```
✅ 推导式                          ❌ 用普通循环
───────────────────────────────   ───────────────────────────
简单映射（如 x**2）               复杂嵌套（>2层）
简单过滤（如 if x > 0）           副作用（print, 文件写入）
小到中等数据集                     超大数据（用生成器）
需要生成 list/dict/set            需要逐行调试
```

## 性能排序（通常）

```
列表推导式 ≈ map+filter > 生成器→列表 > 手写 for 循环
```

## 一句口诀

> **方括号列表，花括号是集合，冒号在其中就变字典，圆括号是生成器。**
