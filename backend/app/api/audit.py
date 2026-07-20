from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import AuditLogResponse, AuditLogDetail
from app.middleware.auth_middleware import get_current_user
from app.services.audit_service import query_audit_logs

router = APIRouter(prefix="/api/v1/audit-logs", tags=["审计日志"])


@router.get("", response_model=dict)
async def list_audit_logs(
    team_id: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询审计日志（仅系统管理员）"""
    if not user.is_system_admin:
        raise HTTPException(status_code=403, detail="仅系统管理员可查看审计日志")

    logs, total = await query_audit_logs(
        db, team_id=team_id, limit=limit, offset=offset
    )

    return {
        "items": [AuditLogDetail.model_validate(log) for log in logs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
