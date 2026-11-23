#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Day 197 — 面试算法题：九类高频模板与不变量

为什么叫「模板」而不是「答案」：
    面试题题干千变万化，但**约束条件 → 算法选择**的映射是稳定的。
    模板把「选择」和「边界」固化下来，省下的注意力全部用来处理题目的特殊要求。

文件里的每个函数都满足两条：
    1. 只依赖标准库，可直接 python3 运行；
    2. 有不变量注释：写明循环/递归每一步为什么仍然正确。

运行：
    python3 01-algorithm-templates.py            # 打印模板清单 + 复杂度表
    python3 01-algorithm-templates.py --self-test
    python3 01-algorithm-templates.py --demo two_sum
"""
from __future__ import annotations

import argparse
import heapq
import sys
from collections import deque
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# 0. 通用工具
# ---------------------------------------------------------------------------


class ListNode:
    """链表节点。面试时手写，不要依赖 typing 之外的东西。"""

    __slots__ = ("val", "next")

    def __init__(self, val: int = 0, nxt: Optional["ListNode"] = None) -> None:
        self.val = val
        self.next = nxt


def build_list(values: Iterable[int]) -> Optional[ListNode]:
    dummy = ListNode()
    tail = dummy
    for v in values:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next


def list_to_list(head: Optional[ListNode]) -> List[int]:
    out: List[int] = []
    while head:
        out.append(head.val)
        head = head.next
    return out


# ---------------------------------------------------------------------------
# 1. 哈希表：用空间换「查过没有」
# ---------------------------------------------------------------------------


def two_sum(nums: Sequence[int], target: int) -> Tuple[int, int]:
    """无序数组两数之和，返回下标。O(n) / O(n)。

    不变量：扫描到 i 时，seen 里存的是 nums[0..i-1] 的全部值→下标。
    因此 nums[i] 只需问一句「target - nums[i] 之前出现过吗」。
    为什么不能先排序再双指针：排序会丢掉原始下标，除非额外存下标数组。
    """
    seen: Dict[int, int] = {}
    for i, x in enumerate(nums):
        need = target - x
        if need in seen:
            return seen[need], i
        seen[x] = i
    raise ValueError("no two sum solution")


def two_sum_sorted(nums: Sequence[int], target: int) -> Tuple[int, int]:
    """有序数组两数之和。O(n) / O(1)。

    不变量：答案若存在，必在 [lo, hi] 内。
    nums[lo] + nums[hi] < target 时，lo 与任何更小的 hi 配对都只会更小，
    所以 lo 可以安全右移；反之 hi 左移。每步排除一行/一列，收敛到答案。
    """
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        s = nums[lo] + nums[hi]
        if s == target:
            return lo, hi
        if s < target:
            lo += 1
        else:
            hi -= 1
    raise ValueError("no two sum solution")


def max_area(height: Sequence[int]) -> int:
    """盛最多水的容器。O(n) / O(1)。

    面积 = min(h[l], h[r]) * (r - l)。每次移动较矮的一侧：
    移动高的一侧不可能让 min 变大，而宽度一定变小，所以只会更差。
    """
    lo, hi = 0, len(height) - 1
    best = 0
    while lo < hi:
        h = min(height[lo], height[hi])
        best = max(best, h * (hi - lo))
        if height[lo] < height[hi]:
            lo += 1
        else:
            hi -= 1
    return best


# ---------------------------------------------------------------------------
# 2. 滑动窗口：把「连续子段」的暴力 O(n^2) 压成 O(n)
# ---------------------------------------------------------------------------


def longest_unique_substring(s: str) -> int:
    """无重复字符的最长子串长度。O(n) / O(字符集)。

    不变量：窗口 [left, right] 内无重复字符。
    right 右移后若出现重复，left 跳到「重复字符上次出现位置 + 1」——
    跳过的是所有以旧 left 开头、必然仍含重复的子串。
    """
    last: Dict[str, int] = {}
    left = best = 0
    for right, ch in enumerate(s):
        if ch in last and last[ch] >= left:
            left = last[ch] + 1
        last[ch] = right
        best = max(best, right - left + 1)
    return best


def min_window(s: str, t: str) -> str:
    """最小覆盖子串。O(n + m) / O(字符集)。

    需要 vs 已有：只有 need[c] == have[c] 时才说明「这个字符的配额满了」。
    窗口收缩条件必须是 formed == required；用 len(t) 比较会在重复字符上出错
    （例如 t='aa'，窗口里 1 个 a 也会被误判为覆盖）。
    """
    if not t:
        return ""
    need: Dict[str, int] = {}
    for ch in t:
        need[ch] = need.get(ch, 0) + 1
    have: Dict[str, int] = {}
    required = len(need)
    formed = 0
    left = 0
    best_len = sys.maxsize
    best_span = (0, 0)

    for right, ch in enumerate(s):
        if ch in need:
            have[ch] = have.get(ch, 0) + 1
            if have[ch] == need[ch]:
                formed += 1
        while formed == required:
            if right - left + 1 < best_len:
                best_len = right - left + 1
                best_span = (left, right)
            out = s[left]
            if out in need:
                have[out] -= 1
                if have[out] < need[out]:
                    formed -= 1
            left += 1
    return "" if best_len == sys.maxsize else s[best_span[0] : best_span[1] + 1]


# ---------------------------------------------------------------------------
# 3. 二分：写对边界的唯一办法是统一「区间语义」
# ---------------------------------------------------------------------------


def lower_bound(nums: Sequence[int], x: int) -> int:
    """第一个 >= x 的下标（等价 bisect_left）。O(log n)。

    统一用左闭右开 [lo, hi)：循环条件 lo < hi，收缩时 hi = mid 而不是 mid-1。
    这样「答案区间」始终是 [lo, hi)，退出时 lo == hi 就是插入点。
    """
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def search_rotated(nums: Sequence[int], target: int) -> int:
    """旋转有序数组查找，找不到返回 -1。O(log n)。

    每轮至少有一半是有序的：比较 nums[mid] 与 nums[lo]，判断哪半有序，
    再判断 target 是否落在有序那半的值域内。边界用 <= 覆盖重复值场景的退化。
    """
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:  # 左半有序
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:  # 右半有序
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1


# ---------------------------------------------------------------------------
# 4. 图与网格：BFS 求最短路，DFS 求连通块
# ---------------------------------------------------------------------------


def bfs_shortest(
    grid: Sequence[Sequence[int]],
    start: Tuple[int, int],
    goal: Tuple[int, int],
) -> int:
    """0/1 网格四方向最短路（0 可走），不可达返回 -1。O(V+E)。

    为什么 BFS 能求最短路：队列按层扩展，第一次弹出 goal 时的距离就是最小距离。
    入队即标记 visited，不能等出队再标记，否则同一节点会被多个前驱重复入队。
    """
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] or grid[goal[0]][goal[1]]:
        return -1
    q = deque([(start, 0)])
    seen = {start}
    while q:
        (r, c), d = q.popleft()
        if (r, c) == goal:
            return d
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and not grid[nr][nc] and (nr, nc) not in seen:
                seen.add((nr, nc))
                q.append(((nr, nc), d + 1))
    return -1


def count_islands(grid: Sequence[Sequence[int]]) -> int:
    """岛屿数量（1 为陆地）。O(V+E) / O(V)。

    用「淹没」代替 visited 集合：访问过的陆地直接改成 0，省内存也省一次查找。
    代价是原地修改输入；面试时要主动说明这一点，或改成显式 visited。
    """
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])

    def sink(r: int, c: int) -> None:
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            if 0 <= cr < rows and 0 <= cc < cols and grid[cr][cc] == 1:
                grid[cr][cc] = 0
                stack.extend(((cr + 1, cc), (cr - 1, cc), (cr, cc + 1), (cr, cc - 1)))

    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1:
                count += 1
                sink(r, c)
    return count


# ---------------------------------------------------------------------------
# 5. 动态规划：先写状态定义，再写转移，最后想边界
# ---------------------------------------------------------------------------


def climb_stairs(n: int) -> int:
    """爬楼梯。O(n) / O(1)。dp[i] = dp[i-1] + dp[i-2]，只留两个变量。"""
    if n <= 2:
        return n
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b


def lis(nums: Sequence[int]) -> int:
    """最长上升子序列长度。O(n log n)。

    tails[k] = 长度为 k+1 的上升子序列中，结尾最小的那个值。
    结尾越小，后面越容易接上——所以对每个 x 只需替换第一个 >= x 的位置。
    tails 本身不是某个真实子序列，不要拿它当答案输出。
    """
    tails: List[int] = []
    for x in nums:
        i = lower_bound(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return len(tails)


def knapsack(weights: Sequence[int], values: Sequence[int], capacity: int) -> int:
    """0/1 背包最大价值。O(n*W) / O(W)。

    一维数组必须**倒序**遍历容量：正序会让同一件物品被重复放进去（变成完全背包）。
    """
    dp = [0] * (capacity + 1)
    for w, v in zip(weights, values):
        for cap in range(capacity, w - 1, -1):
            dp[cap] = max(dp[cap], dp[cap - w] + v)
    return dp[capacity]


# ---------------------------------------------------------------------------
# 6. Top-K：小顶堆维护「当前最好的 k 个」
# ---------------------------------------------------------------------------


def top_k(nums: Sequence[int], k: int) -> List[int]:
    """前 k 大，降序返回。O(n log k) / O(k)。

    堆顶是这 k 个里最小的。新元素只要比堆顶大，就替换堆顶。
    为什么不是大顶堆：大顶堆能拿到最大，但拿不到「第 k 个」的门槛。
    """
    if k <= 0:
        return []
    heap: List[int] = []
    for x in nums:
        if len(heap) < k:
            heapq.heappush(heap, x)
        elif x > heap[0]:
            heapq.heapreplace(heap, x)
    return sorted(heap, reverse=True)


# ---------------------------------------------------------------------------
# 7. 链表：双指针与「哑节点」
# ---------------------------------------------------------------------------


def reverse_list(head: Optional[ListNode]) -> Optional[ListNode]:
    """反转链表。O(n) / O(1)。

    三指针：prev 是已反转部分的头，cur 是待处理部分，nxt 暂存。
    先存 nxt 再改 cur.next，顺序反了就丢链。
    """
    prev, cur = None, head
    while cur:
        nxt = cur.next
        cur.next = prev
        prev, cur = cur, nxt
    return prev


def has_cycle(head: Optional[ListNode]) -> bool:
    """环形链表（Floyd 判圈）。O(n) / O(1)。

    快指针每次 2 步、慢指针 1 步。若有环，二者相对速度为 1，必然相遇；
    若无环，快指针先到 None。
    """
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:
            return True
    return False


# ---------------------------------------------------------------------------
# 8. 回溯：选择 → 递归 → 撤销选择
# ---------------------------------------------------------------------------


def permutations(nums: Sequence[int]) -> List[List[int]]:
    """全排列。O(n * n!) 时间。

    用 used 数组而不是 pop(i)，因为回溯时要按原顺序恢复；
    path[:] 拷贝是必须的，否则最后所有结果都指向同一个被清空的列表。
    """
    res: List[List[int]] = []
    path: List[int] = []
    used = [False] * len(nums)

    def dfs() -> None:
        if len(path) == len(nums):
            res.append(path[:])
            return
        for i, x in enumerate(nums):
            if used[i]:
                continue
            used[i] = True
            path.append(x)
            dfs()
            path.pop()
            used[i] = False

    dfs()
    return res


def n_queens(n: int) -> int:
    """N 皇后解的个数。O(n!)，用三个集合把冲突检查降到 O(1)。

    列、主对角线（r-c 恒定）、副对角线（r+c 恒定）各一个集合。
    这三条不变量是本题唯一的难点，写下来就不会漏。
    """
    cols: set[int] = set()
    diag1: set[int] = set()
    diag2: set[int] = set()
    count = 0

    def dfs(r: int) -> None:
        nonlocal count
        if r == n:
            count += 1
            return
        for c in range(n):
            if c in cols or (r - c) in diag1 or (r + c) in diag2:
                continue
            cols.add(c)
            diag1.add(r - c)
            diag2.add(r + c)
            dfs(r + 1)
            cols.remove(c)
            diag1.remove(r - c)
            diag2.remove(r + c)

    dfs(0)
    return count


# ---------------------------------------------------------------------------
# 9. 自检与演示
# ---------------------------------------------------------------------------

TEMPLATES = [
    ("哈希表", "two_sum", "O(n) / O(n)", "无序两数之和、去重、计数"),
    ("双指针", "two_sum_sorted", "O(n) / O(1)", "有序数组、盛水、三数之和"),
    ("滑动窗口", "min_window", "O(n) / O(k)", "最长/最短连续子段"),
    ("二分", "lower_bound", "O(log n)", "边界查找、旋转数组、答案二分"),
    ("BFS", "bfs_shortest", "O(V+E)", "网格最短路、层序遍历"),
    ("DFS", "count_islands", "O(V+E)", "连通块、拓扑、树的遍历"),
    ("DP", "knapsack", "O(n*W)", "最优子结构 + 重叠子问题"),
    ("堆", "top_k", "O(n log k)", "Top-K、中位数、合并 K 路"),
    ("回溯", "n_queens", "O(n!)", "排列组合、棋盘、子集"),
]


def run_self_test() -> int:
    checks = 0

    def eq(actual, expected, label: str) -> None:
        nonlocal checks
        assert actual == expected, f"{label}: got {actual!r}, want {expected!r}"
        checks += 1

    eq(two_sum([2, 7, 11, 15], 9), (0, 1), "two_sum")
    eq(two_sum([3, 2, 4], 6), (1, 2), "two_sum 重复值")
    eq(two_sum_sorted([1, 2, 3, 4, 6], 6), (1, 3), "two_sum_sorted")
    eq(max_area([1, 8, 6, 2, 5, 4, 8, 3, 7]), 49, "max_area")
    eq(longest_unique_substring("abcabcbb"), 3, "longest_unique")
    eq(longest_unique_substring("pwwkew"), 3, "longest_unique 2")
    eq(min_window("ADOBECODEBANC", "ABC"), "BANC", "min_window")
    eq(min_window("a", "aa"), "", "min_window 重复字符")
    eq(lower_bound([1, 3, 3, 5], 3), 1, "lower_bound")
    eq(lower_bound([1, 3, 3, 5], 6), 4, "lower_bound 末尾")
    eq(search_rotated([4, 5, 6, 7, 0, 1, 2], 0), 4, "search_rotated")
    eq(search_rotated([4, 5, 6, 7, 0, 1, 2], 3), -1, "search_rotated 缺失")

    grid = [
        [0, 0, 0, 1],
        [1, 1, 0, 1],
        [0, 0, 0, 0],
    ]
    eq(bfs_shortest(grid, (0, 0), (2, 3)), 5, "bfs_shortest")
    eq(bfs_shortest(grid, (0, 0), (0, 3)), -1, "bfs 不可达")
    eq(
        count_islands(
            [
                [1, 1, 0, 0],
                [1, 0, 0, 1],
                [0, 0, 1, 0],
            ]
        ),
        3,
        "count_islands",
    )
    eq(climb_stairs(5), 8, "climb_stairs")
    eq(lis([10, 9, 2, 5, 3, 7, 101, 18]), 4, "lis")
    eq(knapsack([1, 3, 4, 5], [1, 4, 5, 7], 7), 9, "knapsack")
    eq(top_k([3, 1, 4, 1, 5, 9, 2, 6], 3), [9, 6, 5], "top_k")
    eq(list_to_list(reverse_list(build_list([1, 2, 3]))), [3, 2, 1], "reverse_list")

    cyc = build_list([1, 2, 3])
    eq(has_cycle(cyc), False, "has_cycle 无环")
    assert cyc is not None and cyc.next is not None
    cyc.next.next.next = cyc  # 人为造环
    eq(has_cycle(cyc), True, "has_cycle 有环")

    eq(sorted(permutations([1, 2, 3])), sorted([[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]), "permutations")
    eq(n_queens(4), 2, "n_queens 4")
    eq(n_queens(8), 92, "n_queens 8")
    print(f"✅ 01-algorithm-templates: {checks} 项断言全部通过")
    return checks


def demo(name: str) -> None:
    demos = {
        "two_sum": lambda: two_sum([2, 7, 11, 15], 9),
        "two_sum_sorted": lambda: two_sum_sorted([1, 2, 3, 4, 6], 6),
        "max_area": lambda: max_area([1, 8, 6, 2, 5, 4, 8, 3, 7]),
        "longest_unique_substring": lambda: longest_unique_substring("abcabcbb"),
        "min_window": lambda: min_window("ADOBECODEBANC", "ABC"),
        "lower_bound": lambda: lower_bound([1, 3, 3, 5], 3),
        "search_rotated": lambda: search_rotated([4, 5, 6, 7, 0, 1, 2], 0),
        "bfs_shortest": lambda: bfs_shortest([[0, 0], [0, 0]], (0, 0), (1, 1)),
        "count_islands": lambda: count_islands([[1, 1, 0], [0, 1, 0], [1, 0, 1]]),
        "climb_stairs": lambda: climb_stairs(10),
        "lis": lambda: lis([10, 9, 2, 5, 3, 7, 101, 18]),
        "knapsack": lambda: knapsack([1, 3, 4, 5], [1, 4, 5, 7], 7),
        "top_k": lambda: top_k([3, 1, 4, 1, 5, 9, 2, 6], 3),
        "reverse_list": lambda: list_to_list(reverse_list(build_list([1, 2, 3]))),
        "has_cycle": lambda: has_cycle(build_list([1, 2, 3])),
        "permutations": lambda: permutations([1, 2]),
        "n_queens": lambda: n_queens(6),
    }
    if name not in demos:
        print(f"未知模板 {name!r}，可选：{', '.join(sorted(demos))}")
        return
    print(f"{name} → {demos[name]()}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Day 197 算法模板库")
    parser.add_argument("--self-test", action="store_true", help="运行全部断言")
    parser.add_argument("--demo", metavar="NAME", help="运行单个模板示例")
    args = parser.parse_args(argv)

    if args.self_test:
        return 0 if run_self_test() else 1
    if args.demo:
        demo(args.demo)
        return 0

    print("Day 197 算法模板速查（共 9 类）\n")
    print(f"{'类别':<8}{'入口函数':<22}{'复杂度':<18}适用场景")
    print("-" * 86)
    for cat, fn, cx, scene in TEMPLATES:
        print(f"{cat:<8}{fn:<22}{cx:<18}{scene}")
    print("\n提示：python3 01-algorithm-templates.py --self-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
