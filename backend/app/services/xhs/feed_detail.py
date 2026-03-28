"""Feed 详情 + 评论加载。"""

from __future__ import annotations

import json
import logging
import random
import re
import time

from .cdp import Page
from .errors import NoFeedDetailError, PageNotAccessibleError
from .human import (
    BUTTON_CLICK_INTERVAL,
    DEFAULT_MAX_ATTEMPTS,
    FINAL_SPRINT_PUSH_COUNT,
    HUMAN_DELAY,
    LARGE_SCROLL_TRIGGER,
    MAX_CLICK_PER_ROUND,
    MIN_SCROLL_DELTA,
    POST_SCROLL,
    REACTION_TIME,
    READ_TIME,
    SCROLL_WAIT,
    SHORT_READ,
    STAGNANT_LIMIT,
    calculate_scroll_delta,
    get_scroll_interval,
    get_scroll_ratio,
    sleep_random,
)
from .selectors import (
    ACCESS_ERROR_WRAPPER,
    END_CONTAINER,
    NO_COMMENTS_TEXT,
    PARENT_COMMENT,
    SHOW_MORE_BUTTON,
)
from .types import CommentList, CommentLoadConfig, FeedDetailResponse
from .urls import make_feed_detail_url

logger = logging.getLogger(__name__)

_INACCESSIBLE_KEYWORDS = [
    "当前笔记暂时无法浏览",
    "该内容因违规已被删除",
    "该笔记已被删除",
    "内容不存在",
    "笔记不存在",
    "已失效",
    "私密笔记",
    "仅作者可见",
    "因用户设置，你无法查看",
    "因违规无法查看",
]

_SCAN_QRCODE_KEYWORDS = [
    "扫码查看",
    "打开小红书App扫码",
    "请使用小红书App扫码",
]

_REPLY_COUNT_RE = re.compile(r"展开\s*(\d+)\s*条回复")
_TOTAL_COMMENT_RE = re.compile(r"共(\d+)条评论")


def get_feed_detail(
    page: Page,
    feed_id: str,
    xsec_token: str,
    load_all_comments: bool = False,
    config: CommentLoadConfig | None = None,
) -> FeedDetailResponse:
    """获取 Feed 详情（含评论）。

    Args:
        page: CDP 页面对象。
        feed_id: Feed ID。
        xsec_token: xsec_token。
        load_all_comments: 是否加载全部评论。
        config: 评论加载配置。

    Raises:
        PageNotAccessibleError: 页面不可访问。
        NoFeedDetailError: 未获取到详情数据。
    """
    if config is None:
        config = CommentLoadConfig()

    url = make_feed_detail_url(feed_id, xsec_token)
    logger.info("打开 feed 详情页: %s", url)

    for attempt in range(3):
        try:
            page.navigate(url)
            page.wait_for_load()
            page.wait_dom_stable()
            break
        except Exception as e:
            logger.debug("页面导航重试 #%d: %s", attempt, e)
            time.sleep(0.5 + random.random())
    else:
        raise RuntimeError("页面导航失败")

    sleep_random(800, 1500)
    _check_page_accessible(page, url)

    if load_all_comments:
        try:
            _load_all_comments(page, config)
        except Exception as e:
            logger.warning("加载全部评论失败: %s", e)

    return _extract_feed_detail(page, feed_id)


def _check_page_accessible(page: Page, url: str = "") -> None:
    """检查页面是否可访问。"""
    time.sleep(0.5)
    text = page.get_element_text(ACCESS_ERROR_WRAPPER)
    if not text:
        return
    text = text.strip()

    if _is_scan_qrcode_verification(text) and url:
        logger.warning("触发小红书扫码验证，等待 10 秒后重新访问...")
        time.sleep(10)
        page.navigate(url)
        page.wait_for_load()
        page.wait_dom_stable()
        time.sleep(1)
        retry_text = page.get_element_text(ACCESS_ERROR_WRAPPER)
        if retry_text and _is_scan_qrcode_verification(retry_text.strip()):
            raise PageNotAccessibleError(
                "触发了小红书验证，需要在浏览器中扫码完成验证后重试。"
            )
        if not retry_text or not retry_text.strip():
            logger.info("验证已消失，继续加载笔记")
            return
        text = retry_text.strip()

    for kw in _INACCESSIBLE_KEYWORDS:
        if kw in text:
            raise PageNotAccessibleError(kw)

    if text:
        raise PageNotAccessibleError(text)


