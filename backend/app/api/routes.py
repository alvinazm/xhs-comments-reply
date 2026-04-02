"""API 路由。"""

import csv
import io
import logging
import sys
import os
import time
from datetime import datetime

import requests
from flask import Blueprint, jsonify, request, Response, send_file

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import Config

from ..models.schemas import ApiResponse, CommentRequest, ReplyRequest
from ..services import XiaohongshuService
from ..services.chrome_launcher import ensure_chrome, has_display
from ..services.xhs.errors import NoFeedDetailError, PageNotAccessibleError, XHSError
from ..services.csv_storage import get_csv_path, csv_exists

logger = logging.getLogger("api")

get_comments_logger = logging.getLogger("get_comments")
get_comments_handler = logging.FileHandler(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "logs",
        f"get_comments_{time.strftime('%Y-%m-%d')}.log",
    ),
    encoding="utf-8",
)
get_comments_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
get_comments_logger.addHandler(get_comments_handler)
get_comments_logger.setLevel(logging.INFO)

comment_bp = Blueprint("comment", __name__, url_prefix="/api")


@comment_bp.route("/start-chrome", methods=["POST"])
def start_chrome():
    """检查 Chrome 调试模式状态。"""
    running = ensure_chrome(host=Config.CHROME_HOST, port=Config.CHROME_PORT)
    if running:
        return jsonify(
            ApiResponse(success=True, message="Chrome 调试模式已就绪").to_dict()
        )
    return jsonify(
        ApiResponse(
            success=False,
            error=f"请手动启动 Chrome 并开启调试模式，端口: {Config.CHROME_PORT}",
        ).to_dict()
    ), 400


@comment_bp.route("/check-chrome", methods=["GET"])
def check_chrome():
    """检查 Chrome 调试模式状态。"""
    from ..services.ws_manager import is_any_client_connected

    if is_any_client_connected():
        from ..services.ws_manager import get_client_count

        return jsonify(
            ApiResponse(
                success=True,
                data={
                    "running": True,
                    "source": "client",
                    "client_count": get_client_count(),
                    "chrome_port": Config.CHROME_PORT,
                },
            ).to_dict()
        )

    try:
        resp = requests.get(
            f"http://{Config.CHROME_HOST}:{Config.CHROME_PORT}/json/version", timeout=2
        )
        running = resp.status_code == 200
        return jsonify(
            ApiResponse(
                success=True,
                data={
                    "running": running,
                    "source": "server" if running else "none",
                    "chrome_port": Config.CHROME_PORT,
                },
            ).to_dict()
        )
    except Exception:
        return jsonify(
            ApiResponse(
                success=True,
                data={
                    "running": False,
                    "source": "none",
                    "chrome_port": Config.CHROME_PORT,
                },
            ).to_dict()
        )


@comment_bp.route("/parse-url", methods=["POST"])
def parse_url():
    """解析小红书链接。"""
    data = request.get_json()
    url = data.get("url", "")

    from ..services import parse_xhs_url

    result = parse_xhs_url(url)
    if result:
        return jsonify(ApiResponse(success=True, data=result).to_dict())
    return jsonify(ApiResponse(success=False, error="无效的小红书链接").to_dict()), 400


