from functools import wraps
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.team_member import TeamMember
from app.models.permission import RolePermission


async def get_team_id_from_request(request: Request) -> int | None:
    """从请求路径中提取 team_id"""
    team_id = request.path_params.get("team_id")
    if team_id is not None:
        return int(team_id)
    return None


async def has_permission(role: str, permission_code: str, db: AsyncSession) -> bool:
    """检查角色是否有指定权限"""
    # 系统管理员拥有所有权限
    # owner（教师）拥有本团队所有权限
    if role == "owner":
        return True

    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role == role,
            RolePermission.permission_code == permission_code,
        )
    )
    return result.scalar_one_or_none() is not None


def require_permission(permission_code: str):
    """权限校验装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user: User = kwargs.get("user") or request.state.user
            db: AsyncSession = kwargs.get("db") or request.state.db

            if user is None or db is None:
                raise HTTPException(status_code=500, detail="权限校验上下文缺失")

            # 系统管理员绕过权限检查
            if user.is_system_admin:
                return await func(*args, **kwargs)

            team_id = await get_team_id_from_request(request)
            if team_id is None:
                # 某些操作不需要团队上下文（如创建团队）
                return await func(*args, **kwargs)

            # 查询用户在团队中的角色
            result = await db.execute(
                select(TeamMember).where(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == user.id,
                )
            )
            member = result.scalar_one_or_none()
            if member is None:
                raise HTTPException(status_code=403, detail="您不在此团队中")

            # 检查权限
            if not await has_permission(member.role, permission_code, db):
                raise HTTPException(status_code=403, detail="权限不足")

            return await func(*args, **kwargs)
        return wrapper
    return decorator
