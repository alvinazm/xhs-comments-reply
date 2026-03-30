"""异步导出任务管理器。"""

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..services.csv_storage import save_comments_to_csv, get_csv_path, csv_exists

logger = logging.getLogger("export_task")


@dataclass
class ExportTask:
    """导出任务。"""

    task_id: str
    url: str
    max_comments: int
    status: str = "pending"
    progress: int = 0
    total_fetched: int = 0
    file_path: str = ""
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    classification_status: str = "none"
    classification_progress: int = 0
    classification_summary: Optional[dict] = field(default_factory=dict)
    classified_file_path: Optional[str] = None
    classification_error: str = ""
    note_title: str = ""
    comment_count: int = 0

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "url": self.url,
            "max_comments": self.max_comments,
            "status": self.status,
            "progress": self.progress,
            "total_fetched": self.total_fetched,
            "file_path": self.file_path,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "classification_status": self.classification_status,
            "classification_progress": self.classification_progress,
            "classification_summary": self.classification_summary,
            "classified_file_path": self.classified_file_path,
            "note_title": self.note_title,
            "comment_count": self.comment_count,
        }


class ExportTaskManager:
    """导出任务管理器。"""

    def __init__(self):
        self._tasks: dict[str, ExportTask] = {}
        self._lock = threading.Lock()

    def create_task(self, url: str, max_comments: int) -> ExportTask:
        """创建新任务。"""
        task_id = str(uuid.uuid4())
        task = ExportTask(
            task_id=task_id,
            url=url,
            max_comments=max_comments,
        )
        with self._lock:
            self._tasks[task_id] = task
        logger.info(f"创建导出任务: {task_id}, url={url}, max_comments={max_comments}")
        return task

    def get_task(self, task_id: str) -> Optional[ExportTask]:
        """获取任务。"""
        with self._lock:
            return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[ExportTask]:
        """获取所有任务，按创建时间倒序。"""
        with self._lock:
            return sorted(
                self._tasks.values(), key=lambda t: t.created_at, reverse=True
            )

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        total_fetched: Optional[int] = None,
        file_path: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """更新任务状态。"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if status is not None:
                    task.status = status
                if progress is not None:
                    task.progress = progress
                if total_fetched is not None:
                    task.total_fetched = total_fetched
                if file_path is not None:
                    task.file_path = file_path
                if error_message is not None:
                    task.error_message = error_message
                task.updated_at = datetime.now()
                if status == "completed":
                    task.completed_at = datetime.now()

    def update_classification_status(
        self,
        task_id: str,
        status: str,
        progress: int = 0,
        summary: Optional[dict] = None,
        classified_file_path: Optional[str] = None,
        classification_error: Optional[str] = None,
    ) -> None:
        """更新分类状态。"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.classification_status = status
                task.classification_progress = progress
                if summary is not None:
                    task.classification_summary = summary
                if classified_file_path is not None:
                    task.classified_file_path = classified_file_path
                if classification_error is not None:
                    task.classification_error = classification_error
                task.updated_at = datetime.now()

    def execute_task(self, task_id: str) -> None:
        """执行导出任务。"""
        task = self.get_task(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return

        try:
            logger.info(f"开始执行导出任务: {task_id}")
            self.update_task(task_id, status="running", progress=0)

            from ..services import XiaohongshuService

            service = XiaohongshuService()

            self.update_task(task_id, progress=10)
            note, comments, total = service.get_comments(task.url, task.max_comments)

            self.update_task(task_id, progress=50, total_fetched=len(comments))

            session_id = save_comments_to_csv(comments)
            file_path = get_csv_path(session_id)

            self.update_task(
                task_id, status="completed", progress=100, file_path=file_path
            )
            logger.info(f"导出任务完成: {task_id}, 文件: {file_path}")

        except Exception as e:
            logger.error(f"导出任务失败: {task_id}, error={e}")
            self.update_task(task_id, status="failed", error_message=str(e))

    def start_background_export(self, task_id: str) -> None:
        """在线程中执行导出任务。"""
        thread = threading.Thread(target=self.execute_task, args=(task_id,))
        thread.daemon = True
        thread.start()


task_manager = ExportTaskManager()
