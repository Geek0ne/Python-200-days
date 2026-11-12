# Day 178 — 容器编排（K8s 入门）

## 概念解释

### 1. Kubernetes（K8s）是什么
- Kubernetes 是谷歌开源的容器编排平台
- 解决容器化应用的部署、扩展、管理等问题
- 实现 "一次构建，随处运行" 的理念
- 提供容器应用的自动化部署、可扩展性和管理平台

### 2. K8s 核心概念
- **Pod**: 最小的部署单元，可容纳一个或多个容器
- **Service**: 提供网络访问和负载均衡
- **Deployment**: 用于管理ReplicaSet的控制器
- **ReplicaSet**: 确保 pod 副本数量
- **ConfigMap**: 配置数据
- **Secret**: 敏感数据
- **Namespace**: 资源隔离
- **Ingress**: 外部访问入口
- **Persistent Volume**: 持久存储

### 3. K8s 体系结构
- **控制平面**: master 节点管理集群状态
- **工作节点**: worker 节点运行 pod
- **API 服务器**: 所有操作的入口
- **调度器**: 分配 pod 到节点
- **控制器**: 确保状态符合期望

## 原理解释

### 1. Pod 的设计原理
- Pod 是 K8s 的基本单位
- 同一 Pod 中的容器共享网络命名空间和存储卷
- 容器在同一节点上运行，资源共享
- Pod 是不可预测的，始终被重启

### 2. ReplicaSet 的工作原理
- 确保指定数量的 pod 副本存在
- 自动监控 pod 数量
- 检测 pod 崩溃时自动替换
- 通过更新 pod 模板实现滚动更新

### 3. Service 的网络模型
- 通过 ClusterIP 提供内部服务发现
- 支持NodePort和LoadBalancer类型
- 使用EndpointSlice实现服务发现
- 自动健康检查和负载均衡

### 4. 命名空间隔离原理
- 基于 Kubernetes API 的分层组织
- 命名空间是资源的分组
- 不同命名空间互不影响
- 资源配额和限额管理

### 5. Ingress 控制器原理
- 外部HTTP/HTTPS流量的入口
- 基于主机名或路径的路由规则
- TLS证书管理
- 负载均衡和SSL终止

## API 速查表

### Deployment API
```bash
# 创建 Deployment
cat > deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        ports:
        - containerPort: 80
EOF

# 应用
cat deployment.yaml | kubectl apply -f -

# 查看状态
kubectl get deployment nginx-deployment

# 扩缩容
kubectl scale deployment nginx-deployment --replicas=5

# 更新
cat deployment.yaml | kubectl apply -f -

# 删除
kubectl delete deployment nginx-deployment
EOF
```

### Service API
```bash
# 创建 Service
cat > service.yaml << EOF
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: NodePort
EOF

# 应用
cat service.yaml | kubectl apply -f -

# 获取服务地址
kubectl get service nginx-service

# 删除
service.yaml | kubectl delete -f -
EOF
```

### Pod 管理
```bash
# 创建 Pod
cat > pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.14.2
    ports:
    - containerPort: 80
EOF

# 查看 Pod 详情
kubectl describe pod nginx-pod

# 执行命令
kubectl exec -it nginx-pod -- nginx -t

# 删除
kubectl delete pod nginx-pod
EOF
```

### 配置文件管理
```bash
# 创建 ConfigMap
cat > configmap.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: "production"
  LOG_LEVEL: "info"
  DATABASE_URL: "mysql://localhost:3306/app"
EOF

# 应用到 Deployment
cat deployment-with-configmap.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
      volumeMounts:
      - name: config-volume
        mountPath: /etc/config
    spec:
      containers:
      - name: app
        image: myapp:1.0
        envFrom:
        - configMapRef:
            name: app-config
      volumes:
      - name: config-volume
        configMap:
          name: app-config
EOF

kubectl apply -f configmap.yaml
kubectl apply -f deployment-with-configmap.yaml
EOF
```

