from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from datetime import datetime
from app.models.audit_log import AuditLog

async def log_audit_action(
    db: AsyncSession,
    team_id: int,
    operator_id: int,
    operator_name: str,
    operator_role: str,
    action_type: str,
    target_type: str,
    target_id: int,
    target_summary: str = "",
    detail: dict = None,
    ip_address: str = None,
    user_agent: str = None,
    result: str = "SUCCESS"
):
    """记录审计日志"""
    log = AuditLog(
        team_id=team_id,
        operator_id=operator_id,
        operator_name=operator_name,
        operator_role=operator_role,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        target_summary=target_summary[:500] if target_summary else None,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
        result=result,
        created_at=datetime.utcnow()
    )
    db.add(log)
    await db.commit()
    return log