@comment_bp.route("/get-comments", methods=["POST"])
def get_comments():
    """获取笔记评论。"""
    data = request.get_json()
    url = data.get("url", "")
    max_comments = data.get("max_comments", 20)

    start_time = time.time()
    start_datetime = time.strftime("%Y-%m-%d %H:%M:%S")
    get_comments_logger.info(
        "[开始] 时间=%s, url=%s, max_comments=%d", start_datetime, url, max_comments
    )

    from ..services.export_task_manager import task_manager

    task = task_manager.create_task(url, max_comments)
    task.status = "running"
    task.progress = 0
    task.note_title = ""
    task.comment_count = 0
    task.total_fetched = 0

    try:
        req = CommentRequest(url=url, max_comments=max_comments)
        service = XiaohongshuService()

        task.note_title = "获取中..."
        task_manager.update_task_full(task.task_id, task)

        note, comments, total = service.get_comments(req.url, req.max_comments)

        from ..services.whitelist_service import load_whitelist

        whitelist = set(load_whitelist())
        comments = [c for c in comments if c.user_id not in whitelist]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "评论人用户名",
                "评论人ID",
                "评论内容",
                "评论ID",
                "评论时间",
                "所在地址",
                "点赞量",
            ]
        )

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

        output.seek(0)

        import uuid
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent.parent
        csv_dir = project_root / "download"
        csv_dir.mkdir(exist_ok=True)

        session_id = str(uuid.uuid4())
        csv_path = csv_dir / f"xhs_comments_{session_id}.csv"
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(output.getvalue())

        if len(comments) > 0:
            task.status = "completed"
            task.progress = 100
            task.total_fetched = len(comments)
            task.file_path = str(csv_path)
            task.completed_at = datetime.now()
            task.note_title = note.title
            task.comment_count = (
                int(note.comment_count) if note.comment_count else total
            )
        else:
            if os.path.exists(csv_path):
                os.remove(csv_path)
            task.status = "failed"
            task.error_message = "未获取到评论"

        task_manager.update_task_full(task.task_id, task)

        def format_comment(c):
            d = c.to_dict()
            d["create_time_str"] = (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(c.create_time)))
                if c.create_time
                else ""
            )
            return d

        elapsed = time.time() - start_time
        end_datetime = time.strftime("%Y-%m-%d %H:%M:%S")
        get_comments_logger.info(
            "[完成] 时间=%s, 耗时=%.2f秒, url=%s, 实际获取=%d, "
            "total=%d, 笔记标题=%s, 作者=%s, IP属地=%s, 点赞=%s, 评论数=%s, CSV文件=%s",
            end_datetime,
            elapsed,
            url,
            len(comments),
            total,
            note.title,
            note.user_nickname,
            note.ip_location,
            note.liked_count,
            note.comment_count,
            csv_path.name,
        )

        return jsonify(
            ApiResponse(
                success=True,
                data={
                    "note": {
                        "note_id": note.note_id,
                        "xsec_token": note.xsec_token,
                        "title": note.title,
                        "desc": note.desc,
                        "type": note.type,
                        "ip_location": note.ip_location,
                        "user": {"nickname": note.user_nickname},
                        "interact_info": {
                            "liked_count": note.liked_count,
                            "collected_count": note.collected_count,
                            "comment_count": note.comment_count,
                            "shared_count": note.shared_count,
                        },
                    },
                    "comments": [format_comment(c) for c in comments[:5]],
                    "total_comments": total,
                },
            ).to_dict()
        )

    except ValueError as e:
        get_comments_logger.error(
            "[失败] url=%s, max_comments=%d, 错误=参数错误: %s", url, max_comments, e
        )
        logger.error("参数错误: %s", e)
        return jsonify(ApiResponse(success=False, error=str(e)).to_dict()), 400
    except PageNotAccessibleError as e:
        get_comments_logger.error(
            "[失败] url=%s, max_comments=%d, 错误=页面不可访问: %s",
            url,
            max_comments,
            e,
        )
        logger.error("页面不可访问: %s", e)
        return jsonify(ApiResponse(success=False, error=str(e)).to_dict()), 400
    except NoFeedDetailError:
        get_comments_logger.error(
            "[失败] url=%s, max_comments=%d, 错误=未获取到详情数据", url, max_comments
        )
        logger.error("未获取到详情数据")
        return jsonify(
            ApiResponse(
                success=False, error="未获取到笔记详情，请检查链接是否正确"
            ).to_dict()
        ), 400
    except XHSError as e:
        get_comments_logger.error(
            "[失败] url=%s, max_comments=%d, 错误=XHS错误: %s", url, max_comments, e
        )
        logger.error("XHS 错误: %s", e)
        return jsonify(ApiResponse(success=False, error=str(e)).to_dict()), 500
    except Exception as e:
        get_comments_logger.error(
            "[失败] url=%s, max_comments=%d, 错误=未知错误: %s", url, max_comments, e
        )
        logger.error("未知错误: %s", e)
        return jsonify(
            ApiResponse(success=False, error=f"未知错误: {e!s}").to_dict()
        ), 500


