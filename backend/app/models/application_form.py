from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base

class ApplicationForm(Base):
    __tablename__ = "application_forms"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(Integer, ForeignKey("application_templates.id"), nullable=True)
    policy_id = Column(Integer, ForeignKey("policy_documents.id"), nullable=True)
    
    # 申报基本信息
    title = Column(String(500), nullable=False)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="draft")  # draft/submitted/reviewed/awarded/failed
    submission_deadline = Column(DateTime, nullable=True)
    
    # 内容
    content = Column(JSONB, nullable=True)
    ai_generated_hint = Column(Text, nullable=True)
    
    # 时间线
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    awarded_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_application_forms_team', 'team_id'),
        Index('idx_application_forms_applicant', 'applicant_id'),
        Index('idx_application_forms_status', 'status'),
        Index('idx_application_forms_deadline', 'submission_deadline', postgresql_where="status IN ('draft', 'submitted')"),
    )
