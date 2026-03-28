"""数据模型。"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NoteInfo:
    """笔记信息。"""

    note_id: str
    xsec_token: str
    title: str
    desc: str
    type: str
    ip_location: str
    user_nickname: str
    liked_count: str
    collected_count: str
    comment_count: str
    shared_count: str


@dataclass
class CommentResponse:
    """评论响应。"""

    id: str
    content: str
    like_count: str
    create_time: int
    ip_location: str
    user_id: str
    user_nickname: str
    sub_comment_count: str
    sub_comments: list["CommentResponse"]

    @classmethod
    def from_dict(cls, d: dict) -> "CommentResponse":
        user = d.get("user", {})
        sub_comments = d.get("sub_comments", [])
        return cls(
            id=d.get("id", ""),
            content=d.get("content", ""),
            like_count=d.get("like_count", ""),
            create_time=d.get("create_time", 0),
            ip_location=d.get("ip_location", ""),
            user_id=user.get("user_id", ""),
            user_nickname=user.get("nickname", ""),
            sub_comment_count=d.get("sub_comment_count", ""),
            sub_comments=[cls.from_dict(c) for c in sub_comments]
            if sub_comments
            else [],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "like_count": self.like_count,
            "create_time": self.create_time,
            "ip_location": self.ip_location,
            "user": {
                "user_id": self.user_id,
                "nickname": self.user_nickname,
            },
            "sub_comment_count": self.sub_comment_count,
            "sub_comments": [c.to_dict() for c in self.sub_comments]
            if self.sub_comments
            else [],
        }


@dataclass
class CommentRequest:
    """评论请求。"""

    url: str
    max_comments: int = 20


@dataclass
class ReplyRequest:
    """回复请求。"""

    url: str
    content: str
    comment_id: str = ""
    user_id: str = ""


@dataclass
class ApiResponse:
    """通用 API 响应。"""

    success: bool
    message: str = ""
    data: Optional[dict] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        result = {"success": self.success}
        if self.message:
            result["message"] = self.message
        if self.data is not None:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        return result
