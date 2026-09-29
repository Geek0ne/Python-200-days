"""
Day 093 - 网络编程深入
01-socket-basics.py: TCP Socket 基础用法

知识点:
  - socket 创建、绑定、监听、连接
  - TCP 客户端/服务器通信
  - 非阻塞 socket 设置
"""

import socket
import threading
import time

# ============================================================
# 第一部分：TCP 服务器
# ============================================================

def run_server():
    """一个简单的 TCP 服务器"""
    # 创建 TCP socket
    # AF_INET = IPv4, SOCK_STREAM = TCP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # SO_REUSEADDR: 允许重用处于 TIME_WAIT 状态的端口
    # 这在开发时非常有用，否则重启服务器会报 "Address already in use"
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # 绑定地址和端口
    # '127.0.0.1' 表示只监听本机，'0.0.0.0' 表示监听所有网卡
    server_socket.bind(('127.0.0.1', 9999))
    
    # 开始监听，backlog=5 表示最多 5 个连接在队列中等待
    server_socket.listen(5)
    print("🟢 服务器启动: 127.0.0.1:9999")
    
    # 设置超时，这样服务器可以被 Ctrl+C 中断
    server_socket.settimeout(1.0)
    
    try:
        while True:
            try:
                # accept() 阻塞等待客户端连接
                # 返回 (新的 socket 对象, 客户端地址)
                conn, addr = server_socket.accept()
                print(f"✅ 新连接: {addr}")
                
                # 为每个连接创建一个线程处理
                t = threading.Thread(
                    target=handle_client, 
                    args=(conn, addr),
                    daemon=True
                )
                t.start()
                
            except socket.timeout:
                # 超时后继续循环，允许捕获 KeyboardInterrupt
                continue
    except KeyboardInterrupt:
        print("\n🔴 服务器关闭")
    finally:
        server_socket.close()


def handle_client(conn, addr):
    """处理单个客户端连接"""
    try:
        while True:
            # recv() 阻塞等待数据
            # 返回 bytes 类型，最大 1024 字节
            data = conn.recv(1024)
            
            if not data:
                # 客户端发送空数据表示断开连接
                print(f"❌ 客户端 {addr} 断开")
                break
            
            message = data.decode('utf-8')
            print(f"📩 收到 [{addr}]: {message}")
            
            # 处理特殊命令
            if message.lower() == 'quit':
                conn.sendall(b'Goodbye!')
                break
            
            # 回显消息（Echo 服务器）
            response = f"Echo: {message}"
            conn.sendall(response.encode('utf-8'))
            
    except Exception as e:
        print(f"❌ 处理 {addr} 出错: {e}")
    finally:
        conn.close()


# ============================================================
# 第部分：TCP 客户端
# ============================================================

def run_client():
    """TCP 客户端示例"""
    # 创建 socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # 连接服务器
        client_socket.connect(('127.0.0.1', 9999))
        print("🔗 已连接到服务器")
        
        # 发送数据
        messages = ["Hello!", "Python Socket", "网络编程真有趣"]
        
        for msg in messages:
            # sendall() 保证发送所有数据
            # send() 可能只发送部分数据
            client_socket.sendall(msg.encode('utf-8'))
            
            # 接收响应
            response = client_socket.recv(1024)
            print(f"📨 服务器回复: {response.decode('utf-8')}")
            
            time.sleep(0.5)
        
        # 发送退出命令
        client_socket.sendall(b'quit')
        response = client_socket.recv(1024)
        print(f"📨 服务器回复: {response.decode('utf-8')}")
        
    except ConnectionRefusedError:
        print("❌ 连接失败，服务器未启动")
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        client_socket.close()


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'client':
        # 以客户端模式运行
        run_client()
    else:
        # 启动服务器（后台线程）
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(1)
        
        # 启动客户端
        run_client()
        
        # 等待一下让服务器输出完成
        time.sleep(0.5)
        print("\n✅ 演示完成")
