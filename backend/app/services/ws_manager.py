"""WebSocket 客户端连接管理"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict
import websockets
from websockets.server import WebSocketServerProtocol

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import Config

logger = logging.getLogger(__name__)

WS_SERVER_HOST = Config.WS_SERVER_HOST
WS_SERVER_PORT = Config.WS_SERVER_PORT

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


async def handle_client(websocket: WebSocketServerProtocol):
    """处理客户端连接"""
    client_id = None
    path = None
    logger.info(f"收到新的 WebSocket 连接")
    try:
        # 等待客户端发送注册消息
        try:
            first_message = await asyncio.wait_for(websocket.recv(), timeout=10)
            logger.info(f"收到第一条消息: {first_message[:100]}")
        except asyncio.TimeoutError:
            logger.warning("客户端超时未发送注册消息")
            return
        except Exception as e:
            logger.error(f"接收消息错误: {e}")
            return

        data = json.loads(first_message)
        msg_type = data.get("type")

        if msg_type == "register":
            client_id = data.get("client_id", "unknown")
            await register_client(client_id, websocket)
            await websocket.send(
                json.dumps({"type": "registered", "client_id": client_id})
            )
            logger.info(f"客户端 {client_id} 注册成功")

            # 持续监听客户端消息
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "response":
                    logger.debug(f"收到客户端响应: {data}")
                    await handle_cdp_response(data)

                elif msg_type == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))

        else:
            logger.warning(f"客户端未发送注册消息，收到: {msg_type}")

    except websockets.exceptions.ConnectionClosed:
        logger.info("客户端断开连接")
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析错误: {e}")
    except Exception as e:
        logger.error(f"处理客户端错误: {e}", exc_info=True)
    finally:
        if client_id:
            await unregister_client(client_id)


def get_client_count() -> int:
    """获取在线客户端数量"""
    return len(clients)


def is_any_client_connected() -> bool:
    """是否有客户端在线"""
    return len(clients) > 0


def get_first_client_id() -> str | None:
    """获取第一个在线客户端的 ID"""
    if clients:
        return next(iter(clients.keys()))
    return None


pending_cdp_responses: Dict[str, asyncio.Future] = {}


async def execute_cdp_command(
    client_id: str,
    command: str,
    params: dict | None = None,
    timeout: float = 60.0,
) -> dict:
    """通过 WebSocket 执行 CDP 命令并等待结果。

    Args:
        client_id: 客户端 ID
        command: CDP 命令（如 Page.navigate, Runtime.evaluate）
        params: 命令参数
        timeout: 超时时间（秒）

    Returns:
        执行结果 dict，包含 success 字段
    """
    if client_id not in clients:
        return {"success": False, "error": "客户端不在线"}

    message_id = f"{client_id}_{command}_{asyncio.get_event_loop().time()}"
    future = asyncio.Future()
    pending_cdp_responses[message_id] = future

    try:
        await clients[client_id].send(
            json.dumps(
                {
                    "type": "cdp",
                    "message_id": message_id,
                    "command": command,
                    "params": params or {},
                }
            )
        )

        result = await asyncio.wait_for(future, timeout=timeout)
        return result

    except asyncio.TimeoutError:
        logger.error(f"CDP 命令超时: {command}")
        return {"success": False, "error": f"命令执行超时: {command}"}
    except Exception as e:
        logger.error(f"CDP 命令执行失败: {e}")
        return {"success": False, "error": str(e)}
    finally:
        pending_cdp_responses.pop(message_id, None)


async def handle_cdp_response(data: dict):
    """处理客户端返回的 CDP 执行结果"""
    message_id = data.get("message_id")
    if message_id and message_id in pending_cdp_responses:
        future = pending_cdp_responses[message_id]
        if not future.done():
            future.set_result(data)


async def start_ws_server(host=WS_SERVER_HOST, port=WS_SERVER_PORT):
    """启动 WebSocket 服务器"""
    logger.info(f"正在启动 WebSocket 服务器: {host}:{port}")

    async with websockets.serve(handle_client, host, port):
        logger.info(f"WebSocket 服务器已启动: {host}:{port}")
        await asyncio.Future()
