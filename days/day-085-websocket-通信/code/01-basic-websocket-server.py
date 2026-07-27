#!/usr/bin/env python3
"""
Day 085 - WebSocket 基础用法
=============================
演示 WebSocket 服务端和客户端的基本通信。

运行方式：
    1. 终端1：python3 01-basic-websocket-server.py
    2. 终端2：python3 01-basic-websocket-client.py
"""

import asyncio
import websockets


# ============================================================
# 服务端代码
# ============================================================

async def echo_handler(websocket):
    """
    回显处理器：接收客户端消息，原样返回。
    
    websocket 对象的核心方法：
    - send(data): 发送消息
    - recv(): 接收消息
    - close(): 关闭连接
    - remote_addr: 客户端地址 (host, port)
    - path: 请求路径
    """
    client_addr = websocket.remote_addr
    print(f"[服务端] 客户端已连接: {client_addr}")
    
    try:
        # async for 会持续监听消息，直到连接关闭
        async for message in websocket:
            print(f"[服务端] 收到来自 {client_addr} 的消息: {message}")
            
            # 回显消息
            response = f"服务器已收到: {message}"
            await websocket.send(response)
            print(f"[服务端] 已回复: {response}")
            
    except websockets.exceptions.ConnectionClosedOK:
        print(f"[服务端] 客户端正常断开: {client_addr}")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"[服务端] 客户端异常断开: {client_addr}, 原因: {e}")
    finally:
        print(f"[服务端] 连接清理完成: {client_addr}")


async def run_server():
    """启动 WebSocket 服务器"""
    print("[服务端] 正在启动 WebSocket 服务器...")
    print("[服务端] 监听地址: ws://localhost:8765")
    
    async with websockets.serve(echo_handler, "localhost", 8765):
        print("[服务端] 服务器已启动，等待客户端连接...")
        print("[服务端] 按 Ctrl+C 停止服务器")
        await asyncio.Future()  # 永久运行，直到被中断


# ============================================================
# 客户端代码
# ============================================================

async def run_client():
    """连接到 WebSocket 服务器并发送消息"""
    uri = "ws://localhost:8765"
    
    print(f"[客户端] 正在连接 {uri}...")
    
    async with websockets.connect(uri) as websocket:
        print("[客户端] 连接成功!")
        
        # 发送几条测试消息
        test_messages = [
            "你好，WebSocket!",
            "这是第二条消息",
            "Python + asyncio 真强大!",
        ]
        
        for msg in test_messages:
            await websocket.send(msg)
            print(f"[客户端] 已发送: {msg}")
            
            # 等待服务器回复
            response = await websocket.recv()
            print(f"[客户端] 收到回复: {response}")
        
        print("[客户端] 所有测试消息发送完毕")


# ============================================================
# 入口：根据命令行参数选择运行模式
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "client":
        # 客户端模式
        asyncio.run(run_client())
    else:
        # 默认运行服务端
        try:
            asyncio.run(run_server())
        except KeyboardInterrupt:
            print("\n[服务端] 服务器已停止")
