from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.user import UserProfileOut, UserProfileUpdate
from app.services.audit_service import log_audit_action

router = APIRouter()


@router.get("/users/me", response_model=UserProfileOut)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """查看当前用户资料（账户管理 · 个人资料）"""
    return current_user


@router.put("/users/me", response_model=UserProfileOut)
async def update_my_profile(
    data: UserProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户资料：昵称 / 头像 / 研究方向 / 简介（账户管理）"""
    if data.name is not None:
        current_user.name = data.name
    if data.avatar_url is not None:
        current_user.avatar_url = data.avatar_url
    if data.research_area is not None:
        current_user.research_area = data.research_area
    if data.bio is not None:
        current_user.bio = data.bio

    await db.commit()
    await db.refresh(current_user)

    # 审计（仅追加）
    await log_audit_action(
        db,
        team_id=None,
        operator_id=current_user.id,
        operator_name=current_user.name,
        operator_role="self",
        action_type="UPDATE",
        target_type="user_profile",
        target_id=current_user.id,
        target_summary=f"用户更新个人资料：{data.name or data.research_area or data.bio or 'profile'}",
        detail={"changed": {k: getattr(data, k) for k in ("name", "avatar_url", "research_area", "bio") if getattr(data, k) is not None}},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return current_user
