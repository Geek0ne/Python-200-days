#!/usr/bin/env python3
"""Day 194 共享库：合成语料、文本清洗、URL 规范化、SimHash、质量规则。

设计原则
--------
1. 零外部服务：所有脚本都能在离线机器上跑通，不依赖数据库/Redis/API。
2. 固定随机种子：每次跑出的数字必须可复现，否则"实测"没有意义。
3. 合成数据的定位：只用来验证**管道逻辑**和**评估方法**是否正确，
   不能代表线上分布。真实项目要换成爬虫日志与人工标注样本。

运行自检：
    python3 pipeline_lib.py --self-test
"""

from __future__ import annotations

import functools
import html as html_mod
import json
import random
import re
import sys
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# ────────────────────────────── 特征定义 ──────────────────────────────

FEATURES = [
    "status_code",
    "body_len",
    "latency_ms",
    "captcha",
    "retry_after",
    "waf_cookie",
    "header_count",
    "js_challenge",
    "redirect_hops",
    "ua_known_bot",
]

FEATURE_HELP = {
    "status_code": "HTTP 状态码，403/429/503 是显式拒绝",
    "body_len": "响应体字节数，拦截页通常远小于正常页",
    "latency_ms": "首字节到收完的耗时，封禁常伴随限速",
    "captcha": "响应里是否出现验证码元素（图片/滑块/iframe）",
    "retry_after": "是否有 Retry-After 头",
    "waf_cookie": "是否下发 WAF 挑战 cookie（如 acw_sc__v2、cf_clearance）",
    "header_count": "响应头数量，拦截页往往头更少",
    "js_challenge": "是否返回 JS 挑战脚本（5 秒盾）",
    "redirect_hops": "重定向跳数，多次跳转常指向封禁落地页",
    "ua_known_bot": "UA 是否命中已知爬虫特征",
}


def synth_responses(n: int = 3000, seed: int = 194) -> list[dict]:
    """生成带标签的爬虫响应样本。

    生成逻辑刻意做成"有重叠"：真实风控不会给你一个线性可分的世界。
    标签也带 4% 噪声（人工标注本身就会错），避免模型看起来完美得可疑。
    """
    rng = random.Random(seed)
    rows: list[dict] = []
    for _ in range(n):
        # 隐藏变量：这个 IP+指纹组合的"风控风险倾向"，爬虫观察不到
        propensity = rng.betavariate(1.6, 3.0)
        blocked = int(propensity + rng.gauss(0, 0.12) > 0.52)

        # 硬封 / 软封 / 限速：三种拒绝方式，特征各不同
        kind = rng.choices(["hard", "soft", "limited"], weights=[0.55, 0.25, 0.20])[0]
        if blocked and kind == "hard":
            status = rng.choice([403, 403, 401])
            body_len = rng.randint(400, 3200)
        elif blocked and kind == "soft":
            status = 200  # 软封：照样 200，但页面是空壳/验证页
            body_len = rng.randint(800, 6000)
        elif blocked and kind == "limited":
            status = rng.choice([429, 503])
            body_len = rng.randint(200, 1200)
        else:
            status = 200
            body_len = rng.randint(18_000, 130_000)

        latency = max(20, int(rng.gauss(260 if blocked else 180, 90)))
        captcha = int(rng.random() < (0.03 + 0.55 * propensity))
        retry_after = int(status in (429, 503))
        waf_cookie = int(rng.random() < (0.08 + 0.45 * propensity))
        header_count = rng.randint(3, 9) if blocked else rng.randint(6, 18)
        js_challenge = int(rng.random() < (0.04 + 0.5 * propensity))
        redirect_hops = rng.choices([0, 1, 2, 3], weights=[0.7, 0.2, 0.07, 0.03])[0]
        ua_known_bot = int(rng.random() < 0.35)

        label = blocked
        if rng.random() < 0.04:  # 标注噪声
            label = 1 - label

        rows.append({
            "status_code": status,
            "body_len": body_len,
            "latency_ms": latency,
            "captcha": captcha,
            "retry_after": retry_after,
            "waf_cookie": waf_cookie,
            "header_count": header_count,
            "js_challenge": js_challenge,
            "redirect_hops": redirect_hops,
            "ua_known_bot": ua_known_bot,
            "label": label,
            # 下面两个字段只在生成器里用，不进模型（避免数据泄漏）
            "_propensity": round(propensity, 4),
            "_kind": kind,
        })
    return rows


def to_matrix(rows: Iterable[dict]) -> list[list[float]]:
    """按 FEATURES 顺序转成二维列表，不依赖 numpy 也能用。"""
    return [[float(r[f]) for f in FEATURES] for r in rows]


