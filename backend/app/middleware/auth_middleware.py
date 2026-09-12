from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.team_member import TeamMember
from app.utils.jwt import decode_token, get_subject

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    # 这里可以添加更多活跃状态检查
    return current_user

async def get_team_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    team_id: int = None
) -> dict:
    """获取用户在指定团队的上下文信息"""
    if not team_id:
        # 获取用户第一个团队
        result = await db.execute(
            select(TeamMember).where(
                TeamMember.user_id == current_user.id,
                TeamMember.is_active == True
            ).order_by(TeamMember.created_at).limit(1)
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=400, detail="用户未加入任何团队")
        team_id = member.team_id
    
    # 获取团队信息
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=403, detail="无权访问此团队")
    
    return {
        "user": current_user,
        "team_id": team_id,
        "role": member.role,
        "member": member
    }
