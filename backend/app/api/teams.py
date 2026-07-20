from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.schemas.user import TeamCreate, TeamUpdate, TeamResponse, TeamListItem
from app.middleware.auth_middleware import get_current_user
from app.middleware.permission import require_permission

router = APIRouter(prefix="/api/v1/teams", tags=["团队"])


@router.post("", response_model=TeamResponse)
async def create_team(
    req: TeamCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建团队（教师）"""
    team = Team(
        name=req.name,
        school=req.school,
        research_area=req.research_area,
        description=req.description,
        meeting_time=req.meeting_time,
        owner_id=user.id,
    )
    db.add(team)
    await db.flush()

    # 创建者自动成为团队 owner
    member = TeamMember(team_id=team.id, user_id=user.id, role="owner")
    db.add(member)
    await db.flush()

    return TeamResponse(
        id=team.id,
        name=team.name,
        school=team.school,
        research_area=team.research_area,
        description=team.description,
        meeting_time=team.meeting_time,
        is_active=team.is_active,
        owner_id=team.owner_id,
        member_count=1,
        created_at=team.created_at,
    )


@router.get("", response_model=list[TeamListItem])
async def list_my_teams(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我的团队列表"""
    result = await db.execute(
        select(TeamMember, Team).join(Team, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user.id, Team.deleted_at.is_(None))
    )
    rows = result.all()

    return [TeamListItem(id=team.id, name=team.name, role=member.role)
            for member, team in rows]


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取团队详情"""
    result = await db.execute(select(Team).where(Team.id == team_id, Team.deleted_at.is_(None)))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 检查是否团队成员
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user.id,
        )
    )
    if not member_result.scalar_one_or_none() and not user.is_system_admin:
        raise HTTPException(status_code=403, detail="您不在此团队中")

    # 成员数量
    count_result = await db.execute(
        select(func.count(TeamMember.id)).where(TeamMember.team_id == team_id)
    )
    member_count = count_result.scalar()

    return TeamResponse(
        id=team.id,
        name=team.name,
        school=team.school,
        research_area=team.research_area,
        description=team.description,
        meeting_time=team.meeting_time,
        is_active=team.is_active,
        owner_id=team.owner_id,
        member_count=member_count or 0,
        created_at=team.created_at,
    )


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    req: TeamUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新团队信息"""
    result = await db.execute(select(Team).where(Team.id == team_id, Team.deleted_at.is_(None)))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 检查是否为 owner
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user.id,
            TeamMember.role == "owner",
        )
    )
    if not member_result.scalar_one_or_none() and not user.is_system_admin:
        raise HTTPException(status_code=403, detail="仅团队教师可修改团队信息")

    if req.name is not None:
        team.name = req.name
    if req.school is not None:
        team.school = req.school
    if req.research_area is not None:
        team.research_area = req.research_area
    if req.description is not None:
        team.description = req.description
    if req.meeting_time is not None:
        team.meeting_time = req.meeting_time

    await db.flush()

    count_result = await db.execute(
        select(func.count(TeamMember.id)).where(TeamMember.team_id == team_id)
    )

    return TeamResponse(
        id=team.id,
        name=team.name,
        school=team.school,
        research_area=team.research_area,
        description=team.description,
        meeting_time=team.meeting_time,
        is_active=team.is_active,
        owner_id=team.owner_id,
        member_count=count_result.scalar() or 0,
        created_at=team.created_at,
    )
