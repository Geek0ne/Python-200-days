#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Day 197 — Python 八股文：12 个「能跑出来」的答案

面试里最危险的不是不会，而是背了一句自己没验证过的话。
比如「Python 有 GIL，所以多线程没用」——IO 密集场景多线程有效；
「小整数有缓存」——只对 -5..256 成立，且 == 与 is 是两件事。

本文件的每个结论都对应一段可执行代码和一条断言：
    python3 02-python-interview-facts.py            # 逐条打印结论与实测值
    python3 02-python-interview-facts.py --self-test
    python3 02-python-interview-facts.py --json     # 给评分器/笔记用

环境：Python 3.12.3 / Linux / 4 vCPU（微型基准只用于量级对比）
"""
from __future__ import annotations

import argparse
import functools
import json
import sys
import timeit
import tracemalloc
from typing import Callable, Dict, List, Tuple

# ---------------------------------------------------------------------------
# 1. 可变默认参数：默认值只求值一次，且挂在函数对象上
# ---------------------------------------------------------------------------


def append_bad(x: int, bucket: List[int] = []) -> List[int]:
    """错误示范：bucket 在 def 执行时创建一次，之后所有调用共享。"""
    bucket.append(x)
    return bucket


def append_good(x: int, bucket: List[int] | None = None) -> List[int]:
    """正确写法：默认 None，函数体内新建。None 是哨兵，不是有效业务值。"""
    if bucket is None:
        bucket = []
    bucket.append(x)
    return bucket


# ---------------------------------------------------------------------------
# 2. 闭包晚绑定：函数体里的自由变量在「调用时」取值
# ---------------------------------------------------------------------------


def make_multipliers_bad() -> List[Callable[[int], int]]:
    funcs = []
    for i in range(3):
        funcs.append(lambda x: x * i)  # i 是自由变量，调用时才读
    return funcs


def make_multipliers_good() -> List[Callable[[int], int]]:
    funcs = []
    for i in range(3):
        funcs.append(lambda x, i=i: x * i)  # 默认参数在定义时求值，冻结当前 i
    return funcs


# ---------------------------------------------------------------------------
# 3. is / == / 小整数缓存 / 字符串驻留
# ---------------------------------------------------------------------------


def identity_facts() -> Dict[str, object]:
    a, b = 256, 256
    c, d = int("257"), int("257")
    # 编译期同一常量会合并；运行时拼接不会自动驻留
    lit = "hello world"
    e = "hello" + " world"  # 编译期常量折叠，与 lit 指向同一对象
    f = "".join(["hello", " world"])
    return {
        "256 is 256": a is b,
        "int('257') is int('257')": c is d,
        "257 == 257": c == d,
        "literal_is_literal": e is lit,
        "join_is_literal": f is lit,
        "join_equals": f == e,
        "sys.intern_equal": sys.intern(f) is sys.intern(lit),
    }


# ---------------------------------------------------------------------------
# 4. 字典为什么快：哈希 + 开放寻址；列表查找是线性扫描
# ---------------------------------------------------------------------------


def dict_vs_list_lookup(n: int = 10_000, rounds: int = 200) -> Tuple[float, float]:
    data_list = list(range(n))
    data_dict = {v: v for v in data_list}
    keys = [n - 1 - (i % n) for i in range(rounds)]

    def list_lookup() -> int:
        hits = 0
        for k in keys:
            if k in data_list:
                hits += 1
        return hits

    def dict_lookup() -> int:
        hits = 0
        for k in keys:
            if k in data_dict:
                hits += 1
        return hits

    # 必须比较结果，避免解释器把「无用计算」优化掉（CPython 不会，但习惯要好）
    assert list_lookup() == dict_lookup() == rounds
    t_list = timeit.timeit(list_lookup, number=1)
    t_dict = timeit.timeit(dict_lookup, number=1)
    return t_list, t_dict


# ---------------------------------------------------------------------------
# 5. 迭代器协议：__iter__ 返回迭代器，__next__ 抛 StopIteration 结束
# ---------------------------------------------------------------------------


class Countdown:
    """手写迭代器，展示「可迭代对象」与「迭代器」的区别。"""

    def __init__(self, start: int) -> None:
        self.current = start

    def __iter__(self) -> "Countdown":
        return self  # 迭代器返回自身，所以只能遍历一次

    def __next__(self) -> int:
        if self.current <= 0:
            raise StopIteration
        value = self.current
        self.current -= 1
        return value


def generator_memory(n: int = 200_000) -> Tuple[int, int]:
    """列表推导 vs 生成器表达式，用 tracemalloc 测峰值增量（字节）。"""

    def build_list() -> List[int]:
        return [i * i for i in range(n)]

    def build_gen() -> int:
        return sum(i * i for i in range(n))

    tracemalloc.start()
    lst = build_list()
    _, peak_list = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del lst

    tracemalloc.start()
    total = build_gen()
    _, peak_gen = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert total == sum(i * i for i in range(n))
    return peak_list, peak_gen


# ---------------------------------------------------------------------------
# 6. 装饰器：本质是「函数 → 函数」，wraps 修的是元数据不是行为
# ---------------------------------------------------------------------------


def timed(fn: Callable[..., object]) -> Callable[..., object]:
    @functools.wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> object:
        start = timeit.default_timer()
        try:
            return fn(*args, **kwargs)
        finally:
            wrapper.last_seconds = timeit.default_timer() - start  # type: ignore[attr-defined]

    wrapper.last_seconds = 0.0  # type: ignore[attr-defined]
    return wrapper


@timed
def add(a: int, b: int) -> int:
    return a + b


def decorator_facts() -> Dict[str, object]:
    _ = add(1, 2)
    wrapped = timed(lambda: 1)
    noop = lambda: 1
    t_plain = timeit.timeit(noop, number=200_000)
    t_wrapped = timeit.timeit(wrapped, number=200_000)
    return {
        "name_preserved": add.__name__,
        "doc_preserved": add.__doc__ is None,  # 本函数没写 docstring
        "plain_200k_s": round(t_plain, 4),
        "wrapped_200k_s": round(t_wrapped, 4),
        "overhead_us_per_call": round((t_wrapped - t_plain) / 200_000 * 1e6, 3),
    }


# ---------------------------------------------------------------------------
# 7. MRO：C3 线性化，保证「子类先于父类、声明顺序靠前者优先」
# ---------------------------------------------------------------------------


class A:
    def who(self) -> str:
        return "A"


class B(A):
    def who(self) -> str:
        return "B"


class C(A):
    def who(self) -> str:
        return "C"


class D(B, C):
    pass


# ---------------------------------------------------------------------------
# 8. 异常：finally 里的 return 会吞掉异常与返回值
# ---------------------------------------------------------------------------


def finally_swallows() -> str:
    try:
        raise RuntimeError("boom")
    finally:
        return "finally wins"  # 不要在生产代码里这样写


def exception_facts() -> Dict[str, object]:
    caught = None
    try:
        finally_swallows()
    except RuntimeError as exc:  # 不会执行，因为异常被 finally 的 return 吞了
        caught = str(exc)
    return {"raised_inside": "RuntimeError('boom')", "caught_outside": caught, "returned": finally_swallows()}


# ---------------------------------------------------------------------------
# 9. 浅拷贝 / 深拷贝 / 可变与不可变
# ---------------------------------------------------------------------------


def copy_facts() -> Dict[str, object]:
    import copy

    original = [[1, 2], [3, 4]]
    shallow = copy.copy(original)
    deep = copy.deepcopy(original)
    shallow[0].append(99)
    return {
        "shallow_shares_inner": original[0] == [1, 2, 99],
        "deep_independent": deep[0] == [1, 2],
        "original_is_shallow_equal": original == shallow,
    }


# ---------------------------------------------------------------------------
# 10. __slots__：省的是 __dict__，代价是不能动态加属性
# ---------------------------------------------------------------------------


class PointDict:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


class PointSlots:
    __slots__ = ("x", "y")

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


def slots_facts() -> Dict[str, object]:
    pd, ps = PointDict(1, 2), PointSlots(1, 2)
    dynamic_ok = True
    try:
        ps.z = 3  # type: ignore[attr-defined]
    except AttributeError:
        dynamic_ok = False
    return {
        "dict_bytes": sys.getsizeof(pd) + sys.getsizeof(pd.__dict__),
        "slots_bytes": sys.getsizeof(ps),
        "slots_allow_dynamic_attr": dynamic_ok,
    }


# ---------------------------------------------------------------------------
# 11. 排序：Timsort 稳定，key 只调用一次
# ---------------------------------------------------------------------------


def sort_facts() -> Dict[str, object]:
    rows = [("b", 2), ("a", 1), ("b", 1)]
    by_first = sorted(rows, key=lambda r: r[0])
    calls = {"n": 0}

    def key(r: Tuple[str, int]) -> str:
        calls["n"] += 1
        return r[0]

    sorted(rows, key=key)
    return {
        "stable_keeps_input_order": by_first == [("a", 1), ("b", 2), ("b", 1)],
        "key_calls": calls["n"],
        "rows": len(rows),
    }


# ---------------------------------------------------------------------------
# 12. 可变对象作为字典键：必须可哈希
# ---------------------------------------------------------------------------


def hashable_facts() -> Dict[str, object]:
    ok_tuple = ("a", 1)
    d = {ok_tuple: "yes"}
    list_key_error = None
    try:
        {["a"]: 1}  # type: ignore[dict-item]
    except TypeError as exc:
        list_key_error = type(exc).__name__
    return {"tuple_key": d[ok_tuple], "list_key_error": list_key_error}


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------


def collect() -> Dict[str, object]:
    t_list, t_dict = dict_vs_list_lookup()
    peak_list, peak_gen = generator_memory()
    deco = decorator_facts()
    facts: Dict[str, object] = {
        "mutable_default": {
            # 必须切片拷贝：直接存引用的话，两次调用其实是同一个 list
            "bad_calls": [append_bad(1)[:], append_bad(2)[:]],
            "good_calls": [append_good(1), append_good(2)],
        },
        "late_binding": {
            "bad": [f(10) for f in make_multipliers_bad()],
            "good": [f(10) for f in make_multipliers_good()],
        },
        "identity": identity_facts(),
        "lookup": {
            "n": 10_000,
            "rounds": 200,
            "list_ms": round(t_list * 1e3, 2),
            "dict_ms": round(t_dict * 1e3, 2),
            "speedup": round(t_list / t_dict, 1),
        },
        "iteration": {
            "countdown": list(Countdown(3)),
            "iterator_is_iterable": iter(Countdown(1)) is not None,
            "peak_list_kb": round(peak_list / 1024, 1),
            "peak_gen_kb": round(peak_gen / 1024, 1),
            "memory_ratio": round(peak_list / max(peak_gen, 1), 1),
        },
        "decorator": deco,
        "mro": [cls.__name__ for cls in D.__mro__],
        "exception": exception_facts(),
        "copy": copy_facts(),
        "slots": slots_facts(),
        "sort": sort_facts(),
        "hashable": hashable_facts(),
    }
    return facts


def run_self_test(facts: Dict[str, object]) -> int:
    checks = 0

    def check(cond: bool, label: str) -> None:
        nonlocal checks
        assert cond, label
        checks += 1

    check(facts["mutable_default"]["bad_calls"] == [[1], [1, 2]], "可变默认参数应被共享")
    check(facts["mutable_default"]["good_calls"] == [[1], [2]], "None 哨兵应每次新建")
    check(facts["late_binding"]["bad"] == [20, 20, 20], "闭包晚绑定应全取最后的 i")
    check(facts["late_binding"]["good"] == [0, 10, 20], "默认参数应冻结 i")

    ident = facts["identity"]
    check(ident["256 is 256"] is True, "小整数缓存")
    check(ident["int('257') is int('257')"] is False, "257 超出缓存")
    check(ident["257 == 257"] is True, "== 比较值")
    check(ident["literal_is_literal"] is True, "同代码对象常量合并")
    check(ident["join_is_literal"] is False, "运行时拼接默认不驻留")
    check(ident["join_equals"] is True, "值相等")
    check(ident["sys.intern_equal"] is True, "intern 后同一对象")

    lookup = facts["lookup"]
    check(lookup["dict_ms"] < lookup["list_ms"], "字典查找应快于列表线性扫描")
    check(facts["iteration"]["countdown"] == [3, 2, 1], "迭代器协议")
    check(facts["iteration"]["peak_gen_kb"] < facts["iteration"]["peak_list_kb"], "生成器应更省内存")

    deco = facts["decorator"]
    check(deco["name_preserved"] == "add", "wraps 保留 __name__")
    check(deco["overhead_us_per_call"] > 0, "装饰器有额外调用开销")
    check(facts["mro"] == ["D", "B", "C", "A", "object"], "C3 线性化顺序")
    check(facts["exception"]["caught_outside"] is None, "finally return 吞异常")
    check(facts["copy"]["shallow_shares_inner"] is True, "浅拷贝共享内层")
    check(facts["copy"]["deep_independent"] is True, "深拷贝独立")
    check(facts["slots"]["slots_bytes"] < facts["slots"]["dict_bytes"], "__slots__ 更省内存")
    check(facts["slots"]["slots_allow_dynamic_attr"] is False, "__slots__ 禁止动态属性")
    check(facts["sort"]["stable_keeps_input_order"] is True, "排序稳定")
    check(facts["sort"]["key_calls"] == facts["sort"]["rows"], "key 每个元素只调一次")
    check(facts["hashable"]["list_key_error"] == "TypeError", "list 不可哈希")
    print(f"✅ 02-python-interview-facts: {checks} 项断言全部通过")
    return checks


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Day 197 Python 八股文实测")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    facts = collect()
    if args.self_test:
        return 0 if run_self_test(facts) else 1
    if args.json:
        print(json.dumps(facts, ensure_ascii=False, indent=2, default=str))
        return 0

    print("Day 197 · Python 八股文 12 条（全部本机实测）\n")
    print("1) 可变默认参数")
    print(f"   bad : {facts['mutable_default']['bad_calls']}  ← 两次调用共享同一个 list")
    print(f"   good: {facts['mutable_default']['good_calls']}  ← None 哨兵每次新建")
    print("\n2) 闭包晚绑定")
    print(f"   bad : {facts['late_binding']['bad']}   good: {facts['late_binding']['good']}")
    print("\n3) is / == / 缓存")
    for k, v in facts["identity"].items():
        print(f"   {k:<32} → {v}")
    print("\n4) dict vs list 查找（1 万键 × 200 次）")
    print(f"   list {facts['lookup']['list_ms']} ms / dict {facts['lookup']['dict_ms']} ms "
          f"→ {facts['lookup']['speedup']}x")
    print("\n5) 生成器内存（20 万元素）")
    print(f"   list 峰值 {facts['iteration']['peak_list_kb']} KB / gen 峰值 "
          f"{facts['iteration']['peak_gen_kb']} KB → {facts['iteration']['memory_ratio']}x")
    print("\n6) 装饰器")
    print(f"   __name__={facts['decorator']['name_preserved']}  "
          f"每次额外开销 {facts['decorator']['overhead_us_per_call']} µs")
    print("\n7) MRO: " + " → ".join(facts["mro"]))
    print("\n8) finally 里的 return 吞掉异常："
          f" 外部捕获={facts['exception']['caught_outside']}，返回值={facts['exception']['returned']!r}")
    print("\n9) 拷贝：" + json.dumps(facts["copy"], ensure_ascii=False))
    print("\n10) __slots__：" + json.dumps(facts["slots"], ensure_ascii=False))
    print("\n11) 排序：" + json.dumps(facts["sort"], ensure_ascii=False))
    print("\n12) 可哈希：" + json.dumps(facts["hashable"], ensure_ascii=False))
    print("\n提示：--self-test 跑断言，--json 导出全部实测值")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
