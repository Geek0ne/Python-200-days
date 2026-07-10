# Day 060 — 阶段项目：高性能计算 · 完成清单

## ✅ 学习检查表

- [ ] 理解多进程 + asyncio 混合架构的设计思路
- [ ] 掌握图像处理管道的并行化策略
- [ ] 理解 Amdahl 定律及其对并行设计的指导意义
- [ ] 能设计健壮的错误处理和监控机制
- [ ] 运行过所有代码示例并观察性能差异

---

## 📝 基础练习题

### 练习 1：扩展爬虫功能

为 `01-concurrent-crawler.py` 添加以下功能：
- 支持代理配置
- 添加重试机制（最多 3 次）
- 保存结果为 CSV 文件

### 练习 2：图像管道扩展

为 `02-image-pipeline.py` 添加新的处理步骤：
- 锐化滤波器（Laplacian 算子）
- 图像缩放（最近邻插值）
- 直方图均衡化

要求使用 Numba 加速。

### 练习 3：基准测试报告

修改 `03-benchmark-framework.py`，添加：
- 导出结果为 JSON
- 计算置信区间
- 对比不同 Numba 参数（cache=True/False, parallel=True/False）

---

## 🚀 进阶挑战题

### 挑战 1：分布式爬虫

设计一个支持多机的分布式爬虫架构：
- 使用 Redis 作为任务队列
- Worker 可以部署在不同机器
- 支持动态扩缩容
- 画出架构图

### 挑战 2：GPU 加速图像处理

使用 CuPy（NumPy 的 GPU 替代品）加速图像管道：
- 安装 CuPy: `pip install cupy-cuda12x`
- 将 Numba 版本改为 CuPy 版本
- 对比 CPU vs GPU 性能

### 挑战 3：性能分析报告

对 Phase 4 的所有知识进行综合性能测试：
- 多线程 vs 多进程 vs asyncio
- Numba vs Cython vs 纯 Python
- 生成 HTML 报告（包含图表）

---

## 💡 思考题答案提示

1. **混合架构**：多进程绕过 GIL，进程内 asyncio 实现高并发 I/O。纯 asyncio 受 GIL 限制无法真正并行，纯多进程 I/O 等待时浪费 CPU。

2. **Numba 并行化策略**：灰度转换是像素级操作，天然并行；模糊和边缘检测有邻域依赖，但 Numba 的 prange 能自动处理。实际生产中三者都应并行。

3. **内存管理**：用 `shared_memory` 共享图像数据，避免进程间复制。分批处理避免内存溢出。用 `mmap` 处理超大图像。

4. **Pool vs ProcessPoolExecutor**：ProcessPoolExecutor 更现代，支持 `as_completed` 更灵活；Pool 更传统但 API 更简单。这个场景两者都可以。

5. **Amdahl 定律分析**：I/O 等待、进程启动、结果收集是串行部分。假设 85% 可并行，4 个 CPU 理论加速比 = 1/(0.15+0.85/4) ≈ 2.58x。
