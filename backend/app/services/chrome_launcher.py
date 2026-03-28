"""Chrome 浏览器启动管理。"""

import logging
import os
import subprocess
import sys
import time
from typing import Optional

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import Config

logger = logging.getLogger(__name__)

CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]


def _find_chrome() -> Optional[str]:
    """查找 Chrome 可执行文件路径。"""
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    result = subprocess.run(["which", "google-chrome"], capture_output=True)
    if result.returncode == 0:
        return result.stdout.decode().strip()
    return None


def has_display() -> bool:
    """检查是否有显示器环境。"""
    return os.environ.get("DISPLAY") is not None or sys.platform == "darwin"


def ensure_chrome(
    host: str = None,
    port: int = None,
    headless: Optional[bool] = None,
) -> bool:
    """确保 Chrome 处于调试模式运行。"""
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

    if headless is None:
        headless = not has_display()

    chrome_path = _find_chrome()
    if not chrome_path:
        logger.error("未找到 Chrome 浏览器")
        return False

    cmd = [chrome_path, f"--remote-debugging-port={port}"]

    if headless:
        cmd.append("--headless=new")

    if sys.platform == "darwin":
        cmd.extend(
            [
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir=/tmp/chrome-debug-{port}",
            ]
        )

    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("启动 Chrome (port=%d, headless=%s)", port, headless)

        for _ in range(15):
            try:
                resp = requests.get(f"http://{host}:{port}/json/version", timeout=2)
                if resp.status_code == 200:
                    logger.info("Chrome 启动成功")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)

        logger.warning("Chrome 启动但未就绪")
        return True

    except Exception as e:
        logger.error("Chrome 启动失败: %s", e)
        return False
