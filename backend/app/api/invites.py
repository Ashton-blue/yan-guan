import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.middleware.permission import get_team_member, require_team_role, TEACHER_ROLES, ALL_ROLES
from app.models.user import User
from app.models.team_member import TeamMember
from app.models.team_invite import TeamInvite
from app.schemas.meeting import InviteCreate
from app.services.audit_service import log_audit_action

router = APIRouter()


def _invite_out(inv: TeamInvite, inviter_name: str | None = None) -> dict:
    return {
        "id": inv.id,
        "code": inv.code,
        "role": inv.role,
        "status": inv.status,
        "invited_by_name": inviter_name,
        "expires_at": inv.expires_at,
        "created_at": inv.created_at,
    }


@router.get("/teams/{team_id}/invites")
async def list_invites(
    team_id: int,
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    """获取团队邀请码列表（含状态，仅团队成员可见）"""
    result = await db.execute(
        select(TeamInvite, User.name)
        .join(User, User.id == TeamInvite.invited_by, isouter=True)
        .where(TeamInvite.team_id == team_id)
        .order_by(TeamInvite.created_at.desc())
    )
    return [_invite_out(inv, name) for inv, name in result.all()]


@router.post("/teams/{team_id}/invites")
async def create_invite(
    team_id: int,
    data: InviteCreate,
    request: Request,
    member: TeamMember = Depends(require_team_role(*TEACHER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """生成邀请码（教师角色：owner/supervisor/co_manager）"""
    if data.role not in ALL_ROLES:
        raise HTTPException(status_code=400, detail=f"非法角色，可选：{'/'.join(ALL_ROLES)}")

    inv = TeamInvite(
        team_id=team_id,
        code=secrets.token_urlsafe(12),
        role=data.role,
        invited_by=member.user_id,
        status="active",
        expires_at=datetime.utcnow() + timedelta(days=data.valid_days),
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)

    await log_audit_action(
        db, team_id=team_id,
        operator_id=member.user_id, operator_name="教师", operator_role=member.role,
        action_type="CREATE", target_type="team_invite", target_id=inv.id,
        target_summary=f"生成邀请码（角色 {inv.role}，{data.valid_days} 天有效）",
        detail={"code": inv.code, "role": inv.role, "valid_days": data.valid_days},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return _invite_out(inv)


@router.delete("/teams/{team_id}/invites/{invite_id}")
async def revoke_invite(
    team_id: int,
    invite_id: int,
    request: Request,
    member: TeamMember = Depends(require_team_role("owner", "supervisor")),
    db: AsyncSession = Depends(get_db),
):
    """作废邀请码（仅 owner/supervisor）"""
    result = await db.execute(
        select(TeamInvite).where(TeamInvite.id == invite_id, TeamInvite.team_id == team_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="邀请码不存在")
    inv.status = "expired"
    await db.commit()

    await log_audit_action(
        db, team_id=team_id,
        operator_id=member.user_id, operator_name="教师", operator_role=member.role,
        action_type="DELETE", target_type="team_invite", target_id=inv.id,
        target_summary="作废邀请码",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return {"message": "邀请码已作废"}


@router.post("/teams/join")
async def join_team(
    data: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """凭邀请码加入团队（账户管理 · 团队与成员）"""
    code = (data.get("code") or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="缺少邀请码")

    result = await db.execute(select(TeamInvite).where(TeamInvite.code == code))
    inv = result.scalar_one_or_none()
    if not inv or inv.status != "active":
        raise HTTPException(status_code=404, detail="邀请码无效或已失效")
    if inv.expires_at and inv.expires_at < datetime.utcnow():
        inv.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="邀请码已过期")

    # 是否已在该团队
    exists = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == inv.team_id,
            TeamMember.user_id == current_user.id,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="你已是该团队成员")

    new_member = TeamMember(
        team_id=inv.team_id,
        user_id=current_user.id,
        role=inv.role,
        invited_by=inv.invited_by,
    )
    inv.status = "used"
    inv.used_by = current_user.id
    db.add(new_member)
    await db.commit()

    await log_audit_action(
        db, team_id=inv.team_id,
        operator_id=current_user.id, operator_name=current_user.name, operator_role=inv.role,
        action_type="CREATE", target_type="team_member", target_id=new_member.id,
        target_summary=f"通过邀请码加入团队（角色 {inv.role}）",
        detail={"invite_code": code},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return {"message": "加入团队成功", "team_id": inv.team_id, "role": inv.role}
