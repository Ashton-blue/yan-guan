from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="登录账号（学号/工号）")
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=False, comment="显示姓名")
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_system_admin = Column(Boolean, default=False, comment="系统管理员标识")
    must_change_password = Column(Boolean, default=False, comment="首次登录强制改密")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
