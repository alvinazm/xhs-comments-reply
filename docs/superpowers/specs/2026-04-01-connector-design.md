# 客户端连接器设计方案

## 目标

让用户访问网页时自动连接服务器，服务器通过 WebSocket 控制用户本地的 Chrome 进行小红书爬取。

## 架构

```
┌─────────────┐         HTTP          ┌─────────────┐
│  用户浏览器 │ <───────────────────> │   服务器    │
│  (前端页面) │                        │  (Flask)    │
└─────────────┘                        └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    │                    WebSocket                   WebSocket
                    │                          │                          │
              ┌─────┴─────┐              ┌──────┴──────┐           ┌───────┴───────┐
              │ 用户1 Chrome │            │ 用户2 Chrome │  ...   │ 用户N Chrome  │
              │ (本地调试模式)│             │ (本地调试模式)│        │ (本地调试模式)│
              └────────────┘               └─────────────┘          └───────────────┘
                    │                             │                         │
              ┌─────┴─────┐              ┌───────┴───────┐          ┌───────┴───────┐
              │  Connector │              │   Connector  │          │    Connector  │
              │ (客户端程序)│              │  (客户端程序) │          │   (客户端程序) │
              └────────────┘              └───────────────┘          └───────────────┘
```

## 组件

### 1. 服务器端 (Python/Flask + WebSocket)

- **HTTP 接口**：前端页面访问
- **WebSocket 服务**：
  - 接受客户端连接，注册 Chrome 实例
  - 接收前端请求 → 转发给对应客户端的 Chrome
  - 返回爬取结果给前端

### 2. 客户端 (Go 编译的轻量程序)

- 启动时自动检测/启动本地 Chrome 调试模式
- 与服务器建立 WebSocket 长连接
- 接收服务器指令，操作本地 Chrome (CDP)
- 返回执行结果

### 3. 前端

- 检测客户端连接状态
- 未连接时显示下载客户端按钮
- 连接后正常提供爬取功能

## 实现步骤

### 阶段一：服务器 WebSocket 服务
1. 安装 `flask-socketio` 依赖
2. 创建 WebSocket 端点 `/ws`
3. 管理客户端连接池（client_id → websocket）
4. 实现请求转发逻辑

###阶段二：Go 客户端
1. 使用 `https://github.com/chromedp/chromedp` 操作 Chrome
2. 使用 `https://github.com/gorilla/websocket` WebSocket 客户端
3. 编译各平台可执行文件（Windows/macOS/Linux）

### 阶段三：前端改造
1. 添加客户端状态检测
2. 未连接时展示下载引导
3. 请求改为通过服务器转发给客户端

## 数据流

```
用户点击"获取评论" 
  → 前端发送请求到服务器 /api/get-comments 
  → 服务器根据当前客户端映射找到对应 WebSocket 
  → 通过 WebSocket 发送 CDP 指令给客户端 
  → 客户端执行 Chrome 操作获取评论 
  → 结果通过 WebSocket 返回服务器 
  → 服务器返回给前端
```

## 安全考虑

1. 客户端需要认证 token（防止非法连接）
2. 超时机制（客户端长时间无响应断开连接）
3. 并发控制（同一客户端同时只能执行一个任务）

## 文件结构

```
xhs-comments-reply/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   └── ws_manager.py      # WebSocket 连接管理
│   │   └── main.py                 # 添加 WebSocket 路由
│   └── requirements.txt            # 添加 flask-socketio
├── connector/
│   ├── main.go                     # Go 主程序
│   ├── chromedp.go                 # Chrome 操作
│   └── client.go                   # WebSocket 客户端
├── frontend/
│   └── src/views/Home.vue          # 改造前端检测客户端
└── releases/
    ├── connector-windows.exe
    ├── connector-macos
    └── connector-linux
```