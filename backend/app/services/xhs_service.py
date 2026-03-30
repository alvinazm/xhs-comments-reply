"""小红书服务。"""

import logging
import os
import re
import sys
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import Config

from ..models.schemas import CommentResponse, NoteInfo
from .chrome_launcher import ensure_chrome, has_display
from .xhs import Browser, FeedDetailResponse
from .xhs.comment import reply_comment
from .xhs.errors import NoFeedDetailError, PageNotAccessibleError, XHSError
from .xhs.feed_detail import get_feed_detail
from .xhs.types import CommentLoadConfig

logger = logging.getLogger(__name__)


def parse_xhs_url(url: str) -> dict | None:
    """解析小红书链接，提取 feed_id 和 xsec_token。"""
    pattern = r"xiaohongshu\.com/explore/([a-f0-9]+)"
    match = re.search(pattern, url)
    if not match:
        return None

    feed_id = match.group(1)
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    xsec_token = query_params.get("xsec_token", [""])[0]
    if not xsec_token:
        return None

    return {"feed_id": feed_id, "xsec_token": xsec_token}


class XiaohongshuService:
    """小红书服务类。"""

    def __init__(self, host: str = None, port: int = None) -> None:
        self.host = host or Config.CHROME_HOST
        self.port = port or Config.CHROME_PORT

    def get_comments(
        self,
        url: str,
        max_comments: int = 20,
    ) -> tuple[NoteInfo, list[CommentResponse], int]:
        """获取笔记评论。

        Args:
            url: 小红书笔记 URL。
            max_comments: 最大评论数。

        Returns:
            (笔记信息, 评论列表, 总评论数)

        Raises:
            ValueError: URL 解析失败。
            PageNotAccessibleError: 页面不可访问。
            NoFeedDetailError: 未获取到详情。
            XHSError: 其他错误。
        """
        parsed = parse_xhs_url(url)
        if not parsed:
            raise ValueError("无效的小红书链接")

        feed_id = parsed["feed_id"]
        xsec_token = parsed["xsec_token"]

        if not ensure_chrome(port=self.port, headless=not has_display()):
            raise RuntimeError("Chrome 启动失败")

        browser = Browser(host=self.host, port=self.port)
        page = browser.new_page()

        try:
            config = CommentLoadConfig(
                click_more_replies=True,
                max_replies_threshold=10,
                max_comment_items=max_comments,
                scroll_speed="normal",
            )

            detail = get_feed_detail(
                page,
                feed_id,
                xsec_token,
                load_all_comments=True,
                config=config,
            )

            note_info = NoteInfo(
                note_id=detail.note.note_id,
                xsec_token=detail.note.xsec_token,
                title=detail.note.title,
                desc=detail.note.desc,
                type=detail.note.type,
                ip_location=detail.note.ip_location,
                user_nickname=detail.note.user.nickname or detail.note.user.nick_name,
                liked_count=detail.note.interact_info.liked_count,
                collected_count=detail.note.interact_info.collected_count,
                comment_count=detail.note.interact_info.comment_count,
                shared_count=detail.note.interact_info.shared_count,
            )

            comments = [
                CommentResponse.from_dict(c.to_dict())
                for c in detail.comments.list_[:max_comments]
            ]
            total = min(max_comments, len(detail.comments.list_))

            return note_info, comments, total

        finally:
            browser.close_page(page)
            browser.close()

    def get_note_and_initial_comments(
        self,
        url: str,
        initial_count: int = 5,
    ) -> tuple[NoteInfo, list[CommentResponse], int]:
        """获取笔记信息和初始评论（不滚动加载，快速响应）。

        Args:
            url: 小红书笔记 URL。
            initial_count: 初始获取的评论数量。

        Returns:
            (笔记信息, 评论列表, 总评论数)

        Raises:
            ValueError: URL 解析失败。
            PageNotAccessibleError: 页面不可访问。
            NoFeedDetailError: 未获取到详情。
            XHSError: 其他错误。
        """
        parsed = parse_xhs_url(url)
        if not parsed:
            raise ValueError("无效的小红书链接")

        feed_id = parsed["feed_id"]
        xsec_token = parsed["xsec_token"]

        if not ensure_chrome(port=self.port, headless=not has_display()):
            raise RuntimeError("Chrome 启动失败")

        browser = Browser(host=self.host, port=self.port)
        page = browser.new_page()

        try:
            detail = get_feed_detail(
                page,
                feed_id,
                xsec_token,
                load_all_comments=False,
            )

            note_info = NoteInfo(
                note_id=detail.note.note_id,
                xsec_token=detail.note.xsec_token,
                title=detail.note.title,
                desc=detail.note.desc,
                type=detail.note.type,
                ip_location=detail.note.ip_location,
                user_nickname=detail.note.user.nickname or detail.note.user.nick_name,
                liked_count=detail.note.interact_info.liked_count,
                collected_count=detail.note.interact_info.collected_count,
                comment_count=detail.note.interact_info.comment_count,
                shared_count=detail.note.interact_info.shared_count,
            )

            comments = [
                CommentResponse.from_dict(c.to_dict())
                for c in detail.comments.list_[:initial_count]
            ]
            total = (
                int(detail.note.interact_info.comment_count)
                if detail.note.interact_info.comment_count
                else 0
            )

            return note_info, comments, total

        finally:
            browser.close_page(page)
            browser.close()

    def reply_comment(
        self,
        url: str,
        content: str,
        comment_id: str = "",
        user_id: str = "",
    ) -> None:
        """回复单条评论。

        Args:
            url: 小红书笔记 URL。
            content: 回复内容。
            comment_id: 评论 ID。
            user_id: 用户 ID。

        Raises:
            ValueError: 参数错误。
            RuntimeError: 回复失败。
        """
        if not content:
            raise ValueError("回复内容不能为空")

        parsed = parse_xhs_url(url)
        if not parsed:
            raise ValueError("无效的小红书链接")

        feed_id = parsed["feed_id"]
        xsec_token = parsed["xsec_token"]

        if not comment_id and not user_id:
            raise ValueError("评论ID或用户ID不能都为空")

        if not ensure_chrome(port=self.port, headless=not has_display()):
            raise RuntimeError("Chrome 启动失败")

        browser = Browser(host=self.host, port=self.port)
        page = browser.new_page()

        try:
            reply_comment(page, feed_id, xsec_token, content, comment_id, user_id)
        finally:
            browser.close_page(page)
            browser.close()

    def reply_comments_batch(
        self,
        url: str,
        comments: list,
    ) -> tuple[int, list]:
        """批量回复评论，复用同一个页面。

        Args:
            url: 小红书笔记 URL。
            comments: 评论列表 [{"comment_id": "", "user_id": "", "reply_text": ""}, ...]

        Returns:
            (成功数量, 失败列表)

        Raises:
            ValueError: 参数错误。
        """
        if not comments:
            return 0, []

        import random

        parsed = parse_xhs_url(url)
        if not parsed:
            raise ValueError("无效的小红书链接")

        feed_id = parsed["feed_id"]
        xsec_token = parsed["xsec_token"]

        if not ensure_chrome(port=self.port, headless=not has_display()):
            raise RuntimeError("Chrome 启动失败")

        browser = Browser(host=self.host, port=self.port)
        page = browser.new_page()

        success_count = 0
        failed = []

        try:
            for comment in comments:
                comment_id = comment.get("comment_id", "")
                user_id = comment.get("user_id", "")
                content = comment.get("reply_text", "")

                if not content:
                    continue
                if not comment_id and not user_id:
                    continue

                try:
                    reply_comment(
                        page, feed_id, xsec_token, content, comment_id, user_id
                    )
                    success_count += 1
                except Exception as e:
                    comment["error"] = str(e)
                    failed.append(comment)

                if comment != comments[-1]:
                    time.sleep(random.uniform(3, 8))

            return success_count, failed
        finally:
            browser.close_page(page)
            browser.close()
