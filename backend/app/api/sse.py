"""SSE 实时推送路由

连接地址：GET /api/v1/messages/stream?team_id=xx&token=xxx
- token 走 URL query（与 download 接口一致，EventSource 无法自定义 header）
- 鉴权失败返回 401
- 成功后建立 SSE 长连接，持续推送消息
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.team_member import TeamMember
from app.services.sse_manager import sse_manager, format_sse
from app.utils.jwt import decode_token, get_subject
import asyncio

router = APIRouter()

TAG = "消息推送"


async def _get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    payload = decode_token(token)
    uid = get_subject(payload)
    if not uid:
        return None
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == uid))
    return result.scalar_one_or_none()


async def _get_team_member(db: AsyncSession, team_id: int, user_id: int) -> Optional[TeamMember]:
    from sqlalchemy import select
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


@router.get("/messages/stream", tags=[TAG])
async def sse_stream(
    team_id: int,
    token: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db),
):
    """SSE 实时消息流。

    使用 EventSource 连接，URL query 传 token。事件类型：
    - `message`：新消息/通知，data 内含 Message 对象
    - `file_upload`：文件上传通知
    - `meeting_created`：新会议通知
    - `ping`：心跳保活
    """
    user = await _get_user_from_token(token, db)
    if not user:
        raise HTTPException(401, "无效的 token")

    member = await _get_team_member(db, team_id, user.id)
    if not member:
        raise HTTPException(403, "您不是该团队成员")

    conn = await sse_manager.add_connection(team_id, user.id)

    async def event_generator():
        try:
            # 连接建立先推一条 ready
            yield format_sse("ready", {
                "team_id": team_id,
                "user_id": user.id,
                "message": "SSE 连接已建立",
            })

            while True:
                try:
                    event, data = await asyncio.wait_for(conn.queue.get(), timeout=30)
                except asyncio.TimeoutError:
                    # 30 秒无消息发个注释帧保活
                    yield ": ping\n\n"
                    conn.last_active = __import__("time").time()
                    continue

                if event == "__ping__":
                    yield ": ping\n\n"
                    conn.last_active = __import__("time").time()
                    continue

                yield format_sse(event, data)
                conn.last_active = __import__("time").time()
        except asyncio.CancelledError:
            pass
        except GeneratorExit:
            pass
        finally:
            await sse_manager.remove_connection(conn)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
