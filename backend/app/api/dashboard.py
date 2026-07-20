from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.audit_log import AuditLog
from app.schemas.user import DashboardResponse
from app.middleware.auth_middleware import get_current_user, get_user_team_role

router = APIRouter(prefix="/api/v1/teams/{team_id}/dashboard", tags=["仪表盘"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    team_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """仪表盘统计数据"""
    # 检查团队访问权限
    result = await db.execute(
        select(Team).where(Team.id == team_id, Team.deleted_at.is_(None))
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")

    role = await get_user_team_role(user, team_id, db)
    if not role and not user.is_system_admin:
        raise HTTPException(status_code=403, detail="您不在此团队中")

    # 成员总数
    count_result = await db.execute(
        select(func.count(TeamMember.id)).where(TeamMember.team_id == team_id)
    )
    total_members = count_result.scalar() or 0

    # Owner数量
    owner_result = await db.execute(
        select(func.count(TeamMember.id)).where(
            TeamMember.team_id == team_id,
            TeamMember.role == "owner",
        )
    )
    total_owners = owner_result.scalar() or 0

    # 主管数量
    sup_result = await db.execute(
        select(func.count(TeamMember.id)).where(
            TeamMember.team_id == team_id,
            TeamMember.role == "supervisor",
        )
    )
    total_supervisors = sup_result.scalar() or 0

    # 最近操作
    recent = await db.execute(
        select(AuditLog)
        .where(AuditLog.team_id == team_id)
        .order_by(AuditLog.created_at.desc())
        .limit(5)
    )
    activities = recent.scalars().all()

    return DashboardResponse(
        team_name=team.name,
        total_members=total_members,
        total_owners=total_owners,
        total_supervisors=total_supervisors,
        recent_activities=[
            {
                "time": str(a.created_at),
                "action": f"{a.action_type} {a.target_type}",
                "summary": a.target_summary or "",
                "operator": a.operator_name or "",
            }
            for a in activities
        ],
    )
