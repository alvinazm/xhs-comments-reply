"""Chrome 浏览器启动管理。"""

import logging
import requests
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import Config

logger = logging.getLogger(__name__)


def has_display() -> bool:
    """检查是否有显示器环境。"""
    return os.environ.get("DISPLAY") is not None or sys.platform == "darwin"


def ensure_chrome(
    host: str = None,
    port: int = None,
) -> bool:
    """检查 Chrome 调试模式是否已运行。"""
    if host is None:
        host = Config.CHROME_HOST
    if port is None:
        port = Config.CHROME_PORT

    try:
        resp = requests.get(f"http://{host}:{port}/json/version", timeout=2)
        if resp.status_code == 200:
            logger.info("Chrome 调试模式已运行 (port=%d)", port)
            return True
    except requests.exceptions.RequestException:
        pass

    logger.warning(
        "Chrome 调试模式未运行，请手动启动 Chrome 并开启调试模式 (port=%d)", port
    )
    return False
