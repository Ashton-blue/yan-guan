from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import List, Optional
import re

from app.database import get_db
from app.middleware.auth_middleware import get_current_user, get_team_context
from app.middleware.permission import require_permission
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.audit_log import AuditLog
from app.models.policy_document import PolicyDocument
from app.models.ai_model_key import AiModelKey
from app.models.policy_qa_session import PolicyQASession
from app.models.application_template import ApplicationTemplate
from app.models.application_form import ApplicationForm
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserOut, ChangePassword, RegisterResponse
from app.utils.jwt import create_access_token, create_refresh_token
from app.utils.password import hash_password, verify_password

router = APIRouter()

@router.post("/auth/register", response_model=RegisterResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    # 检查邮箱是否已存在
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    # 创建新用户
    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        name=user_data.name,
        must_change_password=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return RegisterResponse(
        message="注册成功，请登录并修改密码",
        user=UserOut(
            id=new_user.id,
            email=new_user.email,
            name=new_user.name,
            must_change_password=new_user.must_change_password,
            created_at=new_user.created_at
        )
    )

@router.post("/auth/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    # 查找用户
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    # 创建token
    access_token = create_access_token({"sub": user.id, "email": user.email, "name": user.name})
    refresh_token = create_refresh_token({"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=86400
    )

@router.get("/auth/me", response_model=UserOut)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        must_change_password=current_user.must_change_password,
        created_at=current_user.created_at
    )

@router.post("/auth/change-password")
async def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改密码"""
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    
    current_user.hashed_password = hash_password(data.new_password)
    current_user.must_change_password = False
    await db.commit()
    
    return {"message": "密码修改成功"}

@router.post("/auth/refresh")
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """刷新访问令牌"""
    from app.utils.jwt import decode_token, get_subject
    payload = decode_token(refresh_token)
    
    if payload is None:
        raise HTTPException(status_code=401, detail="无效的刷新令牌")
    
    user_id = get_subject(payload)
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的刷新令牌")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    new_access_token = create_access_token({"sub": user.id, "email": user.email, "name": user.name})
    return {"access_token": new_access_token, "token_type": "bearer", "expires_in": 86400}

@router.post("/auth/forgot-password")
async def forgot_password(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """密码找回入口（管理员重置版）。

    说明：本系统无 SMTP 邮件设施，故密码找回落地为「管理员重置」——
    owner/supervisor 通过 /auth/reset-password 为目标成员重置密码。
    此接口用于校验目标成员是否存在，返回可被重置的成员摘要。
    """
    from app.models.team_member import TeamMember
    email = (data.get("email") or "").strip()
    result = await db.execute(select(User).where(User.email == email))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="未找到该邮箱")
    # 校验操作者是否在某团队中具备教师角色
    perm = await db.execute(
        select(TeamMember).where(
            TeamMember.user_id == current_user.id,
            TeamMember.role.in_(["owner", "supervisor"]),
            TeamMember.is_active == True
        ).limit(1)
    )
    if not perm.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="仅团队管理员可重置成员密码")
    return {"message": "请联系管理员重置或调用 /auth/reset-password", "target_name": target.name}

@router.post("/auth/reset-password")
async def admin_reset_password(
    data: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """管理员（owner/supervisor）为团队成员重置密码（查库校验，越权 403）"""
    from app.models.team_member import TeamMember
    from app.services.audit_service import log_audit_action

    target_user_id = data.get("member_id")
    new_password = data.get("new_password")
    if not target_user_id or not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="参数缺失：member_id 与 new_password(≥6位)")

    # 操作者须为 owner/supervisor
    op = await db.execute(
        select(TeamMember).where(
            TeamMember.user_id == current_user.id,
            TeamMember.role.in_(["owner", "supervisor"]),
            TeamMember.is_active == True
        ).limit(1)
    )
    op_member = op.scalar_one_or_none()
    if not op_member:
        raise HTTPException(status_code=403, detail="仅团队管理员可重置成员密码")

    # 目标须为同团队活跃成员
    target = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == op_member.team_id,
            TeamMember.user_id == target_user_id,
            TeamMember.is_active == True
        )
    )
    target_member = target.scalar_one_or_none()
    if not target_member:
        raise HTTPException(status_code=404, detail="目标不是本团队活跃成员")

    user = await db.get(User, target_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.hashed_password = hash_password(new_password)
    user.must_change_password = True  # 强制其下次登录修改
    await db.commit()

    await log_audit_action(
        db, team_id=op_member.team_id,
        operator_id=current_user.id, operator_name=current_user.name, operator_role=op_member.role,
        action_type="UPDATE", target_type="user", target_id=user.id,
        target_summary=f"为成员 {user.name} 重置密码",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return {"message": "密码已重置，目标用户下次登录须修改密码"}
