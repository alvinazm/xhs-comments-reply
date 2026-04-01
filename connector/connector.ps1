# 本地测试用 localhost，生产环境用实际服务器IP
$WS_URL = "ws://localhost:8765"
$CLIENT_ID = [guid]::NewGuid().ToString()
$CHROME_PORT = 9292

Write-Host "正在启动小红书连接器..."

function Test-ChromeRunning {
    try {
        $null = Invoke-RestMethod "http://localhost:$CHROME_PORT/json/version" -TimeoutSec 2
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-ChromeRunning)) {
    $chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
    if (Test-Path $chromePath) {
        Start-Process $chromePath -ArgumentList "--remote-debugging-port=$CHROME_PORT","--no-first-run" -WindowStyle Hidden
        Start-Sleep 3
        Write-Host "Chrome 调试模式已启动"
    }
}

pip install websockets requests > $null 2>&1

function Execute-CDPCommand {
    param([string]$cmd, [hashtable]$params, [int]$port)
    
    try {
        if ($cmd -eq 'Page.navigate') {
            $url = $params.url
            $resp = Invoke-RestMethod "http://localhost:$port/json/navigate" -Method Post -Body ($url | ConvertTo-Json) -ContentType 'application/json'
            return @{'type'='response'; 'command'=$cmd; 'success'=$true; 'result'=$resp}
        } elseif ($cmd -eq 'Runtime.evaluate') {
            $expression = $params.expression
            $resp = Invoke-RestMethod "http://localhost:$port/json/evaluate" -Method Post -Body ($expression | ConvertTo-Json) -ContentType 'application/json'
            return @{'type'='response'; 'command'=$cmd; 'success'=$true; 'result'=$resp}
        } elseif ($cmd -eq 'Page.reload') {
            $null = Invoke-RestMethod "http://localhost:$port/json/reload" -Method Post -Body '{}' -ContentType 'application/json'
            return @{'type'='response'; 'command'=$cmd; 'success'=$true}
        } else {
            return @{'type'='response'; 'command'=$cmd; 'success'=$false; 'error'="Unknown command: $cmd"}
        }
    } catch {
        return @{'type'='response'; 'command'=$cmd; 'success'=$false; 'error'=$_.Exception.Message}
    }
}

python -Command @"
import asyncio
import json
import requests
from websockets import connect

CHROME_PORT = $CHROME_PORT
WS_URL = '$WS_URL'
CLIENT_ID = '$CLIENT_ID'

async def main():
    uri = f'{WS_URL}?client_id={CLIENT_ID}'
    async with connect(uri) as ws:
        await ws.send(json.dumps({'type': 'register', 'client_id': CLIENT_ID}))
        print('已注册，等待指令...')
        async for msg in ws:
            data = json.loads(msg)
            msg_type = data.get('type')
            
            if msg_type == 'cdp':
                cmd = data.get('command')
                params = data.get('params', {})
                print(f'执行: {cmd}')
                result = {'type': 'response', 'command': cmd, 'success': True}
                
                try:
                    if cmd == 'Page.navigate':
                        url = params.get('url')
                        resp = requests.post(f'http://localhost:{CHROME_PORT}/json/navigate', json={'url': url})
                        result = {'type': 'response', 'command': cmd, 'success': resp.status_code == 200, 'result': resp.json()}
                    elif cmd == 'Runtime.evaluate':
                        expression = params.get('expression', '')
                        resp = requests.post(f'http://localhost:{CHROME_PORT}/json/evaluate', json={'expression': expression})
                        result = {'type': 'response', 'command': cmd, 'success': resp.status_code == 200, 'result': resp.json()}
                    elif cmd == 'Page.reload':
                        resp = requests.post(f'http://localhost:{CHROME_PORT}/json/reload', json={})
                        result = {'type': 'response', 'command': cmd, 'success': resp.status_code == 200}
                except Exception as e:
                    result = {'type': 'response', 'command': cmd, 'success': False, 'error': str(e)}
                
                await ws.send(json.dumps(result))
            elif msg_type == 'ping':
                await ws.send(json.dumps({'type': 'pong'}))

asyncio.run(main())
"@