### 持久化存储
```bash
# 创建 PersistentVolume
cat > pv.yaml << EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: nginx-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteMany
  hostPath:
    path: /data/nginx
EOF

# 创建 PersistentVolumeClaim
cat > pvc.yaml << EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: nginx-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard
EOF

# 应用
cat pv.yaml pvc.yaml | kubectl apply -f -

# 挂载到 Pod
cat pod-with-pv.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pv-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.14.2
    ports:
    - containerPort: 80
    volumeMounts:
    - name: nginx-storage
      mountPath: /usr/share/nginx/html
  volumes:
  - name: nginx-storage
    persistentVolumeClaim:
      claimName: nginx-pvc
EOF

kubectl apply -f pod-with-pv.yaml
EOF
```

## 图解

### Mermaid: K8s 架构图
```mermaid
graph TB
    subgraph "Control Plane"
        apiserver[API Server]
        scheduler[Scheduler]
        controllerManager[Controller Manager]
        etcd[Etcd]
    end
    
    subgraph "Worker Nodes"
        kubelet[Kubelet]
        containerRuntime[Container Runtime]
    end
    
    apiserver --> scheduler
    apiserver --> controllerManager
    scheduler --> kubelet
    controllerManager --> kubelet
    kubelet --> containerRuntime
    
    subgraph "Pods"
        pod1[Pod 1]
        pod2[Pod 2]
        pod3[Pod 3]
    end
    
    containerRuntime --> pod1
    containerRuntime --> pod2
    containerRuntime --> pod3
```

### ASCII: 部署流程
```
Kubernetes 部署流程:

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Docker Image  │───▶│   Container Reg │───▶│   kubelet      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Deployment     │───▶│  Scheduler       │───▶│  Pod Creation   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  ReplicaSet    │───▶│  Pod Management  │───▶│  Service        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Ingress        │───▶│  Load Balance   │───▶│  Client Request │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 实战代码案例

### 1. 基础 K8s 部署脚本
```python
#!/usr/bin/env python3
"""
Kubernetes 部署自动化脚本
功能：部署 Nginx 应用并监控其状态
"""
import subprocess
import time
import yaml
import sys

