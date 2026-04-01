"""WebSocket 客户端连接管理"""

import asyncio
import json
import logging
from typing import Dict
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)

clients: Dict[str, WebSocketServerProtocol] = {}


async def register_client(client_id: str, websocket: WebSocketServerProtocol):
    """注册客户端连接"""
    clients[client_id] = websocket
    logger.info(f"客户端连接: {client_id}, 当前在线: {len(clients)}")


async def unregister_client(client_id: str):
    """注销客户端连接"""
    if client_id in clients:
        del clients[client_id]
        logger.info(f"客户端断开: {client_id}, 当前在线: {len(clients)}")


async def send_to_client(client_id: str, message: dict) -> bool:
    """发送消息给指定客户端"""
    if client_id not in clients:
        logger.warning(f"客户端不存在: {client_id}")
        return False
    try:
        await clients[client_id].send(json.dumps(message))
        return True
    except Exception as e:
        logger.error(f"发送失败: {client_id}, {e}")
        await unregister_client(client_id)
        return False


async def handle_client(websocket: WebSocketServerProtocol, path: str):
    """处理客户端连接"""
    client_id = None
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "register":
                client_id = data.get("client_id", "unknown")
                await register_client(client_id, websocket)
                await websocket.send(
                    json.dumps({"type": "registered", "client_id": client_id})
                )

            elif msg_type == "response":
                logger.debug(f"收到客户端响应: {data}")

    except websockets.exceptions.ConnectionClosed:
        logger.info("客户端断开连接")
    finally:
        if client_id:
            await unregister_client(client_id)


def get_client_count() -> int:
    """获取在线客户端数量"""
    return len(clients)


def is_any_client_connected() -> bool:
    """是否有客户端在线"""
    return len(clients) > 0


async def start_ws_server(host="0.0.0.0", port=8765):
    """启动 WebSocket 服务器"""
    async with websockets.serve(handle_client, host, port):
        logger.info(f"WebSocket 服务器启动: {host}:{port}")
        await asyncio.Future()