# ────────────────────────────── 文本清洗 ──────────────────────────────

_RE_SCRIPT = re.compile(r"<(script|style|noscript)\b[^>]*>.*?</\1>", re.S | re.I)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_WS = re.compile(r"[ \t\u00a0\u3000]+")
_RE_BLANK = re.compile(r"\n{3,}")
_RE_BOILER = re.compile(
    r"(版权所有|Copyright ©?\s*\d{4}.*|扫码关注|点击下载\s*APP|上一篇|下一篇)[^\n]*",
    re.I,
)
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None)


def clean_html(raw: str) -> str:
    """HTML → 干净正文。

    顺序很重要：先删 script/style（否则标签里的 JS 会被当成正文），
    再解实体（否则 &amp; 里的 ; 会被后续逻辑误判），最后压空白。
    """
    text = _RE_SCRIPT.sub(" ", raw)
    text = _RE_TAG.sub(" ", text)
    text = html_mod.unescape(text)
    text = text.translate(_ZERO_WIDTH)
    text = unicodedata.normalize("NFKC", text)  # 全角→半角，统一数字与括号
    text = _RE_WS.sub(" ", text)
    text = _RE_BOILER.sub("", text)
    return _RE_BLANK.sub("\n\n", text).strip()


# ────────────────────────────── URL 规范化 ──────────────────────────────

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "spm", "from", "share_token", "ref", "referer", "_t", "timestamp",
}


def canon_url(url: str, extra_drop: Iterable[str] = ()) -> str:
    """只删**已知**追踪参数，保留其余查询参数。

    这条规则是 Day 194 翻车实验的产物：早期版本"删掉全部查询串"，
    导致 ?sku=123 与 ?sku=456 被合并成同一行，商品数据静默丢失。
    """
    drop = TRACKING_PARAMS | set(extra_drop)
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = re.sub(r"/{2,}", "/", parts.path) or "/"
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k.lower() not in drop]
    query.sort()
    return urlunsplit((scheme, netloc, path, urlencode(query, doseq=True), ""))


# ────────────────────────────── SimHash ──────────────────────────────

_CJK = re.compile(r"[\u4e00-\u9fff]")
_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """中英混排分词：中文用字符二元组，英文用单词。

    不用 jieba 是刻意的：SimHash 只关心"哪些 token 变了"，
    二元组对未登录词和错别字更鲁棒，且零依赖。
    """
    lower = text.lower()
    tokens = _WORD.findall(lower)
    cjk = "".join(_CJK.findall(lower))
    tokens.extend(cjk[i:i + 2] for i in range(len(cjk) - 1))
    return tokens


@functools.lru_cache(maxsize=200_000)
def _token_hash(token: str) -> int:
    # 用内置 hash 会因 PYTHONHASHSEED 每次不同 → 结果不可复现，必须用稳定哈希
    import hashlib
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big")


def simhash(text: str, bits: int = 64) -> int:
    """经典 SimHash：token 哈希的每一位按权重投票。"""
    weights = [0] * bits
    counts: dict[str, int] = {}
    for tok in tokenize(text):
        counts[tok] = counts.get(tok, 0) + 1
    if not counts:
        return 0
    for tok, tf in counts.items():
        h = _token_hash(tok)
        w = 1 + (tf - 1) * 0.3  # 词频只轻微加权，避免关键词刷票
        for i in range(bits):
            weights[i] += w if (h >> i) & 1 else -w
    out = 0
    for i, w in enumerate(weights):
        if w > 0:
            out |= 1 << i
    return out


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def hash_to_signed(h: int, bits: int = 64) -> int:
    """64 位无符号哈希 → SQLite 能存的有符号整数。

    踩过的坑：sqlite3 的 INTEGER 是**有符号** 64 位，直接存 uint64 会抛
    OverflowError: Python int too large to convert to SQLite INTEGER。
    转成有符号后仍可按整数建索引，只是比较时要转回去。
    """
    return h - (1 << bits) if h >= (1 << (bits - 1)) else h


def signed_to_hash(v: int, bits: int = 64) -> int:
    """hash_to_signed 的逆运算。"""
    return v + (1 << bits) if v < 0 else v


