#!/usr/bin/env python3
"""案例 2：pyshark 高级过滤 - 只提取特定协议的数据包"""

import pyshark

def main():
    pcap_file = 'web_traffic.pcap'
    
    print(f"正在过滤文件: {pcap_file}")
    print("=" * 60)
    print("过滤器: 只显示 HTTP 数据包")
    print("=" * 60)
    
    # 使用 display_filter 只过滤 HTTP 流量
    cap = pyshark.FileCapture(pcap_file, 
                              display_filter='http',
                              only_summaries=True)
    
    http_count = 0
    total_count = 0
    
    try:
        for packet in cap:
            total_count += 1
            http_count += 1
            
            print(f"数据包 #{packet.number} (HTTP 流量)")
            
            # HTTP 层属性
            print(f"  方法: {packet.http.method}")
            print(f"  主机: {packet.http.host}")
            print(f"  路径: {packet.http.request_uri}")
            print(f"  协议版本: {packet.http.version}")
            
            if hasattr(packet, 'tcp'):
                print(f"  源端口: {packet.tcp.src_port}")
                print(f"  目标端口: {packet.tcp.dst_port}")
            
            print()
    finally:
        cap.close()
    
    print(f"统计结果:")
    print(f"  总数据包数: {total_count}")
    print(f"  HTTP 数据包数: {http_count}")
    print(f"  占比: {http_count/total_count*100:.1f}%" if total_count > 0 else "  占比: N/A")

if __name__ == "__main__":
    main()