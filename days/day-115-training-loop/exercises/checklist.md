# Day 115 — 训练流程 · 练习清单

## ✅ 今日完成清单

- [ ] 理解 Dataset 和 DataLoader 的关系
- [ ] 掌握自定义 Dataset 的三要素（__init__、__len__、__getitem__）
- [ ] 理解 batch_size、shuffle、num_workers 的作用
- [ ] 掌握 model.train() 和 model.eval() 的区别
- [ ] 理解 torch.no_grad() 的作用
- [ ] 掌握模型保存与加载（state_dict 方式）
- [ ] 完成 MNIST 手写数字识别实战

---

## 基础练习题

### 练习 1：DataLoader 计算
一个数据集有 1000 个样本，batch_size=32：
1. 一共有多少个 batch？
2. 最后一个 batch 有多少个样本？
3. 如果 drop_last=True，一共多少个 batch？

### 练习 2：Dataset 实现
实现一个 Dataset 类，数据来自两个列表：
```python
features = [[1,2,3], [4,5,6], [7,8,9]]
labels = [0, 1, 1]
```
要求：支持 `len(dataset)` 和 `dataset[i]` 访问。

### 练习 3：模式切换
解释以下代码的输出为什么不同：
```python
model.train()
out1 = model(x)
model.eval()
out2 = model(x)
# out1 != out2（有 Dropout 的情况下）
```

---

## 进阶挑战题

### 挑战 1：实现早停
修改 MNIST 训练代码，实现早停机制：连续 5 轮验证集准确率不提升就停止训练。

### 挑战 2：学习率调度
使用 `torch.optim.lr_scheduler.StepLR`，每 5 个 epoch 将学习率减半。

### 挑战 3：混合精度训练
使用 `torch.cuda.amp` 实现混合精度训练，比较训练速度差异。

---

## 💡 自测要点

1. `DataLoader` 的 `shuffle=True` 在训练和测试时分别应该设为什么？
2. 为什么 `model.eval()` 时要配合 `torch.no_grad()`？
3. `torch.save(model, 'model.pth')` 和 `torch.save(model.state_dict(), 'model.pth')` 有什么区别？
