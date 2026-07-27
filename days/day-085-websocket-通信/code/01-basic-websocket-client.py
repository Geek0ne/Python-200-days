#!/usr/bin/env python3
"""
Day 085 - WebSocket 基础客户端
================================
配合 01-basic-websocket-server.py 使用。

运行方式（需先启动服务端）：
    python3 01-basic-websocket-client.py
"""

import asyncio
import websockets


async def simple_client():
    """最简单的 WebSocket 客户端"""
    uri = "ws://localhost:8765"
    
    print(f"[客户端] 正在连接 {uri}...")
    
    async with websockets.connect(uri) as ws:
        print("[客户端] 连接成功!")
        
        # 发送消息并接收回复
        messages = ["Hello!", "你好世界", "WebSocket 真有趣"]
        
        for msg in messages:
            await ws.send(msg)
            print(f"[客户端] 发送: {msg}")
            
            reply = await ws.recv()
            print(f"[客户端] 收到: {reply}")
            print()
        
        print("[客户端] 测试完成，连接将关闭")


async def interactive_client():
    """交互式客户端：从终端输入消息"""
    uri = "ws://localhost:8765"
    
    print(f"[交互客户端] 连接 {uri}...")
    
    async with websockets.connect(uri) as ws:
        print("[交互客户端] 连接成功! 输入消息发送，输入 'quit' 退出")
        print("-" * 50)
        
        loop = asyncio.get_event_loop()
        
        while True:
            # 在终端读取输入（非阻塞）
            message = await loop.run_in_executor(None, input, ">>> ")
            
            if message.strip().lower() == "quit":
                print("[交互客户端] 再见!")
                break
            
            if not message.strip():
                continue
            
            await ws.send(message)
            response = await ws.recv()
            print(f"[服务器] {response}")


async def client_with_error_handling():
    """带完善错误处理的客户端"""
    uri = "ws://localhost:8765"
    
    try:
        # 设置连接超时
        async with websockets.connect(uri, open_timeout=5) as ws:
            print("[客户端] 连接成功!")
            
            await ws.send("测试消息")
            response = await ws.recv()
            print(f"[客户端] 收到: {response}")
            
    except websockets.exceptions.InvalidURI:
        print(f"[客户端] 错误: URI 格式无效 - {uri}")
    except websockets.exceptions.InvalidHandshake as e:
        print(f"[客户端] 错误: 握手失败 - {e}")
    except ConnectionRefusedError:
        print("[客户端] 错误: 连接被拒绝，服务器可能未启动")
    except asyncio.TimeoutError:
        print("[客户端] 错误: 连接超时")
    except Exception as e:
        print(f"[客户端] 未知错误: {type(e).__name__}: {e}")


if __name__ == "__main__":
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "simple"
    
    if mode == "interactive":
        asyncio.run(interactive_client())
    elif mode == "error":
        asyncio.run(client_with_error_handling())
    else:
        asyncio.run(simple_client())
