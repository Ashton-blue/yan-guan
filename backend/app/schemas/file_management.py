"""文件管理 + 讯息管理 Schemas"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date


def _strip_tz(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


# ---------- 文件夹 ----------
class FolderCreate(BaseModel):
    name: str = Field(..., max_length=200)
    parent_id: Optional[int] = None
    visibility: str = Field("team", pattern="^(team|teacher_only|private)$")

class FolderOut(BaseModel):
    id: int
    team_id: int
    parent_id: Optional[int]
    name: str
    visibility: str
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- 文件 ----------
class FileOut(BaseModel):
    id: int
    team_id: int
    folder_id: Optional[int]
    name: str
    original_name: str
    mime_type: Optional[str]
    size: int
    visibility: str
    version: int
    uploaded_by: Optional[int]
    uploaded_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=300)
    folder_id: Optional[int] = None
    visibility: Optional[str] = Field(None, pattern="^(team|teacher_only|private)$")


class FileListParams(BaseModel):
    folder_id: Optional[int] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=200)


# ---------- 讯息 ----------
class MessageOut(BaseModel):
    id: int
    team_id: int
    user_id: int
    sender_id: Optional[int]
    sender_name: Optional[str] = None
    msg_type: str
    title: str
    content: Optional[str]
    reference_type: Optional[str]
    reference_id: Optional[int]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """站内私信（简版）"""
    recipient_id: int
    title: str = Field(..., max_length=300)
    content: Optional[str] = Field(None, max_length=2000)
    msg_type: str = Field("direct")

class MessageListParams(BaseModel):
    tab: str = Field("all", pattern="^(all|notification|mention)$")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class MessageReadResult(BaseModel):
    message: int
    total_unread: int
