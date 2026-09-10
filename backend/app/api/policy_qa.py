from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime, timedelta
from typing import List, Optional
import json
import re

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.services.audit_service import log_audit_action
from app.services.ai_policy import AIService
from app.models.user import User
from app.models.policy_document import PolicyDocument
from app.models.policy_qa_session import PolicyQASession
from app.models.application_template import ApplicationTemplate
from app.models.application_form import ApplicationForm

router = APIRouter()

# ============ 智能问答 ============

@router.post("/policies/qa")
async def ask_question(
    team_id: int = Query(...),
    data: dict = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """政策问答"""
    question = data.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    # 检索相关政策（ILIKE）
    like_pattern = f"%{question}%"
    search_fields = [
        PolicyDocument.title.ilike(like_pattern),
        PolicyDocument.summary.ilike(like_pattern),
        PolicyDocument.key_requirements_desc.ilike(like_pattern)
    ]
    
    result = await db.execute(
        select(PolicyDocument).where(
            PolicyDocument.team_id == team_id,
            PolicyDocument.is_active == True,
            *search_fields
        ).order_by(desc(PolicyDocument.publish_date)).limit(5)
    )
    policies = result.scalars().all()
    
    # 调用AI生成回答
    ai_service = AIService(db, team_id)
    
    if not policies:
        answer = "抱歉，政策库中暂未找到与您问题相关的信息。建议您联系科研管理部门获取准确信息。"
        confidence = 0
        sources = []
    else:
        # 构建prompt
        sources_text = "\n\n".join([
            f"【{p.title}】({p.official_source_url or '无链接'})\n{p.summary or ''}\n关键要求：{p.key_requirements_desc or ''}"
            for p in policies
        ])
        
        prompt = f"""你是科研政策助手。请根据以下政策库内容，回答用户问题。

用户问题：{question}

相关政策库内容：
{sources_text}

要求：
1. 回答必须基于上述政策内容，不得编造
2. 标注每个结论的政策来源
3. 如政策库中没有相关信息，明确告知用户
4. 语言简洁专业
5. 回答末尾附上"⚠️ AI辅助生成，仅供参考"声明
"""
        
        ai_result = await ai_service.generate_content(prompt, temperature=0.3, max_tokens=1000)
        answer = ai_result.get("content", "生成失败")
        confidence = 85
        sources = [
            {"id": p.id, "title": p.title, "url": p.official_source_url, "authority": p.issuing_authority}
            for p in policies
        ]
    
    # 保存问答历史
    session = PolicyQASession(
        team_id=team_id,
        user_id=current_user.id,
        question=question,
        answer=answer,
        source_policies=sources,
        confidence_score=confidence,
        model_used="deepseek-chat",
        tokens_used=ai_result.get("tokens_used", 0) if 'ai_result' in dir() else None
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence / 100,
        "model_used": "deepseek-chat",
        "tokens_used": session.tokens_used,
        "session_id": session.id,
        "follow_up_questions": [
            f"{question}的适用对象是谁？",
            f"{question}的截止时间是什么时候？",
            f"{question}的材料要求有哪些？"
        ]
    }

@router.get("/policies/qa/sessions")
async def list_qa_sessions(
    team_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取问答历史"""
    # 学生只能查看自己的问答
    member = await db.execute(
        select(TeamMember.role).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        )
    )
    role = member.scalar_one_or_none() or "student"
    
    if role in ["student", "collaborator", "temp_student"]:
        query = select(PolicyQASession).where(
            PolicyQASession.team_id == team_id,
            PolicyQASession.user_id == current_user.id
        ).order_by(desc(PolicyQASession.created_at))
    else:
        query = select(PolicyQASession).where(
            PolicyQASession.team_id == team_id
        ).order_by(desc(PolicyQASession.created_at))
    
    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    # 获取总数
    count_query = select(func.count()).select_from(
        select(PolicyQASession).where(
            PolicyQASession.team_id == team_id,
            *([] if role in ["owner", "supervisor", "co_manager"] else [PolicyQASession.user_id == current_user.id])
        ).subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    return {
        "items": [
            {
                "id": s.id,
                "question": s.question,
                "answer": s.answer[:100] + "..." if len(s.answer) > 100 else s.answer,
                "source_policies": s.source_policies,
                "confidence": s.confidence_score / 100 if s.confidence_score else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "is_own": s.user_id == current_user.id
            }
            for s in sessions
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.delete("/policies/qa/sessions/{session_id}")
async def delete_qa_session(
    team_id: int = Query(...),
    session_id: int = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """删除问答记录"""
    session = await db.get(PolicyQASession, session_id)
    if not session or session.team_id != team_id:
        raise HTTPException(status_code=404, detail="问答记录不存在")
    
    # 检查权限
    member = await db.execute(
        select(TeamMember.role).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        )
    )
    role = member.scalar_one_or_none()
    
    if role not in ["owner", "supervisor"] and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此问答记录")
    
    await db.delete(session)
    await db.commit()
    
    return {"message": "问答记录已删除"}

# ============ AI Key 管理 ============

@router.get("/policies/ai-key/status")
async def get_ai_key_status(
    team_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取AI Key配置状态"""
    member = await db.execute(
        select(TeamMember.role).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        )
    )
    role = member.scalar_one_or_none()
    
    if role not in ["owner", "supervisor"]:
        raise HTTPException(status_code=403, detail="只有教师可以配置AI Key")
    
    result = await db.execute(
        select(AiModelKey).where(
            AiModelKey.team_id == team_id,
            AiModelKey.service == "deepseek",
            AiModelKey.is_active == True
        )
    )
    key_record = result.scalar_one_or_none()
    
    if key_record:
        # 脱敏返回
        masked_key = key_record.api_key[:4] + "****" + key_record.api_key[-4:] if len(key_record.api_key) > 8 else "****"
        return {
            "configured": True,
            "service": key_record.service,
            "model": key_record.model,
            "masked_key": masked_key,
            "base_url": key_record.base_url,
            "created_at": key_record.created_at.isoformat() if key_record.created_at else None
        }
    else:
        return {"configured": False}

@router.post("/policies/ai-key")
async def save_ai_key(
    team_id: int = Query(...),
    data: dict = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """保存AI Key"""
    member = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role == "owner"
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="只有教师可以配置AI Key")
    
    api_key = data.get("api_key", "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key不能为空")
    
    # 查找或创建记录
    existing = await db.execute(
        select(AiModelKey).where(
            AiModelKey.team_id == team_id,
            AiModelKey.service == "deepseek",
            AiModelKey.model == "deepseek-chat"
        )
    )
    key_record = existing.scalar_one_or_none()
    
    if key_record:
        key_record.api_key = api_key
        key_record.base_url = data.get("base_url", "https://api.deepseek.com")
        key_record.updated_at = datetime.utcnow()
    else:
        key_record = AiModelKey(
            team_id=team_id,
            service="deepseek",
            model="deepseek-chat",
            api_key=api_key,
            base_url=data.get("base_url", "https://api.deepseek.com"),
            created_by=current_user.id
        )
        db.add(key_record)
    
    await db.commit()
    
    # 记录审计日志
    await log_audit_action(
        db=db,
        team_id=team_id,
        operator_id=current_user.id,
        operator_name=current_user.name,
        operator_role="owner",
        action_type="UPDATE",
        target_type="ai_key",
        target_id=key_record.id,
        target_summary="DeepSeek API Key配置",
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    
    return {"message": "AI Key已保存"}

@router.post("/policies/ai-key/test")
async def test_ai_key(
    team_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """测试AI Key连通性"""
    service = AIService(db, team_id)
    try:
        result = await service.generate_content("你好，请回复OK", temperature=0, max_tokens=10)
        await service.close()
        
        if result.get("success"):
            return {"connected": True, "model": result.get("model")}
        else:
            return {"connected": False, "error": result.get("content", "未知错误")}
    except Exception as e:
        return {"connected": False, "error": str(e)}

@router.delete("/policies/ai-key")
async def delete_ai_key(
    team_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """删除AI Key"""
    member = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role == "owner"
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="只有教师可以删除AI Key")
    
    result = await db.execute(
        select(AiModelKey).where(
            AiModelKey.team_id == team_id,
            AiModelKey.service == "deepseek"
        )
    )
    key_record = result.scalar_one_or_none()
    
    if key_record:
        await db.delete(key_record)
        await db.commit()
    
    return {"message": "AI Key已删除"}