def run_command(cmd):
    """执行 shell 命令"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"命令失败: {cmd}")
        print(f"错误信息: {e.stderr}")
        return None

def create_deployment_yaml():
    """创建 Deployment YAML 文件"""
    deployment = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': 'nginx-deployment',
            'labels': {
                'app': 'nginx',
                'version': 'v1'
            }
        },
        'spec': {
            'replicas': 3,
            'selector': {
                'matchLabels': {
                    'app': 'nginx'
                }
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app': 'nginx',
                        'version': 'v1'
                    }
                },
                'spec': {
                    'containers': [
                        {
                            'name': 'nginx',
                            'image': 'nginx:1.14.2',
                            'ports': [
                                {
                                    'containerPort': 80
                                }
                            ],
                            'resources': {
                                'requests': {
                                    'cpu': '100m',
                                    'memory': '128Mi'
                                },
                                'limits': {
                                    'cpu': '200m',
                                    'memory': '256Mi'
                                }
                            },
                            'livenessProbe': {
                                'httpGet': {
                                    'path': '/health',
                                    'port': 80
                                },
                                'initialDelaySeconds': 30,
                                'periodSeconds': 10
                            },
                            'readinessProbe': {
                                'httpGet': {
                                    'path': '/ready',
                                    'port': 80
                                },
                                'initialDelaySeconds': 5,
                                'periodSeconds': 5
                            }
                        }
                    ]
                }
            }
        }
    }
    
    with open('deployment.yaml', 'w') as f:
        yaml.dump(deployment, f, default_flow_style=False)
    
    print("✅ Deployment YAML 文件已创建")

def create_service_yaml():
    """创建 Service YAML 文件"""
    service = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': 'nginx-service',
            'labels': {
                'app': 'nginx'
            }
        },
        'spec': {
            'selector': {
                'app': 'nginx'
            },
            'ports': [
                {
                    'protocol': 'TCP',
                    'port': 80,
                    'targetPort': 80
                }
            ],
            'type': 'NodePort'
        }
    }
    
    with open('service.yaml', 'w') as f:
        yaml.dump(service, f, default_flow_style=False)
    
    print("✅ Service YAML 文件已创建")

def deploy_app():
    """部署应用到 K8s"""
    print("🚀 开始部署 Nginx 应用...")
    
    # 检查是否安装了 kubectl
    if run_command("kubectl version --client") is None:
        print("❌ kubectl 命令不可用")
        return False
    
    # 检查是否连接到 K8s 集群
    if run_command("kubectl cluster-info") is None:
        print("❌ 无法连接到 K8s 集群")
        return False
    
    # 应用 Deployment
    deploy_output = run_command("kubectl apply -f deployment.yaml")
    if deploy_output is None:
        print("❌ Deployment 应用失败")
        return False
    
    print(f"📦 Deployment 应用成功: {deploy_output}")
    
    # 应用 Service
    service_output = run_command("kubectl apply -f service.yaml")
    if service_output is None:
        print("❌ Service 应用失败")
        return False
    
    print(f"🌐 Service 应用成功: {service_output}")
    
    # 等待 Pod 就绪
    print("⏳ 等待 Pod 就绪...")
    for i in range(30):
        pods = run_command("kubectl get pods -l app=nginx")
        if pods and "Running" in pods:
            print(f"✅ Pod 就绪: {pods}")
            break
        time.sleep(5)
    else:
        print("❌ Pod 未就绪")
        return False
    
    # 获取服务地址
    service_info = run_command("kubectl get service nginx-service")
    print(f"🔗 服务信息: {service_info}")
    
    return True

def monitor_app():
    """监控应用状态"""
    print("📊 开始监控应用...")
    
    # 监控 Pod 状态
    print("\n📋 Pod 状态:")
    run_command("kubectl get pods -l app=nginx -o wide")
    
    # 监控 Deployment 状态
    print("\n📦 Deployment 状态:")
    run_command("kubectl describe deployment nginx-deployment")
    
    # 监控 Service 状态
    print("\n🌐 Service 状态:")
    run_command("kubectl describe service nginx-service")
    
    # 模拟客户端请求
    print("\n🌐 模拟客户端请求...")
    try:
        import requests
        # 获取 NodePort 地址
        nodes = run_command("kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type==\"InternalIP\")].address}'")
        node_port = run_command("kubectl get service nginx-service -o jsonpath='{.spec.ports[0].nodePort}'")
        
        if nodes and node_port:
            for node in nodes.split():
                response = requests.get(f"http://{node}:{node_port}", timeout=5)
                print(f"📡 客户端请求 {node}:{node_port} -> 状态码: {response.status_code}")
    except ImportError:
        print("⚠️ 未安装 requests 库，跳过客户端请求测试")

def cleanup():
    """清理资源"""
    print("🧹 开始清理资源...")
    
    # 删除资源
    run_command("kubectl delete -f deployment.yaml")
    run_command("kubectl delete -f service.yaml")
    
    # 删除本地文件
    import os
    for file in ['deployment.yaml', 'service.yaml']:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ 删除文件: {file}")
    
    print("✅ 资源清理完成")

def main():
    """主函数"""
    print("=" * 60)
    print("Kubernetes 部署自动化脚本 v1.0")
    print("=" * 60)
    
    # 导入 yaml 模块
    try:
        import yaml
    except ImportError:
        print("⚠️ 未安装 PyYAML 库，正在安装...")
        run_command("pip install pyyaml")
        import yaml
    
    # 创建 YAML 文件
    create_deployment_yaml()
    create_service_yaml()
    
    # 部署应用
    if deploy_app():
        # 监控应用
        monitor_app()
        
        # 提示用户
        print("\n🎉 应用部署成功！")
        print("📊 统计信息:")
        print("  - Pod 数量: 3")
        print("  - 服务端口: 80")
        print("  - 类型: NodePort")
        
        # 询问是否清理
        choice = input("\n是否要清理资源? (y/n): ").lower()
        if choice == 'y':
            cleanup()
    else:
        print("❌ 部署失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### 2. K8s 配置管理工具
```python
#!/usr/bin/env python3
"""
K8s 配置管理工具
功能：管理 K8s 配置文件，验证 YAML 格式，部署应用
"""
import yaml
import json
import sys
from typing import Dict, Any

class K8sConfigManager:
    def __init__(self, config_file: str = None):
        self.config_file = config_file
        self.configs = []
    
    def load_config(self, file_path: str):
        """加载 YAML 配置文件"""
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
                self.configs.append((file_path, config))
                print(f"✅ 成功加载配置文件: {file_path}")
                return config
        except Exception as e:
            print(f"❌ 加载配置文件失败: {file_path}, 错误: {e}")
            return None
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证 K8s 配置的基本格式"""
        required_fields = ['apiVersion', 'kind']
        
        for field in required_fields:
            if field not in config:
                print(f"❌ 配置缺少必需字段: {field}")
                return False
        
        # 根据 kind 验证特定字段
        kind = config.get('kind')
        if kind == 'Deployment':
            if 'spec' not in config:
                print("❌ Deployment 类型配置缺少 spec 字段")
                return False
            if 'template' not in config['spec']:
                print("❌ Deployment 类型配置缺少 template 字段")
                return False
        
        elif kind == 'Service':
            if 'spec' not in config:
                print("❌ Service 类型配置缺少 spec 字段")
                return False
            if 'ports' not in config['spec']:
                print("❌ Service 类型配置缺少 ports 字段")
                return False
        
        elif kind == 'Pod':
            if 'spec' not in config:
                print("❌ Pod 类型配置缺少 spec 字段")
                return False
            if 'containers' not in config['spec']:
                print("❌ Pod 类型配置缺少 containers 字段")
                return False
        
        print(f"✅ {kind} 配置验证通过")
        return True
    
    def validate_all_configs(self) -> bool:
        """验证所有已加载的配置"""
        all_valid = True
        for file_path, config in self.configs:
            print(f"\n📋 验证配置文件: {file_path}")
            if not self.validate_config(config):
                all_valid = False
        
        return all_valid
    
    def generate_manifest(self) -> Dict[str, Any]:
        """生成 K8s 资源清单"""
        manifest = {
            'apiVersion': 'v1',
            'kind': 'List',
            'items': [config for _, config in self.configs]
        }
        
        with open('k8s-manifest.yaml', 'w') as f:
            yaml.dump(manifest, f, default_flow_style=False)
        
        print("✅ K8s 资源清单已生成: k8s-manifest.yaml")
        return manifest
    
    def export_to_json(self, output_file: str = None):
        """导出配置为 JSON 格式"""
        if output_file is None:
            output_file = 'k8s-config.json'
        
        json_data = []
        for file_path, config in self.configs:
            # 转换 YAML 为 JSON 可序列化的格式
            json_config = json.loads(json.dumps(config))
            json_data.append({
                'file': file_path,
                'content': json_config
            })
        
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"✅ 配置已导出到 JSON 文件: {output_file}")
    
    def compare_configs(self, other_manager: 'K8sConfigManager'):
        """比较两个配置管理器中的配置"""
        print("🔍 开始比较配置...")
        
        for file_path, config in self.configs:
            # 查找相同文件名的配置
            other_config = None
            for other_path, other_c in other_manager.configs:
                if file_path == other_path:
                    other_config = other_c
                    break
            
            if other_config:
                # 比较配置内容
                if config == other_config:
                    print(f"✅ 配置相同: {file_path}")
                else:
                    print(f"❌ 配置不同: {file_path}")
                    self._print_differences(config, other_config)
            else:
                print(f"⚠️  找到新配置: {file_path}")
    
    def _print_differences(self, config1: Dict[str, Any], config2: Dict[str, Any]):
        """打印配置差异"""
        import difflib
        
        yaml1 = yaml.dump(config1, default_flow_style=False)
        yaml2 = yaml.dump(config2, default_flow_style=False)
        
        diff = difflib.unified_diff(
            yaml1.splitlines(),
            yaml2.splitlines(),
            fromfile='config1',
            tofile='config2',
            lineterm=''
        )
        
        for line in diff:
            if line.startswith('+'):
                print(f"  + {line[1:]}")
            elif line.startswith('-'):
                print(f"  - {line[1:]}")
            else:
                print(f"    {line}")