class SimHashIndex:
    """分桶索引：把 64 位切成 bands 段，任一段完全相同才进入精确比对。

    鸽巢原理：汉明距离 ≤ bands-1 的两篇文档，bands 段里至少 1 段完全相同。
    所以 bands=4 只保证 k≤3，bands=16（每段 4 位）能保证 k≤15，
    但段越细、每段取值空间越小，桶里撞上的候选越多 —— 这是个明确的取舍。
    """

    def __init__(self, bits: int = 64, bands: int = 4):
        if bits % bands:
            raise ValueError("bits 必须能被 bands 整除")
        self.bits = bits
        self.bands = bands
        self.width = bits // bands
        self.mask = (1 << self.width) - 1
        self.buckets: dict[tuple[int, int], list[tuple[int, object]]] = {}

    @property
    def guaranteed_k(self) -> int:
        return self.bands - 1

    def _keys(self, h: int):
        for i in range(self.bands):
            yield i, (h >> (i * self.width)) & self.mask

    def add(self, h: int, payload=None) -> None:
        for k in self._keys(h):
            self.buckets.setdefault(k, []).append((h, payload))

    def query(self, h: int, k: int = 3):
        """返回 [(payload, distance)]，k 必须 ≤ bands-1 才能保证召回。

        注意去重键是 payload（文档 id），不是哈希值：
        早期版本用哈希值去重，凡是两篇文档哈希完全相同（比想象中常见，
        尤其转载稿），就会只保留最后一个 payload，静默漏掉重复对。
        """
        if k > self.guaranteed_k:
            raise ValueError(f"该索引只能保证 k <= {self.guaranteed_k} 的召回")
        seen: dict[object, int] = {}
        for key in self._keys(h):
            for other, payload in self.buckets.get(key, ()):
                if payload in seen:
                    continue
                d = hamming(h, other)
                if d <= k:
                    seen[payload] = d
        return sorted(seen.items(), key=lambda kv: kv[1])


# ────────────────────────────── 语料 ──────────────────────────────

# 语料片段池（对外暴露为 SENTENCES，供管道脚本复用）：每篇文档随机抽 7~10 段拼成，因此无关文档的 Jaccard 相似度天然偏低。
# 第一版生成器只用了 6 个模板句子，导致"无关文档"的 Jaccard 中位数高达 0.55，
# 去重指标全部失真（详见 README 翻车实验 2）。片段池是那次修复的产物。
_FRAGMENTS = [
    "欧洲经销商反馈冬季续航衰减是投诉最集中的问题",
    "国产车型的智能座舱在本地化适配上仍落后一个版本",
    "价格战让单车毛利在两年内从两位数压到个位数",
    "分布式事务的提交延迟在跨机房场景会被放大三倍",
    "列式存储对宽表的扫描裁剪效果取决于统计信息质量",
    "主从切换时未提交事务的回滚策略必须提前演练",
    "面团含水量每提高百分之五，组织气孔会明显变粗",
    "家用烤箱的上下火温差普遍在十五度以上",
    "天然酵母的发酵窗口受室温影响远大于配方",
    "滨江绿道周末早八点前机动车禁行",
    "连续爬坡路段建议把踏频维持在七十以上",
    "夜骑必须配备前后灯与反光条，否则会被劝返",
    "事件循环里任何超过五十毫秒的同步调用都会拖慢整体吞吐",
    "异步任务要显式处理取消，否则连接会泄漏",
    "协程池的并发上限应该由下游限流值反推",
    "一爆开始后脱水速率骤降，升温过快会带来焦苦",
    "浅烘豆的赏味期通常只有三到四周",
    "研磨度调整应该一次只动一个刻度",
    "接口鉴权应统一走网关，业务侧只信任网关注入的身份",
    "日志脱敏要在采集端完成，落盘后再脱敏已经晚了",
    "限流阈值必须留出至少三成余量给突发流量",
    "灰度发布要先切百分之一的真实流量观察错误率",
    "缓存击穿的高发点是热点键过期的那一瞬间",
    "数据库连接池的等待队列长度要小于上游超时时间",
    "监控告警的噪音比漏报更容易摧毁团队信任",
    "压测环境与生产环境的机器规格差异会让结论失真",
    "代码评审的重点应该是边界条件而不是命名风格",
    "单元测试覆盖的是分支，不是行数",
    "依赖升级要先读变更日志再跑回归",
    "离线任务的调度依赖要避免隐式的跨天耦合",
    "数据质量校验失败时应该阻断下游而不是告警了事",
    "爬虫的并发数应该由目标站点的承载能力决定",
    "请求指纹不一致比 IP 封禁更容易被识别",
    "重试必须带退避，否则等于主动触发风控",
    "结构化抽取的字段缺失率要在入库前统计",
    "文本清洗的顺序错了会把正文里的代码当成标签删掉",
    "去重阈值应随文档长度调整，短文本对改动更敏感",
    "模型上线前要用时间切分验证，随机切分会高估效果",
    "标注口径不一致会让离线指标彻底失去意义",
    "任何自动化流程都要有一个人工兜底的出口",
]


