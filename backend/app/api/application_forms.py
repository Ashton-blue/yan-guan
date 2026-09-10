from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
from typing import List, Optional

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.middleware.permission import require_permission
from app.services.audit_service import log_audit_action
from app.services.ai_policy import AIService
from app.models.user import User
from app.models.team_member import TeamMember
from app.models.policy_document import PolicyDocument
from app.models.application_template import ApplicationTemplate
from app.models.application_form import ApplicationForm

router = APIRouter()

# ============ 申报表管理 ============

@router.get("/policies/applications")
async def list_applications(
    team_id: int = Query(...),
    status: Optional[str] = Query(None),
    template_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取申报表列表"""
    # 检查用户角色
    member_result = await db.execute(
        select(TeamMember.role).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        )
    )
    role = member_result.scalar_one_or_none()
    
    # 构建查询
    query = select(ApplicationForm).where(ApplicationForm.team_id == team_id)
    
    # 学生只能查看自己的申报
    if role in ["student", "collaborator", "temp_student"]:
        query = query.where(ApplicationForm.applicant_id == current_user.id)
    
    if status:
        query = query.where(ApplicationForm.status == status)
    if template_id:
        query = query.where(ApplicationForm.template_id == template_id)
    
    query = query.order_by(desc(ApplicationForm.created_at))
    
    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    forms = result.scalars().all()
    
    # 获取总数
    count_query = select(ApplicationForm).where(ApplicationForm.team_id == team_id)
    if role in ["student", "collaborator", "temp_student"]:
        count_query = count_query.where(ApplicationForm.applicant_id == current_user.id)
    if status:
        count_query = count_query.where(ApplicationForm.status == status)
    if template_id:
        count_query = count_query.where(ApplicationForm.template_id == template_id)
    
    count_result = await db.execute(select(func.count()).select_from(count_query.subquery()))
    total = count_result.scalar()
    
    return {
        "items": [
            {
                "id": f.id,
                "team_id": f.team_id,
                "template_id": f.template_id,
                "policy_id": f.policy_id,
                "title": f.title,
                "applicant_id": f.applicant_id,
                "applicant_name": f.applicant.name if hasattr(f, 'applicant') else None,
                "status": f.status,
                "submission_deadline": f.submission_deadline.isoformat() if f.submission_deadline else None,
                "content": f.content,
                "ai_generated_hint": f.ai_generated_hint,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "updated_at": f.updated_at.isoformat() if f.updated_at else None,
                "submitted_at": f.submitted_at.isoformat() if f.submitted_at else None,
            }
            for f in forms
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/policies/applications/{form_id}")
async def get_application(
    team_id: int = Query(...),
    form_id: int = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取申报表详情"""
    result = await db.execute(
        select(ApplicationForm, TeamMember.role).join(
            TeamMember, TeamMember.user_id == ApplicationForm.applicant_id
        ).where(
            ApplicationForm.id == form_id,
            ApplicationForm.team_id == team_id
        )
    )
    form_row = result.first()
    
    if not form_row:
        raise HTTPException(status_code=404, detail="申报表不存在")
    
    form, applicant_role = form_row
    
    # 权限检查：学生只能查看自己的
    if applicant_role in ["student", "collaborator", "temp_student"] and form.applicant_id != current_user.id:
        # 再检查当前用户是否有权限
        current_member = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == current_user.id
            )
        )
        current_role = current_member.scalar_one_or_none()
        if not current_role or current_role.role not in ["owner", "supervisor", "co_manager"]:
            raise HTTPException(status_code=403, detail="无权查看此申报表")
    
    # 获取申请人信息
    applicant_result = await db.execute(select(User).where(User.id == form.applicant_id))
    applicant = applicant_result.scalar_one_or_none()
    
    return {
        "id": form.id,
        "team_id": form.team_id,
        "template_id": form.template_id,
        "policy_id": form.policy_id,
        "title": form.title,
        "applicant_id": form.applicant_id,
        "applicant_name": applicant.name if applicant else None,
        "applicant_email": applicant.email if applicant else None,
        "status": form.status,
        "submission_deadline": form.submission_deadline.isoformat() if form.submission_deadline else None,
        "content": form.content,
        "ai_generated_hint": form.ai_generated_hint,
        "created_at": form.created_at.isoformat() if form.created_at else None,
        "updated_at": form.updated_at.isoformat() if form.updated_at else None,
        "submitted_at": form.submitted_at.isoformat() if form.submitted_at else None,
        "awarded_at": form.awarded_at.isoformat() if form.awarded_at else None,
    }