def main():
    """主函数"""
    print("=" * 60)
    print("K8s 配置管理工具 v1.0")
    print("=" * 60)
    
    # 初始化配置管理器
    manager = K8sConfigManager()
    
    # 加载配置文件
    config_files = ['deployment.yaml', 'service.yaml', 'pod.yaml']
    for file in config_files:
        manager.load_config(file)
    
    # 验证所有配置
    if manager.validate_all_configs():
        print("\n🎉 所有配置验证通过！")
        
        # 生成资源清单
        manager.generate_manifest()
        
        # 导出为 JSON
        manager.export_to_json()
        
        # 显示统计信息
        print("\n📊 配置统计:")
        print(f"  - 总配置文件数: {len(manager.configs)}")
        print(f"  - Deployment 类型: {sum(1 for _, c in manager.configs if c.get('kind') == 'Deployment')}")
        print(f"  - Service 类型: {sum(1 for _, c in manager.configs if c.get('kind') == 'Service')}")
        print(f"  - Pod 类型: {sum(1 for _, c in manager.configs if c.get('kind') == 'Pod')}")
    else:
        print("\n❌ 配置验证失败，请检查配置")

if __name__ == '__main__':
    main()
```

## 思考题

1. **Pod、Deployment、Service 的分工**：为什么生产环境不直接创建裸 Pod，而要套一层 Deployment？Pod 的 IP 会变，客户端怎样才能稳定访问到服务？

**参考答案**

Pod 是最小部署单元，但它是**易失的**：节点故障、资源驱逐、滚动更新都会让 Pod 被销毁重建，新 Pod 的名字和 IP 都变了。裸 Pod 没人负责「重建」，挂了就真挂了。

Deployment 让你只声明**期望状态**（3 个副本、用这个镜像），它管理 ReplicaSet，ReplicaSet 时刻盯着实际副本数：少了就补、崩了就换；改镜像时由 Deployment 编排滚动更新，逐步把旧 ReplicaSet 的 Pod 换成新的。这就是 K8s 的核心套路——**控制器不断把实际状态拉向期望状态**（调谐 / reconcile）。

Service 解决「地址会变」的问题：它用 **label selector** 动态挑出一组 Pod，对外提供一个固定的 ClusterIP 和 DNS 名，并在这组 Pod 间做负载均衡。Pod 增删、换 IP，Service 背后的 EndpointSlice 会自动更新，客户端只需要认 Service 名字。要对集群外暴露就用 NodePort / LoadBalancer，HTTP 按域名和路径路由则交给 Ingress。

💡 提示：Service 的 selector 必须能匹配到 Pod 的 labels，否则它一个后端都选不到，访问就是连接失败——下一题就用代码校验这类一致性。

2. **离线校验清单（代码）**：不连集群，如何用 Python 检查一份 Deployment 清单是否「自洽」？请实现必填字段检查与 selector / labels 一致性检查，并说明为什么值得在 `kubectl apply` 之前做这件事。

**参考答案**

```python
# 依赖：仅标准库（离线校验，不连集群；真正 kubectl apply 需自行准备 K8s 环境）
import json

