from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from datetime import datetime
from app.database import Base

class TeamInvite(Base):
    """团队邀请码：支持用户凭码加入团队（账户管理 · 团队与成员）"""
    __tablename__ = "team_invites"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(64), unique=True, index=True, nullable=False)
    role = Column(String(50), default="student")  # 受邀加入后的角色
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="active")  # active / used / expired
    used_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_team_invites_team', 'team_id'),
        Index('idx_team_invites_code', 'code'),
    )
