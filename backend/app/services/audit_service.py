from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.models.audit_log import AuditLog
from app.models.user import User


async def create_audit_log(
    db: AsyncSession,
    *,
    team_id: Optional[int] = None,
    operator: User,
    operator_role: Optional[str] = None,
    action_type: str,
    target_type: str,
    target_id: Optional[int] = None,
    target_summary: Optional[str] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    result: str = "SUCCESS",
) -> AuditLog:
    """写审计日志（仅追加，不提供更新/删除接口）"""
    log = AuditLog(
        team_id=team_id,
        operator_id=operator.id,
        operator_name=operator.display_name,
        operator_role=operator_role,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        target_summary=target_summary,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
        result=result,
    )
    db.add(log)
    await db.flush()
    return log


async def query_audit_logs(
    db: AsyncSession,
    *,
    team_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    """查询审计日志（仅供系统管理员）"""
    conditions = []
    if team_id:
        conditions.append(AuditLog.team_id == team_id)

    # 查询总数
    count_q = select(func.count(AuditLog.id))
    if conditions:
        count_q = count_q.where(*conditions)
    total = await db.execute(count_q)
    total_count = total.scalar()

    # 查询列表
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if conditions:
        q = q.where(*conditions)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    logs = result.scalars().all()

    return list(logs), total_count or 0