@comment_bp.route("/reply-comment", methods=["POST"])
def reply_comment():
    """回复评论。"""
    data = request.get_json()
    url = data.get("url", "")
    content = data.get("content", "")
    comment_id = data.get("comment_id", "")
    user_id = data.get("user_id", "")

    try:
        req = ReplyRequest(
            url=url,
            content=content,
            comment_id=comment_id,
            user_id=user_id,
        )

        if not req.content:
            return jsonify(
                ApiResponse(success=False, error="回复内容不能为空").to_dict()
            ), 400

        service = XiaohongshuService()
        service.reply_comment(req.url, req.content, req.comment_id, req.user_id)

        return jsonify(ApiResponse(success=True, message="回复成功").to_dict())

    except ValueError as e:
        logger.error("参数错误: %s", e)
        return jsonify(ApiResponse(success=False, error=str(e)).to_dict()), 400
    except RuntimeError as e:
        logger.error("回复失败: %s", e)
        return jsonify(ApiResponse(success=False, error=str(e)).to_dict()), 500
    except XHSError as e:
        logger.error("XHS 错误: %s", e)
        return jsonify(ApiResponse(success=False, error=str(e)).to_dict()), 500
    except Exception as e:
        logger.error("未知错误: %s", e)
        return jsonify(
            ApiResponse(success=False, error=f"未知错误: {e!s}").to_dict()
        ), 500


@comment_bp.route("/download-comments-csv", methods=["POST"])
def download_comments_csv():
    """下载评论 CSV。"""
    data = request.get_json()
    url = data.get("url", "")
    max_comments = data.get("max_comments", 99999)

    try:
        req = CommentRequest(url=url, max_comments=max_comments)
        service = XiaohongshuService()

        note, comments, total = service.get_comments(req.url, req.max_comments)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "评论人用户名",
                "评论人ID",
                "评论内容",
                "评论ID",
                "评论时间",
                "所在地址",
                "点赞量",
            ]
        )

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

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=comments_{note.note_id}.csv"
            },
        )

    except Exception as e:
        logger.error("下载 CSV 失败: %s", e)
        return jsonify(
            ApiResponse(success=False, error=f"下载 CSV 失败: {e!s}").to_dict()
        ), 500


@comment_bp.route("/download-cached-csv", methods=["POST"])
def download_cached_csv():
    """下载已缓存的评论 CSV。"""
    data = request.get_json()
    session_id = data.get("session_id", "")

    if not session_id:
        return jsonify(
            ApiResponse(success=False, error="缺少 session_id").to_dict()
        ), 400

    if not csv_exists(session_id):
        return jsonify(
            ApiResponse(success=False, error="文件已过期，请重新下载").to_dict()
        ), 404

    file_path = get_csv_path(session_id)
    filename = f"comments_{session_id[:8]}.csv"

    from flask import send_file

    return send_file(
        file_path, mimetype="text/csv", as_attachment=True, download_name=filename
    )


@comment_bp.route("/export-comments-async", methods=["POST"])
def export_comments_async():
    """异步导出评论 CSV。"""
    data = request.get_json()
    url = data.get("url", "")
    max_comments = data.get("max_comments", 99999)

    if not url:
        return jsonify(ApiResponse(success=False, error="缺少 url").to_dict()), 400

    try:
        from ..services.export_task_manager import task_manager

        task = task_manager.create_task(url, max_comments)
        task_manager.start_background_export(task.task_id)

        return jsonify(
            ApiResponse(
                success=True,
                data={
                    "task_id": task.task_id,
                    "status": task.status,
                },
            ).to_dict()
        )
    except Exception as e:
        logger.error("创建导出任务失败: %s", e)
        return jsonify(
            ApiResponse(success=False, error=f"创建导出任务失败: {e!s}").to_dict()
        ), 500


