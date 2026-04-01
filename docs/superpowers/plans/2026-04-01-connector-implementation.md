# WebSocket 客户端连接器实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用户运行一行命令后自动连接服务器 WebSocket，服务器通过 CDP 控制用户本地 Chrome 爬取小红书

**Architecture:** 服务器维护 WebSocket 连接池，前端请求通过服务器转发给对应客户端执行 CDP 操作

**Tech Stack:** Python websockets 库 + Go chromedp + CDP 协议

---

### 任务一：服务器 WebSocket 服务

**Files:**
- Create: `backend/app/services/ws_manager.py`
- Modify: `backend/app/main.py`
- Modify: `requirements.txt`

- [ ] **Step 1: 添加依赖**

修改 `requirements.txt` 添加：
```python
websockets>=12.0
aiohttp>=3.9.0
```

- [ ] **Step 2: 创建 WebSocket 管理器**

创建 `backend/app/services/ws_manager.py`:
```python
"""WebSocket 客户端连接管理"""
import asyncio
import json
import logging
from typing import Dict
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)

# 客户端连接池: client_id -> websocket
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
            msg_type = data.get('type')
            
            if msg_type == 'register':
                client_id = data.get('client_id', 'unknown')
                await register_client(client_id, websocket)
                await websocket.send(json.dumps({'type': 'registered', 'client_id': client_id}))
                
            elif msg_type == 'response':
                # 客户端返回的执行结果，暂存或转发
                logger.debug(f"收到客户端响应: {data}")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info("客户端断开连接")
    finally:
        if client_id:
            await unregister_client(client_id)

async def start_ws_server(host='0.0.0.0', port=8765):
    """启动 WebSocket 服务器"""
    async with websockets.serve(handle_client, host, port):
        logger.info(f"WebSocket 服务器启动: {host}:{port}")
        await asyncio.Future()  # 永久运行
```

- [ ] **Step 3: 修改 main.py 集成 WebSocket 服务**

在 `backend/app/main.py` 末尾添加（注意需要用 asyncio 运行）：
```python
# 添加 WebSocket 服务器启动
import threading
def run_ws():
    asyncio.run(start_ws_server())

ws_thread = threading.Thread(target=run_ws, daemon=True)
ws_thread.start()
```

- [ ] **Step 4: 测试 WebSocket 服务**

启动后端，测试连接：
```bash
python -c "import asyncio, websockets, json; asyncio.run(websockets.connect('ws://localhost:8765')).send(json.dumps({'type': 'register', 'client_id': 'test1'}))"
```

---

### 任务二：创建客户端启动脚本

**Files:**
- Create: `connector/connector.sh` (Linux/Mac)
- Create: `connector/connector.ps1` (Windows)

- [ ] **Step 1: 创建 Linux/Mac 启动脚本**

创建 `connector/connector.sh`:
```bash
#!/bin/bash

# 配置
WS_URL="ws://47.94.111.53:8765"
CLIENT_ID=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)
CHROME_PORT=9292

echo "正在启动小红书连接器..."

# 检查 Chrome 是否已运行调试模式
check_chrome() {
    curl -s "http://localhost:$CHROME_PORT/json/version" >/dev/null 2>&1
}

# 启动 Chrome 调试模式
start_chrome() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open -a "Google Chrome" --args --remote-debugging-port=$CHROME_PORT --no-first-run --no-default-browser-check 2>/dev/null &
    else
        google-chrome --remote-debugging-port=$CHROME_PORT --headless=new --no-first-run --no-default-browser-check --user-data-dir=/tmp/chrome-$CLIENT_ID 2>/dev/null &
    fi
    
    # 等待 Chrome 启动
    for i in {1..15}; do
        if check_chrome; then
            echo "Chrome 调试模式已启动 (port=$CHROME_PORT)"
            return 0
        fi
        sleep 1
    done
    echo "Chrome 启动超时"
    return 1
}

# 检查并启动 Chrome
if ! check_chrome; then
    start_chrome
fi

# 使用 Python WebSocket 客户端连接服务器
pip install websockets >/dev/null 2>&1

python3 << EOF
import asyncio
import json
import os
import subprocess
from websockets import connect

WS_URL = "$WS_URL"
CLIENT_ID = "$CLIENT_ID"
CHROME_PORT = $CHROME_PORT

async def main():
    uri = f"{WS_URL}?client_id={CLIENT_ID}"
    print(f"连接服务器: {WS_URL}")
    
    async with connect(uri) as websocket:
        # 发送注册消息
        await websocket.send(json.dumps({"type": "register", "client_id": CLIENT_ID}))
        print("已注册，等待指令...")
        
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "cdp":
                # 执行 CDP 命令
                cmd = data.get("command")
                params = data.get("params", {})
                # 这里简化处理，实际需要用 CDP 库
                print(f"执行: {cmd}")
                
                result = {"type": "response", "command": cmd, "success": True}
                await websocket.send(json.dumps(result))
                
            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

if __name__ == "__main__":
    asyncio.run(main())
EOF
```

