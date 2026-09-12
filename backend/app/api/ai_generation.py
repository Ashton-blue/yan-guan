from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import json

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

# ============ AI生成草稿 ============

@router.post("/policies/applications/{form_id}/generate")
@require_permission("ai_generate")
async def generate_draft(
    team_id: int = Query(...),
    form_id: int = ...,
    data: dict = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """AI生成申报草稿"""
    form = await db.get(ApplicationForm, form_id)
    if not form or form.team_id != team_id:
        raise HTTPException(status_code=404, detail="申报表不存在")
    
    # 检查权限：只有教师/主管可以使用AI生成
    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()
    
    if not member or member.role not in ["owner", "supervisor"]:
        raise HTTPException(status_code=403, detail="只有教师/主管可以使用AI生成草稿")
    
    # 获取模板和政策信息
    template = None
    if form.template_id:
        template_result = await db.execute(
            select(ApplicationTemplate).where(
                ApplicationTemplate.id == form.template_id,
                ApplicationTemplate.team_id == team_id
            )
        )
        template = template_result.scalar_one_or_none()
    
    policy = None
    if form.policy_id:
        policy_result = await db.execute(
            select(PolicyDocument).where(
                PolicyDocument.id == form.policy_id,
                PolicyDocument.team_id == team_id,
                PolicyDocument.is_active == True
            )
        )
        policy = policy_result.scalar_one_or_none()
    
    # 构建AI prompt
    fields_to_generate = data.get("fields", [])
    applicant_profile = data.get("applicant_profile", {})
    
    # 获取申请人信息
    applicant_result = await db.execute(select(User).where(User.id == form.applicant_id))
    applicant = applicant_result.scalar_one_or_none()
    
    # 构建prompt内容
    context_parts = []
    if policy:
        context_parts.append(f"【政策依据】\n{policy.key_requirements_desc or policy.summary or ''}")
    if template and template.ai_prompt_template:
        context_parts.append(f"【模板要求】\n{template.ai_prompt_template}")
    context_parts.append(f"\n【申请人信息】\n姓名：{applicant.name if applicant else '未知'}")
    context_parts.append(f"角色：{member.role}")
    context_parts.append(f"研究方向：{applicant_profile.get('research_interest', '未指定')}")
    context_parts.append(f"\n【项目名称】\n{form.title}")
    
    if fields_to_generate:
        context_parts.append(f"\n【需要生成的字段】\n{', '.join(fields_to_generate)}")
    else:
        # 生成所有字段
        if template and template.fields_schema:
            fields_to_generate = [f.get("key") for f in template.fields_schema]
            context_parts.append(f"\n【需要生成的字段】\n{', '.join(fields_to_generate)}")
    
    prompt = "\n".join(context_parts)
    
    # 调用AI服务
    ai_service = AIService(db, team_id)
    ai_result = await ai_service.generate_content(prompt, temperature=0.5, max_tokens=800)
    await ai_service.close()
    
    if not ai_result.get("success"):
        raise HTTPException(status_code=500, detail=f"AI生成失败: {ai_result.get('error', '未知错误')}")
    
    # 解析AI返回的内容
    generated_content = {}
    try:
        # 尝试解析JSON
        ai_response = ai_result.get("content", "")
        # 提取JSON部分
        json_match = re.search(r'\{[^}]+\}', ai_response, re.DOTALL)
        if json_match:
            generated_content = json.loads(json_match.group())
        else:
            # 如果不是JSON，尝试按字段分割
            lines = ai_response.strip().split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    generated_content[key.strip()] = value.strip()
    except Exception as e:
        generated_content = {"raw_content": ai_result.get("content", "")}
    
    # 更新表单内容
    if form.content is None:
        form.content = {}
    
    # 合并内容，标记AI生成部分
    for field_key, field_value in generated_content.items():
        if field_key in (fields_to_generate or list(form.content.keys())):
            form.content[field_key] = field_value
    
    # 设置AI生成提示
    form.ai_generated_hint = "⚠️ 以上内容为AI辅助生成，请根据实际研究情况修改完善。"
    
    await db.commit()
    
    # 记录审计日志
    await log_audit_action(
        db=db,
        team_id=team_id,
        operator_id=current_user.id,
        operator_name=current_user.name,
        operator_role=member.role,
        action_type="CREATE",
        target_type="application",
        target_id=form.id,
        target_summary=f"{form.title} - AI生成草稿",
        detail={
            "fields_generated": fields_to_generate,
            "tokens_used": ai_result.get("tokens_used", 0)
        },
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    
    return {
        "form_id": form.id,
        "generated_fields": generated_content,
        "ai_hint": form.ai_generated_hint,
        "source_policies": [{"id": policy.id, "title": policy.title}] if policy else [],
        "content": form.content,
        "tokens_used": ai_result.get("tokens_used", 0)
    }
