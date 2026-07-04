# Day 051 — 弱引用（weakref）练习清单

## ✅ 今日学习清单

- [ ] 理解强引用与弱引用的区别
- [ ] 掌握 `weakref.ref()` 的使用
- [ ] 掌握弱引用回调函数的使用
- [ ] 理解 `weakref.ref()` 与 `weakref.proxy()` 的区别
- [ ] 了解哪些对象支持弱引用
- [ ] 掌握 `WeakValueDictionary` 的使用
- [ ] 掌握 `WeakKeyDictionary` 的使用
- [ ] 掌握 `WeakSet` 的使用
- [ ] 理解循环引用问题及弱引用解决方案
- [ ] 完成代码示例的运行和理解

---

## 📝 基础练习

### 练习 1：弱引用基础
创建一个类 `MyObject`，实现以下功能：
1. 创建一个 `MyObject` 实例
2. 创建该实例的弱引用
3. 打印弱引用计数
4. 删除实例后，验证弱引用返回 `None`

```python
# 预期输出示例:
# 引用计数: 1
# 删除实例前: <MyObject object>
# 删除实例后: None
```

### 练习 2：弱引用回调
创建一个类 `TrackedObject`，当对象被回收时打印日志：
1. 创建 `TrackedObject` 实例
2. 使用弱引用回调记录回收事件
3. 多次创建和销毁对象，观察回调触发

```python
# 预期输出示例:
# 创建 obj1
# 回收 obj1
# 创建 obj2
# 回收 obj2
```

### 练习 3：WeakValueDictionary 实现简单缓存
实现一个基于 `WeakValueDictionary` 的缓存类：
1. 支持 `put(key, value)` 和 `get(key)` 方法
2. 当存储的对象被外部删除时，缓存自动清理
3. 编写测试代码验证自动清理功能

---

## 🔥 进阶挑战

### 挑战 1：观察者模式与弱引用
实现一个事件系统，使用 `WeakSet` 管理观察者：
1. 创建 `EventEmitter` 类
2. 支持 `on(event, callback)` 和 `emit(event, data)` 方法
3. 当观察者对象被删除时，自动取消订阅
4. 实现 `listener_count(event)` 方法

### 挑战 2：LRU 缓存实现
实现一个带 TTL（生存时间）的 LRU 缓存：
1. 使用 `WeakValueDictionary` 存储缓存条目
2. 支持最大容量限制
3. 支持过期时间
4. 实现 `stats()` 方法返回命中率等统计信息

### 挑战 3：循环引用检测
编写一个函数 `detect_cycle(obj)`，使用弱引用检测对象是否存在循环引用：
1. 遍历对象的所有属性
2. 使用弱引用追踪已访问的对象
3. 检测是否存在循环引用
4. 返回循环引用路径（如果有）

---

## 🧠 思考题

1. 为什么 Python 不让内置类型（如 `list`、`dict`）支持弱引用？
2. `weakref.proxy()` 与 `weakref.ref()` 在使用体验上有什么区别？
3. 在多线程环境下使用 `WeakValueDictionary` 需要注意什么？
4. 弱引用的回调函数在什么时候被调用？是 `del` 时还是 GC 回收时？
5. 如何在 `__slots__` 的类中支持弱引用？

---

## 📚 参考资料

- [Python 官方文档 - weakref](https://docs.python.org/3/library/weakref.html)
- [Python 源码 - weakref 实现](https://github.com/python/cpython/blob/main/Lib/weakref.py)
- [Python 垃圾回收机制](https://docs.python.org/3/library/gc.html)
