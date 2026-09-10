from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base

class PolicyQASession(Base):
    __tablename__ = "policy_qa_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    source_policies = Column(JSONB, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    model_used = Column(String(50), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_policy_qa_sessions_team', 'team_id'),
        Index('idx_policy_qa_sessions_user', 'user_id'),
        Index('idx_policy_qa_sessions_time', created_at.desc()),
    )
