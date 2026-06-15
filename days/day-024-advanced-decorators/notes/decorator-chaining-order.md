# 装饰器叠加顺序与陷阱

## 洋葱模型口诀

```
贴装饰：从里到外     @A @B @C → C先贴，A最后贴
剥洋葱：从外到里     A先执行前置，再B，再C，最后原始函数
```

## 文本格式化例子

```python
@bold               # 外层
@italic             # 中间
@underline          # 内层
def text(): ...     # 原始函数

# 结果：<b><i><u>原始文本</u></i></b>
```

## 陷阱 1：顺序影响结果

```python
@bold @italic → <b><i>Hello</i></b>
@italic @bold → <i><b>Hello</b></i>
```

## 陷阱 2：验证顺序必须合理

```python
# ✅ 先验证再转换
@uppercase                 # 2. 后转换
@validate_non_empty        # 1. 先验证
def get(name): return name

# ❌ 先转换再验证
@validate_non_empty        # 2. 后验证（可能已为空）
@uppercase                 # 1. 先转换
def get(name): return name
```

## 陷阱 3：缓存 + 重试顺序

```python
# 方式 1：缓存外层，重试内层
@cache_result              # 缓存失败的 None！
@retry                     # 重试直到成功或失败
def fetch(): ...

# 方式 2：重试外层，缓存内层（推荐）
@retry                     # 失败重试
@cache_result              # 仅缓存成功结果
def fetch(): ...
```

## 关注点分离原则

每个装饰器只做**一件事**，且不依赖其他装饰器的存在。
