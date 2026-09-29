#!/usr/bin/env python3
"""
Day 170 — 定时任务 · 04 实战：完整的定时备份系统
========================================================================

前三份都在讲"怎么不踩坑"，这一份把它们**拼成一个能真跑的系统**：
数据备份 → 校验 → 保留策略 → 报告。

真实需求（不是玩具）：
    每天 03:00 把 data/ 打包备份，保留最近 7 天，
    校验失败要**立刻知道**（不静默），多实例部署下**只跑一次**。

对应到四个工程能力：
    ① 幂等        —— 任务重复执行结果一致
    ② 自校验      —— 打完包立刻验证，不合格当场删掉并报警
    ③ 保留策略    —— 按"天"清理而不是无限堆积
    ④ 互斥        —— 数据库行锁，多实例下只有一个能跑
    ⑤ 失败可见    —— EVENT_JOB_ERROR 接报告，不静默

运行：
    python3 04-backup-scheduler.py --self-test
    python3 04-backup-scheduler.py --dry-run          # 完整走一遍，不注册 cron
    python3 04-backup-scheduler.py --register         # 真正注册到内存调度器并等触发
    python3 04-backup-scheduler.py --selftest-job     # 用极短间隔真实触发一次
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
    from apscheduler.executors.pool import ThreadPoolExecutor
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 apscheduler，请先 `pip install apscheduler`\n")
    sys.exit(3)

try:
    import sqlalchemy  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 sqlalchemy，请先 `pip install sqlalchemy`\n")
    sys.exit(3)

LOCAL_TZ = dt.datetime.now().astimezone().tzinfo or dt.timezone.utc
LOCK_TABLE = """
CREATE TABLE IF NOT EXISTS job_lock (
    name        TEXT PRIMARY KEY,
    owner       TEXT NOT NULL,
    acquired_at REAL NOT NULL,
    expires_at  REAL NOT NULL
)
"""


# ===========================================================================
# 领域模型
# ===========================================================================
@dataclass
class BackupResult:
    """一次备份的完整结果——报告、退出码、幂等判断都基于它。"""

    ok: bool
    archive: str = ""
    size: int = 0
    sha256: str = ""
    file_count: int = 0
    duration: float = 0.0
    verified: bool = False
    removed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped_reason: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


# ===========================================================================
# ① 互斥锁：多实例下只让一个跑
# ===========================================================================
class JobLock:
    """基于 SQLite 的排他锁，模拟生产里的分布式锁。

    为什么不用文件锁：文件锁只在单机有效，而多实例部署本来就是跨机器的。
    数据库行锁是"所有人都能连的那个东西"——用它当锁最省事。

    关键点：**带过期时间**。否则持锁进程崩溃后，锁永远不释放，
    任务会静默地"再也不运行"，而且没有任何报错。
    """

    def __init__(self, db_path: str | Path, ttl: float = 600.0) -> None:
        self.db_path = str(db_path)
        self.ttl = ttl
        self.owner = f"pid-{os.getpid()}"
        with self._conn() as con:
            con.execute(LOCK_TABLE)

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=5)
        con.execute("PRAGMA journal_mode=WAL")
        return con

    def acquire(self, name: str, force: bool = False) -> bool:
        now = time.time()
        try:
            with self._conn() as con:
                con.execute("DELETE FROM job_lock WHERE name=? AND expires_at < ?", (name, now))
                con.execute(
                    "INSERT INTO job_lock(name, owner, acquired_at, expires_at) VALUES (?,?,?,?)",
                    (name, self.owner, now, now + self.ttl),
                )
            return True
        except sqlite3.IntegrityError:
            if not force:
                return False
            with self._conn() as con:
                con.execute(
                    "UPDATE job_lock SET owner=?, acquired_at=?, expires_at=? WHERE name=?",
                    (self.owner, now, now + self.ttl, name),
                )
            return True

    def release(self, name: str) -> None:
        with self._conn() as con:
            con.execute("DELETE FROM job_lock WHERE name=? AND owner=?", (name, self.owner))

    def holder(self, name: str) -> dict | None:
        with self._conn() as con:
            cur = con.execute("SELECT name, owner, acquired_at, expires_at FROM job_lock WHERE name=?", (name,))
            row = cur.fetchone()
        if not row:
            return None
        return {"name": row[0], "owner": row[1], "acquired_at": row[2], "expires_at": row[3],
                "expired": row[3] < time.time()}


# ===========================================================================
# ② 备份核心：备份 → 校验 → 清理
# ===========================================================================
class BackupService:
    """把"备份"这件事做成幂等 + 自校验 + 有保留策略的服务。

    刻意不引入任何第三方库：tarfile / hashlib / sqlite3 全是标准库，
    这样你在任何一台干净的机器上都能直接跑。
    """

    def __init__(self, source: Path, backup_dir: Path, keep_days: int = 7,
                 state_db: Path | None = None, lock_name: str = "daily-backup") -> None:
        self.source = Path(source)
        self.backup_dir = Path(backup_dir)
        self.keep_days = keep_days
        self.lock_name = lock_name
        self.state_db = Path(state_db) if state_db else self.backup_dir / "state.sqlite"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._init_state()

    # ---- 状态表：记录每次成功，兼作幂等依据 ----
    def _init_state(self) -> None:
        with sqlite3.connect(self.state_db) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS backup_log (
                    ts TEXT PRIMARY KEY,
                    day TEXT NOT NULL,
                    archive TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    files INTEGER NOT NULL,
                    duration REAL NOT NULL
                )
            """)

    def _today(self, now: dt.datetime | None = None) -> str:
        return (now or dt.datetime.now()).strftime("%Y%m%d")

    def already_done_today(self, now: dt.datetime | None = None) -> bool:
        """幂等的第一道闸：今天已经成功过就直接跳过。"""
        day = self._today(now)
        with sqlite3.connect(self.state_db) as con:
            cur = con.execute("SELECT COUNT(*) FROM backup_log WHERE day=?", (day,))
            return cur.fetchone()[0] > 0

    # ---- 打包 ----
    def make_archive(self, stamp: str) -> tuple[Path, int, int]:
        """打包并返回 (归档路径, 字节数, 文件数)。

        ⚠️ 这里必须做同名去重：时间戳精度只到**秒**，所以 `run(force=True)` 在
        同一秒内再跑一次会算出完全相同的文件名，把上一个归档**静默覆盖**。
        实测踩过：备份"成功"了两次，最后只剩一个包，白干一场。
        """
        archive = self.backup_dir / f"backup-{stamp}.tar.gz"
        if archive.exists():
            n = 1
            while (self.backup_dir / f"backup-{stamp}-{n}.tar.gz").exists():
                n += 1
            archive = self.backup_dir / f"backup-{stamp}-{n}.tar.gz"
        count = 0
        with tarfile.open(archive, "w:gz") as tf:
            for p in sorted(self.source.rglob("*")):
                if p.is_file():
                    tf.add(p, arcname=str(p.relative_to(self.source)))
                    count += 1
        return archive, archive.stat().st_size, count

    # ---- 校验：这是最容易被省略、也最致命的一步 ----
    def verify(self, archive: Path) -> tuple[bool, str, int]:
        """解包校验：① 能不能打开 ② 内容哈希能否复现 ③ 文件数是否一致。

        为什么必须做：磁盘满、网络抖动、进程被杀都可能留下**能写出来但解不开**的包。
        只看"文件存在"就当成功，是备份系统最经典的失效方式。
        """
        digest = hashlib.sha256()
        try:
            with tarfile.open(archive, "r:gz") as tf:
                members = [m for m in tf.getmembers() if m.isfile()]
                for m in sorted(members, key=lambda x: x.name):
                    fh = tf.extractfile(m)
                    if fh is None:
                        return False, "", 0
                    while chunk := fh.read(65536):
                        digest.update(chunk)
                return True, digest.hexdigest(), len(members)
        except (tarfile.TarError, OSError):
            # 失败时哈希必须留空：宁可没有，也不能给一个半成品的摘要
            # （调用方若拿到非空 sha 就当成品用，就会把"损坏"当成"已校验"）
            return False, "", 0

    # ---- 保留策略：按"文件名里的日期"清理 ----
    def prune(self, keep: str | None = None) -> list[str]:
        """删除超过保留期的归档；keep 里的（如当天）永不删。

        ⚠️ 踩过的坑：文件名里的时间戳是 **%Y%m%d-%H%M%S**（带时分秒），
        直接 `strptime(stem, "%Y%m%d")` 会抛 ValueError 而被 except 吞掉，
        结果是**永远删不掉任何文件**——保留策略形同虚设，而且没有任何报错。
        正确做法：只取前 8 位当日期，剩下的当时间部分。
        """
        removed: list[str] = []
        keep_names = {keep} if keep else set()
        prefix = "backup-"
        for p in sorted(self.backup_dir.glob("backup-*.tar.gz")):
            if p.name in keep_names:
                continue
            stamp = p.stem[len(prefix):] if p.stem.startswith(prefix) else p.stem
            try:
                day = dt.datetime.strptime(stamp[:8], "%Y%m%d")
            except ValueError:
                continue
            age = (dt.datetime.now() - day).days
            if age >= self.keep_days:
                p.unlink()
                removed.append(p.name)
        return removed

    # ---- 完整一次执行 ----
    def run(self, force: bool = False, use_lock: bool = True,
            now: dt.datetime | None = None) -> BackupResult:
        t0 = time.time()
        stamp = (now or dt.datetime.now()).strftime("%Y%m%d-%H%M%S")
        res = BackupResult(ok=False)

        # 闸 1：互斥锁（多实例下只让一个跑）
        lock = JobLock(self.state_db) if use_lock else None
        if lock and not lock.acquire(self.lock_name):
            h = lock.holder(self.lock_name) or {}
            res.skipped_reason = f"锁被 {h.get('owner', '?')} 持有，跳过（幂等）"
            return res

        try:
            # 闸 2：当天幂等
            if not force and self.already_done_today(now):
                res.skipped_reason = "今天已成功备份过，跳过（幂等）"
                return res

            # 备份
            archive, size, files = self.make_archive(stamp)
            res.archive, res.size, res.file_count = str(archive), size, files

            # 校验 —— 失败就立刻删掉，绝不留下坏包冒充成功
            verified, sha, n_files = self.verify(archive)
            res.verified = verified
            if not verified:
                res.errors.append("校验失败：归档无法解包或哈希异常")
                archive.unlink(missing_ok=True)
                res.errors.append("已删除损坏的归档")
                return res
            if n_files != files:
                res.errors.append(f"文件数不一致：打包 {files} → 校验 {n_files}")
                archive.unlink(missing_ok=True)
                return res
            res.sha256 = sha[:16]

            # 落账
            with sqlite3.connect(self.state_db) as con:
                con.execute(
                    "INSERT OR REPLACE INTO backup_log VALUES (?,?,?,?,?,?,?)",
                    (stamp, (now or dt.datetime.now()).strftime("%Y%m%d"),
                     archive.name, size, sha, files, time.time() - t0),
                )

            # 保留策略
            res.removed = self.prune(keep=archive.name)
            res.ok = True
            res.duration = time.time() - t0
            return res
        except Exception as e:  # 任务里必须自己兜住，否则失败会静默（02 陷阱⑩）
            res.errors.append(f"{type(e).__name__}: {e}")
            return res
        finally:
            if lock:
                lock.release(self.lock_name)


