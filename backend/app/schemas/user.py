from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# --- Auth ---
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="登录账号")
    password: str = Field(..., min_length=6, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_system_admin: bool
    must_change_password: bool

    model_config = {"from_attributes": True}


class AuthMeResponse(BaseModel):
    user: UserInfo
    teams: list = []  # 当前用户所有团队及角色


# --- Team ---
class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    school: Optional[str] = None
    research_area: Optional[str] = None
    description: Optional[str] = None
    meeting_time: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    school: Optional[str] = None
    research_area: Optional[str] = None
    description: Optional[str] = None
    meeting_time: Optional[str] = None


class TeamResponse(BaseModel):
    id: int
    name: str
    school: Optional[str] = None
    research_area: Optional[str] = None
    description: Optional[str] = None
    meeting_time: Optional[str] = None
    is_active: bool
    owner_id: int
    member_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamListItem(BaseModel):
    id: int
    name: str
    role: str

    model_config = {"from_attributes": True}


# --- Member ---
class MemberAddRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    role: str = Field(default="student", pattern="^(student|co_manager)$")


class MemberResponse(BaseModel):
    id: int
    user_id: int
    username: str
    display_name: str
    email: Optional[str] = None
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class MemberRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(student|co_manager|supervisor)$")


class MemberAddResponse(BaseModel):
    member: MemberResponse
    initial_password: str  # 随机生成的初始密码


class ResetPasswordResponse(BaseModel):
    new_password: str


# --- Dashboard ---
class DashboardResponse(BaseModel):
    team_name: str
    total_members: int
    total_owners: int = 0
    total_supervisors: int = 0
    recent_activities: list = []


# --- Audit Log ---
class AuditLogResponse(BaseModel):
    id: int
    team_id: Optional[int] = None
    operator_name: Optional[str] = None
    operator_role: Optional[str] = None
    action_type: str
    target_type: str
    target_summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogDetail(BaseModel):
    id: int
    team_id: Optional[int] = None
    operator_id: Optional[int] = None
    operator_name: Optional[str] = None
    operator_role: Optional[str] = None
    action_type: str
    target_type: str
    target_id: Optional[int] = None
    target_summary: Optional[str] = None
    detail: Optional[dict] = None
    ip_address: Optional[str] = None
    result: str
    created_at: datetime

    model_config = {"from_attributes": True}
