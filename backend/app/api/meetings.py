from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.middleware.permission import get_team_member, require_team_role, TEACHER_ROLES
from app.models.user import User
from app.models.team_member import TeamMember
from app.models.meeting import Meeting, MeetingAgendaItem, MeetingAction
from app.schemas.meeting import (
    MeetingCreate, MeetingUpdate, MeetingOut, MeetingDetail,
    AgendaItemCreate, ActionCreate, ActionUpdate,
)
from app.services.audit_service import log_audit_action

router = APIRouter()


async def _get_meeting(
    db: AsyncSession, team_id: int, meeting_id: int
) -> Meeting:
    """取会议并确保属于该团队（404）；成员资格由 Depends 依赖另行保证（403）。"""
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.team_id == team_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="组会不存在")
    return meeting


def _meeting_out(m: Meeting, presenter_name: Optional[str] = None) -> dict:
    return {
        "id": m.id,
        "team_id": m.team_id,
        "title": m.title,
        "meeting_type": m.meeting_type,
        "start_at": m.start_at,
        "end_at": m.end_at,
        "location": m.location,
        "presenter_id": m.presenter_id,
        "presenter_name": presenter_name,
        "description": m.description,
        "status": m.status,
        "created_at": m.created_at,
    }


async def _name_map(db: AsyncSession, ids) -> dict:
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    rows = await db.execute(select(User.id, User.name).where(User.id.in_(ids)))
    return {uid: name for uid, name in rows.all()}


async def _detail(db: AsyncSession, m: Meeting) -> dict:
    base = _meeting_out(m)
    ag = await db.execute(
        select(MeetingAgendaItem).where(MeetingAgendaItem.meeting_id == m.id).order_by(MeetingAgendaItem.seq)
    )
    ac = await db.execute(
        select(MeetingAction).where(MeetingAction.meeting_id == m.id).order_by(MeetingAction.due_date)
    )
    agenda_rows, action_rows = ag.scalars().all(), ac.scalars().all()
    names = await _name_map(
        db, [m.presenter_id]
        + [a.presenter_id for a in agenda_rows]
        + [x.owner_id for x in action_rows]
    )
    base["agenda"] = [
        {
            "id": a.id, "seq": a.seq, "time_slot": a.time_slot, "content": a.content,
            "presenter_id": a.presenter_id, "presenter_name": names.get(a.presenter_id),
        }
        for a in agenda_rows
    ]
    base["actions"] = [
        {
            "id": x.id, "content": x.content, "owner_id": x.owner_id,
            "owner_name": names.get(x.owner_id), "due_date": x.due_date,
            "status": x.status, "completed_at": x.completed_at,
        }
        for x in action_rows
    ]
    base["presenter_name"] = names.get(m.presenter_id)
    return base


