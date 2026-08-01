"""
Day 093 - 网络编程深入
02-async-server.py: asyncio 异步网络服务器进阶

知识点:
  - asyncio.start_server 异步 TCP 服务器
  - 协程并发处理多个连接
  - 优雅关闭服务器
  - 超时与心跳检测
"""

import asyncio
import json
import time
from typing import Dict, Set

# ============================================================
# 第一部分：异步聊天服务器
# ============================================================

class AsyncChatServer:
    """基于 asyncio 的异步聊天服务器"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 8888):
        self.host = host
        self.port = port
        # 保存所有在线用户的 writer
        self.clients: Dict[str, asyncio.StreamWriter] = {}
        # 保存每个连接的最后活跃时间
        self.last_active: Dict[str, float] = {}
    
    async def handle_client(self, reader: asyncio.StreamReader, 
                            writer: asyncio.StreamWriter):
        """处理单个客户端连接（异步）"""
        addr = writer.get_extra_info('peername')
        client_id = f"{addr[0]}:{addr[1]}"
        
        print(f"✅ 新用户连接: {client_id}")
        self.clients[client_id] = writer
        self.last_active[client_id] = time.time()
        
        # 发送欢迎消息
        welcome = {
            "type": "system",
            "message": f"欢迎 {client_id}！在线人数: {len(self.clients)}",
            "online_count": len(self.clients)
        }
        writer.write(json.dumps(welcome).encode() + b'\n')
        await writer.drain()
        
        # 广播新用户加入
        await self.broadcast({
            "type": "join",
            "message": f"{client_id} 加入了聊天室"
        }, exclude=client_id)
        
        try:
            while True:
                # 异步等待数据
                # readline() 会一直读到 \n
                data = await reader.readline()
                
                if not data:
                    break
                
                self.last_active[client_id] = time.time()
                message = data.decode().strip()
                
                if not message:
                    continue
                
                # 处理特殊命令
                if message.lower() == '/quit':
                    break
                elif message.lower() == '/online':
                    # 查询在线用户
                    response = {
                        "type": "info",
                        "online_users": list(self.clients.keys())
                    }
                    writer.write(json.dumps(response).encode() + b'\n')
                    await writer.drain()
                elif message.lower().startswith('/msg '):
                    # 私聊功能: /msg 用户名 消息内容
                    parts = message[5:].split(' ', 1)
                    if len(parts) == 2:
                        target_id, private_msg = parts
                        await self.send_private(client_id, target_id, private_msg)
                    else:
                        writer.write(b'{"type":"error","message":"用法: /msg 用户名 消息"}\n')
                        await writer.drain()
                else:
                    # 广播消息
                    await self.broadcast({
                        "type": "message",
                        "from": client_id,
                        "message": message,
                        "timestamp": time.time()
                    }, exclude=client_id)
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ 客户端 {client_id} 出错: {e}")
        finally:
            # 清理连接
            del self.clients[client_id]
            del self.last_active[client_id]
            writer.close()
            await writer.wait_closed()
            
            # 广播用户离开
            await self.broadcast({
                "type": "leave",
                "message": f"{client_id} 离开了聊天室",
                "online_count": len(self.clients)
            })
            print(f"❌ 用户断开: {client_id}")
    
    async def broadcast(self, message: dict, exclude: str = None):
        """广播消息给所有在线用户"""
        data = json.dumps(message).encode() + b'\n'
        disconnected = []
        
        for client_id, writer in self.clients.items():
            if client_id == exclude:
                continue
            try:
                writer.write(data)
                await writer.drain()
            except Exception:
                disconnected.append(client_id)
        
        # 清理断开的连接
        for cid in disconnected:
            self.clients.pop(cid, None)
            self.last_active.pop(cid, None)
    
    async def send_private(self, from_id: str, to_id: str, message: str):
        """发送私聊消息"""
        writer = self.clients.get(to_id)
        if writer:
            private_msg = {
                "type": "private",
                "from": from_id,
                "message": message
            }
            writer.write(json.dumps(private_msg).encode() + b'\n')
            await writer.drain()
        else:
            sender = self.clients.get(from_id)
            if sender:
                error = {"type": "error", "message": f"用户 {to_id} 不在线"}
                sender.write(json.dumps(error).encode() + b'\n')
                await sender.drain()
    
    async def heartbeat_check(self, timeout: float = 60.0):
        """定期检查不活跃的连接"""
        while True:
            await asyncio.sleep(30)
            now = time.time()
            disconnected = []
            
            for client_id, last_time in self.last_active.items():
                if now - last_time > timeout:
                    disconnected.append(client_id)
            
            for cid in disconnected:
                writer = self.clients.pop(cid, None)
                self.last_active.pop(cid, None)
                if writer:
                    writer.close()
                    print(f"💤 踢出不活跃用户: {cid}")
    
    async def run(self):
        """启动服务器"""
        # 启动 TCP 服务器
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        
        print(f"🟢 异步聊天服务器启动: {self.host}:{self.port}")
        
        # 启动心跳检测任务
        heartbeat_task = asyncio.create_task(self.heartbeat_check())
        
        try:
            # serve_forever() 会一直运行
            await server.serve_forever()
        finally:
            heartbeat_task.cancel()
            server.close()
            await server.wait_closed()


# ============================================================
# 第二部分：异步 TCP 客户端
# ============================================================

class AsyncChatClient:
    """异步 TCP 客户端"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 8888):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
    
    async def connect(self):
        """连接服务器"""
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port
        )
        print(f"🔗 已连接到 {self.host}:{self.port}")
    
    async def receive_messages(self):
        """持续接收服务器消息"""
        try:
            while True:
                data = await self.reader.readline()
                if not data:
                    print("❌ 服务器断开连接")
                    break
                
                msg = json.loads(data.decode().strip())
                
                # 根据消息类型显示不同格式
                msg_type = msg.get('type')
                if msg_type == 'system':
                    print(f"🟢 {msg['message']}")
                elif msg_type == 'join':
                    print(f"➕ {msg['message']}")
                elif msg_type == 'leave':
                    print(f"➖ {msg['message']}")
                elif msg_type == 'message':
                    print(f"💬 {msg['from']}: {msg['message']}")
                elif msg_type == 'private':
                    print(f"🔒 {msg['from']} (私聊): {msg['message']}")
                elif msg_type == 'info':
                    print(f"📋 在线用户: {msg.get('online_users', [])}")
                elif msg_type == 'error':
                    print(f"⚠️ {msg['message']}")
                    
        except asyncio.CancelledError:
            pass
    
    async def send_messages(self):
        """读取用户输入并发送"""
        loop = asyncio.get_event_loop()
        try:
            while True:
                # 在事件循环中执行阻塞的 input()
                message = await loop.run_in_executor(None, input)
                if not message:
                    continue
                
                self.writer.write(message.encode() + b'\n')
                await self.writer.drain()
                
                if message.lower() == '/quit':
                    break
        except (EOFError, KeyboardInterrupt):
            self.writer.write(b'/quit\n')
            await self.writer.drain()
    
    async def run(self):
        """运行客户端"""
        await self.connect()
        
        # 并发运行接收和发送
        receive_task = asyncio.create_task(self.receive_messages())
        send_task = asyncio.create_task(self.send_messages())
        
        # 等待任一任务完成（通常是发送退出命令）
        done, pending = await asyncio.wait(
            [receive_task, send_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # 取消未完成的任务
        for task in pending:
            task.cancel()
        
        self.writer.close()
        await self.writer.wait_closed()
        print("👋 已断开连接")


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'client':
        client = AsyncChatClient()
        asyncio.run(client.run())
    else:
        server = AsyncChatServer()
        try:
            asyncio.run(server.run())
        except KeyboardInterrupt:
            print("\n🔴 服务器已关闭")
