# 客户端-服务器架构改造设计

## 背景

当前项目采用"服务器直接爬取"模式，需要在服务器上安装 Chrome。用户的真实需求是：
- 服务器只运行 Flask API
- 用户本地 Chrome 爬取数据，通过 WebSocket 与服务器通信

## 架构

```
┌─────────────┐     WebSocket (8765)      ┌─────────────┐
│  用户本地   │ ←─────────────────────────→│   服务器    │
│             │                            │             │
│  Chrome     │   CDP 命令                 │  Flask API  │
│  + 脚本     │   数据回传 (HTTP POST)     │  (5000)     │
│             │                            │             │
└─────────────┘                            │  保存CSV   │
                                           │  download/ │
                                           └─────────────┘
```

## 流程

1. **连接阶段**
   - 用户手动运行 `connector.sh`
   - 脚本自动启动本地 Chrome（调试模式）
   - 脚本通过 WebSocket 连接到服务器 (8765)
   - 发送注册消息，服务器记录客户端在线

2. **获取评论流程**
   - 用户访问页面，输入小红书链接
   - 前端调用 `/api/check-chrome` 检测连接状态
   - 未连接时提示运行 connector.sh
   - 用户点击"获取评论"
   - 服务器通过 WebSocket 下发 CDP 任务
   - 客户端执行爬取，数据通过 HTTP POST 回传
   - 服务器保存 CSV，返回结果

## 改动点

### 1. WebSocket 任务分发 (ws_manager.py)
- 新增 `execute_cdp_command()` 函数
- 通过 WebSocket 发送 CDP 命令给客户端
- 等待客户端返回执行结果（带超时）

### 2. 客户端 connector.sh
- 接收 CDP 命令并执行
- 爬取完成后通过 HTTP POST 上传数据到 `/api/upload-comments`

### 3. 后端路由 (routes.py)
- 新增 `/api/upload-comments` 接口接收数据
- 修改 `/api/get-comments` 通过 WebSocket 调度任务

### 4. 前端 Home.vue
- 连接检测逻辑保持不变
- 获取评论改为同步等待模式

## 超时与重试

- WebSocket 命令超时：60 秒
- 超时后返回错误，提示用户重试
- 客户端需保持网络稳定

## 文件改动

- `backend/app/services/ws_manager.py` - 任务分发
- `connector/connector.sh` - 执行爬虫 + 数据回传
- `backend/app/api/routes.py` - 新增数据接收接口
- `frontend/src/views/Home.vue` - 同步等待逻辑