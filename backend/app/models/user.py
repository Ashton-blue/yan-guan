from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    must_change_password = Column(Boolean, default=True)
    # P0 批次 A：账户管理扩展字段
    avatar_url = Column(String(500), nullable=True)
    research_area = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    status = Column(String(20), default="active")  # active / disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_users_email', 'email'),
    )