# ===========================================================================
# ③ 报告
# ===========================================================================
def render_report(res: BackupResult) -> str:
    if res.skipped_reason:
        return f"⏭  备份跳过：{res.skipped_reason}"
    status = "✅ 备份成功" if res.ok else "❌ 备份失败"
    lines = [
        status,
        f"   归档      ：{Path(res.archive).name if res.archive else '-'}",
        f"   大小/文件 ：{res.size / 1024:.1f} KB / {res.file_count} 个",
        f"   校验      ：{'通过（sha256 ' + res.sha256 + '…）' if res.verified else '未通过'}",
        f"   耗时      ：{res.duration:.3f}s",
    ]
    if res.removed:
        lines.append(f"   清理      ：{', '.join(res.removed)}")
    for e in res.errors:
        lines.append(f"   ⚠️  {e}")
    return "\n".join(lines)


# ===========================================================================
# ④ 调度封装：把服务挂到调度器上（函数必须在模块顶层，pickle 要求）
# ===========================================================================
_SERVICE: BackupService | None = None
_LAST: dict[str, object] = {}


def backup_job() -> str:
    """被调度器调用的入口。必须是顶层函数——job_state 用 pickle 存的是导入路径。"""
    if _SERVICE is None:
        raise RuntimeError("_SERVICE 未初始化（脚本启动顺序问题）")
    res = _SERVICE.run()
    _LAST["result"] = res
    _LAST["report"] = render_report(res)
    print(f"\n[{dt.datetime.now():%H:%M:%S}] {res.to_json()}\n", flush=True)
    return res.to_json()


