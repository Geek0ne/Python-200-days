# Day 157 — pyshark 流量分析 完成清单

## ✅ 基础任务

- [x] 安装 pyshark 和 tshark
- [x] 理解 PCAP 文件格式和网络流量捕获原理
- [x] 使用 FileCapture 读取 PCAP 文件
- [x] 访问数据包的基本属性 (IP、TCP、UDP 信息)
- [x] 使用 display_filter 过滤特定协议的数据包

## 📝 练习题

### 基础练习

1. **PCAP 遍历**
   编写一个脚本，读取 `day-157-example.pcap` 并打印出所有数据包的编号、源 IP 和目标 IP。
   *提示：使用 `hasattr()` 检查数据包是否包含 IP 层。*

2. **协议计数**
   编写一个统计函数，返回 PCAP 文件中每种协议（IP、TCP、UDP、ICMP 等）的包数量。

3. **HTTP 请求提取**
   编写一个脚本，从 PCAP 文件中提取所有 HTTP GET 请求的 URL，并打印出方法、主机和路径。

### 进阶练习

4. **端口统计**
   编写一个脚本，统计每个目的端口出现的次数，并输出前 5 个最常见的目的端口。

5. **TCP 标志分析**
   编写一个分析 TCP 标志的脚本，计算 SYN、ACK、FIN、RST、PSH 中每个标志出现的次数和占比。

6. **异常检测**
   编写一个脚本，检测是否有单个源 IP 向单个目的 IP 发送异常多的 TCP 数据包（阈值可配置）。如果发现，打印警告信息。

## 🎯 思考与实验

- [ ] 尝试使用 `only_summaries=True` 和默认模式对比处理速度差异
- [ ] 尝试使用 BPF (Berkeley Packet Filter) 语言进行过滤：`cap = pyshark.FileCapture('file.pcap', bpf_filter='tcp port 80')`
- [ ] 尝试使用 scapy 与 pyshark 同时处理同一个 PCAP 文件，对比结果一致性和性能
- [ ] 思考：当 PCAP 文件很大（>50MB）时，应该如何分批处理以避免内存不足？