"""
Day 069 — 备份与恢复
运行方式：
  python 04-backup-restore.py --self-test   # SQLite 备份/恢复流程离线自检
  python 04-backup-restore.py               # 调用 mysqldump 备份 MySQL（需环境）
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import time


def mysql_backup(db_name, out_dir="backups"):
    """逻辑备份：mysqldump + 时间戳归档。生产应加：异地存放 + 定期演练恢复。"""
    os.makedirs(out_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_file = os.path.join(out_dir, f"{db_name}-{ts}.sql")
    env = {
        "MYSQL_PWD": os.getenv("MYSQL_PASSWORD", ""),
        "PATH": os.environ.get("PATH", ""),
    }
    cmd = [
        "mysqldump",
        f"-h{os.getenv('MYSQL_HOST', '127.0.0.1')}",
        f"-u{os.getenv('MYSQL_USER', 'root')}",
        "--single-transaction",   # InnoDB 一致性快照，不锁写
        db_name,
    ]
    with open(out_file, "w") as f:
        subprocess.run(cmd, stdout=f, env=env, check=True)
    prune_backups(out_dir, keep=7)
    return out_file


def mysql_restore(db_name, sql_file):
    env = {
        "MYSQL_PWD": os.getenv("MYSQL_PASSWORD", ""),
        "PATH": os.environ.get("PATH", ""),
    }
    cmd = [
        "mysql",
        f"-h{os.getenv('MYSQL_HOST', '127.0.0.1')}",
        f"-u{os.getenv('MYSQL_USER', 'root')}",
        db_name,
    ]
    with open(sql_file) as f:
        subprocess.run(cmd, stdin=f, env=env, check=True)


def prune_backups(out_dir, keep=7):
    """只保留最近 keep 份备份"""
    files = sorted(f for f in os.listdir(out_dir) if f.endswith(".sql"))
    for old in files[:-keep]:
        os.remove(os.path.join(out_dir, old))


# ========== SQLite 等价流程（离线自检用） ==========

def sqlite_backup(src_path, out_file):
    """sqlite3 的备份 API 也是"一致性快照"语义"""
    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(out_file)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()


def self_test():
    import tempfile
    with tempfile.TemporaryDirectory(dir=".") as tmp:
        src_path = os.path.join(tmp, "app.db")
        src = sqlite3.connect(src_path)
        src.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        src.executemany("INSERT INTO t (v) VALUES (?)", [("a",), ("b",), ("c",)])
        src.commit()
        src.close()

        # 备份
        bak = os.path.join(tmp, "app-backup.db")
        sqlite_backup(src_path, bak)
        assert os.path.exists(bak), "备份文件应存在"

        # 破坏原库
        src = sqlite3.connect(src_path)
        src.execute("DROP TABLE t")
        src.commit()
        src.close()

        # 从备份恢复
        shutil.copyfile(bak, src_path)
        src = sqlite3.connect(src_path)
        rows = src.execute("SELECT COUNT(*) FROM t").fetchone()
        assert rows[0] == 3, f"恢复后数据不对: {rows}"
        src.close()

        # 保留策略
        bdir = os.path.join(tmp, "backups")
        os.makedirs(bdir)
        for i in range(10):
            open(os.path.join(bdir, f"db-2026010{i}-000000.sql"), "w").close()
        prune_backups(bdir, keep=7)
        assert len(os.listdir(bdir)) == 7, "应当只保留 7 份"

    print("✅ self-test 全部通过（备份 → 破坏 → 恢复 → 保留策略）")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        out = mysql_backup(os.getenv("MYSQL_DB", "testdb"))
        print("✅ 备份完成:", out)
