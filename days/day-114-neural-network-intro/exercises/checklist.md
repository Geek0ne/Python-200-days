# Day 114 — 神经网络入门 · 练习清单

## ✅ 今日完成清单

- [ ] 理解 nn.Module 的作用和继承方式
- [ ] 掌握 nn.Linear 的参数含义（in_features, out_features）
- [ ] 理解为什么需要激活函数（非线性）
- [ ] 掌握 ReLU、Sigmoid、Tanh 的区别和适用场景
- [ ] 理解 CrossEntropyLoss 内含 Softmax
- [ ] 掌握训练五步循环：forward → loss → backward → step → zero_grad
- [ ] 完成手写数字分类器代码

---

## 基础练习题

### 练习 1：参数计算
一个网络结构为 `Linear(128, 64) → ReLU → Linear(64, 10)`，请问：
1. 总共有多少个可训练参数？
2. 第一层的权重矩阵 shape 是什么？

<details>
<summary>提示</summary>

Linear(128, 64): 权重 64×128 + 偏置 64 = 8,256
Linear(64, 10): 权重 10×64 + 偏置 10 = 650
总计: 8,906
</details>

### 练习 2：激活函数选择
为以下任务选择合适的激活函数：
1. 图像分类网络的隐藏层
2. 预测房价的输出层
3. 判断邮件是否是垃圾邮件的输出层

### 练习 3：手动实现前向传播
不运行代码，手动计算以下网络的输出：
```
输入 x = [1.0, 2.0]
Linear(2, 3) 权重 W = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]，偏置 b = [0.1, 0.2, 0.3]
ReLU 激活
```

---

## 进阶挑战题

### 挑战 1：修改网络结构
修改 Day 114 的 DigitNet：
1. 增加到 3 层（64→128→64→10）
2. 在每层之间加 Dropout(0.2)
3. 比较准确率变化

### 挑战 2：实现 LeakyReLU
不用 PyTorch 的 `nn.LeakyReLU`，手动实现一个 LeakyReLU 模块（继承 nn.Module）。

### 挑战 3：调试训练问题
运行以下代码，找出问题并修复：
```python
class BrokenNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(10, 64)
        self.fc2 = nn.Linear(64, 3)

    def forward(self, x):
        x = self.fc1(x)
        x = self.fc2(x)  # 缺了什么？
        return x
```

---

## 💡 自测要点

完成今天内容后，你能回答以下问题吗？

1. `nn.Linear(10, 3)` 的权重形状是什么？
2. 为什么训练循环中 `zero_grad()` 要在 `backward()` 之后、`step()` 之前？
3. CrossEntropyLoss 的输入应该是经过 Softmax 的还是未经过的？
4. ReLU 激活函数有什么缺点？如何缓解？
