# Day 020 — 递归练习题与检查表

## ✅ 完成检查表

### 概念理解
- [ ] 理解递归的定义和两个必要组成部分（基线条件 + 递归条件）
- [ ] 能解释递归函数的调用栈和栈帧模型
- [ ] 能说出递归与数学归纳法的对应关系
- [ ] 理解递归深度限制及其原因
- [ ] 能区分尾递归和非尾递归
- [ ] 知道 Python 不支持尾递归优化的原因

### 代码实践
- [ ] 能徒手写出递归阶乘（factorial）
- [ ] 能徒手写出递归斐波那契
- [ ] 能用 memoization 优化斐波那契
- [ ] 能实现汉诺塔递归解法
- [ ] 能实现递归二分查找
- [ ] 能实现递归文件树遍历
- [ ] 会使用 `functools.lru_cache`
- [ ] 会手工实现 memoization（字典缓存）
- [ ] 能比较递归和迭代的性能差异

### 练习完成
- [ ] 基础练习（1-4 题）
- [ ] 进阶练习（5-8 题）
- [ ] 挑战练习（9-10 题）

---

## 📝 基础练习

### 练习 1：实现 pow 递归

不使用 `**` 运算符，用递归实现幂运算函数 `pow_recursive(base, exp)`。

```python
# 要求:
# pow_recursive(2, 0) → 1
# pow_recursive(2, 3) → 8
# pow_recursive(5, 4) → 625
```

<details>
<summary>提示</summary>
base^exp = base * base^(exp-1)
</details>

### 练习 2：字符串反转

用递归实现字符串反转函数 `reverse(s)`。

```python
# 要求:
# reverse("hello") → "olleh"
# reverse("ab") → "ba"
# reverse("a") → "a"
# reverse("") → ""
```

<details>
<summary>提示</summary>
reverse(s) = reverse(s[1:]) + s[0]
</details>

### 练习 3：判断回文

用递归判断字符串是否为回文。

```python
# 要求:
# is_palindrome("racecar") → True
# is_palindrome("hello") → False
# is_palindrome("a") → True
# is_palindrome("") → True
```

### 练习 4：列表扁平化

用递归将任意嵌套的列表展开为一维列表。

```python
# 输入: [1, [2, [3, 4]], 5, [6, [7, [8]]]]
# 输出: [1, 2, 3, 4, 5, 6, 7, 8]
```

---

## 🔥 进阶练习

### 练习 5：数字根 (Digital Root)

数字根是递归求各位数字之和直到结果为一位数。

```python
# digital_root(942) → 9+4+2=15 → 1+5=6
# digital_root(0) → 0
```

**要求：** 用递归实现，不使用循环。

### 练习 6：最大公约数 (GCD)

用递归实现欧几里得算法求最大公约数。

```python
# gcd(48, 18) → 6
# gcd(100, 25) → 25
# gcd(17, 13) → 1
```

公式：`gcd(a, b) = gcd(b, a % b)`，基线条件：`b == 0` 时返回 `a`

### 练习 7：弗洛伊德三角

用递归打印弗洛伊德三角：

```
1
2 3
4 5 6
7 8 9 10
11 12 13 14 15
```

### 练习 8：递归计数器装饰器

编写一个装饰器 `count_calls`，统计被装饰的递归函数的总调用次数。

```python
@count_calls
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

fib(10)
print(fib.call_count)  # 应该输出 fib(10) 被调用的总次数
```

---

## 🏆 挑战练习

### 练习 9：二叉树的深度与遍历

定义二叉树节点类：

```python
class TreeNode:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
```

用递归实现：
1. `max_depth(root)` — 计算二叉树的最大深度
2. `inorder_traversal(root)` — 中序遍历（左-根-右）
3. `mirror(root)` — 镜像翻转二叉树

### 练习 10：N 皇后问题

用递归回溯算法解决 N 皇后问题：在 N×N 棋盘上放置 N 个皇后，使它们互不攻击。

