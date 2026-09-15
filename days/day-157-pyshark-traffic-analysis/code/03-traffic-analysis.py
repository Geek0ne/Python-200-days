#!/usr/bin/env python3
"""案例 3：网络流量分析实战 - 连接统计与异常检测"""

import pyshark
from collections import Counter, defaultdict

def main():
    pcap_file = 'network_traffic.pcap'
    
    print(f"网络流量分析报告")
    print(f"分析文件: {pcap_file}")
    print("=" * 70)
    
    # 统计各种指标
    protocol_counts = Counter()
    src_dst_ports = defaultdict(Counter)  # (src_ip, dst_ip) -> {dst_port: count}
    tcp_flags_counter = Counter()
    total_packets = 0
    
    # 只过滤 TCP 流量以提高性能
    cap = pyshark.FileCapture(pcap_file,
                              display_filter='tcp',
                              only_summaries=True)
    
    try:
        for packet in cap:
            total_packets += 1
            
            # 统计协议 - TCP 已由 display_filter 过滤
            protocol_counts['TCP'] += 1
            
            # 检查 IP 层
            if hasattr(packet, 'ip'):
                src_ip = packet.ip.src_ip
                dst_ip = packet.ip.dst_ip
                
                # 统计源/目的端口组合
                if hasattr(packet, 'tcp'):
                    dst_port = int(packet.tcp.dst_port)
                    src_port = int(packet.tcp.src_port)
                    
                    # (源IP, 目的IP) -> 目的端口计数
                    src_dst_ports[(src_ip, dst_ip)][dst_port] += 1
                    
                    # 统计 TCP 标志
                    if hasattr(packet.tcp, 'flags'):
                        flag_str = packet.tcp.flags
                        # 解析常用标志位
                        if 'S' in flag_str:  # SYN
                            tcp_flags_counter['SYN'] += 1
                        if 'F' in flag_str:  # FIN
                            tcp_flags_counter['FIN'] += 1
                        if 'P' in flag_str:  # PSH
                            tcp_flags_counter['PSH'] += 1
                        if 'R' in flag_str:  # RST
                            tcp_flags_counter['RST'] += 1
                        if 'A' in flag_str:  # ACK
                            tcp_flags_counter['ACK'] += 1
    finally:
        cap.close()
    
    # 输出分析报告
    print(f"\n总数据包数: {total_packets}")
    print(f"\n协议分布:")
    for proto, count in protocol_counts.most_common():
        print(f"  {proto}: {count} ({count/total_packets*100:.1f}%)")
    
    print(f"\nTCP 标志分布:")
    for flag, count in tcp_flags_counter.most_common():
        print(f"  {flag}: {count} ({count/total_packets*100:.1f}%)")
    
    print(f"\n活跃连接 (前 10):")
    # 找出最活跃的连接
    connection_counts = defaultdict(int)
    for (src_ip, dst_ip), ports in src_dst_ports.items():
        for dst_port, count in ports.items():
            key = f"{src_ip}:{dst_port} → {dst_ip}"
            connection_counts[key] += count
    
    for conn, count in sorted(connection_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {conn}: {x[1] if False else count} 次")  # bug fix needed
    
    # 正确的排序输出
    print(f"\n最活跃的连接:")
    sorted_connections = sorted(connection_counts.items(), key=lambda x: x[1], reverse=True)
    for conn, count in sorted_connections[:10]:
        print(f"  {conn}: {count} 个数据包")
    
    # 检测潜在的异常（例如：单个源 IP 大量连接同一目的 IP）
    print(f"\n潜在异常检测:")
    for (src_ip, dst_ip), ports in src_dst_ports.items():
        total_from_src = sum(ports.values())
        if total_from_src > 50:  # 超过50个数据包从同一源IP
            print(f"  警告: {src_ip} 向 {dst_ip} 发送了 {total_from_src} 个 TCP 数据包")

if __name__ == "__main__":
    main()