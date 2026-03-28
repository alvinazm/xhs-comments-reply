"""通用响应工具。"""

from typing import Any, Optional

from flask import jsonify


def api_response(
    success: bool,
    data: Optional[Any] = None,
    message: str = "",
    error: Optional[str] = None,
    status_code: int = 200,
):
    """通用 API 响应格式。"""
    result = {"success": success}
    if message:
        result["message"] = message
    if data is not None:
        result["data"] = data
    if error:
        result["error"] = error
    return jsonify(result), status_code


def success_response(data: Any = None, message: str = "", status_code: int = 200):
    """成功响应。"""
    return api_response(
        success=True, data=data, message=message, status_code=status_code
    )


def error_response(error: str, status_code: int = 400, message: str = ""):
    """错误响应。"""
    return api_response(
        success=False,
        error=error,
        message=message,
        status_code=status_code,
    )
