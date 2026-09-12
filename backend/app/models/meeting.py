from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Index
from datetime import datetime
from app.database import Base

class Meeting(Base):
    """研究室组会：文献报告 / 进展汇报 / 答辩预演（会议管理模块）"""
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    meeting_type = Column(String(20), nullable=False)  # journal / progress / defense
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=True)
    location = Column(String(200), nullable=True)
    presenter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="upcoming")  # upcoming / finished / cancelled
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_meetings_team', 'team_id'),
        Index('idx_meetings_type', 'team_id', 'meeting_type'),
        Index('idx_meetings_start', 'start_at'),
    )

class MeetingAgendaItem(Base):
    """组会议程（有序）：时间 / 内容 / 主讲人"""
    __tablename__ = "meeting_agenda_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    seq = Column(Integer, default=0)
    time_slot = Column(String(50), nullable=True)
    content = Column(String(300), nullable=False)
    presenter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_meeting_agenda_meeting', 'meeting_id'),
    )

class MeetingAction(Base):
    """组会行动项：内容 / 负责人 / 截止日 / 状态 / 完成时间"""
    __tablename__ = "meeting_actions"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    content = Column(String(300), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String(20), default="open")  # open / done / cancelled
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_meeting_actions_meeting', 'meeting_id'),
        Index('idx_meeting_actions_owner', 'owner_id'),
    )
