"""
Day 054 — 线程基础用法
演示 threading 模块的基本使用方式
"""

import threading
import time


# ============================================================
# 1. 创建线程的基本方式
# ============================================================

def worker(name, delay):
    """线程执行的工作函数"""
    print(f"[{name}] 开始工作 (线程ID: {threading.current_thread().ident})")
    time.sleep(delay)
    print(f"[{name}] 工作完成")


print("=== 方式 1: 使用 target 参数 ===")
t1 = threading.Thread(target=worker, args=("任务A", 1))
t2 = threading.Thread(target=worker, args=("任务B", 0.5))
t1.start()
t2.start()
t1.join()
t2.join()
print("方式 1 完成\n")


# ============================================================
# 2. 继承 Thread 类（更复杂场景推荐）
# ============================================================

class DownloadThread(threading.Thread):
    """自定义线程类 — 下载器"""
    
    def __init__(self, url, size):
        super().__init__()
        self.url = url
        self.size = size
        self.result = None  # 保存结果
    
    def run(self):
        """线程启动时执行的方法"""
        print(f"开始下载: {self.url}")
        # 模拟下载
        time.sleep(self.size / 100)  # 按大小模拟耗时
        self.result = {"url": self.url, "size": self.size, "status": "ok"}
        print(f"下载完成: {self.url}")


print("=== 方式 2: 继承 Thread 类 ===")
threads = [
    DownloadThread("https://example.com/file1.mp4", 200),
    DownloadThread("https://example.com/file2.mp4", 150),
    DownloadThread("https://example.com/file3.mp4", 100),
]

for t in threads:
    t.start()
for t in threads:
    t.join()

for t in threads:
    print(f"  结果: {t.result}")
print("方式 2 完成\n")


# ============================================================
# 3. 守护线程 vs 普通线程
# ============================================================

def background_task():
    """后台监控任务（守护线程）"""
    count = 0
    while count < 5:
        count += 1
        print(f"  [守护线程] 心跳 #{count}")
        time.sleep(0.2)
    print("  [守护线程] 退出")


def main_task():
    """主要任务"""
    print("  [主线程] 开始主要工作")
    time.sleep(0.3)
    print("  [主线程] 主要工作完成")


print("=== 守护线程 vs 普通线程 ===")
daemon_t = threading.Thread(target=background_task, daemon=True)
normal_t = threading.Thread(target=main_task)

daemon_t.start()
normal_t.start()
normal_t.join()
# 注意：不 join daemon_t，主线程退出时它会被终止
print("主线程退出（守护线程会被强制终止）\n")


# ============================================================
# 4. 线程信息
# ============================================================

print("=== 线程信息 ===")
current = threading.current_thread()
print(f"  当前线程名: {current.name}")
print(f"  当前线程ID: {current.ident}")
print(f"  是否主线程: {current is threading.main_thread()}")
print(f"  活跃线程数: {threading.active_count()}")
print(f"  所有线程: {[t.name for t in threading.enumerate()]}")
