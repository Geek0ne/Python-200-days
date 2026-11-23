#!/usr/bin/env python3
"""
K8s 基础用法示例
功能：演示如何使用 Python 与 Kubernetes 交互
"""
import subprocess
import json
import sys

def run_kubectl_command(command: str) -> str:
    """执行 kubectl 命令"""
    try:
        result = subprocess.run(
            ['kubectl'] + command.split(),
            capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            print(f"命令错误: {' '.join(['kubectl'] + command.split())}")
            print(f"stderr: {result.stderr}")
            return ""
        return result.stdout.strip()
    except Exception as e:
        print(f"执行异常: {e}")
        return ""

def get_pods(namespace: str = "default") -> list:
    """获取所有 Pod"""
    output = run_kubectl_command(f"get pods -n {namespace} -o json")
    if not output:
        return []
    try:
        data = json.loads(output)
        return data.get('items', [])
    except json.JSONDecodeError:
        return []

def get_deployments(namespace: str = "default") -> list:
    """获取所有 Deployment"""
    output = run_kubectl_command(f"get deployment -n {namespace} -o json")
    if not output:
        return []
    try:
        data = json.loads(output)
        return data.get('items', [])
    except json.JSONDecodeError:
        return []

def describe_pod(pod_name: str, namespace: str = "default") -> str:
    """查看 Pod 详细信息"""
    output = run_kubectl_command(f"describe pod {pod_name} -n {namespace}")
    return output

def create_deployment(name: str, image: str, replicas: int = 1) -> bool:
    """创建 Deployment"""
    yaml_content = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
      - name: {name}
        image: {image}
        ports:
        - containerPort: 80
"""
    # 写入临时 YAML 文件
    with open('/tmp/deploy.yaml', 'w') as f:
        f.write(yaml_content)
    
    # 应用 Deployment
    output = run_kubectl_command(f"apply -f /tmp/deploy.yaml")
    print(f"✅ Deployment 创建结果: {output}")
    return output != ""

def create_service(name: str, service_type: str = "NodePort") -> bool:
    """创建 Service"""
    yaml_content = f"""
apiVersion: v1
kind: Service
metadata:
  name: {name}
spec:
  selector:
    app: {name}
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: {service_type}
"""
    # 写入临时 YAML 文件
    with open('/tmp/service.yaml', 'w') as f:
        f.write(yaml_content)
    
    # 应用 Service
    output = run_kubectl_command(f"apply -f /tmp/service.yaml")
    print(f"✅ Service 创建结果: {output}")
    return output != ""

def main():
    """主函数"""
    print("=" * 60)
    print("K8s 基础用法示例")
    print("=" * 60)
    
    # 检查 kubectl 是否可用
    output = run_kubectl_command("version --client")
    if not output:
        print("❌ kubectl 命令不可用，请确保已安装 kubectl")
        sys.exit(1)
    
    print(f"✅ kubectl 版本信息: {output[:50]}...")
    
    # 检查集群连接
    output = run_kubectl_command("cluster-info")
    if not output:
        print("⚠️ 无法连接到 K8s 集群，可能需要配置 kubeconfig")
    
    print("\n📋 可用操作:")
    print("  1. 查看 Pod 状态")
    print("  2. 查看 Deployment 状态")
    print("  3. 创建 Deployment")
    print("  4. 创建 Service")
    print("  5. 描述特定 Pod")
    
    choice = input("\n请选择操作 (1-5): ").strip()
    
    if choice == '1':
        print("\n📦 Pod 状态:")
        pods = get_pods()
        if pods:
            for pod in pods:
                name = pod['metadata']['name']
                phase = pod['status']['phase']
                ready = pod['status']['containerStatuses'][0]['ready'] if pod['status'].get('containerStatuses') else False
                print(f"  - {name}: {phase} (就绪: {ready})")
        else:
            print("  - 当前没有运行中的 Pod")
    
    elif choice == '2':
        print("\n📦 Deployment 状态:")
        deployments = get_deployments()
        if deployments:
            for deploy in deployments:
                name = deploy['metadata']['name']
                replicas = deploy['spec']['replicas']
                ready_replicas = deploy['status'].get('readyReplicas', 0)
                print(f"  - {name}: {ready_replicas}/{replicas} 副本就绪")
        else:
            print("  - 当前没有 Deployment")
    
    elif choice == '3':
        name = input("请输入 Deployment 名称: ").strip()
        image = input("请输入容器镜像: ").strip()
        replicas = input("请输入副本数 (默认1): ").strip() or "1"
        if create_deployment(name, image, int(replicas)):
            print("✅ Deployment 创建成功")
        else:
            print("❌ Deployment 创建失败")
    
    elif choice == '4':
        name = input("请输入 Service 名称: ").strip()
        service_type = input("请输入 Service 类型 (ClusterIP/NodePort/LoadBalancer，默认NodePort): ").strip() or "NodePort"
        if create_service(name, service_type):
            print("✅ Service 创建成功")
        else:
            print("❌ Service 创建失败")
    
    elif choice == '5':
        pod_name = input("请输入 Pod 名称: ").strip()
        namespace = input("请输入命名空间 (默认default): ").strip() or "default"
        description = describe_pod(pod_name, namespace)
        print(f"\n📄 Pod 详细信息:\n{description}")
    
    else:
        print("❌ 无效的选择")

if __name__ == '__main__':
    main()