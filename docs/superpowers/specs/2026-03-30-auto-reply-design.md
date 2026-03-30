# 自动回复功能设计

## 目标
用户编辑AI生成的回复建议后，上传CSV文件，系统自动批量发送回复。

## 流程

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 获取评论 | 获取5条展示 |
| 2 | 导出CSV | 获取max_comments条 → 自动AI分类 → 生成带generated_reply的CSV |
| 3 | 用户下载 | 下载CSV，修改generated_reply列（留空=不发，有内容=要发送） |
| 4 | 上传CSV | 上传修改后的CSV |
| 5 | 确认发送 | 显示要回复的数量，用户确认 |
| 6 | 自动回复 | 按顺序发送，显示进度 |

## CSV格式

| 字段 | 说明 |
|------|------|
| user_nickname | 评论用户 |
| content | 评论内容 |
| classification | 分类结果 |
| confidence | 置信度 |
| generated_reply | **用户编辑的回复内容，空=不发 |

## 发送机制

- 发送间隔：随机 3-8 秒
- 发送顺序：praise → question → constructive → neutral
- 失败处理：跳过继续，最后显示失败列表
- 进度推送：WebSocket

## WebSocket事件

```json
// 开始
{ "event": "reply_started", "total": 10 }

// 进度
{ "event": "reply_progress", "current": 3, "total": 10, "comment_id": "xxx" }

// 完成
{ "event": "reply_completed", "success": 8, "failed": 2, "failed_list": [...] }
```

## API设计

### POST /api/reply-from-csv
- 上传CSV文件
- 返回：{ to_reply: 10, comments: [...] }

### POST /api/reply-confirm
- 确认发送
- 返回：{ status: "running" }

### GET /api/reply-status
- 查询发送状态
- 返回：{ status, progress, failed_list }