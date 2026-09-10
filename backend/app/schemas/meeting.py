from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

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

class MeetingUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    meeting_type: Optional[str] = Field(None, pattern="^(journal|progress|defense)$")
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    location: Optional[str] = None
    presenter_id: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = None

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
