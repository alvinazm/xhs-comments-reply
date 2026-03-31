"""CSV 存储服务。"""

import csv
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import List

DOWNLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "download",
)

CSV_HEADERS = [
    "评论人用户名",
    "评论人ID",
    "评论内容",
    "评论ID",
    "评论时间",
    "所在地址",
    "点赞量",
]


def save_comments_to_csv(comments: List) -> str:
    """保存评论到 CSV 文件，返回 session_id。"""
    session_id = str(uuid.uuid4())
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    file_path = os.path.join(DOWNLOAD_DIR, f"xhs_comments_{session_id}.csv")

    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)

        for c in comments:
            if not c.content or not c.content.strip():
                continue
            writer.writerow(
                [
                    c.user_nickname,
                    c.user_id,
                    c.content,
                    c.id,
                    time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(int(c.create_time))
                    )
                    if c.create_time
                    else "",
                    c.ip_location,
                    c.like_count,
                ]
            )

    return session_id


def get_csv_path(session_id: str) -> str:
    """获取指定 session_id 对应的 CSV 文件路径。"""
    return os.path.join(DOWNLOAD_DIR, f"xhs_comments_{session_id}.csv")


def csv_exists(session_id: str) -> bool:
    """检查 CSV 文件是否存在。"""
    return os.path.exists(get_csv_path(session_id))


def cleanup_old_csvs(days: int = 20) -> int:
    """删除超过指定天数的 CSV 文件，返回删除的文件数量。"""
    if not os.path.exists(DOWNLOAD_DIR):
        return 0

    cutoff_timestamp = (datetime.now() - timedelta(days=days)).timestamp()
    deleted_count = 0

    for filename in os.listdir(DOWNLOAD_DIR):
        if filename.startswith("xhs_comments_") and filename.endswith(".csv"):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.getmtime(file_path) < cutoff_timestamp:
                os.remove(file_path)
                deleted_count += 1

    return deleted_count