- [ ] **Step 2: 创建 Windows 启动脚本**

创建 `connector/connector.ps1`:
```powershell
# 配置
$WS_URL = "ws://47.94.111.53:8765"
$CLIENT_ID = [guid]::NewGuid().ToString()
$CHROME_PORT = 9292

Write-Host "正在启动小红书连接器..."

# 检查 Chrome
function Test-ChromeRunning {
    try {
        $null = Invoke-RestMethod "http://localhost:$CHROME_PORT/json/version" -TimeoutSec 2
        return $true
    } catch {
        return $false
    }
}

# 启动 Chrome
if (-not (Test-ChromeRunning)) {
    $chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
    if (Test-Path $chromePath) {
        Start-Process $chromePath -ArgumentList "--remote-debugging-port=$CHROME_PORT","--no-first-run" -WindowStyle Hidden
        Start-Sleep 3
        Write-Host "Chrome 调试模式已启动"
    }
}

# 安装依赖并运行
pip install websockets > $null 2>&1

python -Command @"
import asyncio
import json
from websockets import connect

async def main():
    uri = '$WS_URL?client_id=$CLIENT_ID'
    async with connect(uri) as ws:
        await ws.send(json.dumps({'type': 'register', 'client_id': '$CLIENT_ID'}))
        print('已连接服务器')
        async for msg in ws:
            print(f'收到: {msg}')

asyncio.run(main())
"@
```

- [ ] **Step 3: 测试客户端脚本**

在本地运行脚本，验证连接成功

---

### 任务三：实现 CDP 命令执行

**Files:**
- Modify: `backend/app/services/ws_manager.py`
- Create: `backend/app/services/cdp_client.py`

- [ ] **Step 1: 创建 CDP 客户端封装**

创建 `backend/app/services/cdp_client.py`:
```python
"""CDP 命令客户端封装"""
import asyncio
import json
import aiohttp
from typing import Optional, Dict, Any

class CDPClient:
    def __init__(self, host: str = "localhost", port: int = 9292):
        self.host = host
        self.port = port
        self._ws = None
    
    async def connect(self):
        """连接 CDP WebSocket"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{self.host}:{self.port}/json/version") as resp:
                data = await resp.json()
                ws_url = data["webSocketDebuggerUrl"]
            async with session.ws_connect(ws_url) as ws:
                self._ws = ws
                return True
    
    async def send(self, method: str, params: dict = None) -> Dict[str, Any]:
        """发送 CDP 命令"""
        if not self._ws:
            await self.connect()
        
        msg = {"id": 1, "method": method, "params": params or {}}
        await self._ws.send_json(msg)
        
        async for msg in self._ws:
            data = json.loads(msg)
            if "id" in data and data["id"] == 1:
                return data.get("result", {})
    
    async def navigate(self, url: str):
        """导航到 URL"""
        return await self.send("Page.navigate", {"url": url})
    
    async def evaluate(self, script: str):
        """执行 JavaScript"""
        return await self.send("Runtime.evaluate", {"expression": script})
```

