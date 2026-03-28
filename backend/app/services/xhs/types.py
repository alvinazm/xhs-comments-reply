"""小红书数据类型定义。"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class User:
    user_id: str = ""
    nickname: str = ""
    nick_name: str = ""
    avatar: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "User":
        return cls(
            user_id=d.get("userId", ""),
            nickname=d.get("nickname", ""),
            nick_name=d.get("nickName", ""),
            avatar=d.get("avatar", ""),
        )

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "nickname": self.nickname or self.nick_name,
        }


@dataclass
class InteractInfo:
    liked: bool = False
    liked_count: str = ""
    shared_count: str = ""
    comment_count: str = ""
    collected_count: str = ""
    collected: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "InteractInfo":
        return cls(
            liked=d.get("liked", False),
            liked_count=d.get("likedCount", ""),
            shared_count=d.get("sharedCount", ""),
            comment_count=d.get("commentCount", ""),
            collected_count=d.get("collectedCount", ""),
            collected=d.get("collected", False),
        )

    def to_dict(self) -> dict:
        return {
            "liked": self.liked,
            "liked_count": self.liked_count,
            "shared_count": self.shared_count,
            "comment_count": self.comment_count,
            "collected_count": self.collected_count,
            "collected": self.collected,
        }


@dataclass
class DetailImageInfo:
    width: int = 0
    height: int = 0
    url_default: str = ""
    url_pre: str = ""
    live_photo: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "DetailImageInfo":
        return cls(
            width=d.get("width", 0),
            height=d.get("height", 0),
            url_default=d.get("urlDefault", ""),
            url_pre=d.get("urlPre", ""),
            live_photo=d.get("livePhoto", False),
        )


@dataclass
class Comment:
    id: str = ""
    note_id: str = ""
    content: str = ""
    like_count: str = ""
    create_time: int = 0
    ip_location: str = ""
    liked: bool = False
    user_info: User = field(default_factory=User)
    sub_comment_count: str = ""
    sub_comments: list["Comment"] = field(default_factory=list)
    show_tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Comment":
        return cls(
            id=d.get("id", ""),
            note_id=d.get("noteId", ""),
            content=d.get("content", ""),
            like_count=d.get("likeCount", ""),
            create_time=d.get("createTime", 0),
            ip_location=d.get("ipLocation", ""),
            liked=d.get("liked", False),
            user_info=User.from_dict(d.get("userInfo", {})),
            sub_comment_count=d.get("subCommentCount", ""),
            sub_comments=[cls.from_dict(c) for c in d.get("subComments", []) or []],
            show_tags=d.get("showTags", []) or [],
        )

    def to_dict(self) -> dict:
        result: dict = {
            "id": self.id,
            "content": self.content,
            "like_count": self.like_count,
            "create_time": self.create_time,
            "ip_location": self.ip_location,
            "user": self.user_info.to_dict(),
            "sub_comment_count": self.sub_comment_count,
        }
        if self.sub_comments:
            result["sub_comments"] = [c.to_dict() for c in self.sub_comments]
        return result


@dataclass
class CommentList:
    list_: list[Comment] = field(default_factory=list)
    cursor: str = ""
    has_more: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "CommentList":
        return cls(
            list_=[Comment.from_dict(c) for c in d.get("list", []) or []],
            cursor=d.get("cursor", ""),
            has_more=d.get("hasMore", False),
        )


@dataclass
class FeedDetail:
    note_id: str = ""
    xsec_token: str = ""
    title: str = ""
    desc: str = ""
    type: str = ""
    time: int = 0
    ip_location: str = ""
    user: User = field(default_factory=User)
    interact_info: InteractInfo = field(default_factory=InteractInfo)
    image_list: list[DetailImageInfo] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "FeedDetail":
        return cls(
            note_id=d.get("noteId", ""),
            xsec_token=d.get("xsecToken", ""),
            title=d.get("title", ""),
            desc=d.get("desc", ""),
            type=d.get("type", ""),
            time=d.get("time", 0),
            ip_location=d.get("ipLocation", ""),
            user=User.from_dict(d.get("user", {})),
            interact_info=InteractInfo.from_dict(d.get("interactInfo", {})),
            image_list=[
                DetailImageInfo.from_dict(i) for i in d.get("imageList", []) or []
            ],
        )

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "title": self.title,
            "desc": self.desc,
            "type": self.type,
            "time": self.time,
            "ip_location": self.ip_location,
            "user": self.user.to_dict(),
            "interact_info": self.interact_info.to_dict(),
            "image_list": [
                {
                    "width": img.width,
                    "height": img.height,
                    "url_default": img.url_default,
                }
                for img in self.image_list
            ],
        }


@dataclass
class FeedDetailResponse:
    note: FeedDetail = field(default_factory=FeedDetail)
    comments: CommentList = field(default_factory=CommentList)

    @classmethod
    def from_dict(cls, d: dict) -> "FeedDetailResponse":
        return cls(
            note=FeedDetail.from_dict(d.get("note", {})),
            comments=CommentList.from_dict(d.get("comments", {})),
        )

    def to_dict(self) -> dict:
        return {
            "note": self.note.to_dict(),
            "comments": [c.to_dict() for c in self.comments.list_],
        }


@dataclass
class CommentLoadConfig:
    click_more_replies: bool = False
    max_replies_threshold: int = 10
    max_comment_items: int = 0
    scroll_speed: str = "normal"
