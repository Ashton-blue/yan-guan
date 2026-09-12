from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date, timezone


def _strip_tz(dt: Optional[datetime]) -> Optional[datetime]:
    """PostgreSQL TIMESTAMP WITHOUT TIME ZONE 列不接受带时区信息的 datetime。
    若客户端传入带 tzinfo 的值（如 'Z' 结尾的 ISO 字符串），统一剥离为 naive。"""
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt

# ---------- 会议 ----------
class MeetingCreate(BaseModel):
    title: str = Field(..., max_length=200)
    meeting_type: str = Field(..., pattern="^(journal|progress|defense)$")  # 文献报告/进展汇报/答辩预演
    start_at: datetime
    end_at: Optional[datetime] = None
    location: Optional[str] = None
    presenter_id: Optional[int] = None
    description: Optional[str] = None
    status: str = "upcoming"

    @field_validator("start_at", "end_at", mode="after")
    @classmethod
    def _strip_tzinfo(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _strip_tz(v)

class MeetingUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    meeting_type: Optional[str] = Field(None, pattern="^(journal|progress|defense)$")
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    location: Optional[str] = None
    presenter_id: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = None

    @field_validator("start_at", "end_at", mode="after")
    @classmethod
    def _strip_tzinfo(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _strip_tz(v)

class MeetingOut(BaseModel):
    id: int
    team_id: int
    title: str
    meeting_type: str
    start_at: datetime
    end_at: Optional[datetime]
    location: Optional[str]
    presenter_id: Optional[int]
    presenter_name: Optional[str] = None
    description: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class MeetingDetail(MeetingOut):
    agenda: List["AgendaItemOut"] = []
    actions: List["ActionOut"] = []

# ---------- 议程 ----------
class AgendaItemCreate(BaseModel):
    seq: int = 0
    time_slot: Optional[str] = None
    content: str = Field(..., max_length=300)
    presenter_id: Optional[int] = None

class AgendaItemOut(BaseModel):
    id: int
    seq: int
    time_slot: Optional[str]
    content: str
    presenter_id: Optional[int]
    presenter_name: Optional[str] = None

    class Config:
        from_attributes = True

# ---------- 行动项 ----------
class ActionCreate(BaseModel):
    content: str = Field(..., max_length=300)
    owner_id: Optional[int] = None
    due_date: Optional[date] = None

class ActionUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=300)
    owner_id: Optional[int] = None
    due_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(open|done|cancelled)$")
    completed_at: Optional[datetime] = None

class ActionOut(BaseModel):
    id: int
    content: str
    owner_id: Optional[int]
    owner_name: Optional[str] = None
    due_date: Optional[date]
    status: str
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

# ---------- 团队邀请码 ----------
class InviteCreate(BaseModel):
    role: str = "student"  # 受邀加入后的默认角色
    valid_days: Optional[int] = Field(7, ge=1, le=90)

class InviteOut(BaseModel):
    id: int
    code: str
    role: str
    status: str
    invited_by_name: Optional[str] = None
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

MeetingDetail.model_rebuild()