@comment_bp.route("/export-status/<task_id>", methods=["GET"])
def export_status(task_id: str):
    """获取导出任务状态。"""
    from ..services.export_task_manager import task_manager

    task = task_manager.get_task(task_id)
    if not task:
        return jsonify(ApiResponse(success=False, error="任务不存在").to_dict()), 404

    return jsonify(
        ApiResponse(
            success=True,
            data={
                "task_id": task.task_id,
                "status": task.status,
                "progress": task.progress,
                "total_fetched": task.total_fetched,
                "file_path": task.file_path,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "completed_at": task.completed_at.isoformat()
                if task.completed_at
                else None,
                "classification_status": task.classification_status or "none",
                "classification_progress": task.classification_progress,
                "classification_summary": task.classification_summary,
                "classified_file_path": task.classified_file_path,
            },
        ).to_dict()
    )


@comment_bp.route("/export-tasks", methods=["GET"])
def export_tasks():
    """获取导出任务列表。"""
    from ..services.export_task_manager import task_manager

    tasks = task_manager.get_all_tasks()
    return jsonify(
        ApiResponse(
            success=True,
            data=[task.to_dict() for task in tasks],
        ).to_dict()
    )


@comment_bp.route("/retry-task", methods=["POST"])
def retry_task():
    """重试导出任务。"""
    from ..services.export_task_manager import task_manager

    data = request.get_json()
    task_id = data.get("task_id", "")

    if not task_id:
        return jsonify(ApiResponse(success=False, error="缺少 task_id").to_dict()), 400

    task = task_manager.get_task(task_id)
    if not task:
        return jsonify(ApiResponse(success=False, error="任务不存在").to_dict()), 404

    if task.total_fetched > 0:
        return jsonify(ApiResponse(success=False, error="任务已有数据").to_dict()), 400

    try:
        task_manager.start_background_export(task.task_id)
        return jsonify(
            ApiResponse(
                success=True,
                data={
                    "task_id": task.task_id,
                    "status": task.status,
                },
            ).to_dict()
        )
    except Exception as e:
        logger.error("重试导出任务失败: %s", e)
        return jsonify(
            ApiResponse(success=False, error=f"重试失败: {e!s}").to_dict()
        ), 500


@comment_bp.route("/export-download/<task_id>", methods=["GET"])
def export_download(task_id: str):
    """下载已完成导出的 CSV 文件。"""
    from ..services.export_task_manager import task_manager

    task = task_manager.get_task(task_id)
    if not task:
        return jsonify(ApiResponse(success=False, error="任务不存在").to_dict()), 404

    if task.status != "completed":
        return jsonify(ApiResponse(success=False, error="任务尚未完成").to_dict()), 400

    if not task.file_path or not os.path.exists(task.file_path):
        return jsonify(
            ApiResponse(success=False, error="文件不存在，请重新导出").to_dict()
        ), 404

    filename = f"comments_{task.task_id[:8]}.csv"
    return send_file(
        task.file_path, mimetype="text/csv", as_attachment=True, download_name=filename
    )


