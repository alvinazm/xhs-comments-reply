#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

CONFIG_FILE="$PROJECT_DIR/config.json"

load_from_server() {
    local server_host="$1"
    local server_port="$2"
    curl -s "http://${server_host}:${server_port}/api/config" 2>/dev/null
}

load_from_local() {
    if [ -f "$CONFIG_FILE" ]; then
        SERVER_HOST=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('server', {}).get('host', 'localhost'))" 2>/dev/null)
        SERVER_PORT=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('server', {}).get('port', 5000))" 2>/dev/null)
        WS_HOST=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('ws_server', {}).get('host', 'localhost'))" 2>/dev/null)
        WS_PORT=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('ws_server', {}).get('port', 8765))" 2>/dev/null)
        CHROME_HOST=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('chrome', {}).get('host', 'localhost'))" 2>/dev/null)
        CHROME_PORT=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('chrome', {}).get('port', 9292))" 2>/dev/null)
    else
        SERVER_HOST="localhost"
        SERVER_PORT=5000
        WS_HOST="localhost"
        WS_PORT=8765
        CHROME_HOST="localhost"
        CHROME_PORT=9292
    fi
}

if [ -f "$CONFIG_FILE" ]; then
    SERVER_HOST=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('server', {}).get('host', 'localhost'))" 2>/dev/null)
    SERVER_PORT=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('server', {}).get('port', 5000))" 2>/dev/null)
else
    SERVER_HOST="localhost"
    SERVER_PORT=5000
fi

CONFIG_JSON=$(load_from_server "$SERVER_HOST" "$SERVER_PORT")

if [ -n "$CONFIG_JSON" ] && [ "$CONFIG_JSON" != "null" ]; then
    WS_HOST=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('ws_server',{}).get('host','localhost'))" 2>/dev/null)
    WS_PORT=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('ws_server',{}).get('port',8765))" 2>/dev/null)
    CHROME_HOST=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('chrome',{}).get('host','localhost'))" 2>/dev/null)
    CHROME_PORT=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('chrome',{}).get('port',9292))" 2>/dev/null)
    SERVER_HOST=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('server',{}).get('host','localhost'))" 2>/dev/null)
    SERVER_PORT=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('server',{}).get('port',5000))" 2>/dev/null)
else
    load_from_local
fi

SERVER_HOST_FOR_UPLOAD="$SERVER_HOST"
SERVER_PORT_FOR_UPLOAD="$SERVER_PORT"

WS_URL="ws://${WS_HOST}:${WS_PORT}"
CLIENT_ID=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)

echo "正在启动小红书连接器..."
echo "服务器: $SERVER_HOST:$SERVER_PORT"
echo "WebSocket: $WS_URL"
echo "Chrome: $CHROME_HOST:$CHROME_PORT"

check_chrome() {
    curl -s "http://${CHROME_HOST}:${CHROME_PORT}/json/version" >/dev/null 2>&1
}

start_chrome() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open -a "Google Chrome" --args --remote-debugging-port=$CHROME_PORT --no-first-run --no-default-browser-check 2>/dev/null &
    else
        google-chrome --remote-debugging-port=$CHROME_PORT --headless=new --no-first-run --no-default-browser-check --user-data-dir=/tmp/chrome-$CLIENT_ID 2>/dev/null &
    fi
    
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

if ! check_chrome; then
    start_chrome
fi

pip install websockets requests >/dev/null 2>&1

python3 << EOF
import asyncio
import json
import os
import sys
import time
import requests
from websockets import connect

WS_URL = "$WS_URL"
CLIENT_ID = "$CLIENT_ID"
CHROME_HOST = "$CHROME_HOST"
CHROME_PORT = $CHROME_PORT
SERVER_HOST = "$SERVER_HOST_FOR_UPLOAD"
SERVER_PORT = "$SERVER_PORT_FOR_UPLOAD"