def synth_corpus(n: int = 1200, dup_ratio: float = 0.30, seed: int = 194) -> list[dict]:
    """生成"原创 + 近重复"混合语料，用于去重实验。

    近重复的构造方式贴近真实转载：加站点前缀、改标点、插广告词、
    换数字/日期，正文主体保持 85% 以上一致。
    """
    rng = random.Random(seed)
    docs: list[dict] = []
    originals: list[tuple[int, str]] = []
    for i in range(n):
        if originals and rng.random() < dup_ratio:
            base_id, base = rng.choice(originals)
            text = mutate(base, rng)
            docs.append({"id": i, "text": text, "base_id": base_id, "is_dup": True})
        else:
            frags = rng.sample(_FRAGMENTS, rng.randint(7, 10))
            text = f"样本编号 {i:05d}。" + "".join(f + "。" for f in frags)
            originals.append((i, text))
            docs.append({"id": i, "text": text, "base_id": i, "is_dup": False})
    return docs


def mutate(text: str, rng: random.Random) -> str:
    """模拟转载改写：前缀、标点替换、插入推广语、局部同义替换。"""
    out = "【转载】" + text.replace("，", ",").replace("。", ".")
    out = out.replace("效率", rng.choice(["效率", "效能"]))
    if rng.random() < 0.5:
        out += "（本文由 XX 观察整理，转载请注明出处）"
    return out


# ────────────────────────────── 质量规则 ──────────────────────────────

@dataclass
class Issue:
    code: str
    field: str
    detail: str


_MOJIBAKE_SEQ = re.compile(r"(Ã.|â€|ï¿½|\ufffd)")
_SUSPECT = re.compile(r"[\u0080-\u00bf\u00c0-\u00ff]")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def looks_mojibake(text: str, threshold: float = 0.15) -> bool:
    """判断"GBK 被当 UTF-8 解码"这类乱码。

    三种信号，任一命中即判定：
      1. 出现替换符 / 经典乱码三连（Ã.、â€、ï¿½）
      2. Latin-1 补充区字符占比过高 —— 中文正文里不该有 ä¸­æ–‡ 这种密度
      3. 整段能用 cp1252 编码、再用 utf-8 解码成功且得到汉字（可逆修复）

    这是启发式，不是判定器：法语/德语正文的变音符号会被第 2 条误伤，
    所以阈值取 0.15 而不是 0.05。宁可漏一点，不要把正常外文当乱码隔离。
    """
    if not text:
        return False
    if _MOJIBAKE_SEQ.search(text):
        return True
    letters = [c for c in text if not c.isspace()]
    if len(letters) < 4:
        return False
    if len(_SUSPECT.findall(text)) / len(letters) >= threshold:
        return True
    try:
        repaired = text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False
    return bool(_CJK.search(repaired))


def check_record(rec: dict) -> list[Issue]:
    """质量门禁：只做"能明确判定错"的规则，不做主观判断。"""
    issues: list[Issue] = []
    title = (rec.get("title") or "").strip()
    if not title:
        issues.append(Issue("TITLE_EMPTY", "title", "标题为空"))
    elif len(title) > 200:
        issues.append(Issue("TITLE_TOO_LONG", "title", f"{len(title)} 字"))

    price = rec.get("price")
    if price is None:
        issues.append(Issue("PRICE_MISSING", "price", "无价格"))
    else:
        try:
            p = float(price)
        except (TypeError, ValueError):
            issues.append(Issue("PRICE_NOT_NUMBER", "price", repr(price)))
        else:
            if p <= 0 or p > 5_000_000:
                issues.append(Issue("PRICE_OUTLIER", "price", str(p)))

    date = rec.get("published_at") or ""
    if not _DATE.match(date):
        issues.append(Issue("DATE_BAD", "published_at", date))
    else:
        y, m, d = (int(x) for x in date.split("-"))
        if not (2000 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31):
            issues.append(Issue("DATE_OUT_OF_RANGE", "published_at", date))

    text = rec.get("text") or ""
    if len(text) < 50:
        issues.append(Issue("TEXT_TOO_SHORT", "text", f"{len(text)} 字"))
    # 标题和正文分开判：正文很长时会把标题里的乱码比例稀释掉
    if looks_mojibake(title) or looks_mojibake(text):
        issues.append(Issue("MOJIBAKE", "text", "疑似 GBK/UTF-8 混用"))

    url = rec.get("url") or ""
    if not url.startswith(("http://", "https://")):
        issues.append(Issue("URL_BAD", "url", url[:60]))
    return issues


