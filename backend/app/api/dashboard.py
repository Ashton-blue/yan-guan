from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.policy_document import PolicyDocument
from app.models.application_form import ApplicationForm
from app.models.policy_qa_session import PolicyQASession

router = APIRouter()

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取仪表盘统计数据"""
    # 检查成员资格
    member = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True
        )
    )
    if not member.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权访问此团队数据")
    
    # 统计各类数据
    policy_count = await db.execute(
        select(func.count()).where(
            PolicyDocument.team_id == team_id,
            PolicyDocument.is_active == True
        )
    )
    
    application_count = await db.execute(
        select(func.count()).where(
            ApplicationForm.team_id == team_id
        )
    )
    
    draft_count = await db.execute(
        select(func.count()).where(
            ApplicationForm.team_id == team_id,
            ApplicationForm.status == "draft"
        )
    )
    
    upcoming_count = await db.execute(
        select(func.count()).where(
            ApplicationForm.team_id == team_id,
            ApplicationForm.status.in_(["draft", "submitted"]),
            ApplicationForm.submission_deadline >= datetime.utcnow(),
            ApplicationForm.submission_deadline <= datetime.utcnow() + timedelta(days=7)
        )
    )
    
    qa_count = await db.execute(
        select(func.count()).where(
            PolicyQASession.team_id == team_id
        )
    )
    
    return {
        "policy_count": policy_count.scalar(),
        "application_count": application_count.scalar(),
        "draft_count": draft_count.scalar(),
        "upcoming_deadline_count": upcoming_count.scalar(),
        "qa_session_count": qa_count.scalar(),
        "team_id": team_id,
        "user_id": current_user.id,
        "user_name": current_user.name
    }
