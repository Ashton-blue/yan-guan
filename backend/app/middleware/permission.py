from functools import wraps
from fastapi import HTTPException, status
from typing import List

# 角色权限映射
ROLE_PERMISSIONS = {
    "owner": ["create_template", "edit_template", "delete_template", "view_all_applications",
              "edit_all_applications", "ai_generate", "manage_templates"],
    "supervisor": ["view_all_applications", "edit_all_applications", "ai_generate"],
    "co_manager": ["view_all_applications"],
    "student": ["view_own_applications", "edit_own_applications"],
    "collaborator": ["view_own_applications", "edit_own_applications"],
    "temp_student": ["view_own_applications", "edit_own_applications"]
}

def require_permission(*permissions):
    """权限装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取team_context
            team_context = kwargs.get("team_context")
            if not team_context:
                # 尝试从args中获取
                for arg in args:
                    if hasattr(arg, 'role'):
                        team_context = {"role": arg.role}
                        break
            
            if not team_context:
                raise HTTPException(status_code=401, detail="未提供团队上下文")
            
            role = team_context.get("role", "")
            allowed_permissions = ROLE_PERMISSIONS.get(role, [])
            
            for perm in permissions:
                if perm not in allowed_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"无权执行此操作：{perm}"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def check_teacher_only(role: str) -> bool:
    """检查是否为教师角色（owner或supervisor）"""
    return role in ["owner", "supervisor"]

def check_student_only(role: str) -> bool:
    """检查是否为学生角色"""
    return role in ["student", "collaborator", "temp_student"]

# ============ P0 批次 A：权限升级为「按团队查库校验」 ============
# 旧的 require_permission 是静态映射（供 policies 等历史模块沿用，不破坏）；
# 新增以下查库依赖，后端统一校验、越权返回 403，前端仅做显隐不能绕过。
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.team_member import TeamMember

TEACHER_ROLES = ("owner", "supervisor", "co_manager")
STUDENT_ROLES = ("student", "collaborator", "temp_student")
ALL_ROLES = TEACHER_ROLES + STUDENT_ROLES

async def get_team_member(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TeamMember:
    """查库确认当前用户是该团队的活跃成员，返回成员记录；否则 403。"""
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="无权访问此团队")
    return member

def require_team_role(*roles):
    """按团队查库校验角色：确认成员角色在 roles 内，否则 403。

    用法（在路由上）：
        member: TeamMember = Depends(require_team_role(*TEACHER_ROLES))
    team_id 从路径或 query 自动注入，member 携带真实 role。
    """
    async def _check(
        team_id: int,
        member: TeamMember = Depends(get_team_member),
    ) -> TeamMember:
        if member.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"需要角色 {('/'.join(roles))}，当前 {member.role} 无此权限",
            )
        return member
    return _check