# ────────────────────────────── 自检 ──────────────────────────────

def _self_test() -> int:
    failures = 0

    def check(name: str, cond: bool, extra: str = "") -> None:
        nonlocal failures
        if cond:
            print(f"  ✅ {name}")
        else:
            failures += 1
            print(f"  ❌ {name} {extra}")

    # 清洗
    raw = '<div><script>var x=1</script><p>价格&amp;库存</p>\u200b</div>'
    check("clean_html 去脚本与实体", clean_html(raw) == "价格&库存", clean_html(raw))
    check("clean_html 压空白", "\n\n\n" not in clean_html("<p>a</p><p></p><p></p><p>b</p>"))

    # URL
    u1 = "https://WWW.Example.com/a//b?sku=1&utm_source=x"
    check("canon_url 去 www 与追踪参数", canon_url(u1) == "https://example.com/a/b?sku=1", canon_url(u1))
    check("canon_url 保留业务参数", "sku=2" in canon_url("http://e.com/p?sku=2&spm=9"))
    check("canon_url 参数排序稳定",
          canon_url("http://e.com/p?b=2&a=1") == canon_url("http://e.com/p?a=1&b=2"))

    # SimHash
    t1 = "国产新能源汽车在欧洲市场的接受度明显上升"
    t2 = "国产新能源汽车在欧洲市场的接受度明显提高"
    t3 = "家庭烘焙面包时面团含水量决定最终口感"
    h1, h2, h3 = simhash(t1), simhash(t2), simhash(t3)
    check("相同文本哈希相同", simhash(t1) == h1)
    check("近似文本距离小", hamming(h1, h2) <= 8, f"d={hamming(h1, h2)}")
    check("无关文本距离大", hamming(h1, h3) >= 12, f"d={hamming(h1, h3)}")
    check("不同进程可复现", _token_hash("测试") == _token_hash("测试"))

    # SQLite 有符号整数往返
    for sample_h in (0, 1, (1 << 63) - 1, 1 << 63, (1 << 64) - 1):
        check(f"哈希 {sample_h} 可无损往返",
              signed_to_hash(hash_to_signed(sample_h)) == sample_h)
    check("有符号转换结果落在 SQLite 范围内",
          -2 ** 63 <= hash_to_signed((1 << 64) - 1) < 2 ** 63)

    # 索引
    idx = SimHashIndex()
    idx.add(h1, "t1")
    check("索引命中自身", idx.query(h1, k=3)[0][0] == "t1")
    try:
        idx.query(h1, k=5)
    except ValueError:
        check("索引拒绝不可保证召回的阈值", True)
    else:
        check("索引拒绝不可保证召回的阈值", False)

    # 哈希完全相同但 payload 不同的两篇文档，必须都返回
    idx2 = SimHashIndex()
    idx2.add(h1, "doc-a")
    idx2.add(h1, "doc-b")
    got = {p for p, _ in idx2.query(h1, k=3)}
    check("同哈希不同文档不互相覆盖", got == {"doc-a", "doc-b"}, str(got))

    # 质量规则
    bad = {"title": "", "price": "-1", "published_at": "2026/10/24",
           "text": "短", "url": "ftp://x"}
    codes = {i.code for i in check_record(bad)}
    check("质量规则能抓到全部 5 类错误",
          {"TITLE_EMPTY", "PRICE_OUTLIER", "DATE_BAD", "TEXT_TOO_SHORT", "URL_BAD"} <= codes,
          str(codes))
    good = {"title": "标题", "price": "99.5", "published_at": "2026-10-24",
            "text": "这是一段足够长的正文内容，" * 5, "url": "https://e.com/p"}
    check("干净记录不误报", check_record(good) == [], str(check_record(good)))

    # 乱码识别：真乱码要抓到，正常法语不能被误伤
    garbled = "ä¸­æ–‡æ ‡é¢˜ 商品 00123 的详细说明"
    check("识别 GBK/UTF-8 混用", looks_mojibake(garbled), garbled)
    check("法语正文不误判", not looks_mojibake("Le café crème est très bon, à demain"))
    check("替换符直接命中", looks_mojibake("正常文字\ufffd\ufffd"))

    # 语料可复现
    a = synth_corpus(20, seed=7)
    b = synth_corpus(20, seed=7)
    check("合成语料可复现", json.dumps(a, ensure_ascii=False) == json.dumps(b, ensure_ascii=False))

    print(f"\n{'✅ 全部通过' if failures == 0 else f'❌ {failures} 项失败'}")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    print(__doc__)


SENTENCES = _FRAGMENTS  # 公开别名