def make_deployment(name, replicas, image):
    """用字典构造 Deployment 清单：labels 与 selector 同源，避免写歪"""
    labels = {"app": name}
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": name, "labels": dict(labels)},
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": dict(labels)},   # 各自一份副本，互不影响
            "template": {
                "metadata": {"labels": dict(labels)},
                "spec": {"containers": [
                    {"name": name, "image": image,
                     "ports": [{"containerPort": 80}]}
                ]},
            },
        },
    }

def validate(manifest):
    """离线校验：必填字段 + selector 与 Pod 模板 labels 是否匹配"""
    problems = []
    for field in ("apiVersion", "kind", "metadata", "spec"):
        if field not in manifest:
            problems.append(f"缺少必填字段 {field}")
    if problems:
        return problems

    spec = manifest["spec"]
    if manifest["kind"] == "Deployment":
        selector = spec.get("selector", {}).get("matchLabels", {})
        pod_labels = spec.get("template", {}).get("metadata", {}).get("labels", {})
        # selector 的每个键值都必须出现在 Pod 模板的 labels 里
        for k, v in selector.items():
            if pod_labels.get(k) != v:
                problems.append(f"selector 与模板 labels 不匹配: {k}={v}")
        if not isinstance(spec.get("replicas"), int) or spec["replicas"] < 0:
            problems.append("replicas 必须是非负整数")
    return problems

