from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operator_name = Column(String(100), nullable=False)
    operator_role = Column(String(50), nullable=False)
    action_type = Column(String(20), nullable=False)  # CREATE/UPDATE/DELETE
    target_type = Column(String(50), nullable=False)
    target_id = Column(Integer, nullable=False)
    target_summary = Column(String(500), nullable=True)
    detail = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    result = Column(String(20), default="SUCCESS")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_audit_logs_team', 'team_id'),
        Index('idx_audit_logs_time', Column('created_at', DateTime).desc()),
    )