- [ ] **Step 2: 集成 CDP 到 WebSocket 管理器**

在 `ws_manager.py` 添加：
```python
from .cdp_client import CDPClient

async def execute_cdp_command(client_id: str, method: str, params: dict = None) -> dict:
    """通过客户端执行 CDP 命令"""
    if client_id not in clients:
        return {"success": False, "error": "客户端不在线"}
    
    # 发送 CDP 指令给客户端
    await send_to_client(client_id, {
        "type": "cdp",
        "command": method,
        "params": params
    })
    
    # 等待响应（简化版，实际需要超时机制）
    return {"success": True, "message": "指令已发送"}
```

---

### 任务四：前端改造

**Files:**
- Modify: `frontend/src/views/Home.vue`

- [ ] **Step 1: 添加客户端连接状态检测**

在 Home.vue 添加：
```javascript
const clientConnected = ref(false)

// 检测客户端连接
const checkClientStatus = async () => {
  try {
    const res = await fetch('/api/client-status')
    const json = await res.json()
    clientConnected.value = json.connected
  } catch {
    clientConnected.value = false
  }
}
```

- [ ] **Step 2: 未连接时显示脚本**

在模板中添加：
```html
<div v-if="!clientConnected" class="bg-yellow-50 border border-yellow-200 p-4 rounded-lg mb-4">
  <p class="text-yellow-800 mb-2">请先运行连接脚本：</p>
  <div class="bg-gray-800 text-green-400 p-3 rounded font-mono text-sm">
    curl -s 47.94.111.53:3000/static/connector.sh | bash
  </div>
</div>
```

- [ ] **Step 3: 添加静态文件路由**

在 `backend/app/main.py` 添加：
```python
from flask import send_from_directory

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('../connector', filename)
```

---

### 任务五：创建 API 端点

**Files:**
- Modify: `backend/app/api/routes.py`
- Create: `backend/app/services/task_queue.py`

- [ ] **Step 1: 创建任务队列**

创建 `backend/app/services/task_queue.py`:
```python
"""任务队列管理"""
import asyncio
import uuid
from typing import Dict, Optional
from .ws_manager import execute_cdp_command, clients

tasks: Dict[str, dict] = {}

async def submit_task(client_id: str, task_type: str, data: dict) -> str:
    """提交任务到队列"""
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "type": task_type,
        "data": data,
        "status": "pending",
        "client_id": client_id
    }
    
    # 发送给客户端执行
    await execute_cdp_command(client_id, task_type, data)
    
    return task_id
```

- [ ] **Step 2: 添加 API 路由**

在 `routes.py` 添加：
```python
@bp.route('/get-comments', methods=['POST'])
def get_comments():
    """获取评论（通过客户端 Chrome）"""
    data = request.json
    url = data.get('url')
    max_comments = data.get('max_comments', 20)
    
    # 获取在线客户端
    if not clients:
        return jsonify({"success": False, "error": "无客户端在线"})
    
    # 选择一个客户端执行
    client_id = list(clients.keys())[0]
    
    # 提交任务
    task_id = asyncio.run(submit_task(client_id, "get_comments", {
        "url": url,
        "max_comments": max_comments
    }))
    
    return jsonify({"success": True, "task_id": task_id})
```

---

### 任务六：整体测试

- [ ] **Step 1: 启动后端服务**

```bash
cd backend && python app/main.py
```

- [ ] **Step 2: 用户运行连接脚本**

```bash
curl -s 47.94.111.53:3000/static/connector.sh | bash
```

- [ ] **Step 3: 前端测试获取评论**

访问 http://47.94.111.53:3000/ 测试完整流程

- [ ] **Step 4: 提交代码**

```bash
git add -A
git commit -m "feat: 添加 WebSocket 客户端连接器支持"
git push
```

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2026-04-01-connector-implementation.md`. Two execution options:**

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**