from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)
    name: str = Field(..., max_length=100)

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 86400

class UserOut(BaseModel):
    id: int
    email: str
    name: str
    must_change_password: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)

class RegisterResponse(BaseModel):
    message: str
    user: UserOut

# ---------- 账户管理（P0 批次 A） ----------
class UserProfileOut(BaseModel):
    id: int
    email: str
    name: str
    avatar_url: Optional[str] = None
    research_area: Optional[str] = None
    bio: Optional[str] = None
    status: str = "active"
    must_change_password: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
    research_area: Optional[str] = None
    bio: Optional[str] = None

class AdminResetPassword(BaseModel):
    """管理员（owner/supervisor）为团队成员重置密码"""
    member_id: int
    new_password: str = Field(..., min_length=6)
