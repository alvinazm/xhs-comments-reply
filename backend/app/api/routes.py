"""API 路由。"""

import csv
import io
import logging
import sys
import os
import time

import requests
from flask import Blueprint, jsonify, request, Response

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import Config

from ..models.schemas import ApiResponse, CommentRequest, ReplyRequest
from ..services import XiaohongshuService
from ..services.chrome_launcher import ensure_chrome, has_display
from ..services.xhs.errors import NoFeedDetailError, PageNotAccessibleError, XHSError

logger = logging.getLogger("api")

comment_bp = Blueprint("comment", __name__, url_prefix="/api")


@comment_bp.route("/start-chrome", methods=["POST"])
def start_chrome():
    """启动 Chrome 调试模式。"""
    try:
        if ensure_chrome(
            host=Config.CHROME_HOST, port=Config.CHROME_PORT, headless=False
        ):
            from ..services.xhs.cdp import Browser

            browser = Browser(host=Config.CHROME_HOST, port=Config.CHROME_PORT)
            page = browser.new_page("https://www.xiaohongshu.com/")
            return jsonify(
                ApiResponse(success=True, message="Chrome 启动成功").to_dict()
            )
        return jsonify(
            ApiResponse(success=False, error="Chrome 启动失败").to_dict()
        ), 500
    except Exception as e:
        logger.error("启动 Chrome 失败: %s", e)
        return jsonify(ApiResponse(success=False, error=str(e)).to_dict()), 500


@comment_bp.route("/check-chrome", methods=["GET"])
def check_chrome():
    """检查 Chrome 调试模式状态。"""
    try:
        resp = requests.get(
            f"http://{Config.CHROME_HOST}:{Config.CHROME_PORT}/json/version", timeout=2
        )
        running = resp.status_code == 200
        return jsonify(ApiResponse(success=True, data={"running": running}).to_dict())
    except Exception:
        return jsonify(ApiResponse(success=True, data={"running": False}).to_dict())


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

    try:
        req = CommentRequest(url=url, max_comments=max_comments)
        service = XiaohongshuService()

        note, comments, total = service.get_comments(req.url, req.max_comments)

        def format_comment(c):
            d = c.to_dict()
            d["create_time_str"] = (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(c.create_time)))
                if c.create_time
                else ""
            )
            return d

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
                    "comments": [format_comment(c) for c in comments],
                    "total_comments": total,
                },
            ).to_dict()
        )

    except ValueError as e:
        logger.error("参数错误: %s", e)
        return jsonify(ApiResponse(success=False, error=str(e)).to_dict()), 400
    except PageNotAccessibleError as e:
        logger.error("页面不可访问: %s", e)
        return jsonify(ApiResponse(success=False, error=str(e)).to_dict()), 400
    except NoFeedDetailError:
        logger.error("未获取到详情数据")
        return jsonify(
            ApiResponse(
                success=False, error="未获取到笔记详情，请检查链接是否正确"
            ).to_dict()
        ), 400
    except XHSError as e:
        logger.error("XHS 错误: %s", e)
        return jsonify(ApiResponse(success=False, error=str(e)).to_dict()), 500
    except Exception as e:
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
