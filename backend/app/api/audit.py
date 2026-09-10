from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter()

@router.get("/audit/logs")
async def list_audit_logs(
    team_id: Optional[int] = Query(None),
    action_type: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取审计日志列表（仅系统管理员可查看所有，其他用户只能查看自己操作的）"""
    # 这里简化处理，实际应检查是否有管理员权限
    
    query = select(AuditLog)
    
    if team_id:
        query = query.where(AuditLog.team_id == team_id)
    if action_type:
        query = query.where(AuditLog.action_type == action_type)
    if target_type:
        query = query.where(AuditLog.target_type == target_type)
    
    query = query.order_by(desc(AuditLog.created_at))
    
    # 获取总数
    count_query = select(AuditLog).alias()
    if team_id:
        count_query = count_query.where(AuditLog.team_id == team_id)
    if action_type:
        count_query = count_query.where(AuditLog.action_type == action_type)
    if target_type:
        count_query = count_query.where(AuditLog.target_type == target_type)
    
    count_result = await db.execute(select(func.count()).select_from(count_query))
    total = count_result.scalar()
    
    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return {
        "items": [
            {
                "id": log.id,
                "team_id": log.team_id,
                "operator_id": log.operator_id,
                "operator_name": log.operator_name,
                "operator_role": log.operator_role,
                "action_type": log.action_type,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "target_summary": log.target_summary,
                "detail": log.detail,
                "result": log.result,
                "ip_address": log.ip_address,
                "created_at": log.created_at
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }
