from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from app.database import Base


class PermissionConfig(Base):
    """权限定义"""
    __tablename__ = "permission_config"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, comment="权限编码 e.g. member.create")
    name = Column(String(100), nullable=False, comment="权限名称")
    module = Column(String(50), nullable=False, comment="所属模块")
    description = Column(String(500), nullable=True)


class RolePermission(Base):
    """角色-权限映射"""
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20), nullable=False, comment="owner/supervisor/co_manager/student")
    permission_code = Column(String(100), ForeignKey("permission_config.code"), nullable=False)

    __table_args__ = (
        UniqueConstraint("role", "permission_code", name="uq_role_permission"),
    )
