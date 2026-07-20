from sqlalchemy import Column, Integer, BigInteger, String, DateTime, JSON, ForeignKey, func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, comment="归属团队")
    operator_id = Column(Integer, ForeignKey("users.id"), comment="操作人")
    operator_name = Column(String(100), comment="操作人姓名（冗余）")
    operator_role = Column(String(20), comment="操作发生时该用户在团队的角色")
    action_type = Column(String(50), nullable=False, comment="CREATE/UPDATE/DELETE/LOGIN/EXPORT")
    target_type = Column(String(50), nullable=False, comment="team/member/project/paper/task/file/announcement/meeting/system")
    target_id = Column(Integer, nullable=True)
    target_summary = Column(String(200), comment="对象简述")
    detail = Column(JSON, nullable=True, comment="操作详情（变更前后对比）")
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    result = Column(String(20), default="SUCCESS", comment="SUCCESS/FAILURE/BLOCKED")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="操作时间（不可修改）")
