"""讯息管理 API：消息中心（通知/@我/私信）+ 已读未读"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.permission import get_team_member
from app.models.file_management import Message
from app.models.user import User
from app.models.team_member import TeamMember
from app.schemas.file_management import MessageCreate, MessageOut, MessageReadResult
from app.services.audit_service import log_audit_action

router = APIRouter()

TAG = "讯息管理"


@router.get("/messages", tags=[TAG])
async def list_messages(
    team_id: int,
    tab: str = Query("all", pattern="^(all|notifications|at_me)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    """
    三页签：
    - all: 全部消息
    - notifications: 通知类（system/action_item/file_upload/meeting_reminder）
    - at_me: @我（mention/direct 类型且 sender != me）
    """
    user_id = member.user_id
    q = select(Message).where(Message.team_id == team_id, Message.user_id == user_id)
    if tab == "notifications":
        q = q.where(Message.msg_type.in_(["system", "action_item", "file_upload", "meeting_reminder"]))
    elif tab == "at_me":
        q = q.where(Message.msg_type.in_(["mention", "direct"]), Message.sender_id != user_id)

    total_q = select(func.count()).select_from(Message.__table__).where(Message.team_id == team_id, Message.user_id == user_id)
    if tab == "notifications":
        total_q = total_q.where(Message.msg_type.in_(["system", "action_item", "file_upload", "meeting_reminder"]))
    elif tab == "at_me":
        total_q = total_q.where(Message.msg_type.in_(["mention", "direct"]), Message.sender_id != user_id)

    total = await db.scalar(total_q)
    result = await db.execute(
        q.order_by(Message.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    msgs = result.scalars().all()

    # 查发件人名称
    sender_ids = list({m.sender_id for m in msgs if m.sender_id})
    names: dict = {}
    if sender_ids:
        ur = await db.execute(select(User.id, User.name).where(User.id.in_(sender_ids)))
        names = {row[0]: row[1] for row in ur.all()}

    items = []
    for m in msgs:
        d = {c.name: getattr(m, c.name) for c in m.__table__.columns}
        d["sender_name"] = names.get(m.sender_id)
        items.append(d)

    # 未读数
    unread = await db.scalar(
        select(func.count()).select_from(Message.__table__).where(
            Message.team_id == team_id, Message.user_id == user_id, Message.is_read == False
        )
    )
    return {"items": items, "total": total or 0, "page": page, "page_size": page_size, "unread_count": unread or 0}


@router.put("/messages/{msg_id}/read", response_model=MessageReadResult, tags=[TAG])
async def mark_read(
    team_id: int,
    msg_id: int,
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    m = await db.get(Message, msg_id)
    if not m or m.team_id != team_id:
        raise HTTPException(404, "消息不存在")
    if m.user_id != member.user_id:
        raise HTTPException(403, "只能标记自己的消息为已读")
    if not m.is_read:
        from datetime import datetime
        m.is_read = True
        m.read_at = datetime.utcnow()
        await db.commit()

    unread = await db.scalar(
        select(func.count()).select_from(Message.__table__).where(
            Message.team_id == team_id, Message.user_id == member.user_id, Message.is_read == False
        )
    )
    return {"message": "已标记为已读", "total_unread": unread or 0}


@router.put("/messages/read-all", response_model=MessageReadResult, tags=[TAG])
async def mark_all_read(
    team_id: int,
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    updated = await db.execute(
        update(Message)
        .where(Message.team_id == team_id, Message.user_id == member.user_id, Message.is_read == False)
        .values(is_read=True, read_at=datetime.utcnow())
    )
    await db.commit()
    return {"message": "全部标记为已读", "total_unread": 0}


@router.post("/messages", response_model=MessageOut, status_code=201, tags=[TAG])
async def send_direct_message(
    team_id: int,
    data: MessageCreate,
    request: Request,
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    """简版站内私信：发送给同团队其他成员"""
    # 验证收件人是同团队成员
    recipient = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == data.recipient_id, TeamMember.is_active == True)
    )
    if not recipient.scalar_one_or_none():
        raise HTTPException(404, "收件人不是本团队活跃成员")

    # 查收件人姓名
    rec_user = await db.get(User, data.recipient_id)
    sender_user = await db.get(User, member.user_id)

    msg = Message(
        team_id=team_id, user_id=data.recipient_id, sender_id=member.user_id,
        msg_type=data.msg_type or "direct",
        title=data.title, content=data.content,
        reference_type=None, reference_id=None,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    await log_audit_action(
        db, team_id=team_id, operator_id=member.user_id,
        operator_name=sender_user.name if sender_user else str(member.user_id),
        operator_role=member.role,
        action_type="CREATE", target_type="message", target_id=msg.id,
        target_summary=f"私信 {rec_user.name if rec_user else data.recipient_id}：{data.title[:50]}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return msg


# ============ 内部通知触发（供其他模块调用）============
async def notify_meeting_created(db: AsyncSession, team_id: int, meeting_id: int, meeting_title: str, organizer_id: int, user_ids: list):
    """会议创建后通知被邀请者"""
    for uid in user_ids:
        if uid == organizer_id:
            continue
        m = Message(
            team_id=team_id, user_id=uid, sender_id=organizer_id,
            msg_type="meeting_reminder", title=f"会议邀请：{meeting_title}",
            content="你被邀请参加一次组会",
            reference_type="meeting", reference_id=meeting_id,
        )
        db.add(m)
    await db.commit()


async def notify_action_item_assigned(db: AsyncSession, team_id: int, action_id: int, assignee_id: int, title: str, assigner_id: int):
    """行动项指派通知"""
    m = Message(
        team_id=team_id, user_id=assignee_id, sender_id=assigner_id,
        msg_type="action_item", title=f"行动项指派：{title}",
        content="你被指派了一个行动项",
        reference_type="action_item", reference_id=action_id,
    )
    db.add(m)
    await db.commit()


async def send_system_notification(db: AsyncSession, team_id: int, user_id: int, title: str, content: str = None):
    """系统通知"""
    m = Message(
        team_id=team_id, user_id=user_id, sender_id=None,
        msg_type="system", title=title, content=content,
    )
    db.add(m)
    await db.commit()
