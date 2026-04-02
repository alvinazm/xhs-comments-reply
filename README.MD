## 说明

## 安装说明

- 复制.env.example 为.env 文件：在里面填入minmax的apikey

### 第一次启动
- 删除frontend/ 下 node_modules 和 package-lock.json 文件
- 输入 screen -S xhs -dm ./start.sh
- http://localhost:5000 浏览器访问

常用 screen 命令：
- screen -r xhs — 重新连接会话查看输出
- screen -r -d xhs — 强制断开其他连接并重新attach
- screen -X -S xhs quit — 停止并删除会话

## TODO
停止任务：爬取评论、智能分类
评论加载慢重试
要一个个写入到csv中
补全日志