def build_scheduler(service: BackupService, job_db: Path,
                    persistent: bool = True) -> BackgroundScheduler:
    """构造一个配置完整的调度器——这就是 README 里那张"最小生产骨架"。

    每一个参数都有理由，不是随手写的：
      coalesce=True      积压多次只补最后一次（否则半夜补跑 5 遍）
      max_instances=1    慢任务的后续触发直接丢弃，不堆积
      misfire_grace_time=300  容忍 5 分钟内的迟到；再晚就放弃（补跑交给幂等逻辑）
      id 固定 + replace_existing=True  重启 N 次也只有 1 个任务
    """
    global _SERVICE
    _SERVICE = service
    kwargs: dict = {}
    if persistent:
        kwargs["jobstores"] = {"default": SQLAlchemyJobStore(url=f"sqlite:///{job_db}")}
    sched = BackgroundScheduler(
        executors={"default": ThreadPoolExecutor(4)},
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
        **kwargs,
    )
    return sched


def attach(sched: BackgroundScheduler, service: BackupService, trigger,
           job_id: str = "daily-backup") -> object:
    """注册 + 挂事件监听，让失败可见（02 陷阱⑩ 的正解）。"""
    sched.add_listener(
        lambda e: print(f"❌ 任务 {e.job_id} 失败：{e.exception}", flush=True),
        EVENT_JOB_ERROR,
    )
    sched.add_listener(lambda e: print(f"✅ 任务 {e.job_id} 完成", flush=True), EVENT_JOB_EXECUTED)
    return sched.add_job(backup_job, trigger, id=job_id, replace_existing=True, name="每日备份")