def _is_scan_qrcode_verification(text: str) -> bool:
    """判断页面文本是否为扫码验证。"""
    return any(kw in text for kw in _SCAN_QRCODE_KEYWORDS)


def _extract_feed_detail(page: Page, feed_id: str) -> FeedDetailResponse:
    """从 __INITIAL_STATE__ 提取 Feed 详情。"""
    js_code = f"""
    (() => {{
        try {{
            const state = window.__INITIAL_STATE__;
            if (state && state.note && state.note.noteDetailMap) {{
                const data = state.note.noteDetailMap["{feed_id}"];
                if (data) {{
                    return JSON.stringify(data);
                }}
            }}
            return "";
        }} catch(e) {{
            return "";
        }}
    }})()
    """

    result = None
    for _ in range(3):
        result = page.evaluate(js_code)
        if result:
            break
        time.sleep(0.2)

    if not result or result == "":
        raise NoFeedDetailError()

    note_data = json.loads(result)
    if not note_data:
        raise NoFeedDetailError()

    return FeedDetailResponse.from_dict(note_data)


def _load_all_comments(page: Page, config: CommentLoadConfig) -> None:
    """加载全部评论的状态机。"""
    max_attempts = (
        config.max_comment_items * 3
        if config.max_comment_items > 0
        else DEFAULT_MAX_ATTEMPTS
    )
    scroll_interval = get_scroll_interval(config.scroll_speed)

    logger.info("开始加载评论...")
    _scroll_to_comments_area(page)
    sleep_random(*HUMAN_DELAY)

    if _check_no_comments(page):
        logger.info("检测到无评论区域，跳过加载")
        return

    last_count = 0
    last_scroll_top = 0
    stagnant_checks = 0
    total_clicked = 0
    total_skipped = 0

    for attempt in range(max_attempts):
        logger.debug("=== 尝试 %d/%d ===", attempt + 1, max_attempts)

        if _check_end_container(page):
            count = _get_comment_count(page)
            logger.info(
                "检测到 THE END，加载完成: %d 条评论, 点击: %d, 跳过: %d",
                count,
                total_clicked,
                total_skipped,
            )
            return

        if config.click_more_replies and attempt % BUTTON_CLICK_INTERVAL == 0:
            clicked, skipped = _click_show_more_buttons(
                page, config.max_replies_threshold
            )
            total_clicked += clicked
            total_skipped += skipped
            if clicked > 0 or skipped > 0:
                sleep_random(*READ_TIME)
                c2, s2 = _click_show_more_buttons(page, config.max_replies_threshold)
                total_clicked += c2
                total_skipped += s2
                if c2 > 0 or s2 > 0:
                    sleep_random(*SHORT_READ)

        current_count = _get_comment_count(page)
        if current_count != last_count:
            logger.info("评论增加: %d -> %d", last_count, current_count)
            last_count = current_count
            stagnant_checks = 0
        else:
            stagnant_checks += 1

        if config.max_comment_items > 0 and current_count >= config.max_comment_items:
            logger.info(
                "已达到目标评论数: %d/%d", current_count, config.max_comment_items
            )
            return

        if current_count > 0:
            _scroll_to_last_comment(page)
            sleep_random(*POST_SCROLL)

        large_mode = stagnant_checks >= LARGE_SCROLL_TRIGGER
        push_count = 1
        if large_mode:
            push_count = 3 + random.randint(0, 2)

        scroll_delta, current_scroll_top = _human_scroll(
            page, config.scroll_speed, large_mode, push_count
        )

        if scroll_delta < MIN_SCROLL_DELTA or current_scroll_top == last_scroll_top:
            stagnant_checks += 1
        else:
            stagnant_checks = 0
            last_scroll_top = current_scroll_top

        if stagnant_checks >= STAGNANT_LIMIT:
            logger.info("停滞过多，尝试大冲刺...")
            _human_scroll(page, config.scroll_speed, True, 10)
            stagnant_checks = 0

        time.sleep(scroll_interval)

    logger.info("达到最大尝试次数，最后冲刺...")
    _human_scroll(page, config.scroll_speed, True, FINAL_SPRINT_PUSH_COUNT)
    count = _get_comment_count(page)
    logger.info(
        "加载结束: %d 条评论, 点击: %d, 跳过: %d", count, total_clicked, total_skipped
    )