@comment_bp.route("/classify/<task_id>", methods=["POST"])
def start_classify(task_id: str):
    """启动AI评论分类（异步执行）。"""
    from ..services.export_task_manager import task_manager

    task = task_manager.get_task(task_id)
    if not task:
        return jsonify(ApiResponse(success=False, error="任务不存在").to_dict()), 404

    if task.status != "completed":
        return jsonify(
            ApiResponse(success=False, error="任务未完成，无法分类").to_dict()
        ), 400

    if not os.path.exists(task.file_path):
        return jsonify(
            ApiResponse(success=False, error="评论文件不存在").to_dict()
        ), 404

    if task.classification_status == "running":
        return jsonify(
            ApiResponse(success=False, error="分类正在进行中").to_dict()
        ), 400

    data = request.get_json() or {}
    try:
        batch_size = max(1, min(int(data.get("batch_size", 20)), 100))
        workers = max(1, min(int(data.get("workers", 5)), 20))
    except (ValueError, TypeError):
        return jsonify(
            ApiResponse(
                success=False, error="batch_size 和 workers 必须为整数"
            ).to_dict()
        ), 400

    task_manager.update_classification_status(task_id, "running", 0)

    import threading
    from ..services.ai_classifier import execute_classify_task

    def run_classification():
        def progress_callback(progress):
            try:
                task_manager.update_classification_status(task_id, "running", progress)
            except Exception as e:
                logger.error("进度更新失败: %s", e)

        result = execute_classify_task(
            task_id, task.file_path, batch_size, workers, progress_callback
        )
        if result["status"] == "completed":
            task_manager.update_classification_status(
                task_id, "completed", 100, result["summary"], result["file_path"]
            )
        else:
            task_manager.update_classification_status(
                task_id,
                "failed",
                classification_error=result.get("error", "Unknown error"),
            )

    thread = threading.Thread(target=run_classification)
    thread.daemon = True
    try:
        thread.start()
    except Exception as e:
        logger.error("启动分类线程失败: %s", e)
        task_manager.update_classification_status(
            task_id, "failed", error_message=str(e)
        )
        return jsonify(
            ApiResponse(success=False, error=f"启动分类线程失败: {e}").to_dict()
        ), 500

    return jsonify(
        ApiResponse(
            success=True,
            data={"task_id": task_id, "status": "started", "message": "分类任务已启动"},
        ).to_dict()
    )


@comment_bp.route("/classification-status/<task_id>", methods=["GET"])
def get_classification_status(task_id: str):
    """获取评论分类状态。"""
    from ..services.export_task_manager import task_manager

    task = task_manager.get_task(task_id)
    if not task:
        return jsonify(ApiResponse(success=False, error="任务不存在").to_dict()), 404

    return jsonify(
        ApiResponse(
            success=True,
            data={
                "task_id": task_id,
                "classification_status": task.classification_status or "none",
                "classification_progress": task.classification_progress,
                "classification_summary": task.classification_summary,
                "classified_file_path": task.classified_file_path,
                "error_message": task.error_message,
            },
        ).to_dict()
    )


@comment_bp.route("/download-classified/<task_id>", methods=["GET"])
def download_classified_file(task_id: str):
    """下载已分类的评论文件。"""
    from ..services.export_task_manager import task_manager

    task = task_manager.get_task(task_id)
    if not task:
        return jsonify(ApiResponse(success=False, error="任务不存在").to_dict()), 404

    if task.classification_status != "completed":
        return jsonify(ApiResponse(success=False, error="请先完成分类").to_dict()), 400

    classified_path = task.classified_file_path
    if not classified_path or not os.path.exists(classified_path):
        base, ext = os.path.splitext(task.file_path)
        classified_path = f"{base}_classified{ext}" if ext else f"{base}_classified.csv"
        if not os.path.exists(classified_path):
            return jsonify(
                ApiResponse(success=False, error="分类文件不存在").to_dict()
            ), 404

    filename = f"classified_{task.task_id[:8]}.csv"
    return send_file(
        classified_path, mimetype="text/csv", as_attachment=True, download_name=filename
    )


@comment_bp.route("/reply-from-csv", methods=["POST"])
def reply_from_csv():
    """解析上传的CSV，返回要回复的评论列表"""
    if "file" not in request.files:
        return jsonify(ApiResponse(success=False, error="请上传文件").to_dict()), 400

    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return jsonify(ApiResponse(success=False, error="请上传CSV文件").to_dict()), 400

    import uuid
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent.parent
    upload_dir = project_root / "upload"
    upload_dir.mkdir(exist_ok=True)

    file_content = file.read().decode("utf-8-sig")
    file_id = str(uuid.uuid4())[:8]
    original_name = file.filename
    saved_path = upload_dir / f"reply_{file_id}_{original_name}"
    with open(saved_path, "w", encoding="utf-8-sig") as f:
        f.write(file_content)
    logger.info(f"保存上传的CSV: {saved_path}")

    comments = []
    stream = io.StringIO(file_content, newline="")
    reader = csv.DictReader(stream)

    for row in reader:
        reply_text = row.get("generated_reply", "").strip()
        if reply_text:
            comments.append(
                {
                    "comment_id": row.get("评论ID", ""),
                    "user_nickname": row.get("评论人用户名", ""),
                    "content": row.get("评论内容", ""),
                    "user_id": row.get("评论人ID", ""),
                    "reply_text": reply_text,
                }
            )

    return jsonify(
        ApiResponse(
            success=True,
            data={
                "to_reply": len(comments),
                "comments": comments,
            },
        ).to_dict()
    )


