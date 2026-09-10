from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, UniqueConstraint
from datetime import datetime
from app.database import Base

class AiModelKey(Base):
    __tablename__ = "ai_model_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    service = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    api_key = Column(Text, nullable=False)
    base_url = Column(String(500), default="https://api.deepseek.com")
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('team_id', 'service', 'model', name='uq_ai_model_keys_unique'),
    )