```python
def solve_n_queens(n):
    """返回所有合法的皇后放置方案
    
    每个方案是一个列表 Q，Q[i] = j 表示第 i 行的皇后在第 j 列
    """
```

---

## 💡 思考题

1. 递归函数的空间复杂度如何分析？什么情况下递归的空间复杂度优于迭代？
2. 快速排序的递归实现中，为什么最坏情况时间复杂度是 O(n²)？
3. 为什么 Python 选择不实现尾递归优化？函数式语言（如 Haskell）为什么必须实现？
4. 如何在不改变函数签名的情况下，给一个递归函数添加记忆化功能？
5. 递归和分治的关系是什么？所有分治算法都可以用递归实现吗？

## 📊 自我评估

| 技能 | 😰 不熟练 | 🤔 基本掌握 | 💪 熟练 |
|------|----------|------------|--------|
| 理解递归概念 | | | |
| 实现简单递归函数 | | | |
| 调用栈分析 | | | |
| Memoization 优化 | | | |
| 递归转迭代 | | | |
| 文件系统遍历 | | | |
| 回溯算法 | | | |
| 性能分析 | | | |


---

## 🧪 挑战题解答思路

### 练习 9：二叉树递归遍历（解答思路）

```python
class TreeNode:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

# 1. 最大深度
def max_depth(root):
    if root is None:          # 基线条件：空树深度为 0
        return 0
    left_depth = max_depth(root.left)
    right_depth = max_depth(root.right)
    return max(left_depth, right_depth) + 1

# 2. 中序遍历
def inorder_traversal(root):
    if root is None:          # 基线条件
        return []
    return (inorder_traversal(root.left) +
            [root.val] +
            inorder_traversal(root.right))

# 3. 镜像翻转
def mirror(root):
    if root is None:          # 基线条件
        return None
    root.left, root.right = root.right, root.left
    mirror(root.left)          # 递归翻转左子树
    mirror(root.right)         # 递归翻转右子树
    return root
```

### 练习 10：N 皇后问题（回溯框架）

```python
def solve_n_queens(n):
    def is_safe(board, row, col):
        # 检查列、对角线是否有皇后
        for i in range(row):
            if (board[i] == col or
                board[i] - i == col - row or
                board[i] + i == col + row):
                return False
        return True

    def backtrack(row, board):
        if row == n:          # 基线条件：所有行都放了皇后
            solutions.append(board[:])
            return
        for col in range(n):
            if is_safe(board, row, col):
                board.append(col)        # 选择
                backtrack(row + 1, board)  # 递归
                board.pop()               # 回溯

    solutions = []
    backtrack(0, [])
    return solutions
```

---

## 📊 递归学习路线图

```mermaid
graph LR
    A[理解递归概念] --> B[简单递归函数<br>阶乘/斐波那契]
    B --> C[递归思想<br>汉诺塔/二分查找]
    C --> D[调用栈分析<br>调试技巧]
    D --> E[优化递归<br>Memoization/TCO]
    E --> F[递归实战<br>文件遍历/树操作]
    F --> G[高级应用<br>回溯/分治/动态规划]

    style A fill:#e1f5fe
    style G fill:#c8e6c9
```

## 💡 递归模式速查表

| 模式 | 结构 | 适用于 | 示例 |
|------|------|--------|------|
| **尾部递归** | 返回值直接是递归调用 | 累加、遍历 | `fact_tail(n, acc)` |
| **头部递归** | 先递归再处理 | 反向输出 | `reverse(s[1:]) + s[0]` |
| **树形递归** | 多次调用自身 | 分治算法 | 斐波那契、树遍历 |
| **嵌套递归** | 调用参数包含递归调用 | 复杂数学 | Ackermann 函数 |
| **互递归** | 函数 A 调 B, B 调 A | 语法解析 | `parse_expr` + `parse_term` |