@router.get("/meetings")
async def list_meetings(
    team_id: int,
    type: Optional[str] = None,
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    """组会列表（可按类型 journal/progress/defense 筛选），新会优先"""
    q = select(Meeting).where(Meeting.team_id == team_id)
    if type in ("journal", "progress", "defense"):
        q = q.where(Meeting.meeting_type == type)
    q = q.order_by(Meeting.start_at.desc())
    meetings = (await db.execute(q)).scalars().all()
    names = await _name_map(db, [m.presenter_id for m in meetings])
    return [_meeting_out(m, names.get(m.presenter_id)) for m in meetings]


@router.post("/meetings")
async def create_meeting(
    team_id: int,
    data: MeetingCreate,
    request: Request,
    member: TeamMember = Depends(require_team_role(*TEACHER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """新建组会（教师角色）。状态按开始时间自动判定 upcoming/finished。"""
    auto_status = "finished" if data.start_at < datetime.utcnow() else "upcoming"
    m = Meeting(
        team_id=team_id,
        title=data.title,
        meeting_type=data.meeting_type,
        start_at=data.start_at,
        end_at=data.end_at,
        location=data.location,
        presenter_id=data.presenter_id,
        description=data.description,
        status=data.status or auto_status,
        created_by=member.user_id,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)

    await log_audit_action(
        db, team_id=team_id,
        operator_id=member.user_id, operator_name="教师", operator_role=member.role,
        action_type="CREATE", target_type="meeting", target_id=m.id,
        target_summary=f"新建组会：{m.title}（{m.meeting_type}）",
        detail={"title": m.title, "type": m.meeting_type, "start_at": str(m.start_at)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return await _detail(db, m)


@router.get("/meetings/{meeting_id}")
async def get_meeting(
    team_id: int,
    meeting_id: int,
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    """组会详情（含议程与行动项）"""
    m = await _get_meeting(db, team_id, meeting_id)
    return await _detail(db, m)


@router.put("/meetings/{meeting_id}")
async def update_meeting(
    team_id: int,
    meeting_id: int,
    data: MeetingUpdate,
    request: Request,
    member: TeamMember = Depends(require_team_role(*TEACHER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """更新组会（教师角色）"""
    m = await _get_meeting(db, team_id, meeting_id)
    for field in ("title", "meeting_type", "start_at", "end_at", "location",
                  "presenter_id", "description", "status"):
        val = getattr(data, field)
        if val is not None:
            setattr(m, field, val)
    await db.commit()
    await db.refresh(m)

    await log_audit_action(
        db, team_id=team_id,
        operator_id=member.user_id, operator_name="教师", operator_role=member.role,
        action_type="UPDATE", target_type="meeting", target_id=m.id,
        target_summary=f"更新组会：{m.title}",
        detail={k: getattr(data, k) for k in ("title", "status", "start_at", "location") if getattr(data, k) is not None},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return await _detail(db, m)


@router.delete("/meetings/{meeting_id}")
async def delete_meeting(
    team_id: int,
    meeting_id: int,
    request: Request,
    member: TeamMember = Depends(require_team_role("owner", "supervisor")),
    db: AsyncSession = Depends(get_db),
):
    """删除组会（仅 owner/supervisor），级联删除议程与行动项"""
    m = await _get_meeting(db, team_id, meeting_id)
    await db.delete(m)
    await db.commit()

    await log_audit_action(
        db, team_id=team_id,
        operator_id=member.user_id, operator_name="教师", operator_role=member.role,
        action_type="DELETE", target_type="meeting", target_id=meeting_id,
        target_summary=f"删除组会：{m.title}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return {"message": "组会已删除"}


# ---------- 议程 ----------
@router.post("/meetings/{meeting_id}/agenda")
async def add_agenda_item(
    team_id: int,
    meeting_id: int,
    data: AgendaItemCreate,
    request: Request,
    member: TeamMember = Depends(require_team_role(*TEACHER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """新增议程项（有序）"""
    m = await _get_meeting(db, team_id, meeting_id)
    item = MeetingAgendaItem(
        meeting_id=m.id, seq=data.seq, time_slot=data.time_slot,
        content=data.content, presenter_id=data.presenter_id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    await log_audit_action(
        db, team_id=team_id,
        operator_id=member.user_id, operator_name="教师", operator_role=member.role,
        action_type="CREATE", target_type="meeting_agenda", target_id=item.id,
        target_summary=f"{m.title} 新增议程：{item.content}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    names = await _name_map(db, [item.presenter_id])
    return {
        "id": item.id, "seq": item.seq, "time_slot": item.time_slot, "content": item.content,
        "presenter_id": item.presenter_id, "presenter_name": names.get(item.presenter_id),
    }


@router.delete("/meetings/{meeting_id}/agenda/{item_id}")
async def delete_agenda_item(
    team_id: int,
    meeting_id: int,
    item_id: int,
    request: Request,
    member: TeamMember = Depends(require_team_role(*TEACHER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """删除议程项"""
    m = await _get_meeting(db, team_id, meeting_id)
    result = await db.execute(
        select(MeetingAgendaItem).where(MeetingAgendaItem.id == item_id, MeetingAgendaItem.meeting_id == m.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="议程项不存在")
    await db.delete(item)
    await db.commit()

    await log_audit_action(
        db, team_id=team_id,
        operator_id=member.user_id, operator_name="教师", operator_role=member.role,
        action_type="DELETE", target_type="meeting_agenda", target_id=item_id,
        target_summary=f"{m.title} 删除议程：{item.content}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return {"message": "议程项已删除"}


# ---------- 行动项 ----------
@router.post("/meetings/{meeting_id}/actions")
async def add_action(
    team_id: int,
    meeting_id: int,
    data: ActionCreate,
    request: Request,
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    """新增行动项（成员可登记，教师可指派）"""
    m = await _get_meeting(db, team_id, meeting_id)
    act = MeetingAction(
        meeting_id=m.id, content=data.content, owner_id=data.owner_id, due_date=data.due_date,
    )
    db.add(act)
    await db.commit()
    await db.refresh(act)

    await log_audit_action(
        db, team_id=team_id,
        operator_id=member.user_id, operator_name=member.role, operator_role=member.role,
        action_type="CREATE", target_type="meeting_action", target_id=act.id,
        target_summary=f"{m.title} 新增行动项：{act.content}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    names = await _name_map(db, [act.owner_id])
    return {
        "id": act.id, "content": act.content, "owner_id": act.owner_id,
        "owner_name": names.get(act.owner_id), "due_date": act.due_date,
        "status": act.status, "completed_at": act.completed_at,
    }


@router.patch("/meetings/{meeting_id}/actions/{action_id}")
async def update_action(
    team_id: int,
    meeting_id: int,
    action_id: int,
    data: ActionUpdate,
    request: Request,
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    """更新行动项（状态 open/done/cancelled；done 时记录完成时间）"""
    m = await _get_meeting(db, team_id, meeting_id)
    result = await db.execute(
        select(MeetingAction).where(MeetingAction.id == action_id, MeetingAction.meeting_id == m.id)
    )
    act = result.scalar_one_or_none()
    if not act:
        raise HTTPException(status_code=404, detail="行动项不存在")

    for field in ("content", "owner_id", "due_date", "status"):
        val = getattr(data, field)
        if val is not None:
            setattr(act, field, val)
    if data.status == "done" and not act.completed_at:
        act.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(act)

    await log_audit_action(
        db, team_id=team_id,
        operator_id=member.user_id, operator_name=member.role, operator_role=member.role,
        action_type="UPDATE", target_type="meeting_action", target_id=act.id,
        target_summary=f"{m.title} 更新行动项：{act.content}（{act.status}）",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    names = await _name_map(db, [act.owner_id])
    return {
        "id": act.id, "content": act.content, "owner_id": act.owner_id,
        "owner_name": names.get(act.owner_id), "due_date": act.due_date,
        "status": act.status, "completed_at": act.completed_at,
    }
