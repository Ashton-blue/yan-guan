from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.team_member import TeamMember
from app.models.application_form import ApplicationForm

router = APIRouter()

@router.get("/policies/applications/reminders")
async def get_application_reminders(
    team_id: int = Query(...),
    days_ahead: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取即将到期的申报提醒"""
    # 检查用户角色
    member_result = await db.execute(
        select(TeamMember.role).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        )
    )
    role = member_result.scalar_one_or_none()
    
    # 构建查询：查询7天内到期的草稿和已提交的申报
    now = datetime.utcnow()
    deadline_range = now + timedelta(days=days_ahead)
    
    query = select(ApplicationForm).where(
        ApplicationForm.team_id == team_id,
        ApplicationForm.status.in_(["draft", "submitted"]),
        ApplicationForm.submission_deadline >= now,
        ApplicationForm.submission_deadline <= deadline_range
    ).order_by(ApplicationForm.submission_deadline)
    
    # 学生只能查看自己的
    if role in ["student", "collaborator", "temp_student"]:
        query = query.where(ApplicationForm.applicant_id == current_user.id)
    
    result = await db.execute(query)
    forms = result.scalars().all()
    
    # 获取申请人信息
    reminders = []
    for form in forms:
        applicant_result = await db.execute(select(User).where(User.id == form.applicant_id))
        applicant = applicant_result.scalar_one_or_none()
        
        days_left = (form.submission_deadline - now).days
        
        reminders.append({
            "form_id": form.id,
            "title": form.title,
            "applicant_id": form.applicant_id,
            "applicant_name": applicant.name if applicant else "未知",
            "deadline": form.submission_deadline.isoformat(),
            "days_left": days_left,
            "status": form.status,
            "is_urgent": days_left <= 3,  # 3天内为紧急
            "created_at": form.created_at.isoformat() if form.created_at else None
        })
    
    return {
        "upcoming": reminders,
        "total": len(reminders),
        "query_period_days": days_ahead,
        "query_time": now.isoformat()
    }
