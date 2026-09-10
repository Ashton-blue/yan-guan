from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from datetime import datetime
from app.database import Base


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(50), nullable=False)  # owner/supervisor/co_manager/student/collaborator/temp_student
    invited_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index('idx_team_members_team', 'team_id'),
        Index('idx_team_members_user', 'user_id'),
        Index('idx_team_members_role', 'team_id', 'role'),
    )
