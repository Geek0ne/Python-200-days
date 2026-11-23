"""
Day 39 — 设计模式（结构型）
02-proxy-pattern.py
代理模式 — 为对象提供替身以控制访问

场景：大型 PDF 报告系统，每份报告包含元数据和文件内容。
文件内容加载开销大，使用虚拟代理延迟加载，
只有真正需要内容时才读取文件。

┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  客户端      │────▶│  ReportProxy      │────▶│  RealPDFReport   │
│              │     │  (虚拟代理)      │     │  (真实PDF操作)  │
│ - 查看元数据  │     │                  │     │                  │
│ - 下载内容    │     │  metadata: 立即返回│     │  content: 延迟加载│
└──────────────┘     └──────────────────┘     └──────────────────┘
"""

from abc import ABC, abstractmethod
import time


# ── 抽象主题：报告接口 ──────────────────────────────

class Report(ABC):
    """抽象报告接口：定义真实报告和代理的共同接口"""
    
    @abstractmethod
    def get_title(self) -> str:
        """获取报告标题"""
        pass
    
    @abstractmethod
    def get_author(self) -> str:
        """获取报告作者"""
        pass
    
    @abstractmethod
    def get_summary(self) -> str:
        """获取报告摘要"""
        pass
    
    @abstractmethod
    def download_content(self) -> bytes:
        """下载报告完整内容（开销大的操作）"""
        pass


# ── 真实主题：实际的 PDF 报告 ──────────────────────

class RealPDFReport(Report):
    """
    真实的 PDF 报告
    
    文件内容读取是开销大的操作（模拟 3 秒延迟），
    希望在真正需要时才加载。
    """
    
    def __init__(self, report_id: str, title: str, author: str, summary: str):
        """
        初始化报告（仅加载元数据，不加载内容）
        """
        self._report_id = report_id
        self._title = title
        self._author = author
        self._summary = summary
        self._content: bytes | None = None  # 内容延迟加载
        
        print(f"  [RealPDFReport] 报告对象已创建: {title}")
    
    def get_title(self) -> str:
        return self._title
    
    def get_author(self) -> str:
        return self._author
    
    def get_summary(self) -> str:
        return self._summary
    
    def _load_content(self) -> bytes:
        """
        模拟从磁盘加载 PDF 文件内容
        实际操作：open("report.pdf", "rb").read()
        """
        print(f"  [RealPDFReport] ⏳ 正在从磁盘读取报告内容...")
        time.sleep(3)  # 模拟 I/O 延迟
        
        # 模拟 PDF 内容（真实情况是文件二进制数据）
        content = f"PDF 内容: {self._title} by {self._author}\n{self._summary * 100}".encode("utf-8")
        print(f"  [RealPDFReport] ✅ 内容读取完毕 ({len(content)} bytes)")
        return content
    
    def download_content(self) -> bytes:
        """
        下载完整报告内容
        注意：如果之前已加载过，不会重复加载
        """
        if self._content is None:
            self._content = self._load_content()
        else:
            print(f"  [RealPDFReport] 🔄 从缓存返回内容")
        return self._content


# ── 代理：延迟加载 + 统计 ──────────────────────────

