from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base

class PolicyDocument(Base):
    __tablename__ = "policy_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    
    # 政策基本信息
    title = Column(String(500), nullable=False)
    issuing_authority = Column(String(200), nullable=False)
    publish_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    expire_date = Column(DateTime, nullable=True)
    category = Column(String(100), nullable=False)
    
    # 内容
    summary = Column(Text, nullable=True)
    key_requirements = Column(JSONB, nullable=True)
    key_requirements_desc = Column(Text, nullable=True)
    application_link = Column(String(500), nullable=True)
    official_source_url = Column(String(500), nullable=True)
    
    # AI辅助字段
    embedding_vector = Column(Text, nullable=True)
    ai_tagged_keywords = Column(JSONB, nullable=True)
    
    # 元数据
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_policy_documents_team', 'team_id'),
        Index('idx_policy_documents_category', 'category'),
        Index('idx_policy_documents_active', 'is_active'),
        Index('idx_policy_documents_publish', publish_date.desc()),
    )
