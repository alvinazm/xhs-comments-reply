"""远程 Chrome 页面控制器 - 通过 WebSocket 将 CDP 命令转发给客户端."""

import json
import logging
import random
import time
from typing import Any

from .ws_manager import execute_cdp_command, get_first_client_id, ws_loop

logger = logging.getLogger(__name__)

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
"""


class RemotePage:
    """远程页面对象，通过 WebSocket 转发 CDP 命令到客户端 Chrome。"""

    def __init__(self, client_id: str = None):
        self.client_id = client_id or get_first_client_id()
        if not self.client_id:
            raise RuntimeError("没有在线的客户端")

    def _execute(self, command: str, params: dict = None, timeout: float = 30.0) -> Any:
        """执行 CDP 命令并返回结果。"""
        global ws_loop
        if ws_loop is None:
            raise RuntimeError("WebSocket 服务器未启动")
        result = ws_loop.run_until_complete(
            execute_cdp_command(self.client_id, command, params or {}, timeout=timeout)
        )
        if not result.get("success"):
            raise RuntimeError(f"CDP 命令失败: {result.get('error', 'unknown')}")

        # 提取实际结果
        cdp_result = result.get("result", {})
        if "result" in cdp_result:
            return cdp_result["result"]
        return cdp_result

    def navigate(self, url: str):
        """导航到 URL。"""
        self._execute("Page.navigate", {"url": url})
        self.wait_for_load()

    def wait_for_load(self, timeout: float = 60.0):
        """等待页面加载完成。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                state = self.evaluate("document.readyState")
                if state == "complete":
                    return
            except Exception:
                pass
            time.sleep(0.5)
        logger.warning("等待页面加载超时")

    def evaluate(self, expression: str, timeout: float = 30.0) -> Any:
        """执行 JavaScript 并返回结果。"""
        result = self._execute(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": False,
            },
            timeout=timeout,
        )
        if "exceptionDetails" in result:
            raise RuntimeError(f"JS 执行异常: {result['exceptionDetails']}")
        remote_obj = result.get("result", {})
        return remote_obj.get("value")

    def query_selector(self, selector: str) -> str | None:
        """查找单个元素。"""
        result = self._execute(
            "Runtime.evaluate",
            {
                "expression": f"document.querySelector({json.dumps(selector)})",
                "returnByValue": False,
            },
        )
        remote_obj = result.get("result", {})
        if remote_obj.get("subtype") == "null" or remote_obj.get("type") == "undefined":
            return None
        return remote_obj.get("objectId")

    def has_element(self, selector: str) -> bool:
        """检查元素是否存在。"""
        return (
            self.evaluate(f"document.querySelector({json.dumps(selector)}) !== null")
            is True
        )

    def wait_for_element(self, selector: str, timeout: float = 30.0) -> str:
        """等待元素出现。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            oid = self.query_selector(selector)
            if oid:
                return oid
            time.sleep(0.5)
        raise RuntimeError(f"元素未找到: {selector}")

    def click_element(self, selector: str):
        """点击元素。"""
        box = self.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return null;
                el.scrollIntoView({{block: 'center'}});
                const rect = el.getBoundingClientRect();
                return {{x: rect.left + rect.width / 2, y: rect.top + rect.height / 2}};
            }})()
            """
        )
        if not box:
            return
        x = box["x"] + random.uniform(-3, 3)
        y = box["y"] + random.uniform(-3, 3)
        self._execute(
            "Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y}
        )
        time.sleep(random.uniform(0.03, 0.08))
        self._execute(
            "Input.dispatchMouseEvent",
            {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1},
        )
        self._execute(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1,
            },
        )

    def input_content_editable(self, selector: str, text: str):
        """向 contentEditable 元素输入文本。"""
        self.click_element(selector)
        time.sleep(0.2)

        # 清空
        self._execute(
            "Input.dispatchKeyEvent",
            {
                "type": "keyDown",
                "key": "a",
                "code": "KeyA",
                "windowsVirtualKeyCode": 65,
            },
        )
        self._execute(
            "Input.dispatchKeyEvent",
            {"type": "keyUp", "key": "a", "code": "KeyA", "windowsVirtualKeyCode": 65},
        )
        self._execute(
            "Input.dispatchKeyEvent",
            {
                "type": "keyDown",
                "key": "Backspace",
                "code": "Backspace",
                "windowsVirtualKeyCode": 8,
            },
        )
        time.sleep(0.1)

        # 输入
        for char in text:
            if char == "\n":
                self._execute(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyDown",
                        "key": "Enter",
                        "code": "Enter",
                        "windowsVirtualKeyCode": 13,
                    },
                )
                self._execute(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyUp",
                        "key": "Enter",
                        "code": "Enter",
                        "windowsVirtualKeyCode": 13,
                    },
                )
            else:
                self._execute(
                    "Input.dispatchKeyEvent",
                    {"type": "keyDown", "text": char},
                )
                self._execute(
                    "Input.dispatchKeyEvent",
                    {"type": "keyUp", "text": char},
                )
            time.sleep(random.uniform(0.03, 0.08))

    def get_element_text(self, selector: str) -> str | None:
        """获取元素文本。"""
        return self.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                return el ? el.textContent : null;
            }})()
            """
        )

    def get_elements_count(self, selector: str) -> int:
        """获取匹配元素数量。"""
        result = self.evaluate(
            f"document.querySelectorAll({json.dumps(selector)}).length"
        )
        return result if isinstance(result, int) else 0

    def scroll_by(self, x: int, y: int):
        """滚动页面。"""
        self.evaluate(f"window.scrollBy({x}, {y})")

    def scroll_to_bottom(self):
        """滚动到页面底部。"""
        self.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    def scroll_element_into_view(self, selector: str):
        """将元素滚动到可视区域。"""
        self.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (el) el.scrollIntoView({{block: 'center'}});
            }})()
            """
        )

    def get_scroll_position(self) -> int:
        """获取滚动位置。"""
        result = self.evaluate(
            "window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0"
        )
        return int(result) if result else 0

    def get_viewport_height(self) -> int:
        """获取视口高度。"""
        result = self.evaluate("window.innerHeight")
        return int(result) if result else 768

    def dispatch_wheel_event(self, delta_y: float):
        """触发滚轮事件。"""
        self.evaluate(
            f"""
            (() => {{
                let target = document.querySelector('.note-scroller')
                    || document.querySelector('.interaction-container')
                    || document.documentElement;
                const event = new WheelEvent('wheel', {{
                    deltaY: {delta_y},
                    deltaMode: 0,
                    bubbles: true,
                    cancelable: true,
                    view: window,
                }});
                target.dispatchEvent(event);
            }})()
            """
        )

    def get_scroll_top(self) -> int:
        """获取滚动位置。"""
        result = self.evaluate(
            "window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0"
        )
        return int(result) if result else 0

    def scroll_nth_element_into_view(self, selector: str, index: int):
        """将第 N 个元素滚动到可视区域。"""
        self.evaluate(
            f"""
            (() => {{
                const els = document.querySelectorAll({json.dumps(selector)});
                if (els[{index}]) els[{index}].scrollIntoView({{behavior: 'smooth', block: 'center'}});
            }})()
            """
        )

    def wait_dom_stable(self, timeout: float = 10.0, interval: float = 0.5):
        """等待 DOM 稳定。"""
        last_html = ""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                html = self.evaluate(
                    "document.body ? document.body.innerHTML.length : 0"
                )
                if html == last_html and html != "":
                    return
                last_html = html
            except Exception:
                pass
            time.sleep(interval)

    def inject_stealth(self):
        """注入反检测脚本。"""
        self._execute("Page.addScriptToEvaluateOnNewDocument", {"source": STEALTH_JS})