class ReportProxy(Report):
    """
    报告代理
    
    职责：
    1. 延迟加载：仅在需要内容时才创建真实报告对象
    2. 访问控制：检查下载权限
    3. 访问统计：记录谁在什么时候下载了什么
    4. 缓存控制：可配合缓存策略
    """
    
    def __init__(self, report_id: str, title: str, author: str, summary: str):
        """
        创建代理（不创建真实对象）
        """
        self._report_id = report_id
        self._title = title
        self._author = author
        self._summary = summary
        self._real_report: RealPDFReport | None = None  # 延迟创建
        
        # 访问统计
        self._access_log: list[dict] = []
        
        print(f"  [ReportProxy] 代理已创建，真实报告尚未实例化")
    
    def _get_real_report(self) -> RealPDFReport:
        """
        获取真实报告对象（延迟创建）
        """
        if self._real_report is None:
            print(f"  [ReportProxy] ⚡ 首次访问，创建真实报告对象...")
            self._real_report = RealPDFReport(
                self._report_id,
                self._title,
                self._author,
                self._summary
            )
        return self._real_report
    
    def get_title(self) -> str:
        """元数据不需要创建真实对象"""
        return self._title
    
    def get_author(self) -> str:
        """元数据不需要创建真实对象"""
        return self._author
    
    def get_summary(self) -> str:
        """元数据不需要创建真实对象"""
        return self._summary
    
    def _log_access(self, username: str, action: str) -> None:
        """记录访问日志"""
        log_entry = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "username": username,
            "action": action,
            "report": self._title
        }
        self._access_log.append(log_entry)
        print(f"  [AuditLog] 📝 {username} 执行了 {action}")
    
    def download_content(self, username: str | None = None) -> bytes:
        """
        下载报告内容（需要经过权限检查）
        """
        if username is None:
            username = "anonymous"
        
        # ⚡ 权限检查（保护代理）
        if not self._check_permission(username):
            print(f"  [Permission] ❌ {username} 无下载权限！")
            raise PermissionError(f"{username} 无下载权限")
        
        # 📝 记录下载日志
        self._log_access(username, "download")
        
        # ⚡ 延迟加载：此时才创建真实对象
        real = self._get_real_report()
        
        # 委托给真实对象
        return real.download_content()
    
    def _check_permission(self, username: str) -> bool:
        """
        权限检查逻辑
        """
        allowed_users = {"admin", "聂董", "张三", "李四"}
        has_permission = username in allowed_users
        print(f"  [Permission] {'✅' if has_permission else '❌'} {username} {'有' if has_permission else '无'}下载权限")
        return has_permission
    
    def get_access_log(self) -> list[dict]:
        """获取访问日志"""
        return self._access_log
    
    def display_metadata_preview(self) -> None:
        """
        显示报告元数据（不需要加载内容）
        这是代理模式的优势：无需昂贵操作即可获取基本信息
        """
        print(f"\n  📋 报告预览")
        print(f"  ┌──────────────────────────────────")
        print(f"  │ 标题: {self._title}")
        print(f"  │ 作者: {self._author}")
        print(f"  │ 摘要: {self._summary[:50]}...")
        print(f"  │ 大小: 待下载后可知")
        print(f"  └──────────────────────────────────")
        print(f"  ℹ️  查看元数据无需加载 PDF 内容")


# ── 虚拟代理：图片懒加载 ──────────────────────────

class LazyImage:
    """
    图片懒加载虚拟代理
    
    场景：网页上有 50 张图片，用户只浏览前 5 张。
    用代理延迟加载，只有图片进入视口才真正加载。
    """
    
    def __init__(self, filename: str):
        self._filename = filename
        self._image_data: bytes | None = None
        self._placeholder = f"[占位图: {filename}]"
        print(f"  [LazyImage] 代理创建: {filename}（未加载）")
    
    def _load(self) -> None:
        """模拟图片加载（仅首次）"""
        print(f"  [LazyImage] ⏳ 加载图片: {self._filename}...")
        time.sleep(1.5)  # 模拟网络加载
        self._image_data = f"<图片: {self._filename}>".encode()
        print(f"  [LazyImage] ✅ 加载完成: {len(self._image_data)} bytes")
    
    def display_thumbnail(self) -> str:
        """显示缩略图（低分辨率，不需要加载全尺寸图）"""
        return f"[缩略图: {self._filename}] (150x150)"
    
    def display_full(self) -> str:
        """
        显示全尺寸图片（此时才真正加载）
        """
        if self._image_data is None:
            self._load()
        return f"[全尺寸: {self._filename}] ({len(self._image_data)} bytes)"
    
    def get_metadata(self) -> dict:
        return {
            "filename": self._filename,
            "loaded": self._image_data is not None,
            "placeholder": self._placeholder
        }


