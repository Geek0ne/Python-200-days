#!/usr/bin/env python3
"""
Day 085 - WebSocket 进阶用法
================================
演示并发连接管理、心跳检测、消息广播、JSON 协议等进阶话题。

运行方式：
    1. 终端1：python3 02-advanced-websocket.py server
    2. 终端2/3/...：python3 02-advanced-websocket.py client
"""

import asyncio
import json
import time
import websockets
from datetime import datetime


# ============================================================
# 第一部分：并发连接管理（广播服务器）
# ============================================================

class BroadcastServer:
    """
    广播服务器：支持多客户端同时连接，消息广播给所有人。
    
    关键点：
    1. 用 set 存储所有连接
    2. 广播时复制集合，防止遍历时修改报错
    3. 连接断开时必须清理资源
    """
    
    def __init__(self):
        self.connected = set()  # 存储所有活跃连接
        self.user_count = 0     # 用户计数器
    
    async def handler(self, websocket):
        """处理单个客户端连接"""
        self.user_count += 1
        username = f"用户{self.user_count}"
        
        # 注册连接
        self.connected.add(websocket)
        print(f"[广播] {username} 已连接 (当前在线: {len(self.connected)})")
        
        # 通知所有用户有人加入
        await self.broadcast({
            "type": "system",
            "message": f"{username} 加入了聊天室",
            "online_count": len(self.connected),
        })
        
        try:
            async for raw_message in websocket:
                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "消息格式错误，需要 JSON"
                    }))
                    continue
                
                # 广播聊天消息
                await self.broadcast({
                    "type": "chat",
                    "username": username,
                    "content": message.get("content", ""),
                    "timestamp": datetime.now().isoformat(),
                })
                
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # 清理连接（必须在 finally 中！）
            self.connected.discard(websocket)
            print(f"[广播] {username} 已断开 (当前在线: {len(self.connected)})")
            
            # 通知所有人
            if self.connected:
                await self.broadcast({
                    "type": "system",
                    "message": f"{username} 离开了聊天室",
                    "online_count": len(self.connected),
                })
    
    async def broadcast(self, message):
        """
        广播消息给所有客户端。
        
        ⚠️ 重要：使用 .copy() 复制集合！
        遍历过程中如果某客户端断开，集合会变化，导致 RuntimeError。
        """
        data = json.dumps(message, ensure_ascii=False)
        
        # 复制集合再遍历
        for client in self.connected.copy():
            try:
                await client.send(data)
            except websockets.exceptions.ConnectionClosed:
                # 发送失败说明已断开，清理掉
                self.connected.discard(client)
    
    async def run(self, host="localhost", port=8766):
        """启动服务器"""
        print(f"[广播] 启动广播服务器 ws://{host}:{port}")
        
        async with websockets.serve(
            self.handler,
            host,
            port,
            ping_interval=20,    # 20秒心跳间隔
            ping_timeout=10,     # 10秒超时
            max_size=10 * 1024,  # 最大消息 10KB
        ):
            print("[广播] 服务器已启动，等待连接...")
            await asyncio.Future()


# ============================================================
# 第二部分：心跳检测演示
# ============================================================

class HeartbeatDemo:
    """
    演示 WebSocket 心跳机制。
    
    websockets 库内置了 ping/pong 心跳支持：
    - ping_interval: 每隔 N 秒发送 ping
    - ping_timeout: 收不到 pong 则判定连接断开
    
    手动发送心跳（备用方案）：
    - await websocket.ping()
    """
    
    @staticmethod
    async def heartbeat_server():
        """带心跳检测的服务端"""
        async def handler(websocket):
            print("[心跳服务端] 新连接")
            try:
                async for message in websocket:
                    print(f"[心跳服务端] 收到: {message}")
                    await websocket.send(f"echo: {message}")
            except websockets.exceptions.ConnectionClosed as e:
                # code=1001 表示正常关闭
                # code=1006 表示异常关闭（未收到关闭帧）
                print(f"[心跳服务端] 连接关闭 code={e.code}")
        
        async with websockets.serve(
            handler, "localhost", 8767,
            ping_interval=10,  # 每10秒 ping 一次
            ping_timeout=5,    # 5秒内没 pong 则断开
        ):
            print("[心跳服务端] 启动，ping间隔=10s, 超时=5s")
            await asyncio.Future()
    
    @staticmethod
    async def heartbeat_client():
        """带自动重连的客户端"""
        uri = "ws://localhost:8767"
        reconnect_delay = 1  # 初始重连延迟（秒）
        max_delay = 30       # 最大重连延迟
        
        while True:
            try:
                print(f"[心跳客户端] 尝试连接 {uri}...")
                async with websockets.connect(uri) as ws:
                    print("[心跳客户端] 连接成功!")
                    reconnect_delay = 1  # 重置延迟
                    
                    # 发送测试消息
                    for i in range(5):
                        msg = f"消息 {i+1}"
                        await ws.send(msg)
                        reply = await ws.recv()
                        print(f"[心跳客户端] {reply}")
                        await asyncio.sleep(2)
                    
                    print("[心跳客户端] 测试完成")
                    break
                    
            except websockets.exceptions.ConnectionClosed:
                print(f"[心跳客户端] 连接断开，{reconnect_delay}秒后重连...")
            except ConnectionRefusedError:
                print(f"[心跳客户端] 服务器未启动，{reconnect_delay}秒后重试...")
            except Exception as e:
                print(f"[心跳客户端] 错误: {e}")
            
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_delay)  # 指数退避