@router.post("/policies/applications")
async def create_application(
    team_id: int = Query(...),
    data: dict = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """创建申报表"""
    template_id = data.get("template_id")
    
    # 获取模板信息（如果提供）
    template = None
    if template_id:
        template_result = await db.execute(
            select(ApplicationTemplate).where(
                ApplicationTemplate.id == template_id,
                ApplicationTemplate.team_id == team_id
            )
        )
        template = template_result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
    
    # 确定申请人
    applicant_id = data.get("applicant_id", current_user.id)
    
    # 学生只能为自己创建申报
    member_result = await db.execute(
        select(TeamMember.role).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        )
    )
    role = member_result.scalar_one_or_none()
    
    if role in ["student", "collaborator", "temp_student"] and applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="学生只能为自己创建申报表")
    
    # 创建申报表
    form = ApplicationForm(
        team_id=team_id,
        template_id=template_id,
        policy_id=template.policy_id if template else data.get("policy_id"),
        title=data["title"],
        applicant_id=applicant_id,
        status="draft",
        content=data.get("content", {}),
        submission_deadline=datetime.fromisoformat(data["submission_deadline"]) if data.get("submission_deadline") else None,
    )
    db.add(form)
    await db.commit()
    await db.refresh(form)
    
    # 如果模板有fields_schema，初始化内容结构
    if template and template.fields_schema:
        initial_content = {}
        for field in template.fields_schema:
            initial_content[field.get("key", "")] = ""
        form.content = initial_content
        await db.commit()
    
    # 记录审计日志
    await log_audit_action(
        db=db,
        team_id=team_id,
        operator_id=current_user.id,
        operator_name=current_user.name,
        operator_role=role or "unknown",
        action_type="CREATE",
        target_type="application",
        target_id=form.id,
        target_summary=form.title,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    
    return {
        "id": form.id,
        "message": "申报表创建成功",
        "form": {
            "id": form.id,
            "title": form.title,
            "status": form.status,
            "content": form.content,
        }
    }

@router.put("/policies/applications/{form_id}")
async def update_application(
    team_id: int = Query(...),
    form_id: int = ...,
    data: dict = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """更新申报表"""
    form = await db.get(ApplicationForm, form_id)
    if not form or form.team_id != team_id:
        raise HTTPException(status_code=404, detail="申报表不存在")
    
    # 检查权限
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=403, detail="不是团队成员")
    
    # 学生只能编辑自己的申报
    if member.role in ["student", "collaborator", "temp_student"] and form.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己的申报表")
    
    # 已提交的申报不允许编辑
    if form.status == "submitted":
        raise HTTPException(status_code=400, detail="已提交的申报不能编辑")
    
    # 更新字段
    updatable_fields = ["title", "content", "submission_deadline", "ai_generated_hint"]
    for field in updatable_fields:
        if field in data:
            setattr(form, field, data[field])
    
    await db.commit()
    await db.refresh(form)
    
    # 记录审计日志
    await log_audit_action(
        db=db,
        team_id=team_id,
        operator_id=current_user.id,
        operator_name=current_user.name,
        operator_role=member.role,
        action_type="UPDATE",
        target_type="application",
        target_id=form.id,
        target_summary=form.title,
        detail={"changes": data},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    
    return {"message": "申报表已更新", "form_id": form.id}

@router.post("/policies/applications/{form_id}/submit")
async def submit_application(
    team_id: int = Query(...),
    form_id: int = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """提交申报表"""
    form = await db.get(ApplicationForm, form_id)
    if not form or form.team_id != team_id:
        raise HTTPException(status_code=404, detail="申报表不存在")
    
    # 检查权限
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=403, detail="不是团队成员")
    
    # 学生只能提交自己的申报
    if member.role in ["student", "collaborator", "temp_student"] and form.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能提交自己的申报表")
    
    # 更新状态
    form.status = "submitted"
    form.submitted_at = datetime.utcnow()
    await db.commit()
    
    # 记录审计日志
    await log_audit_action(
        db=db,
        team_id=team_id,
        operator_id=current_user.id,
        operator_name=current_user.name,
        operator_role=member.role,
        action_type="UPDATE",
        target_type="application",
        target_id=form.id,
        target_summary=f"{form.title} - 已提交",
        detail={"status": "submitted"},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    
    return {"message": "申报表已提交", "form_id": form.id}
