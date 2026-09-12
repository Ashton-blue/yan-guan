from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.audit_log import AuditLog

router = APIRouter()

@router.post("/teams/{team_id}/members")
async def add_member(
    team_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """添加团队成员"""
    # 检查权限
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role.in_(["owner", "supervisor"])
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="无权添加成员")
    
    # 检查用户是否存在
    user_result = await db.execute(select(User).where(User.email == data.get("email")))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查是否已在团队中
    existing = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该用户已在团队中")
    
    # 添加成员
    new_member = TeamMember(
        team_id=team_id,
        user_id=user.id,
        role=data.get("role", "student"),
        invited_by=current_user.id
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)
    
    return {
        "id": new_member.id,
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "role": new_member.role,
        "created_at": new_member.created_at
    }

@router.get("/teams/{team_id}/members")
async def list_members(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取团队成员列表"""
    result = await db.execute(
        select(TeamMember, User).join(User).where(
            TeamMember.team_id == team_id,
            TeamMember.is_active == True
        ).order_by(TeamMember.created_at)
    )
    members = result.all()
    
    return [
        {
            "id": m.id,
            "user_id": u.id,
            "email": u.email,
            "name": u.name,
            "role": m.role,
            "invited_by": m.invited_by,
            "created_at": m.created_at
        }
        for m, u in members
    ]

@router.put("/teams/{team_id}/members/{member_id}")
async def update_member(
    team_id: int,
    member_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新成员信息"""
    # 检查权限
    owner_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role == "owner"
        )
    )
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="只有团队所有者可以修改成员角色")
    
    member = await db.get(TeamMember, member_id)
    if not member or member.team_id != team_id:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    if "role" in data:
        member.role = data["role"]
    if "is_active" in data:
        member.is_active = data["is_active"]
    
    await db.commit()
    return {"message": "成员信息已更新"}

@router.delete("/teams/{team_id}/members/{member_id}")
async def remove_member(
    team_id: int,
    member_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """移除团队成员"""
    # 检查权限
    owner_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role == "owner"
        )
    )
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="只有团队所有者可以移除成员")
    
    member = await db.get(TeamMember, member_id)
    if not member or member.team_id != team_id:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    member.is_active = False
    await db.commit()
    
    return {"message": "成员已移除"}

@router.get("/teams/{team_id}/members/me")
async def get_my_role(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户在团队中的角色"""
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=404, detail="您不是该团队的成员")
    
    return {
        "team_id": team_id,
        "user_id": current_user.id,
        "role": member.role,
        "created_at": member.created_at
    }

@router.patch("/teams/{team_id}/members/{user_id}")
async def patch_member(
    team_id: int,
    user_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """按 user_id 调整成员角色 / 启用状态（账户管理 · 成员管理）。

    仅团队 owner 可操作；越权 403。成员启用/禁用/移除、角色调整均进审计。
    """
    from app.services.audit_service import log_audit_action

    owner_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role == "owner"
        )
    )
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="仅团队所有者可调整成员")

    result = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")

    valid_roles = ["owner", "supervisor", "co_manager", "student", "collaborator", "temp_student"]
    changed = {}
    if "role" in data:
        if data["role"] not in valid_roles:
            raise HTTPException(status_code=400, detail=f"非法角色，可选：{'/'.join(valid_roles)}")
        member.role = data["role"]
        changed["role"] = data["role"]
    if "is_active" in data:
        member.is_active = bool(data["is_active"])
        changed["is_active"] = bool(data["is_active"])
    await db.commit()
    await db.refresh(member)

    target = await db.get(User, user_id)
    await log_audit_action(
        db, team_id=team_id,
        operator_id=current_user.id, operator_name=current_user.name, operator_role="owner",
        action_type="UPDATE", target_type="team_member", target_id=member.id,
        target_summary=f"调整成员 {target.name if target else user_id}：{changed or '无变更'}",
        detail=changed,
    )
    return {"user_id": user_id, "role": member.role, "is_active": bool(member.is_active), "changed": changed}
