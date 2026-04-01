"""CDP 命令客户端封装 - 用于在服务器端构建 CDP 命令"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional


class CDPCommand:
    """CDP 命令构建器"""

    @staticmethod
    def navigate(url: str) -> Dict[str, Any]:
        return {"method": "Page.navigate", "params": {"url": url}}

    @staticmethod
    def reload() -> Dict[str, Any]:
        return {"method": "Page.reload", "params": {}}

    @staticmethod
    def evaluate(script: str) -> Dict[str, Any]:
        return {
            "method": "Runtime.evaluate",
            "params": {"expression": script, "returnByValue": True},
        }

    @staticmethod
    def get_document() -> Dict[str, Any]:
        return {"method": "DOM.getDocument", "params": {}}

    @staticmethod
    def query_selector(selector: str) -> Dict[str, Any]:
        return {"method": "DOM.querySelector", "params": {"selector": selector}}

    @staticmethod
    def get_all_messages() -> Dict[str, Any]:
        return {"method": "Runtime.getConsoleMessages", "params": {}}
