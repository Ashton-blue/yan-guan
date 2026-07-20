from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.schemas.user import (
    MemberAddRequest, MemberResponse, MemberRoleUpdate,
    MemberAddResponse, ResetPasswordResponse,
)
from app.utils.password import hash_password, generate_random_password, verify_password
from app.middleware.auth_middleware import get_current_user, get_user_team_role
from app.services.audit_service import create_audit_log

router = APIRouter(prefix="/api/v1/teams/{team_id}/members", tags=["成员管理"])


async def _check_team_access(
    team_id: int, user: User, db: AsyncSession,
    require_roles: list[str] | None = None,
) -> str:
    """检查团队访问权限，返回用户角色"""
    result = await db.execute(
        select(Team).where(Team.id == team_id, Team.deleted_at.is_(None))
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")

    role = await get_user_team_role(user, team_id, db)
    if not role and not user.is_system_admin:
        raise HTTPException(status_code=403, detail="您不在此团队中")

    if require_roles and role not in require_roles and not user.is_system_admin:
        raise HTTPException(status_code=403, detail="权限不足")

    return role or "system_admin"


@router.get("", response_model=list[MemberResponse])
async def list_members(
    team_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取团队成员列表"""
    await _check_team_access(team_id, user, db)

    result = await db.execute(
        select(TeamMember, User).join(User, TeamMember.user_id == User.id)
        .where(TeamMember.team_id == team_id)
        .order_by(TeamMember.joined_at)
    )
    rows = result.all()

    return [
        MemberResponse(
            id=member.id,
            user_id=u.id,
            username=u.username,
            display_name=u.display_name,
            email=u.email,
            role=member.role,
            joined_at=member.joined_at,
        )
        for member, u in rows
    ]


@router.post("", response_model=MemberAddResponse)
async def add_member(
    team_id: int,
    req: MemberAddRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新增成员（需owner/supervisor/co_manager权限）"""
    role = await _check_team_access(team_id, user, db, ["owner", "supervisor", "co_manager"])

    # 检查账号是否已存在
    result = await db.execute(select(User).where(User.username == req.username))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # 用户已存在，直接加入团队
        target_user = existing_user
        # 检查是否已在团队中
        check = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == target_user.id,
            )
        )
        if check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该用户已是团队成员")
    else:
        # 创建新用户
        initial_password = generate_random_password()
        target_user = User(
            username=req.username,
            password_hash=hash_password(initial_password),
            display_name=req.display_name,
            email=req.email,
            must_change_password=True,
        )
        db.add(target_user)
        await db.flush()

    # 加入团队
    member = TeamMember(team_id=team_id, user_id=target_user.id, role=req.role)
    db.add(member)
    await db.flush()

    # 写审计日志
    await create_audit_log(
        db,
        team_id=team_id,
        operator=user,
        operator_role=role,
        action_type="CREATE",
        target_type="member",
        target_id=target_user.id,
        target_summary=f"新增成员 {target_user.display_name}（{req.role}）",
        ip_address=request.client.host if request.client else None,
    )

    return MemberAddResponse(
        member=MemberResponse(
            id=member.id,
            user_id=target_user.id,
            username=target_user.username,
            display_name=target_user.display_name,
            email=target_user.email,
            role=member.role,
            joined_at=member.joined_at,
        ),
        initial_password=initial_password if not existing_user else "用户已存在，无需密码",
    )


@router.put("/{target_user_id}/role")
async def update_member_role(
    team_id: int,
    target_user_id: int,
    req: MemberRoleUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改成员角色"""
    role = await _check_team_access(team_id, user, db, ["owner"])

    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == target_user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")

    old_role = member.role
    member.role = req.role
    await db.flush()

    # 审计日志
    target_user = await db.execute(select(User).where(User.id == target_user_id))
    target = target_user.scalar_one_or_none()

    await create_audit_log(
        db,
        team_id=team_id,
        operator=user,
        operator_role=role,
        action_type="UPDATE",
        target_type="member",
        target_id=target_user_id,
        target_summary=f"修改成员角色：{target.display_name if target else ''} {old_role}→{req.role}",
        detail={"old_role": old_role, "new_role": req.role},
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "角色修改成功"}


@router.delete("/{target_user_id}")
async def remove_member(
    team_id: int,
    target_user_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """移除成员"""
    role = await _check_team_access(team_id, user, db, ["owner", "supervisor"])

    # 不能移除教师（owner）
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == target_user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")

    if member.role == "owner":
        raise HTTPException(status_code=403, detail="不能移除团队教师")

    # 获取成员信息用于日志
    target_user = await db.execute(select(User).where(User.id == target_user_id))
    target = target_user.scalar_one_or_none()

    await db.delete(member)
    await db.flush()

    await create_audit_log(
        db,
        team_id=team_id,
        operator=user,
        operator_role=role,
        action_type="DELETE",
        target_type="member",
        target_id=target_user_id,
        target_summary=f"移除成员 {target.display_name if target else ''}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "成员已移除"}


@router.post("/{target_user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_member_password(
    team_id: int,
    target_user_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """重置成员密码"""
    role = await _check_team_access(team_id, user, db, ["owner", "supervisor"])

    result = await db.execute(select(User).where(User.id == target_user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    new_password = generate_random_password()
    target_user.password_hash = hash_password(new_password)
    target_user.must_change_password = True
    await db.flush()

    await create_audit_log(
        db,
        team_id=team_id,
        operator=user,
        operator_role=role,
        action_type="UPDATE",
        target_type="member",
        target_id=target_user_id,
        target_summary=f"重置密码：{target_user.display_name}",
        ip_address=request.client.host if request.client else None,
    )

    return ResetPasswordResponse(new_password=new_password)