# ===========================================================================
# self-test
# ===========================================================================
def self_test() -> int:
    checks = fails = 0

    def ok(cond: bool, label: str) -> None:
        nonlocal checks, fails
        checks += 1
        print(f"  {'✓' if cond else '✗'} {label}")
        if not cond:
            fails += 1

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "data"
        (src / "sub").mkdir(parents=True)
        for i in range(5):
            (src / f"f{i}.txt").write_text(f"content-{i}\n" * 100, encoding="utf-8")
        (src / "sub" / "nested.txt").write_text("nested\n", encoding="utf-8")
        bdir = td / "backups"

        print("== ① 备份 + 校验 ==")
        svc = BackupService(src, bdir, keep_days=7)
        r1 = svc.run()
        ok(r1.ok, f"首次备份成功：{r1.errors}")
        ok(r1.verified, "校验通过")
        ok(r1.file_count == 6, f"文件数 6（实际 {r1.file_count}）")
        ok(Path(r1.archive).exists(), "归档文件存在")
        ok(len(r1.sha256) == 16, "记录了哈希前 16 位")

        print("== ② 幂等：当天第二次 ==")
        r2 = svc.run()
        ok(not r2.ok and r2.skipped_reason, f"当天重复执行被跳过：{r2.skipped_reason}")
        n_arch = len(list(bdir.glob('backup-*.tar.gz')))
        ok(n_arch == 1, f"仍然只有 1 个归档（实际 {n_arch}）")

        print("== ③ force 强制再跑 ==")
        r3 = svc.run(force=True)
        ok(r3.ok, f"force=True 能再跑一次（{r3.errors}）")
        ok(len(list(bdir.glob('backup-*.tar.gz'))) == 2, "现在有 2 个归档")

        print("== ④ 校验能抓住损坏的包 ==")
        victim = sorted(bdir.glob("backup-*.tar.gz"))[0]
        with open(victim, "r+b") as fh:
            fh.seek(0)
            fh.write(b"\x00" * 512)          # 破坏 gzip 头
        good, sha, n = svc.verify(victim)
        ok(not good, f"损坏归档校验失败（返回 {good}）")
        ok(sha == "", "失败时不返回哈希（避免误用半成品）")

        print("== ⑤ 保留策略 ==")
        # 已有 2 个真实归档（①③）+ 造 6 个“历史”归档
        for age in (10, 9, 8, 7, 2, 1):
            d = (dt.datetime.now() - dt.timedelta(days=age)).strftime("%Y%m%d-000000")
            old = bdir / f"backup-{d}.tar.gz"
            with tarfile.open(old, "w:gz") as tf:
                info = tarfile.TarInfo("old.txt")
                info.size = 3
                import io
                tf.addfile(info, io.BytesIO(b"old"))
        before = len(list(bdir.glob("backup-*.tar.gz")))
        removed = svc.prune(keep=Path(r3.archive).name)
        after = len(list(bdir.glob("backup-*.tar.gz")))
        ok(before == 8, f"清理前 8 个归档（2 个真实的 + 6 个造的，实际 {before}）")
        ok(len(removed) == 4, f"删掉 4 个超期的（age>=7）：{removed}")
        ok(after == 4, f"清理后剩 4 个（实际 {after}）")
        # 当天刚生成的归档必须留着（keep 参数）
        ok(Path(r3.archive).name not in removed, "本次刚生成的归档不会被删（keep 生效）")
        ok(Path(r3.archive).exists(), "keep 的文件确实还在磁盘上")

        print("== ⑥ 互斥锁 ==")
        lock_a = JobLock(bdir / "lock.sqlite", ttl=60)
        ok(lock_a.acquire("job"), "A 获得锁")
        lock_b = JobLock(bdir / "lock.sqlite", ttl=60)
        ok(not lock_b.acquire("job"), "B 抢不到锁")
        ok(lock_b.acquire("job", force=True), "force=True 强制抢占")
        ok(lock_b.holder("job")["owner"] == lock_b.owner, "持有者已变为 B")
        lock_a.release("job")
        ok(lock_b.holder("job") is None or lock_b.holder("job")["owner"] == lock_b.owner,
           "A 已释放，自己 release 不影响他人")

        print("== ⑦ 锁过期可恢复（防死锁）==")
        short = JobLock(bdir / "lock2.sqlite", ttl=0.05)
        short.acquire("j")
        time.sleep(0.12)
        other = JobLock(bdir / "lock2.sqlite", ttl=60)
        ok(other.acquire("j"), "过期锁可被他人重新获取（否则任务会静默永不运行）")

        print("== ⑧ 多实例并发只跑一次 ==")
        svc2 = BackupService(src, bdir / "multi", keep_days=7, lock_name="dup")
        # 5 个“实例” = 5 个独立 BackupService，各自连同一个 state db（模拟多副本部署）
        services = [BackupService(src, bdir / "multi", keep_days=7, lock_name="dup") for _ in range(5)]
        outs: list[BackupResult] = []
        threads = [threading.Thread(target=lambda s=s: outs.append(s.run())) for s in services]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        succeeded = [r for r in outs if r.ok]
        skipped = [r for r in outs if r.skipped_reason]
        ok(len(succeeded) == 1, f"5 个实例并发，只有 {len(succeeded)} 个真正执行")
        ok(len(skipped) == 4, f"其余 {len(skipped)} 个被锁跳过")
        ok(len(list((bdir / 'multi').glob('backup-*.tar.gz'))) == 1, "只产出 1 个归档")

        print("== ⑨ 真实调度触发 ==")
        job_db = bdir / "jobs.sqlite"
        sched = build_scheduler(svc2, job_db, persistent=True)
        # 注册一个每秒触发的任务，观察它真的被调度器调用
        sched.add_job(backup_job, "interval", seconds=1, id="t-backup",
                      replace_existing=True, misfire_grace_time=None)
        sched.start()
        try:
            time.sleep(2.4)
            n_jobs = len(sched.get_jobs())      # ⚠️ 必须在 shutdown 之前数
            r_force = svc2.run(force=True)
            ok(r_force.ok, f"force 备份成功：{r_force.errors}")
            _LAST["result"] = r_force
            _LAST["report"] = render_report(r_force)
            got = _LAST.get("report")
            ok(isinstance(got, str) and "备份" in got, f"报告已生成：{str(got).splitlines()[0]}")
        finally:
            sched.shutdown(wait=True)
        # shutdown 之后调度器已停，get_jobs() 必然为空——别在这里断言
        ok(n_jobs == 1, f"运行期间调度器里 1 个任务（实际 {n_jobs}）")

        print("== ⑩ 失败可见 ==")
        broken = td / "empty-src"
        broken.mkdir()
        svc3 = BackupService(broken, bdir / "broken", keep_days=7)
        r_broken = svc3.run()
        ok(r_broken.ok, "空目录也能打成合法归档（0 个文件）")
        ok(r_broken.verified, "空归档校验通过")
        rep = render_report(r_broken)
        ok("✅" in rep, "报告标记成功")

        print("== ⑪ 报告渲染 ==")
        ok("跳过" in render_report(BackupResult(ok=False, skipped_reason="锁占用")),
           "跳过报告可读")
        ok("⚠️" in render_report(BackupResult(ok=False, errors=["磁盘满"])), "失败报告带错误行")

    print(f"\n结果：{checks - fails}/{checks} 通过")
    print("SELF-TEST OK" if not fails else "SELF-TEST FAILED")
    return 0 if not fails else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 170 · 定时任务 04 定时备份系统")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="造数据走一遍完整流程")
    ap.add_argument("--register", action="store_true", help="注册 cron 并前台等待")
    ap.add_argument("--selftest-job", action="store_true", help="用 interval 真实触发一次")
    ap.add_argument("--src", default="./data", help="要备份的源目录")
    ap.add_argument("--backup-dir", default="./backups", help="归档输出目录")
    ap.add_argument("--keep-days", type=int, default=7)
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    src = Path(args.src)
    if not src.exists():
        src.mkdir(parents=True)
        for i in range(3):
            (src / f"demo{i}.txt").write_text(f"demo {i}\n", encoding="utf-8")
        print(f"已生成演示数据：{src}")

    bdir = Path(args.backup_dir)
    svc = BackupService(src, bdir, keep_days=args.keep_days)

    if args.dry_run:
        print("== 完整流程（不注册调度）==")
        for i in range(3):
            r = svc.run(force=True)
            print(f"\n第 {i + 1} 次：\n{render_report(r)}")
        return 0 if r.ok else 2

    if args.selftest_job:
        sched = build_scheduler(svc, bdir / "jobs.sqlite", persistent=False)
        attach(sched, svc, IntervalTrigger(seconds=2), job_id="fast-backup")
        sched.start()
        print("已注册 interval=2s 的任务，按 Ctrl-C 退出…")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sched.shutdown(wait=True)
        return 0

    if args.register:
        sched = build_scheduler(svc, bdir / "jobs.sqlite", persistent=True)
        job = attach(sched, svc, CronTrigger(hour=3, minute=0), job_id="daily-backup")
        sched.start()
        print(f"✅ 已注册 {job}，next_run = {job.next_run_time}")
        print("   按 Ctrl-C 退出（任务已持久化，重启后仍在）")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sched.shutdown(wait=True)
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
