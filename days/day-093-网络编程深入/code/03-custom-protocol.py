"""
Day 093 - 网络编程深入
03-custom-protocol.py: 自定义协议服务器实战

知识点:
  - 协议设计（长度前缀 + 消息类型）
  - 结构化消息编解码
  - 协议版本兼容
  - 实战：远程命令执行服务器
"""

import asyncio
import json
import struct
import os
import sys
from datetime import datetime
from typing import Optional

# ============================================================
# 协议定义
# ============================================================
#
# 消息格式 (二进制协议):
# ┌────────┬────────┬────────┬─────────────────┐
# │ Magic  │Version │MsgType │    Payload      │
# │ 2 bytes│1 byte  │1 byte  │  N bytes        │
# └────────┴────────┴────────┴─────────────────┘
#
# Magic:   0x48 0x54 ("HT" for "Hello Transport")
# Version: 协议版本号 (当前 1)
# MsgType: 消息类型
#   0x01 = REQUEST   (客户端请求)
#   0x02 = RESPONSE  (服务端响应)
#   0x03 = HEARTBEAT (心跳)
#   0x04 = ERROR     (错误)
# Payload: JSON 格式的消息体
# ============================================================

# 协议常量
MAGIC = b'\x48\x54'      # "HT"
VERSION = 1
HEADER_SIZE = 4           # 2(Magic) + 1(Version) + 1(MsgType)

# 消息类型
MSG_REQUEST = 0x01
MSG_RESPONSE = 0x02
MSG_HEARTBEAT = 0x03
MSG_ERROR = 0x04


class ProtocolCodec:
    """协议编解码器"""
    
    @staticmethod
    def encode(msg_type: int, payload: dict) -> bytes:
        """编码消息为二进制格式"""
        # 将 payload 序列化为 JSON
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        
        # 构建头部
        header = MAGIC + bytes([VERSION, msg_type])
        
        # 添加 payload 长度 (4 bytes, 大端序)
        length_bytes = struct.pack('>I', len(payload_bytes))
        
        return header + length_bytes + payload_bytes
    
    @staticmethod
    def decode(data: bytes) -> Optional[tuple]:
        """
        解码二进制数据
        返回 (msg_type, payload_dict) 或 None（数据不完整）
        """
        if len(data) < HEADER_SIZE + 4:
            return None  # 头部不完整
        
        # 验证 Magic
        if data[:2] != MAGIC:
            raise ValueError(f"无效的 Magic: {data[:2].hex()}")
        
        # 验证版本
        version = data[2]
        if version > VERSION:
            raise ValueError(f"不支持的协议版本: {version}")
        
        # 解析消息类型
        msg_type = data[3]
        
        # 解析 payload 长度
        payload_length = struct.unpack('>I', data[4:8])[0]
        
        # 检查数据是否完整
        total_length = HEADER_SIZE + 4 + payload_length
        if len(data) < total_length:
            return None  # 数据不完整
        
        # 解析 payload
        payload_bytes = data[HEADER_SIZE + 4:total_length]
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        return (msg_type, payload, total_length)


# ============================================================
# 协议服务器
# ============================================================

