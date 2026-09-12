from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime
from typing import List, Optional

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.middleware.permission import require_permission
from app.services.audit_service import log_audit_action
from app.models.user import User
from app.models.team_member import TeamMember
from app.models.application_template import ApplicationTemplate
from app.models.audit_log import AuditLog

router = APIRouter()

# ============ 模板管理 ============

@router.get("/policies/templates")
async def list_templates(
    team_id: int = Query(...),
    template_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取模板列表"""
    query = select(ApplicationTemplate).where(
        ApplicationTemplate.team_id == team_id
    )
    
    if template_type:
        query = query.where(ApplicationTemplate.template_type == template_type)
    if status:
        query = query.where(ApplicationTemplate.status == status)
    
    query = query.order_by(desc(ApplicationTemplate.created_at))
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return [
        {
            "id": t.id,
            "team_id": t.team_id,
            "name": t.name,
            "policy_id": t.policy_id,
            "template_type": t.template_type,
            "status": t.status,
            "fields_schema": t.fields_schema,
            "ai_prompt_template": t.ai_prompt_template,
            "created_by": t.created_by,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in templates
    ]

@router.get("/policies/templates/{template_id}")
async def get_template(
    team_id: int = Query(...),
    template_id: int = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取模板详情"""
    result = await db.execute(
        select(ApplicationTemplate).where(
            ApplicationTemplate.id == template_id,
            ApplicationTemplate.team_id == team_id
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    return {
        "id": template.id,
        "team_id": template.team_id,
        "name": template.name,
        "policy_id": template.policy_id,
        "template_type": template.template_type,
        "status": template.status,
        "structure": template.structure,
        "placeholder_text": template.placeholder_text,
        "fields_schema": template.fields_schema,
        "ai_prompt_template": template.ai_prompt_template,
        "created_by": template.created_by,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }

@router.post("/policies/templates")
@require_permission("create_template")
async def create_template(
    team_id: int = Query(...),
    data: dict = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """创建模板（教师专用）"""
    # 检查权限
    member = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role == "owner"
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="只有教师可以创建模板")
    
    template = ApplicationTemplate(
        team_id=team_id,
        name=data["name"],
        policy_id=data.get("policy_id"),
        template_type=data.get("template_type", "application"),
        status=data.get("status", "active"),
        structure=data.get("structure"),
        placeholder_text=data.get("placeholder_text"),
        fields_schema=data.get("fields_schema"),
        ai_prompt_template=data.get("ai_prompt_template"),
        created_by=current_user.id
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    
    # 记录审计日志
    await log_audit_action(
        db=db,
        team_id=team_id,
        operator_id=current_user.id,
        operator_name=current_user.name,
        operator_role="owner",
        action_type="CREATE",
        target_type="template",
        target_id=template.id,
        target_summary=template.name,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    
    return {"id": template.id, "message": "模板创建成功"}

@router.put("/policies/templates/{template_id}")
@require_permission("edit_template")
async def update_template(
    team_id: int = Query(...),
    template_id: int = ...,
    data: dict = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """更新模板"""
    template = await db.get(ApplicationTemplate, template_id)
    if not template or template.team_id != team_id:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 检查权限
    member = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role == "owner"
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="只有教师可以编辑模板")
    
    # 更新字段
    updatable_fields = ["name", "policy_id", "template_type", "status", 
                        "structure", "placeholder_text", "fields_schema", "ai_prompt_template"]
    
    for field in updatable_fields:
        if field in data:
            setattr(template, field, data[field])
    
    await db.commit()
    
    # 记录审计日志
    await log_audit_action(
        db=db,
        team_id=team_id,
        operator_id=current_user.id,
        operator_name=current_user.name,
        operator_role="owner",
        action_type="UPDATE",
        target_type="template",
        target_id=template.id,
        target_summary=template.name,
        detail={"changes": data},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    
    return {"message": "模板更新成功"}

@router.delete("/policies/templates/{template_id}")
@require_permission("delete_template")
async def delete_template(
    team_id: int = Query(...),
    template_id: int = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """删除模板"""
    template = await db.get(ApplicationTemplate, template_id)
    if not template or template.team_id != team_id:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 检查权限
    member = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role == "owner"
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="只有教师可以删除模板")
    
    await db.delete(template)
    await db.commit()
    
    # 记录审计日志
    await log_audit_action(
        db=db,
        team_id=team_id,
        operator_id=current_user.id,
        operator_name=current_user.name,
        operator_role="owner",
        action_type="DELETE",
        target_type="template",
        target_id=template.id,
        target_summary=template.name,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    
    return {"message": "模板已删除"}
