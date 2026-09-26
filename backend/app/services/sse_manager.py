"""SSE 实时推送管理器（单实例内存版）

设计：
- 每个 SSE 连接是一个 asyncio.Queue（单连接单队列）
- 连接以 (team_id, user_id) 为维度注册：一个用户在同一团队可有多个连接（多标签页）
- 广播按 team_id → 该团队所有用户的所有连接
- 点对点按 user_id 推送（跨团队也能推，但建议传 team_id 减少遍历）
- 30 秒心跳保活（: ping \\n\\n 形式的 SSE 注释帧）
- 预留 Redis Pub/Sub 扩展点（当前不实现，仅留接口注释）

消息格式（SSE event/data）：
event: message
data: {"type":"message","team_id":1,"payload":{...}}

event: file_upload
data: {"type":"file_upload","team_id":1,"payload":{...}}

event: meeting_created
data: {"type":"meeting_created","team_id":1,"payload":{...}}
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any


class SSEConnection:
    __slots__ = ("team_id", "user_id", "queue", "last_active")

    def __init__(self, team_id: int, user_id: int):
        self.team_id = team_id
        self.user_id = user_id
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=128)
        self.last_active: float = time.time()

    async def send(self, event: str, data: Any):
        try:
            self.queue.put_nowait((event, data))
            self.last_active = time.time()
        except asyncio.QueueFull:
            # 队列满（消费者卡死），丢最老的一帧再塞新的
            try:
                self.queue.get_nowait()
                self.queue.put_nowait((event, data))
            except Exception:
                pass


class SSEManager:
    """SSE 连接管理器（单例）"""

    def __init__(self):
        # team_id -> user_id -> list[SSEConnection]
        self._team_users: Dict[int, Dict[int, List[SSEConnection]]] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_interval = 25  # 秒
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动心跳任务（在 app lifespan 中调用）"""
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self):
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def _heartbeat_loop(self):
        """定期向所有活动连接发送 : ping 注释帧保活。"""
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                now = time.time()
                async with self._lock:
                    for team_users in self._team_users.values():
                        for conns in team_users.values():
                            for conn in conns:
                                # 超过 90 秒无活动视为僵死，下一轮遍历清理前先关闭
                                if now - conn.last_active > 90:
                                    continue
                                try:
                                    conn.queue.put_nowait(("__ping__", None))
                                except asyncio.QueueFull:
                                    pass
                # 清理僵死连接
                await self._cleanup_stale()
            except asyncio.CancelledError:
                break
            except Exception:
                continue

    async def _cleanup_stale(self):
        now = time.time()
        async with self._lock:
            for team_id in list(self._team_users.keys()):
                team_users = self._team_users[team_id]
                for user_id in list(team_users.keys()):
                    conns = team_users[user_id]
                    alive = [c for c in conns if now - c.last_active <= 90]
                    if len(alive) != len(conns):
                        if alive:
                            team_users[user_id] = alive
                        else:
                            del team_users[user_id]
                if not team_users:
                    del self._team_users[team_id]

    async def add_connection(self, team_id: int, user_id: int) -> SSEConnection:
        conn = SSEConnection(team_id, user_id)
        async with self._lock:
            if team_id not in self._team_users:
                self._team_users[team_id] = {}
            team_users = self._team_users[team_id]
            if user_id not in team_users:
                team_users[user_id] = []
            team_users[user_id].append(conn)
        return conn

    async def remove_connection(self, conn: SSEConnection):
        async with self._lock:
            team_users = self._team_users.get(conn.team_id)
            if not team_users:
                return
            conns = team_users.get(conn.user_id)
            if not conns:
                return
            try:
                conns.remove(conn)
            except ValueError:
                pass
            if not conns:
                del team_users[conn.user_id]
            if not team_users:
                del self._team_users[conn.team_id]

    async def broadcast_to_team(self, team_id: int, event: str, data: dict):
        """向指定团队所有在线用户广播。"""
        async with self._lock:
            team_users = self._team_users.get(team_id)
            if not team_users:
                return
            targets: List[SSEConnection] = []
            for conns in team_users.values():
                targets.extend(conns)
        for conn in targets:
            await conn.send(event, data)

    async def send_to_user(self, team_id: int, user_id: int, event: str, data: dict):
        """向指定团队的指定用户推送（包含该用户的所有连接）。"""
        async with self._lock:
            team_users = self._team_users.get(team_id)
            if not team_users:
                return
            conns = team_users.get(user_id)
            if not conns:
                return
            targets = list(conns)
        for conn in targets:
            await conn.send(event, data)

    async def get_stats(self) -> dict:
        """调试用：返回当前连接数统计。"""
        async with self._lock:
            teams = len(self._team_users)
            users = sum(len(u) for u in self._team_users.values())
            conns = sum(
                len(conns)
                for team_users in self._team_users.values()
                for conns in team_users.values()
            )
        return {"teams": teams, "users": users, "connections": conns}


# 全局单例
sse_manager = SSEManager()


def format_sse(event: str, data: Any) -> str:
    """将事件和数据格式化为 SSE 协议文本。"""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    lines = [f"event: {event}"]
    for line in payload.split("\n"):
        lines.append(f"data: {line}")
    lines.append("")  # 空行分隔
    lines.append("")
    return "\n".join(lines)