good = make_deployment("nginx", 3, "nginx:1.14.2")
print(validate(good))                     # [] 表示校验通过

bad = make_deployment("nginx", 3, "nginx:1.14.2")
bad["spec"]["template"]["metadata"]["labels"]["app"] = "nginx-v2"   # 手滑改错标签
print(validate(bad))

bad2 = make_deployment("nginx", -1, "nginx:1.14.2")
print(validate(bad2))

spec = good["spec"]
container = spec["template"]["spec"]["containers"][0]
print(f"{good['metadata']['name']}: replicas={spec['replicas']}, image={container['image']}")
print(json.dumps(spec["selector"], ensure_ascii=False))
```

预期输出：

```
[]
['selector 与模板 labels 不匹配: app=nginx']
['replicas 必须是非负整数']
nginx: replicas=3, image=nginx:1.14.2
{"matchLabels": {"app": "nginx"}}
```

K8s 清单本质就是结构化数据（YAML/JSON 都能表达），所以完全可以在本地用字典先做一遍「体检」：必填字段齐不齐、`replicas` 是不是非负整数、`selector.matchLabels` 是否被 Pod 模板的 `labels` 覆盖。本日实战里的 `K8sConfigManager.validate_config` 做的是同一类事，这里改成纯标准库实现，不依赖 PyYAML、也不访问集群。

值得提前做的原因：`selector` 与模板 labels 不匹配这类错误，清单本身「格式合法」，apply 可能成功，但 Deployment 永远选不到自己创建的 Pod，副本数迟迟不达标——排查起来远比一条本地报错费劲。把校验放进 CI，问题就挡在提交阶段。

⚠️ 注意：构造清单时如果把**同一个 labels 字典对象**同时塞给 selector 和 template，改一处等于改两处（别名共享），校验就失真了；本例用 `dict(labels)` 各拷一份。需要输出 YAML 文件时用 `yaml.dump`（`pip install pyyaml`），结构与字典一一对应；真正 apply / scale 需自行准备集群（minikube、kind 等）。

3. **两种探针的区别**：`livenessProbe` 与 `readinessProbe` 各自决定什么？把一个启动需要 60 秒的应用配成 `livenessProbe.initialDelaySeconds: 5`、又不配 readiness，会发生什么？

**参考答案**

**livenessProbe（存活探针）**失败 → kubelet 认为容器「已经死了」，按重启策略**重启容器**。它治的是「进程还在但不干活」：死锁、卡死、内存泄漏后无响应。

**readinessProbe（就绪探针）**失败 → **不重启**，只把该 Pod 从 Service 的后端列表（Endpoints/EndpointSlice）里摘掉，不再转发流量给它；探测恢复后自动加回。它治的是「暂时不能服务」：启动加载中、依赖未就绪、瞬时过载。

启动要 60 秒的应用，liveness 从第 5 秒就开始探测，此时应用还没监听端口，探测连续失败达到 `failureThreshold` → 容器被重启 → 再次启动到一半又被杀，陷入 **CrashLoopBackOff**，永远起不来。正确做法：把 `initialDelaySeconds` 设得大于启动时间，或加 `startupProbe`（启动探针，专门保护慢启动，成功前暂停另外两种探针），或放宽 `periodSeconds` / `failureThreshold`。

不配 readiness 的后果：Pod 一进入 Running 就可能被 Service 纳入流量，而应用其实还没准备好，滚动更新期间就会掉请求、报 502。

⚠️ 注意：本日清单给 `nginx:1.14.2` 配了 `/health` 和 `/ready` 两个探测路径，但官方 nginx 镜像默认并没有这两个 location，直接 apply 会探测失败。照抄时要改成 `/`，或在镜像/ConfigMap 里补上对应配置（需自行准备环境验证）。