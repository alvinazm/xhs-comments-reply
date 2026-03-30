import random
import threading
import time


class ReplySender:
    """自动回复发送器"""

    def __init__(self, xhs_service):
        self.xhs_service = xhs_service
        self.running = False
        self.comments = []
        self.sended_cnt = 0
        self.failed = []
        self.current = 0
        self.total = 0
        self.target_url = ""
        self._callbacks: list = []

    def register_callback(self, cb):
        self._callbacks.append(cb)

    def _emit(self, event: str, data: dict):
        for cb in self._callbacks:
            cb(event, data)

    def start(self, comments: list, url: str):
        """启动自动回复"""
        self.running = True
        self.comments = comments
        self.sended_cnt = 0
        self.failed = []
        self.current = 0
        self.total = len(comments)
        self.target_url = url

        order = {"praise": 0, "question": 1, "constructive": 2, "neutral": 3}
        comments = sorted(
            comments, key=lambda x: order.get(x.get("classification", ""), 99)
        )

        self._emit("reply_started", {"total": self.total})

        threading.Thread(target=self._send_loop, daemon=True).start()

    def _send_loop(self):
        try:
            success, failed = self.xhs_service.reply_comments_batch(
                self.target_url,
                self.comments,
            )
            self.sended_cnt = success
            self.failed = failed

            for i, c in enumerate(self.comments):
                self.current = i + 1
                self._emit(
                    "reply_progress",
                    {
                        "current": self.current,
                        "total": self.total,
                        "comment_id": c.get("comment_id", ""),
                        "user_nickname": c.get("user_nickname", ""),
                    },
                )
                if i < len(self.comments) - 1:
                    time.sleep(random.uniform(3, 8))
        except Exception as e:
            for c in self.comments:
                c["error"] = str(e)
                self.failed.append(c)

        self.running = False
        self._emit(
            "reply_completed",
            {
                "success": self.sended_cnt,
                "failed": len(self.failed),
                "failed_list": self.failed,
            },
        )

    def stop(self):
        self.running = False

    def get_status(self):
        return {
            "running": self.running,
            "current": self.current,
            "total": self.total,
            "sended": self.sended_cnt,
            "failed": self.failed,
        }
