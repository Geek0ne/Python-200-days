#!/usr/bin/env python3
"""案例 1：pyshark 基础用法 - 读取 PCAP 并列出数据包基本信息"""

import pyshark

def main():
    pcap_file = 'example_traffic.pcap'
    
    print(f"正在分析文件: {pcap_file}")
    print("=" * 60)
    
    # 创建 FileCapture 对象
    # only_summaries=True 只获取摘要信息，性能更好
    cap = pyshark.FileCapture(pcap_file, only_summaries=True)
    
    packet_count = 0
    
    try:
        for packet in cap:
            packet_count += 1
            # 访问基本属性
            print(f"数据包 #{packet.number}")
            
            # 尝试访问 IP 层信息
            if hasattr(packet, 'ip'):
                print(f"  源 IP: {packet.ip.src_ip}")
                print(f"  目标 IP: {packet.ip.dst_ip}")
                print(f"  协议: {packet.ip.protocol}")
            
            # 尝试访问 TCP 层信息
            if hasattr(packet, 'tcp'):
                print(f"  源端口: {packet.tcp.src_port}")
                print(f"  目标端口: {packet.tcp.dst_port}")
                print(f"  TCP 标志: {packet.tcp.flags}")
            
            # 尝试访问 UDP 层信息
            if hasattr(packet, 'udp'):
                print(f"  源端口: {packet.udp.src_port}")
                print(f"  目标端口: {packet.udp.dst_port}")
            
            print()  # 空行分隔数据包
    finally:
        cap.close()
    
    print(f"总计处理了 {packet_count} 个数据包")

if __name__ == "__main__":
    main()