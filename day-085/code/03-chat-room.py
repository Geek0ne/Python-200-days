#!/usr/bin/env python3
"""
Day 085 - WebSocket 实战：聊天室
==================================
一个功能完整的聊天室，支持：
- 多人同时聊天
- 用户加入/离开通知
- 在线人数统计
- 消息历史记录
- 客户端自动重连

运行方式：
    1. 终端1：python3 03-chat-room.py server
    2. 终端2/3/...：python3 03-chat-room.py client [用户名]
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, Set, Optional

import websockets


# ============================================================
# 聊天室服务器
# ============================================================

class ChatRoom:
    """
    聊天室核心类
    
    功能：
    1. 管理所有连接的客户端
    2. 广播消息给所有用户
    3. 记录聊天历史
    4. 处理用户加入/离开
    """
    
    def __init__(self, name: str = "默认聊天室"):
        self.name = name
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.history: list = []
        self.max_history = 100  # 最多保存100条历史消息
        self.user_id_counter = 0
    
    def _next_user_id(self) -> int:
        """生成下一个用户ID"""
        self.user_id_counter += 1
        return self.user_id_counter
    
    def _make_message(self, msg_type: str, **kwargs) -> str:
        """创建标准化消息"""
        return json.dumps({
            "type": msg_type,
            "timestamp": datetime.now().isoformat(),
            "room": self.name,
            **kwargs,
        }, ensure_ascii=False)
    
    async def broadcast(self, message: str, exclude: Optional[str] = None):
        """
        广播消息给所有客户端（可排除某人）
        
        ⚠️ 使用 .copy() 复制字典的值集合，防止遍历时修改报错
        """
        for client in list(self.clients.values()):
            if client.remote_addr != exclude:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    # 连接已断开，忽略
                    pass
    
    def _add_history(self, message: dict):
        """添加消息到历史记录"""
        self.history.append(message)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    async def handle_connection(self, websocket):
        """
        处理一个新的 WebSocket 连接
        
        流程：
        1. 等待用户发送注册信息
        2. 注册用户
        3. 欢迎消息 + 历史记录
        4. 进入消息循环
        5. 清理断开的连接
        """
        username = None
        
        try:
            # 等待第一条消息作为注册信息
            raw = await websocket.recv()
            reg_info = json.loads(raw)
            username = reg_info.get("username", f"匿名_{self._next_user_id()}")
            
            # 注册用户
            self.clients[username] = websocket
            user_id = self._next_user_id()
            
            print(f"[聊天室] {username} 已加入 (ID: {user_id}, 在线: {len(self.clients)})")
            
            # 发送欢迎消息（包含历史记录）
            welcome = self._make_message(
                "welcome",
                username=username,
                user_id=user_id,
                online_count=len(self.clients),
                online_users=list(self.clients.keys()),
                history=self.history[-20:],  # 最近20条历史
            )
            await websocket.send(welcome)
            
            # 通知其他人
            join_msg = self._make_message(
                "join",
                username=username,
                user_id=user_id,
                online_count=len(self.clients),
            )
            self._add_history(json.loads(join_msg))
            await self.broadcast(join_msg)
            
            # 消息循环
            async for raw_message in websocket:
                try:
                    msg_data = json.loads(raw_message)
                except json.JSONDecodeError:
                    await websocket.send(self._make_message(
                        "error", message="消息格式无效，请发送 JSON"
                    ))
                    continue
                
                msg_type = msg_data.get("type", "chat")
                
                if msg_type == "chat":
                    content = msg_data.get("content", "").strip()
                    if not content:
                        continue
                    
                    # 处理特殊命令
                    if content.startswith("/"):
                        await self._handle_command(websocket, username, content)
                        continue
                    
                    # 普通聊天消息
                    chat_msg = self._make_message(
                        "chat",
                        username=username,
                        user_id=user_id,
                        content=content,
                    )
                    self._add_history(json.loads(chat_msg))
                    await self.broadcast(chat_msg)
                
                elif msg_type == "ping":
                    await websocket.send(self._make_message("pong"))
                
                elif msg_type == "list_users":
                    await websocket.send(self._make_message(
                        "user_list",
                        users=list(self.clients.keys()),
                        count=len(self.clients),
                    ))
                
                else:
                    await websocket.send(self._make_message(
                        "error", message=f"未知消息类型: {msg_type}"
                    ))
        
        except websockets.exceptions.ConnectionClosed as e:
            print(f"[聊天室] 连接关闭: {username} (code={e.code})")
        
        finally:
            # 清理用户
            if username and username in self.clients:
                del self.clients[username]
                print(f"[聊天室] {username} 已断开 (在线: {len(self.clients)})")
                
                # 通知其他人
                if self.clients:
                    leave_msg = self._make_message(
                        "leave",
                        username=username,
                        online_count=len(self.clients),
                    )
                    self._add_history(json.loads(leave_msg))
                    await self.broadcast(leave_msg)
    
    async def _handle_command(self, websocket, username: str, command: str):
        """处理用户命令"""
        cmd = command.strip().lower()
        
        if cmd == "/help":
            help_text = (
                "可用命令:\n"
                "  /help    - 显示帮助\n"
                "  /list    - 查看在线用户\n"
                "  /time    - 当前时间\n"
                "  /clear   - 清空屏幕（客户端自己处理）\n"
                "  /quit    - 退出聊天室"
            )
            await websocket.send(self._make_message(
                "system", message=help_text
            ))
        
        elif cmd == "/list":
            users = list(self.clients.keys())
            await websocket.send(self._make_message(
                "user_list", users=users, count=len(users)
            ))
        
        elif cmd == "/time":
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await websocket.send(self._make_message(
                "system", message=f"当前服务器时间: {now}"
            ))
        
        elif cmd == "/quit":
            await websocket.send(self._make_message(
                "system", message="正在断开连接..."
            ))
            await websocket.close(1000, "用户主动退出")
        
        else:
            await websocket.send(self._make_message(
                "error", message=f"未知命令: {cmd}，输入 /help 查看帮助"
            ))
    
    async def run(self, host: str = "localhost", port: int = 8769):
        """启动聊天室服务器"""
        print(f"{'='*50}")
        print(f"  聊天室服务器: {self.name}")
        print(f"  地址: ws://{host}:{port}")
        print(f"  支持功能:")
        print(f"    - 多人实时聊天")
        print(f"    - 加入/离开通知")
        print(f"    - 消息历史记录")
        print(f"    - 用户命令 (/help)")
        print(f"{'='*50}")
        
        async with websockets.serve(
            self.handle_connection,
            host,
            port,
            ping_interval=30,
            ping_timeout=10,
            max_size=10 * 1024,
        ):
            print("[聊天室] 等待用户连接...\n")
            await asyncio.Future()


# ============================================================
# 聊天室客户端
# ============================================================

class ChatClient:
    """
    聊天室客户端
    
    功能：
    1. 连接到聊天室
    2. 发送消息
    3. 接收并显示消息
    4. 自动重连
    """
    
    def __init__(self, username: str, uri: str = "ws://localhost:8769"):
        self.username = username
        self.uri = uri
        self.running = True
    
    async def receive_messages(self, websocket):
        """接收消息的协程"""
        try:
            async for raw in websocket:
                msg = json.loads(raw)
                self._display_message(msg)
        except websockets.exceptions.ConnectionClosed:
            print("\n[客户端] 连接已断开")
    
    def _display_message(self, msg: dict):
        """格式化显示消息"""
        msg_type = msg.get("type", "")
        ts = msg.get("timestamp", "")
        # 只显示时分秒
        time_str = ts.split("T")[1][:8] if "T" in ts else ""
        
        if msg_type == "welcome":
            print(f"\n{'='*50}")
            print(f"  欢迎来到 {msg.get('room', '聊天室')}")
            print(f"  你的用户名: {msg.get('username')}")
            print(f"  当前在线: {msg.get('online_count')} 人")
            print(f"  在线用户: {', '.join(msg.get('online_users', []))}")
            if msg.get("history"):
                print(f"\n  --- 最近消息 ---")
                for h in msg["history"]:
                    if h["type"] == "chat":
                        print(f"  [{h.get('username', '?')}] {h.get('content', '')}")
                    elif h["type"] == "join":
                        print(f"  >> {h.get('username', '?')} 加入了聊天室")
                    elif h["type"] == "leave":
                        print(f"  << {h.get('username', '?')} 离开了聊天室")
                print(f"  --- 历史结束 ---")
            print(f"{'='*50}\n")
            print("输入消息开始聊天，输入 /help 查看命令\n")
        
        elif msg_type == "chat":
            username = msg.get("username", "?")
            content = msg.get("content", "")
            if username == self.username:
                print(f"[{time_str}] 我: {content}")
            else:
                print(f"[{time_str}] {username}: {content}")
        
        elif msg_type == "system":
            print(f"[系统] {msg.get('message', '')}")
        
        elif msg_type == "join":
            username = msg.get("username", "?")
            count = msg.get("online_count", "?")
            print(f"[系统] >> {username} 加入了聊天室 (在线: {count})")
        
        elif msg_type == "leave":
            username = msg.get("username", "?")
            count = msg.get("online_count", "?")
            print(f"[系统] << {username} 离开了聊天室 (在线: {count})")
        
        elif msg_type == "user_list":
            users = msg.get("users", [])
            count = msg.get("count", 0)
            print(f"[系统] 在线用户 ({count}): {', '.join(users)}")
        
        elif msg_type == "error":
            print(f"[错误] {msg.get('message', '')}")
        
        elif msg_type == "pong":
            pass  # 心跳回复，静默处理
    
    async def run(self):
        """启动客户端，带自动重连"""
        reconnect_delay = 1
        max_delay = 30
        
        while self.running:
            try:
                print(f"[客户端] 正在连接 {self.uri}...")
                
                async with websockets.connect(self.uri) as websocket:
                    # 发送注册信息
                    await websocket.send(json.dumps({
                        "username": self.username,
                    }))
                    
                    reconnect_delay = 1
                    print("[客户端] 连接成功!")
                    
                    # 启动接收消息的协程
                    recv_task = asyncio.create_task(
                        self.receive_messages(websocket)
                    )
                    
                    # 主循环：读取用户输入并发送
                    loop = asyncio.get_event_loop()
                    try:
                        while self.running:
                            message = await loop.run_in_executor(
                                None, input, ""
                            )
                            
                            if not message.strip():
                                continue
                            
                            if message.strip().lower() == "/quit":
                                await websocket.send(json.dumps({
                                    "type": "chat",
                                    "content": "/quit"
                                }))
                                await asyncio.sleep(0.5)
                                self.running = False
                                break
                            
                            # 发送聊天消息
                            await websocket.send(json.dumps({
                                "type": "chat",
                                "content": message,
                            }))
                    
                    except (KeyboardInterrupt, EOFError):
                        print("\n[客户端] 正在断开...")
                        self.running = False
                    
                    finally:
                        recv_task.cancel()
                        try:
                            await recv_task
                        except asyncio.CancelledError:
                            pass
            
            except websockets.exceptions.ConnectionClosed:
                if not self.running:
                    break
                print(f"[客户端] 连接断开，{reconnect_delay}秒后重连...")
            except ConnectionRefusedError:
                if not self.running:
                    break
                print(f"[客户端] 服务器未启动，{reconnect_delay}秒后重试...")
            except Exception as e:
                if not self.running:
                    break
                print(f"[客户端] 错误: {e}")
            
            if self.running:
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_delay)
        
        print("[客户端] 已退出")


# ============================================================
# 入口
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 03-chat-room.py server                    # 启动服务器")
        print("  python3 03-chat-room.py client [用户名]           # 启动客户端")
        print("")
        print("示例:")
        print("  终端1: python3 03-chat-room.py server")
        print("  终端2: python3 03-chat-room.py client Alice")
        print("  终端3: python3 03-chat-room.py client Bob")
        sys.exit(0)
    
    mode = sys.argv[1]
    
    if mode == "server":
        room = ChatRoom("Python 学习者聊天室")
        try:
            asyncio.run(room.run())
        except KeyboardInterrupt:
            print("\n[服务器] 已停止")
    
    elif mode == "client":
        username = sys.argv[2] if len(sys.argv) > 2 else f"访客"
        client = ChatClient(username)
        try:
            asyncio.run(client.run())
        except KeyboardInterrupt:
            print("\n[客户端] 已退出")
    
    else:
        print(f"未知模式: {mode}")


if __name__ == "__main__":
    main()