def _human_scroll(
    page: Page,
    speed: str,
    large_mode: bool,
    push_count: int,
) -> tuple[int, int]:
    """人类化滚动。"""
    before_top = page.get_scroll_top()
    viewport_height = page.get_viewport_height()

    base_ratio = get_scroll_ratio(speed)
    if large_mode:
        base_ratio *= 2.0

    actual_delta = 0
    current_scroll_top = before_top

    for i in range(max(1, push_count)):
        scroll_delta = calculate_scroll_delta(viewport_height, base_ratio)
        page.scroll_by(0, int(scroll_delta))
        sleep_random(*SCROLL_WAIT)
        current_scroll_top = page.get_scroll_top()
        delta_this = current_scroll_top - before_top
        actual_delta += delta_this
        before_top = current_scroll_top
        if i < push_count - 1:
            sleep_random(*HUMAN_DELAY)

    if actual_delta < MIN_SCROLL_DELTA and push_count > 0:
        page.scroll_to_bottom()
        sleep_random(*POST_SCROLL)
        current_scroll_top = page.get_scroll_top()
        actual_delta = current_scroll_top - (before_top - actual_delta)

    return actual_delta, current_scroll_top


def _scroll_to_comments_area(page: Page) -> None:
    """滚动到评论区。"""
    logger.info("滚动到评论区...")
    page.scroll_element_into_view(".comments-container")
    time.sleep(0.5)
    page.dispatch_wheel_event(100)


def _scroll_to_last_comment(page: Page) -> None:
    """滚动到最后一条评论。"""
    count = page.get_elements_count(PARENT_COMMENT)
    if count > 0:
        page.scroll_nth_element_into_view(PARENT_COMMENT, count - 1)


def _get_comment_count(page: Page) -> int:
    """获取当前评论数量。"""
    return page.get_elements_count(PARENT_COMMENT)


def _check_no_comments(page: Page) -> bool:
    """检查是否无评论区域。"""
    text = page.get_element_text(NO_COMMENTS_TEXT)
    if not text:
        return False
    return "这是一片荒地" in text.strip()


def _check_end_container(page: Page) -> bool:
    """检查是否到达底部 THE END。"""
    text = page.get_element_text(END_CONTAINER)
    if not text:
        return False
    upper = text.strip().upper()
    return "THE END" in upper or "THEEND" in upper


def _click_show_more_buttons(page: Page, max_threshold: int) -> tuple[int, int]:
    """点击"展开N条回复"按钮。"""
    count = page.get_elements_count(SHOW_MORE_BUTTON)
    if count == 0:
        return 0, 0

    max_click = MAX_CLICK_PER_ROUND + random.randint(0, MAX_CLICK_PER_ROUND - 1)
    clicked = 0
    skipped = 0

    for i in range(count):
        if clicked >= max_click:
            break

        text = page.evaluate(
            f"document.querySelectorAll({json.dumps(SHOW_MORE_BUTTON)})[{i}]?.textContent || ''"
        )
        if not text:
            continue

        if max_threshold > 0:
            match = _REPLY_COUNT_RE.search(text)
            if match:
                reply_count = int(match.group(1))
                if reply_count > max_threshold:
                    logger.debug(
                        "跳过 '%s'（回复数 %d > 阈值 %d）",
                        text,
                        reply_count,
                        max_threshold,
                    )
                    skipped += 1
                    continue

        page.scroll_nth_element_into_view(SHOW_MORE_BUTTON, i)
        sleep_random(*REACTION_TIME)
        page.evaluate(
            f"document.querySelectorAll({json.dumps(SHOW_MORE_BUTTON)})[{i}]?.click()"
        )
        sleep_random(*READ_TIME)
        clicked += 1

    return clicked, skipped
