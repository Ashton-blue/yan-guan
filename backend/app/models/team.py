from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, func
from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="团队名称")
    school = Column(String(200), comment="所属院校")
    research_area = Column(String(500), comment="研究领域")
    description = Column(Text, nullable=True)
    meeting_time = Column(String(100), comment="组会时间")
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"), comment="团队创建者（教师）")
    deleted_at = Column(DateTime(timezone=True), nullable=True, comment="软删除时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
