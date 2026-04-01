#!/bin/bash

# 本地测试用 localhost，生产环境用实际服务器IP
WS_URL="ws://localhost:8765"
CLIENT_ID=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)
CHROME_PORT=9292

echo "正在启动小红书连接器..."

check_chrome() {
    curl -s "http://localhost:$CHROME_PORT/json/version" >/dev/null 2>&1
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
import subprocess
import requests
from websockets import connect

WS_URL = "$WS_URL"
CLIENT_ID = "$CLIENT_ID"
CHROME_PORT = $CHROME_PORT

async def execute_cdp_command(cmd: str, params: dict):
    """通过 HTTP API 执行 CDP 命令"""
    try:
        if cmd == "Page.navigate":
            url = params.get("url")
            resp = requests.post(f"http://localhost:{CHROME_PORT}/json/navigate", json={"url": url})
            return {"type": "response", "command": cmd, "success": resp.status_code == 200, "result": resp.json()}
        elif cmd == "Runtime.evaluate":
            expression = params.get("expression", "")
            resp = requests.post(f"http://localhost:{CHROME_PORT}/json/evaluate", json={"expression": expression})
            return {"type": "response", "command": cmd, "success": resp.status_code == 200, "result": resp.json()}
        elif cmd == "Page.reload":
            resp = requests.post(f"http://localhost:{CHROME_PORT}/json/reload", json={})
            return {"type": "response", "command": cmd, "success": resp.status_code == 200}
        else:
            return {"type": "response", "command": cmd, "success": False, "error": f"Unknown command: {cmd}"}
    except Exception as e:
        return {"type": "response", "command": cmd, "success": False, "error": str(e)}

async def main():
    uri = f"{WS_URL}?client_id={CLIENT_ID}"
    print(f"连接服务器: {WS_URL}")
    
    async with connect(uri) as websocket:
        await websocket.send(json.dumps({"type": "register", "client_id": CLIENT_ID}))
        print("已注册，等待指令...")
        
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "cdp":
                cmd = data.get("command")
                params = data.get("params", {})
                print(f"执行: {cmd}")
                
                result = await execute_cdp_command(cmd, params)
                await websocket.send(json.dumps(result))
                
            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

if __name__ == "__main__":
    asyncio.run(main())
EOF