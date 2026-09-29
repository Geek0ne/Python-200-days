"""
Scrapyd 客户端 - 爬虫部署与管理
功能：通过 Scrapyd API 远程管理爬虫的启动、停止和状态查看
"""

import requests
import time
import json
from datetime import datetime


class ScrapydClient:
    """Scrapyd API 客户端"""
    
    def __init__(self, host="http://localhost:6800", project="ecommerce_monitor"):
        """
        初始化客户端
        
        Args:
            host: Scrapyd 服务地址
            project: 项目名称
        """
        self.host = host.rstrip("/")
        self.project = project
        self.session = requests.Session()
    
    def _request(self, method, endpoint, **kwargs):
        """统一请求方法"""
        url = f"{self.host}/{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            print(f"❌ 无法连接 Scrapyd 服务: {self.host}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP 错误: {e}")
            return None
    
    def list_projects(self):
        """列出所有项目"""
        result = self._request("GET", "listprojects.json")
        if result:
            projects = result.get("projects", [])
            print(f"📋 可用项目: {projects}")
            return projects
        return []
    
    def list_spiders(self, project=None):
        """列出项目中的爬虫"""
        project = project or self.project
        result = self._request("GET", "listspiders.json", params={"project": project})
        if result:
            spiders = result.get("spiders", [])
            print(f"🕷️  项目 {project} 的爬虫: {spiders}")
            return spiders
        return []
    
    def deploy(self, egg_path, project=None, version=None):
        """
        部署项目
        
        Args:
            egg_path: .egg 文件路径
            project: 项目名称
            version: 版本号（可选）
        """
        project = project or self.project
        
        with open(egg_path, "rb") as f:
            files = {"egg": ("project.egg", f, "application/octet-stream")}
            data = {"project": project}
            if version:
                data["version"] = version
            
            result = self._request("POST", "addversion.json", data=data, files=files)
        
        if result:
            status = result.get("status")
            if status == "ok":
                print(f"✅ 部署成功: {project}")
            else:
                print(f"❌ 部署失败: {result}")
            return result
        return None
    
    def start_spider(self, spider_name, **kwargs):
        """
        启动爬虫
        
        Args:
            spider_name: 爬虫名称
            **kwargs: 传递给爬虫的参数
        """
        data = {
            "project": self.project,
            "spider": spider_name,
        }
        data.update(kwargs)
        
        result = self._request("POST", "schedule.json", data=data)
        if result:
            job_id = result.get("jobid")
            print(f"🚀 爬虫已启动: {spider_name}")
            print(f"   Job ID: {job_id}")
            return job_id
        return None
    
    def cancel_spider(self, job_id):
        """取消爬虫任务"""
        data = {
            "project": self.project,
            "job": job_id,
        }
        result = self._request("POST", "cancel.json", data=data)
        if result:
            print(f"🗑️  任务已取消: {job_id}")
        return result
    
    def list_jobs(self, project=None):
        """查看任务状态"""
        project = project or self.project
        result = self._request("GET", "listjobs.json", params={"project": project})
        
        if not result:
            return {}
        
        running = result.get("running", [])
        pending = result.get("pending", [])
        finished = result.get("finished", [])
        
        print("\n" + "=" * 60)
        print(f"📊 项目 {project} 任务状态")
        print("=" * 60)
        
        print(f"\n🔄 运行中 ({len(running)}):")
        for job in running:
            start = job.get("start_time", "N/A")
            print(f"   - {job['spider']} (ID: {job['id'][:8]}...) 开始: {start}")
        
        print(f"\n⏳ 等待中 ({len(pending)}):")
        for job in pending:
            print(f"   - {job['spider']} (ID: {job['id'][:8]}...)")
        
        print(f"\n✅ 已完成 ({len(finished)}):")
        for job in finished[-5:]:  # 只显示最近5个
            end = job.get("end_time", "N/A")
            print(f"   - {job['spider']} (ID: {job['id'][:8]}...) 结束: {end}")
        
        if len(finished) > 5:
            print(f"   ... 还有 {len(finished) - 5} 个已完成任务")
        
        return result
    
    def delete_project(self, project=None):
        """删除项目"""
        project = project or self.project
        result = self._request("POST", "delproject.json", data={"project": project})
        if result:
            print(f"🗑️  项目已删除: {project}")
        return result


def demo():
    """演示 Scrapyd 客户端功能"""
    print("🎯 Scrapyd 客户端演示")
    print("=" * 40)
    
    # 创建客户端
    client = ScrapydClient(
        host="http://localhost:6800",
        project="ecommerce_monitor"
    )
    
    # 1. 列出项目
    print("\n📋 步骤1: 列出所有项目")
    projects = client.list_projects()
    
    # 2. 列出爬虫
    if projects:
        print("\n📋 步骤2: 列出爬虫")
        client.list_spiders()
    
    # 3. 启动爬虫（需要 Scrapyd 服务运行）
    print("\n🚀 步骤3: 启动爬虫")
    job_id = client.start_spider("price_monitor", category="electronics")
    
    if job_id:
        # 4. 等待并查看状态
        print("\n⏳ 步骤4: 等待 3 秒后查看状态...")
        time.sleep(3)
        client.list_jobs()
        
        # 5. 取消任务
        print(f"\n🗑️  步骤5: 取消任务 {job_id[:8]}...")
        client.cancel_spider(job_id)
    
    print("\n✅ 演示完成!")


if __name__ == "__main__":
    demo()
