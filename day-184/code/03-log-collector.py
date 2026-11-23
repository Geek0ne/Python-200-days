#!/usr/bin/env python3
"""
Day 184 · 示例 03 —— 日志采集器：跟文件、处理轮转、处理「半行」

为什么要有这个文件？
    有了接收端（02），还得有人把**文件里的日志搬过去**。这一步看着简单
    （"不就是 tail -f 吗"），但生产上 80% 的「日志丢了」都出在这里：

    坑 1：日志轮转（logrotate / rename）。
        采集器打开的是 inode，不是文件名。文件被 rename 成 app.log.1 之后，
        采集器还在读旧 inode —— 新写入 app.log 的内容**一条都收不到**，
        而且它不会报错，你只会发现「昨天之后就没日志了」。
    坑 2：半行。
        写日志的进程是「先 write 前半段，再 write 后半段」的，采集器如果
        按 read() 拿多少算多少，就会把一条 JSON 从中间截断 → 接收端解析失败。
        正确做法：**只处理以换行结尾的完整行**，剩下的留在缓冲区里等下一次。
    坑 3：截断（truncate）。
        有人用 『: > app.log』 清日志，文件大小突然变小。必须能发现并回到 0 位置重读。

本文件两种模式，可以对照实验（实验手册里的「翻车实验」就是跑这两个）：
    --naive   只用 open() 拿句柄一直读：不做任何轮转检测（复现坑 1）
    默认      用 (inode, size) 做检测：轮转后重开、截断后回 0、半行缓冲

运行方式（真实运行，依赖 02 号服务）：
    # 终端 A
    python3 03-log-collector.py --file /tmp/day184/app.log --url http://127.0.0.1:8099/ingest
    # 终端 B（模拟 logrotate 的 rename 轮转）
    mv /tmp/day184/app.log /tmp/day184/app.log.1
    # 模拟应用继续往「新的」app.log 写
    printf '%s\n' '{"level":"INFO","msg":"after-rotation"}' >> /tmp/day184/app.log

离线自证（不需要 02 服务，采集逻辑自己证明自己对）：
    python3 03-log-collector.py --self-test
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


class FollowReader:
    """按行跟随一个正在被写的文件，抗轮转 / 抗截断 / 抗半行。"""

    def __init__(self, path: str, naive: bool = False, poll_interval: float = 0.2):
        self.path = path
        self.naive = naive
        self.poll_interval = poll_interval
        self.fh = None
        self.ino: int | None = None
        self.mtime_ns = 0
        self.pos = 0
        self.buf = ""
        self.rotations = 0
        self.truncations = 0
        # 排错用：把「为什么判定轮转/截断」记下来。
        # 这几个字段在生产里就是「采集器自证」的证据 —— 丢日志时先看它。
        self.events: list[dict] = []

    # ── 打开 / 重开 ──
    def _open(self) -> None:
        self.fh = open(self.path, "r", encoding="utf-8", errors="replace")
        st = os.fstat(self.fh.fileno())
        self.ino = st.st_ino
        self.mtime_ns = st.st_mtime_ns
        self.pos = 0
        self.buf = ""

    def _reopen(self) -> str:
        """轮转后重开。注意先把旧句柄读到 EOF 再关，避免丢掉转走前最后几行。"""
        leftover = self.fh.read() if self.fh else ""
        if self.fh:
            self.fh.close()
        self._open()
        self.rotations += 1
        return leftover

    # ── 主循环里调用的核心 ──
    def poll(self) -> list[str]:
        """返回「本次新出现的完整行」列表。"""
        if self.fh is None:
            # 文件还不存在也要能等：运维平台启动早于应用的场景很常见
            if not os.path.exists(self.path):
                time.sleep(self.poll_interval)
                return []
            self._open()
            return []

        new_text = ""

        if not self.naive:
            try:
                st = os.stat(self.path)
            except FileNotFoundError:
                return []

            if st.st_ino != self.ino:
                # ① 轮转：文件名指向了新的 inode
                self.events.append({"kind": "rotation", "old_ino": self.ino,
                                    "new_ino": st.st_ino, "pos_before": self.pos})
                new_text += self._reopen()
            elif st.st_size < self.pos or (
                st.st_size <= self.pos and st.st_mtime_ns != self.mtime_ns
            ):
                # ③ 截断：大小回退，回到 0 重读。
                #    只比大小是不够的 —— 自证脚本抓到过：文件被 truncate 后又
                #    正好写成同样字节数时 st_size == pos，大小判据完全失灵。
                #    所以补一条 mtime 判据：大小没涨但 mtime 变了，说明内容被重写了。
                self.events.append({"kind": "truncation", "size": st.st_size, "pos_before": self.pos,
                                    "mtime_changed": st.st_mtime_ns != self.mtime_ns,
                                    "buf_kept": bool(self.buf)})
                self.fh.seek(0)
                self.pos = 0
                self.mtime_ns = st.st_mtime_ns
                self.truncations += 1

        # ② 正常增量读。用 read() 而不是 readline()：
        #    半行留在 buf 里，等下一次 poll 补齐 —— 这是「不切碎 JSON」的关键。
        chunk = self.fh.read()
        self.pos = self.fh.tell()
        try:
            self.mtime_ns = os.stat(self.path).st_mtime_ns
        except FileNotFoundError:
            pass
        new_text += chunk

        self.buf += new_text
        *complete, self.buf = self.buf.split("\n")
        return [line for line in complete if line.strip()]

    def stop(self) -> None:
        if self.fh:
            self.fh.close()
            self.fh = None


class Sender:
    """把行批量 POST 到接收端；失败要能重试，重试仍失败要有降级路径（落本地文件）。"""

    def __init__(self, url: str | None, batch_size: int = 50, spill: str | None = None):
        self.url = url
        self.batch_size = batch_size
        self.spill = spill
        self.sent = 0
        self.spilled = 0
        self.failed_batches = 0

    def send(self, lines: list[str]) -> None:
        if not lines:
            return
        if self.url is None:
            self.sent += len(lines)
            return
        body = ("\n".join(lines) + "\n").encode()
        for attempt in range(1, 4):  # 退避重试 3 次
            try:
                req = urllib.request.Request(
                    self.url, data=body, headers={"Content-Type": "application/x-ndjson"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    resp.read()
                self.sent += len(lines)
                return
            except (urllib.error.URLError, OSError) as exc:
                if attempt == 3:
                    self.failed_batches += 1
                    # 降级：写到本地 spill 文件，等服务恢复再补送。
                    # 「绝不丢日志」的底线就是这个降级路径给的。
                    if self.spill:
                        with open(self.spill, "a", encoding="utf-8") as fh:
                            fh.write("\n".join(lines) + "\n")
                        self.spilled += len(lines)
                    print(f"⚠️  批次投递失败（已降级落盘）: {exc}", file=sys.stderr)
                else:
                    time.sleep(0.5 * attempt)


def run(path: str, url: str | None, naive: bool, stop_event: threading.Event | None = None,
        max_seconds: float | None = None) -> dict:
    reader = FollowReader(path, naive=naive)
    sender = Sender(url)
    started = time.monotonic()
    last_send = started
    batch: list[str] = []
    try:
        while not (stop_event and stop_event.is_set()):
            batch += reader.poll()
            # 两种触发：攒够 batch_size，或者攒了 1 秒（保证小流量下也有 1 秒可见性）
            if len(batch) >= sender.batch_size or (batch and time.monotonic() - last_send >= 1.0):
                sender.send(batch)
                batch = []
                last_send = time.monotonic()
            elif batch:
                time.sleep(0.05)
            if max_seconds and time.monotonic() - started > max_seconds:
                break
        sender.send(batch)
    finally:
        reader.stop()
    return {
        "rotations_detected": reader.rotations,
        "truncations_detected": reader.truncations,
        "events": reader.events[-5:],
        "lines_sent": sender.sent,
        "lines_spilled": sender.spilled,
        "failed_batches": sender.failed_batches,
    }


# ────────────────────────── 离线自证 ──────────────────────────

def self_test() -> int:
    """在临时目录里真造一次轮转 + 截断 + 半行，断言采集结果。"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "app.log"
        log.write_text("", encoding="utf-8")

        reader = FollowReader(str(log), poll_interval=0.01)
        collected: list[str] = []
        collected += reader.poll()

        # ① 普通写入（两条完整行）
        with open(log, "a", encoding="utf-8") as fh:
            fh.write('{"msg":"line-1"}\n{"msg":"line-2"}\n')
        collected += reader.poll()

        # ② 半行：只写一半，此时不应该产出任何「完整行」
        with open(log, "a", encoding="utf-8") as fh:
            fh.write('{"msg":"par')
        collected += reader.poll()
        assert len(collected) == 2, collected

        # ③ 补齐半行 → 应该产出第 3 条完整行
        with open(log, "a", encoding="utf-8") as fh:
            fh.write('tial"}\n')
        collected += reader.poll()
        assert collected[2] == '{"msg":"partial"}', collected

        # ④ 轮转：rename 后新建同名文件并写入
        os.rename(log, Path(tmp) / "app.log.1")
        with open(log, "a", encoding="utf-8") as fh:
            fh.write('{"msg":"after-rotation"}\n')
        collected += reader.poll()
        assert reader.rotations == 1, reader.rotations
        assert collected[-1] == '{"msg":"after-rotation"}', collected

        # ⑤ 截断
        with open(log, "w", encoding="utf-8") as fh:
            fh.write('{"msg":"after-truncate"}\n')
        collected += reader.poll()
        assert reader.truncations == 1, reader.truncations
        assert collected[-1] == '{"msg":"after-truncate"}', collected

        reader.stop()

        # ⑥ 反面对照：naive 模式在轮转后会丢日志（这就是坑 1 的复现基础）
        log.write_text('{"msg":"before"}\n', encoding="utf-8")
        naive_reader = FollowReader(str(log), naive=True, poll_interval=0.01)
        naive_seen = list(naive_reader.poll())
        os.rename(log, Path(tmp) / "app.log.2")
        with open(log, "a", encoding="utf-8") as fh:
            fh.write('{"msg":"lost-in-naive"}\n')
        naive_seen += naive_reader.poll()
        naive_reader.stop()
        assert len(naive_seen) == 1, naive_seen
        assert "lost-in-naive" not in "".join(naive_seen)

    print("✅ self-test 通过：轮转/截断/半行 全处理；naive 模式在轮转后确定丢日志（反面证明）")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if "--self-test" in args:
        return self_test()

    def opt(name: str, default):
        return args[args.index(name) + 1] if name in args else default

    path = opt("--file", "/tmp/day184/app.log")
    url = opt("--url", None)
    naive = "--naive" in args
    seconds = float(opt("--seconds", 0)) or None
    stop_event = None
    if seconds is None:
        stop_event = threading.Event()

    print(f"📡 采集 {path} → {url or 'stdout'}  {'(naive 模式)' if naive else '(抗轮转模式)'}",
          flush=True)
    stats = run(path, url, naive, stop_event=stop_event, max_seconds=seconds)
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
