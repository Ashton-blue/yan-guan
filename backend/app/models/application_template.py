from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base

class ApplicationTemplate(Base):
    __tablename__ = "application_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    
    # 模板基本信息
    name = Column(String(200), nullable=False)
    policy_id = Column(Integer, ForeignKey("policy_documents.id"), nullable=True)
    template_type = Column(String(50), nullable=False)  # application/progress/final_report
    status = Column(String(20), default="active")
    
    # 模板结构
    structure = Column(JSONB, nullable=True)
    placeholder_text = Column(JSONB, nullable=True)
    
    # AI生成配置（阶段1.3新增）
    fields_schema = Column(JSONB, nullable=True)  # 模板字段定义
    ai_prompt_template = Column(Text, nullable=True)
    
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_application_templates_team', 'team_id'),
        Index('idx_application_templates_type', 'template_type'),
    )
