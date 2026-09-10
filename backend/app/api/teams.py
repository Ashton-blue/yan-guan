from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.schemas.user import UserOut

router = APIRouter()

@router.post("/teams")
async def create_team(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建团队"""
    team = Team(
        name=data.get("name"),
        description=data.get("description", ""),
        created_by=current_user.id
    )
    db.add(team)
    await db.flush()
    
    # 创建者设为owner
    member = TeamMember(
        team_id=team.id,
        user_id=current_user.id,
        role="owner"
    )
    db.add(member)
    await db.commit()
    await db.refresh(team)
    
    return {"id": team.id, "name": team.name, "description": team.description}

@router.get("/teams")
async def list_teams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户所在团队列表"""
    result = await db.execute(
        select(Team, TeamMember.role).join(TeamMember).where(
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True,
            Team.is_active == True
        )
    )
    teams = result.all()
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "role": role,
            "created_at": t.created_at
        }
        for t, role in teams
    ]

@router.get("/teams/{team_id}")
async def get_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取团队详情"""
    result = await db.execute(
        select(Team).where(Team.id == team_id, Team.is_active == True)
    )
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    
    # 检查用户是否在团队中
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True
        )
    )
    member = member_result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=403, detail="无权访问此团队")
    
    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "role": member.role,
        "created_at": team.created_at
    }

@router.put("/teams/{team_id}")
async def update_team(
    team_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新团队信息"""
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role == "owner"
        )
    )
    member = member_result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=403, detail="只有团队所有者可以修改团队信息")
    
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    
    if "name" in data:
        team.name = data["name"]
    if "description" in data:
        team.description = data["description"]
    
    await db.commit()
    return {"message": "团队信息已更新"}

@router.delete("/teams/{team_id}")
async def delete_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除团队（软删除）"""
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role == "owner"
        )
    )
    member = member_result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=403, detail="只有团队所有者可以删除团队")
    
    team = await db.get(Team, team_id)
    if team:
        team.is_active = False
        await db.commit()
    
    return {"message": "团队已删除"}