class ProtocolServer:
    """基于自定义协议的服务器"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 7777):
        self.host = host
        self.port = port
        self.codec = ProtocolCodec()
    
    async def handle_client(self, reader: asyncio.StreamReader,
                            writer: asyncio.StreamWriter):
        """处理客户端连接"""
        addr = writer.get_extra_info('peername')
        print(f"✅ 客户端连接: {addr}")
        
        buffer = b''  # 接收缓冲区
        
        try:
            while True:
                # 读取数据
                chunk = await reader.read(4096)
                if not chunk:
                    break
                
                buffer += chunk
                
                # 尝试解析完整消息
                while len(buffer) >= HEADER_SIZE + 4:
                    result = self.codec.decode(buffer)
                    if result is None:
                        break  # 数据不完整，等待更多数据
                    
                    msg_type, payload, consumed = result
                    buffer = buffer[consumed:]  # 移除已处理的数据
                    
                    # 处理消息
                    await self.process_message(writer, msg_type, payload)
                    
        except Exception as e:
            print(f"❌ 客户端 {addr} 错误: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"❌ 客户端断开: {addr}")
    
    async def process_message(self, writer: asyncio.StreamWriter,
                              msg_type: int, payload: dict):
        """处理收到的消息"""
        if msg_type == MSG_HEARTBEAT:
            # 回复心跳
            response = self.codec.encode(MSG_HEARTBEAT, {
                "status": "ok",
                "timestamp": datetime.now().isoformat()
            })
            writer.write(response)
            await writer.drain()
            
        elif msg_type == MSG_REQUEST:
            # 处理请求
            command = payload.get('command')
            result = await self.execute_command(command, payload)
            
            # 发送响应
            response = self.codec.encode(MSG_RESPONSE, result)
            writer.write(response)
            await writer.drain()
    
    async def execute_command(self, command: str, payload: dict) -> dict:
        """执行客户端请求的命令"""
        if command == 'time':
            return {
                "command": "time",
                "result": datetime.now().isoformat()
            }
        
        elif command == 'info':
            return {
                "command": "info",
                "result": {
                    "platform": sys.platform,
                    "python": sys.version,
                    "pid": os.getpid()
                }
            }
        
        elif command == 'echo':
            return {
                "command": "echo",
                "result": payload.get('data', '')
            }
        
        elif command == 'calc':
            # 简单计算器（仅用于演示，生产环境需安全处理）
            expression = payload.get('expression', '0')
            try:
                # 注意：生产环境中绝对不要用 eval()！
                # 这里仅作为协议演示
                result = eval(expression)
                return {"command": "calc", "result": result}
            except Exception as e:
                return {"command": "calc", "error": str(e)}
        
        else:
            return {"error": f"未知命令: {command}"}
    
    async def run(self):
        """启动服务器"""
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        
        print(f"🟢 协议服务器启动: {self.host}:{self.port}")
        print(f"   协议版本: v{VERSION}")
        print(f"   Magic: {MAGIC.hex()}")
        
        async with server:
            await server.serve_forever()


# ============================================================
# 协议客户端
# ============================================================

class ProtocolClient:
    """基于自定义协议的客户端"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 7777):
        self.host = host
        self.port = port
        self.codec = ProtocolCodec()
        self.reader = None
        self.writer = None
    
    async def connect(self):
        """连接服务器"""
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port
        )
        print(f"🔗 已连接到 {self.host}:{self.port}")
    
    async def send_request(self, command: str, **kwargs) -> dict:
        """发送请求并等待响应"""
        # 构建请求
        payload = {"command": command, **kwargs}
        data = self.codec.encode(MSG_REQUEST, payload)
        
        self.writer.write(data)
        await self.writer.drain()
        
        # 接收响应
        response_data = await self.reader.read(4096)
        result = self.codec.decode(response_data)
        
        if result:
            msg_type, payload, _ = result
            return payload
        return {"error": "无响应"}
    
    async def heartbeat(self):
        """发送心跳"""
        data = self.codec.encode(MSG_HEARTBEAT, {"ping": True})
        self.writer.write(data)
        await self.writer.drain()
        
        response = await self.reader.read(4096)
        result = self.codec.decode(response)
        if result:
            return result[1]
        return None
    
    async def close(self):
        """关闭连接"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()


# ============================================================
# 演示程序
# ============================================================

async def demo():
    """演示自定义协议通信"""
    # 启动服务器
    server = ProtocolServer()
    server_task = asyncio.create_task(server.run())
    await asyncio.sleep(0.5)  # 等待服务器启动
    
    # 创建客户端
    client = ProtocolClient()
    await client.connect()
    
    try:
        # 测试心跳
        print("\n--- 测试心跳 ---")
        heartbeat = await client.heartbeat()
        print(f"💓 心跳响应: {heartbeat}")
        
        # 测试获取时间
        print("\n--- 测试获取时间 ---")
        result = await client.send_request('time')
        print(f"⏰ 服务器时间: {result.get('result')}")
        
        # 测试获取服务器信息
        print("\n--- 测试服务器信息 ---")
        result = await client.send_request('info')
        print(f"📊 服务器信息:")
        info = result.get('result', {})
        for key, value in info.items():
            print(f"   {key}: {value}")
        
        # 测试 echo
        print("\n--- 测试 Echo ---")
        result = await client.send_request('echo', data='Hello, Protocol!')
        print(f"🔊 Echo: {result.get('result')}")
        
        # 测试计算器
        print("\n--- 测试计算器 ---")
        result = await client.send_request('calc', expression='2 + 3 * 4')
        print(f"🧮 2 + 3 * 4 = {result.get('result')}")
        
    finally:
        await client.close()
        server_task.cancel()
        print("\n✅ 演示完成")


if __name__ == '__main__':
    try:
        asyncio.run(demo())
    except KeyboardInterrupt:
        print("\n程序退出")
