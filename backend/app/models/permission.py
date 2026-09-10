from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Index
from datetime import datetime
from app.database import Base

class Permission(Base):
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(50), nullable=False)  # owner/supervisor/co_manager/student
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_permissions_team_user', 'team_id', 'user_id', unique=True),
        Index('idx_permissions_role', 'team_id', 'role'),
    )