# ============================================================
# 第三部分：JSON 协议设计
# ============================================================

class MessageProtocol:
    """
    WebSocket 消息协议设计最佳实践。
    
    规范：
    1. 所有消息使用 JSON 格式
    2. 必须包含 type 字段区分消息类型
    3. 包含 timestamp 记录时间
    4. 错误消息统一格式
    """
    
    @staticmethod
    def create_message(msg_type, **kwargs):
        """创建标准消息"""
        return json.dumps({
            "type": msg_type,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }, ensure_ascii=False)
    
    @staticmethod
    def parse_message(raw):
        """解析并验证消息"""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None, "无效的 JSON 格式"
        
        if "type" not in data:
            return None, "缺少 type 字段"
        
        return data, None
    
    @staticmethod
    async def protocol_server():
        """遵循协议的服务端"""
        async def handler(websocket):
            try:
                async for raw in websocket:
                    msg, error = MessageProtocol.parse_message(raw)
                    
                    if error:
                        await websocket.send(MessageProtocol.create_message(
                            "error", message=error
                        ))
                        continue
                    
                    msg_type = msg["type"]
                    
                    if msg_type == "ping":
                        await websocket.send(MessageProtocol.create_message("pong"))
                    
                    elif msg_type == "chat":
                        content = msg.get("content", "")
                        print(f"[协议服务端] 聊天: {content}")
                        await websocket.send(MessageProtocol.create_message(
                            "ack", original_type="chat"
                        ))
                    
                    else:
                        await websocket.send(MessageProtocol.create_message(
                            "error", message=f"未知消息类型: {msg_type}"
                        ))
                        
            except websockets.exceptions.ConnectionClosed:
                print("[协议服务端] 连接关闭")
        
        async with websockets.serve(handler, "localhost", 8768):
            print("[协议服务端] 启动，支持 JSON 协议")
            await asyncio.Future()
    
    @staticmethod
    async def protocol_client():
        """遵循协议的客户端"""
        uri = "ws://localhost:8768"
        
        async with websockets.connect(uri) as ws:
            print("[协议客户端] 连接成功")
            
            # 发送心跳
            await ws.send(MessageProtocol.create_message("ping"))
            reply = json.loads(await ws.recv())
            print(f"[协议客户端] 心跳回复: {reply['type']}")
            
            # 发送聊天消息
            await ws.send(MessageProtocol.create_message(
                "chat", content="你好！这是协议客户端"
            ))
            ack = json.loads(await ws.recv())
            print(f"[协议客户端] 确认: {ack['type']}")
            
            # 发送无效消息（演示错误处理）
            await ws.send("这不是JSON")
            error = json.loads(await ws.recv())
            print(f"[协议客户端] 错误响应: {error}")


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 02-advanced-websocket.py server        # 广播服务器")
        print("  python3 02-advanced-websocket.py client        # 广播客户端")
        print("  python3 02-advanced-websocket.py heartbeat-s   # 心跳服务端")
        print("  python3 02-advanced-websocket.py heartbeat-c   # 心跳客户端")
        print("  python3 02-advanced-websocket.py protocol-s    # 协议服务端")
        print("  python3 02-advanced-websocket.py protocol-c    # 协议客户端")
        sys.exit(0)
    
    mode = sys.argv[1]
    
    if mode == "server":
        server = BroadcastServer()
        try:
            asyncio.run(server.run())
        except KeyboardInterrupt:
            print("\n[广播] 服务器已停止")
    
    elif mode == "client":
        async def broadcast_client():
            uri = "ws://localhost:8766"
            async with websockets.connect(uri) as ws:
                print("[广播客户端] 已连接广播服务器")
                # 启动接收协程
                async def receiver():
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg["type"] == "system":
                            print(f"[系统] {msg['message']} (在线: {msg.get('online_count', '?')})")
                        elif msg["type"] == "chat":
                            print(f"[{msg['username']}] {msg['content']}")
                
                recv_task = asyncio.create_task(receiver())
                
                # 发送几条测试消息
                for i in range(3):
                    await ws.send(json.dumps({
                        "type": "chat",
                        "content": f"广播测试消息 {i+1}"
                    }))
                    await asyncio.sleep(0.5)
                
                await asyncio.sleep(1)
                recv_task.cancel()
        
        asyncio.run(broadcast_client())
    
    elif mode == "heartbeat-s":
        try:
            asyncio.run(HeartbeatDemo.heartbeat_server())
        except KeyboardInterrupt:
            print("\n[心跳] 服务端已停止")
    
    elif mode == "heartbeat-c":
        asyncio.run(HeartbeatDemo.heartbeat_client())
    
    elif mode == "protocol-s":
        try:
            asyncio.run(MessageProtocol.protocol_server())
        except KeyboardInterrupt:
            print("\n[协议] 服务端已停止")
    
    elif mode == "protocol-c":
        asyncio.run(MessageProtocol.protocol_client())
    
    else:
        print(f"未知模式: {mode}")
