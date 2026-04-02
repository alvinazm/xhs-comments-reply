#!/bin/bash
echo "=== 安装依赖 ==="

pip install -r requirements.txt

echo "=== 小红书评论获取系统启动 ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

if [ -f "$PROJECT_DIR/config.json" ]; then
    CHROME_PORT=$(python3 -c "import json; print(json.load(open('$PROJECT_DIR/config.json'))['chrome']['port'])" 2>/dev/null || echo 9222)
    BACKEND_PORT=$(python3 -c "import json; print(json.load(open('$PROJECT_DIR/config.json'))['backend']['port'])" 2>/dev/null || echo 5000)
    FRONTEND_PORT=$(python3 -c "import json; print(json.load(open('$PROJECT_DIR/config.json'))['frontend']['port'])" 2>/dev/null || echo 3000)
else
    CHROME_PORT=9222
    BACKEND_PORT=5000
    FRONTEND_PORT=3000
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup_ports() {
    echo -e "${YELLOW}清理占用端口...${NC}"
    
    for port in $FRONTEND_PORT $BACKEND_PORT $CHROME_PORT 8765 5000; do
        pid=$(lsof -t -i :$port 2>/dev/null || true)
        if [ -n "$pid" ]; then
            echo "  释放端口 $port (PID: $pid)"
            kill -9 $pid 2>/dev/null || true
        fi
    done
    
    pkill -9 -f "chrome-debug" 2>/dev/null || true
    pkill -9 -f "app.main" 2>/dev/null || true
    
    sleep 2
}

start_backend() {
    echo -e "${YELLOW}启动后端服务...${NC}"
    cd "$PROJECT_DIR/backend"
    
    if ! pip show flask > /dev/null 2>&1; then
        echo -e "${YELLOW}安装后端依赖...${NC}"
        pip install -r "$PROJECT_DIR/requirements.txt"
    fi
    
    mkdir -p "$PROJECT_DIR/logs"
    nohup python3 -m app.main >> "$PROJECT_DIR/logs/server_$(date +%Y-%m-%d).log" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/xhs_backend.pid
    echo -e "${GREEN}后端已启动 (PID: $BACKEND_PID, port=$BACKEND_PORT)${NC}"
    
    sleep 5
}

start_frontend() {
    echo -e "${YELLOW}启动前端服务...${NC}"
    cd "$PROJECT_DIR/frontend"
    
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}安装前端依赖...${NC}"
        npm install
    fi
    
    npm run dev >> /tmp/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > /tmp/xhs_frontend.pid
    echo -e "${GREEN}前端已启动 (PID: $FRONTEND_PID, port=$FRONTEND_PORT)${NC}"
    
    sleep 3
}

stop() {
    echo -e "${YELLOW}停止服务...${NC}"
    
    if [ -f /tmp/xhs_backend.pid ]; then
        kill $(cat /tmp/xhs_backend.pid) 2>/dev/null || true
        rm -f /tmp/xhs_backend.pid
        echo "后端已停止"
    fi
    
    if [ -f /tmp/xhs_frontend.pid ]; then
        kill $(cat /tmp/xhs_frontend.pid) 2>/dev/null || true
        rm -f /tmp/xhs_frontend.pid
        echo "前端已停止"
    fi
    
    cleanup_ports
}

case "${1:-start}" in
    start)
        cleanup_ports
        start_backend
        start_frontend
        echo ""
        echo -e "${GREEN}=== 所有服务已启动 ==="
        echo -e "后端: http://0.0.0.0:$BACKEND_PORT"
        echo -e "前端: http://0.0.0.0:$FRONTEND_PORT"
        echo -e "Chrome: port=$CHROME_PORT"
        echo -e "按 Ctrl+C 停止所有服务${NC}"
        echo ""
        
        trap "stop; exit 0" INT TERM
        while true; do
            sleep 1
        done
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start_backend
        start_frontend
        echo ""
        echo -e "${GREEN}=== 所有服务已启动 ==="
        echo -e "后端: http://0.0.0.0:$BACKEND_PORT"
        echo -e "前端: http://0.0.0.0:$FRONTEND_PORT"
        echo -e "按 Ctrl+C 停止所有服务${NC}"
        echo ""
        trap "stop; exit 0" INT TERM
        while true; do sleep 1; done
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    *)
        echo "用法: $0 {start|stop|restart|backend|frontend|chrome}"
        exit 1
        ;;
esac