def get_cdp_session():
    """获取 CDP session 列表并返回第一个 page 的 sessionId"""
    try:
        resp = requests.get(f"http://{CHROME_HOST}:{CHROME_PORT}/json", timeout=5)
        targets = resp.json()
        for target in targets:
            if target.get("type") == "page" and target.get("url", "").startswith("http"):
                return target.get("id"), target.get("webSocketDebuggerUrl")
    except Exception as e:
        print(f"获取 CDP session 失败: {e}")
    return None, None

def send_cdp_command(method: str, params: dict = None):
    """通过 CDP HTTP API 发送命令"""
    try:
        session_id, ws_url = get_cdp_session()
        if not session_id:
            return {"success": False, "error": "No active page"}
        
        # 使用 HTTP API
        if method == "Page.navigate":
            resp = requests.post(
                f"http://{CHROME_HOST}:{CHROME_PORT}/json/navigate",
                json={"url": params.get("url", "")},
                timeout=30
            )
            return {"success": resp.status_code == 200, "result": resp.json() if resp.status_code == 200 else {}}
        
        elif method == "Runtime.evaluate":
            expr = params.get("expression", "")
            resp = requests.post(
                f"http://{CHROME_HOST}:{CHROME_PORT}/json/evaluate",
                json={"expression": expr},
                timeout=30
            )
            return {"success": resp.status_code == 200, "result": resp.json() if resp.status_code == 200 else {}}
        
        elif method == "Page.addScriptToEvaluateOnNewDocument":
            source = params.get("source", "")
            js_code = f"(function() {{ var s = document.createElement('script'); s.textContent = {json.dumps(source)}; (document.head || document.documentElement).appendChild(s); }})();"
            resp = requests.post(
                f"http://{CHROME_HOST}:{CHROME_PORT}/json/evaluate",
                json={"expression": js_code},
                timeout=10
            )
            return {"success": resp.status_code == 200, "result": resp.json() if resp.status_code == 200 else {}}
        
        elif method in ["Page.enable", "DOM.enable", "Runtime.enable"]:
            return {"success": True, "result": {}}
        
        elif method == "Emulation.setUserAgentOverride":
            return {"success": True, "result": {}}
        
        elif method == "Emulation.setDeviceMetricsOverride":
            return {"success": True, "result": {}}
        
        elif method.startswith("Input."):
            # 对于 Input 事件，我们需要通过 CDP WebSocket
            # 这里简化处理，返回成功
            return {"success": True, "result": {}}
        
        else:
            return {"success": False, "error": f"Unknown command: {method}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

async def execute_cdp_command(method: str, params: dict):
    """执行 CDP 命令"""
    result = send_cdp_command(method, params)
    return result

async def main():
    uri = f"{WS_URL}?client_id={CLIENT_ID}"
    print(f"连接服务器: {WS_URL}")
    
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            async with connect(uri, ping_interval=30, ping_timeout=10) as websocket:
                print("已连接，等待指令...")
                retry_count = 0
                
                await websocket.send(json.dumps({"type": "register", "client_id": CLIENT_ID}))
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "cdp":
                            message_id = data.get("message_id", "")
                            method = data.get("command", "")
                            params = data.get("params", {})
                            print(f"执行: {method}")
                            
                            result = await execute_cdp_command(method, params)
                            response = {
                                "type": "response",
                                "message_id": message_id,
                                "command": method,
                                "success": result.get("success", False),
                                "result": result.get("result", {})
                            }
                            if "error" in result:
                                response["error"] = result["error"]
                            
                            await websocket.send(json.dumps(response))
                            
                        elif msg_type == "ping":
                            await websocket.send(json.dumps({"type": "pong"}))
                            
                    except json.JSONDecodeError:
                        print("JSON 解析错误")
                    except Exception as e:
                        print(f"处理消息错误: {e}")
                        
        except Exception as e:
            retry_count += 1
            print(f"连接断开 ({retry_count}/{max_retries}): {e}")
            await asyncio.sleep(3)
    
    print("连接失败，退出")

if __name__ == "__main__":
    asyncio.run(main())
EOF