# ── 测试 ──────────────────────────────────────────────

def test_virtual_proxy():
    """测试虚拟代理：延迟加载"""
    
    print("=" * 60)
    print("虚拟代理: 报告系统延迟加载")
    print("=" * 60)
    
    # 创建代理（不创建真实对象）
    proxy = ReportProxy(
        report_id="RPT-2026-001",
        title="2026年度技术架构报告",
        author="聂董",
        summary="本报告详细分析了当前技术架构的演进方向，包含微服务、容器化和AI驱动的系统设计..."
    )
    
    print("\n📋 第一步：查看元数据（无需加载PDF）")
    proxy.display_metadata_preview()
    
    print("\n📥 第二步：下载内容（此时才创建真实对象并加载）")
    try:
        content = proxy.download_content(username="聂董")
        print(f"  下载成功: {len(content)} bytes")
    except PermissionError as e:
        print(f"  下载失败: {e}")
    
    print("\n📥 第三步：再次下载（使用缓存，无需重复加载）")
    try:
        content = proxy.download_content(username="聂董")
        print(f"  下载成功: {len(content)} bytes")
    except PermissionError as e:
        print(f"  下载失败: {e}")
    
    print("\n📊 访问日志:")
    for log in proxy.get_access_log():
        print(f"  - {log['time']} | {log['username']} | {log['action']}: {log['report']}")


def test_protection_proxy():
    """测试保护代理：权限控制"""
    
    print("\n" + "=" * 60)
    print("保护代理: 权限控制演示")
    print("=" * 60)
    
    proxy = ReportProxy("RPT-002", "机密报告", "管理员", "仅供授权人员查阅")
    
    # 有权限的用户
    print("\n✅ 有权限用户下载:")
    proxy.download_content(username="聂董")
    
    # 无权限的用户
    print("\n❌ 无权限用户下载:")
    try:
        proxy.download_content(username="聂董的黑粉")
    except PermissionError:
        print("  🚫 已拦截非法访问")
    
    print("  ✅ 保护代理阻止了未授权访问")


def test_image_proxy():
    """测试图片懒加载"""
    
    print("\n" + "=" * 60)
    print("虚拟代理: 图片懒加载（模拟网页加载）")
    print("=" * 60)
    
    # 创建多个图片代理（不加载任何图片）
    images = [
        LazyImage("hero-banner.jpg"),
        LazyImage("product-1.png"),
        LazyImage("product-2.png"),
        LazyImage("testimonial.jpg"),
        LazyImage("footer-bg.png"),
    ]
    
    print("\n🖼️  显示所有缩略图（无需加载原图）:")
    for img in images:
        print(f"  {img.display_thumbnail()}")
    
    print("\n📸 用户点开第一张图片（此时才加载）:")
    print(f"  {images[0].display_full()}")
    
    print("\n📸 用户又点开第一张图片（缓存，无需二次加载）:")
    print(f"  {images[0].display_full()}")
    
    print("\n📸 用户点开第三张图片:")
    print(f"  {images[2].display_full()}")
    
    # 统计加载状态
    loaded = sum(1 for img in images if img.get_metadata()["loaded"])
    print(f"\n📊 加载统计: {loaded}/{len(images)} 张图片已加载（其余延迟加载）")


if __name__ == "__main__":
    test_virtual_proxy()
    test_protection_proxy()
    test_image_proxy()

"""
运行结果要点：

⏳ 延迟加载前后对比：
  无代理：创建报告时就要读磁盘 → 创建 10 份报告 = 30 秒
  有代理：查看元数据 0 秒，真正下载时才读磁盘

🔒 保护代理效果：
  聂董 → ✅ 允许访问
  聂董的黑粉 → ❌ 拒绝访问 + 权限提示

🖼️  图片懒加载效果：
  5 张图片代理创建：0 秒（无 I/O）
  仅加载用户点开的 2 张
  其余 3 张从未加载
"""
