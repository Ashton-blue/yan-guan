from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, Boolean
from datetime import datetime
from app.database import Base


class Folder(Base):
    """文件管理：文件夹（树形层级）"""
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(Integer, ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(200), nullable=False)
    visibility = Column(String(20), default="team")  # team / teacher_only / private
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_folders_team', 'team_id'),
        Index('idx_folders_parent', 'parent_id'),
    )


class FileRecord(Base):
    """文件管理：文件元数据（本体落持久卷，元数据进 PG）"""
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    folder_id = Column(Integer, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(300), nullable=False)
    original_name = Column(String(300), nullable=False)
    mime_type = Column(String(100), nullable=True)
    size = Column(Integer, default=0)
    storage_path = Column(String(500), nullable=False)  # 持久卷内相对路径
    visibility = Column(String(20), default="team")  # team / teacher_only / private
    version = Column(Integer, default=1)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_files_team', 'team_id'),
        Index('idx_files_folder', 'folder_id'),
        Index('idx_files_team_name', 'team_id', 'name'),
    )


class Message(Base):
    """讯息管理：消息中心（系统通知 / @提醒 / 行动项指派 / 文件上传 / 会议提醒 / 私信）"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # 接收人
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # 发送人（系统通知为 NULL）
    msg_type = Column(String(30), default="system")  # system / mention / action_item / file_upload / meeting_reminder / direct
    title = Column(String(300), nullable=False)
    content = Column(String(2000), nullable=True)
    reference_type = Column(String(50), nullable=True)  # 关联资源类型：meeting / file / action_item / folder
    reference_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_messages_user', 'user_id', 'is_read'),
        Index('idx_messages_team', 'team_id'),
        Index('idx_messages_type', 'msg_type'),
    )