_reply_sender = None


@comment_bp.route("/reply-direct", methods=["POST"])
def reply_direct():
    """直接使用AI分类后的CSV文件发送回复"""
    global _reply_sender

    from ..services.reply_sender import ReplySender
    from ..services.export_task_manager import task_manager
    import os
    import csv

    data = request.get_json()
    task_id = data.get("task_id", "")

    task = task_manager.get_task(task_id)
    if not task or not task.classified_file_path:
        return jsonify(ApiResponse(success=False, error="没有分类文件").to_dict()), 400

    classified_file = task.classified_file_path
    if not os.path.exists(classified_file):
        return jsonify(
            ApiResponse(success=False, error="分类文件不存在").to_dict()
        ), 400

    comments_to_reply = []
    with open(classified_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            action = row.get("action", "")
            comment_id = row.get("评论ID", row.get("comment_id", ""))
            reply_content = row.get("generated_reply", "").strip()
            if action == "回复" and reply_content and comment_id:
                comments_to_reply.append(
                    {"comment_id": comment_id, "reply_text": reply_content}
                )

    if not comments_to_reply:
        return jsonify(
            ApiResponse(success=False, error="没有需要回复的评论").to_dict()
        ), 400

    service = XiaohongshuService()
    _reply_sender = ReplySender(service)
    _reply_sender.start(comments_to_reply, task.url)

    return jsonify(
        ApiResponse(success=True, data={"to_reply": len(comments_to_reply)}).to_dict()
    )


@comment_bp.route("/reply-confirm", methods=["POST"])
def reply_confirm():
    """确认发送回复"""
    global _reply_sender

    from ..services.reply_sender import ReplySender

    data = request.get_json()
    url = data.get("url", "")
    comments = data.get("comments", [])

    if not comments:
        return jsonify(
            ApiResponse(success=False, error="没有要发送的评论").to_dict()
        ), 400

    service = XiaohongshuService()
    _reply_sender = ReplySender(service)
    _reply_sender.start(comments, url)

    return jsonify(ApiResponse(success=True, data={"status": "running"}).to_dict())


@comment_bp.route("/reply-status", methods=["GET"])
def reply_status():
    """查询发送状态"""
    from ..services.reply_sender import ReplySender

    if _reply_sender:
        return jsonify(
            ApiResponse(success=True, data=_reply_sender.get_status()).to_dict()
        )
    return jsonify(ApiResponse(success=True, data={"running": False}).to_dict())


@comment_bp.route("/whitelist", methods=["GET"])
def get_whitelist():
    """获取白名单列表"""
    from ..services.whitelist_service import load_whitelist

    user_ids = load_whitelist()
    return jsonify(ApiResponse(success=True, data={"user_ids": user_ids}).to_dict())


@comment_bp.route("/whitelist", methods=["POST"])
def set_whitelist():
    """保存白名单列表"""
    from ..services.whitelist_service import save_whitelist

    data = request.get_json()
    user_ids = data.get("user_ids", [])

    if not isinstance(user_ids, list):
        return jsonify(
            ApiResponse(success=False, error="user_ids 必须为数组").to_dict()
        ), 400

    user_ids = [uid.strip() for uid in user_ids if uid.strip()]

    if save_whitelist(user_ids):
        return jsonify(ApiResponse(success=True, message="白名单已保存").to_dict())
    return jsonify(ApiResponse(success=False, error="保存失败").to_dict()), 500
