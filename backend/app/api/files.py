"""文件管理 API：文件夹 + 文件上传/下载/列表/重命名/移动/删除"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.middleware.permission import get_team_member, require_team_role, TEACHER_ROLES
from app.models.file_management import Folder, FileRecord, Message
from app.models.user import User
from app.models.team_member import TeamMember
from app.schemas.file_management import FolderCreate, FolderOut, FileOut, FileUpdate
from app.services.storage import storage
from app.services.audit_service import log_audit_action
import mimetypes

router = APIRouter()

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_MIME_PREFIXES = (
    "image/", "application/pdf", "application/msword", "application/vnd.openxmlformats",
    "application/zip", "application/octet-stream", "text/", "video/", "audio/",
)

TAG = "文件管理"


# ============ 文件夹 ============
@router.post("/folders", response_model=FolderOut, tags=[TAG])
async def create_folder(
    team_id: int,
    data: FolderCreate,
    request: Request,
    member: TeamMember = Depends(require_team_role(*TEACHER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    if data.parent_id:
        parent = await db.get(Folder, data.parent_id)
        if not parent or parent.team_id != team_id:
            raise HTTPException(404, "父文件夹不存在")
    dup = await db.execute(
        select(Folder).where(
            Folder.team_id == team_id,
            Folder.parent_id == data.parent_id,
            Folder.name == data.name,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(409, "该文件夹下已存在同名文件夹")

    folder = Folder(team_id=team_id, parent_id=data.parent_id, name=data.name,
                    visibility=data.visibility, created_by=member.user_id)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)

    await log_audit_action(
        db, team_id=team_id, operator_id=member.user_id,
        operator_name="教师", operator_role=member.role,
        action_type="CREATE", target_type="folder", target_id=folder.id,
        target_summary=f"新建文件夹：{folder.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return folder


@router.get("/folders", tags=[TAG])
async def list_folders(
    team_id: int,
    parent_id: Optional[int] = Query(None),
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    q = select(Folder).where(Folder.team_id == team_id)
    if parent_id is not None:
        q = q.where(Folder.parent_id == parent_id)
    else:
        q = q.where(Folder.parent_id.is_(None))
    result = await db.execute(q.order_by(Folder.name))
    return result.scalars().all()


@router.delete("/folders/{folder_id}", tags=[TAG])
async def delete_folder(
    team_id: int,
    folder_id: int,
    request: Request,
    member: TeamMember = Depends(require_team_role(*TEACHER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    folder = await db.get(Folder, folder_id)
    if not folder or folder.team_id != team_id:
        raise HTTPException(404, "文件夹不存在")
    child_count = await db.scalar(
        select(func.count()).select_from(Folder).where(Folder.parent_id == folder_id)
    )
    file_count = await db.scalar(
        select(func.count()).select_from(FileRecord).where(FileRecord.folder_id == folder_id)
    )
    if child_count > 0 or file_count > 0:
        raise HTTPException(400, "文件夹非空，无法删除")

    db.delete(folder)
    await db.commit()
    await log_audit_action(
        db, team_id=team_id, operator_id=member.user_id,
        operator_name="教师", operator_role=member.role,
        action_type="DELETE", target_type="folder", target_id=folder_id,
        target_summary=f"删除文件夹：{folder.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return {"message": "文件夹已删除"}


# ============ 文件 ============
@router.post("/files/upload", tags=[TAG])
async def upload_file(
    team_id: int,
    file: UploadFile,
    folder_id: Optional[int] = Query(None),
    visibility: str = Query("team"),
    request: Request = None,
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, f"文件超过 {MAX_UPLOAD_SIZE // 1024 // 1024}MB 上限")
    if len(content) == 0:
        raise HTTPException(400, "文件不能为空")

    mime = file.content_type or (mimetypes.guess_type(file.filename or "")[0] or "")
    if not any(mime.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(415, f"不支持的文件类型：{mime}")

    if folder_id:
        f = await db.get(Folder, folder_id)
        if not f or f.team_id != team_id:
            raise HTTPException(404, "目标文件夹不存在")

    name = file.filename or "unnamed"

    # 同名覆盖留版本
    existing = await db.execute(
        select(FileRecord).where(
            FileRecord.team_id == team_id,
            FileRecord.folder_id == folder_id,
            FileRecord.name == name,
        )
    )
    old = existing.scalars().first()
    version = 1
    if old:
        version = old.version + 1
        old.version = version
        old.mime_type = mime
        old.size = len(content)
        old.visibility = visibility
        old.uploaded_by = member.user_id
        old.storage_path = await storage.save(team_id, f"v{version}_{name}", content, mime)
        await db.flush()
        file_id = old.id
    else:
        storage_path = await storage.save(team_id, name, content, mime)
        fr = FileRecord(
            team_id=team_id, folder_id=folder_id, name=name, original_name=name,
            mime_type=mime, size=len(content), storage_path=storage_path,
            visibility=visibility, version=1, uploaded_by=member.user_id,
        )
        db.add(fr)
        await db.flush()
        file_id = fr.id

    await log_audit_action(
        db, team_id=team_id, operator_id=member.user_id,
        operator_name="教师" if member.role in TEACHER_ROLES else "成员",
        operator_role=member.role,
        action_type="CREATE" if version == 1 else "UPDATE",
        target_type="file", target_id=file_id,
        target_summary=f"上传文件：{name} (v{version})",
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500] if request else "",
    )

    # 发通知：文件上传
    msg = Message(
        team_id=team_id, user_id=member.user_id, sender_id=member.user_id,
        msg_type="file_upload", title=f"文件已上传：{name}",
        content=f"v{version}，{mime or '未知类型'}",
        reference_type="file", reference_id=file_id,
    )
    db.add(msg)
    await db.commit()

    return {"id": file_id, "name": name, "version": version, "message": "上传成功"}


@router.get("/files", tags=[TAG])
async def list_files(
    team_id: int,
    folder_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    q = select(FileRecord).where(FileRecord.team_id == team_id)
    total_q = select(func.count()).select_from(FileRecord.__table__).where(FileRecord.team_id == team_id)
    if folder_id is not None:
        q = q.where(FileRecord.folder_id == folder_id)
        total_q = total_q.where(FileRecord.folder_id == folder_id)
    else:
        q = q.where(FileRecord.folder_id.is_(None))
        total_q = total_q.where(FileRecord.folder_id.is_(None))

    total = await db.scalar(total_q)
    result = await db.execute(
        q.order_by(FileRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    files = result.scalars().all()

    up_ids = list({f.uploaded_by for f in files if f.uploaded_by})
    names: dict = {}
    if up_ids:
        ur = await db.execute(select(User.id, User.name).where(User.id.in_(up_ids)))
        names = {row[0]: row[1] for row in ur.all()}

    out = []
    for f in files:
        d = {c.name: getattr(f, c.name) for c in f.__table__.columns}
        d["uploaded_by_name"] = names.get(f.uploaded_by)
        out.append(d)
    return {"items": out, "total": total or 0, "page": page, "page_size": page_size}


@router.get("/files/{file_id}/download", tags=[TAG])
async def download_file(
    team_id: int,
    file_id: int,
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    f = await db.get(FileRecord, file_id)
    if not f or f.team_id != team_id:
        raise HTTPException(404, "文件不存在")

    user_id = member.user_id
    if f.visibility == "private" and f.uploaded_by != user_id:
        raise HTTPException(403, "该文件仅限上传者本人访问")
    if f.visibility == "teacher_only" and member.role not in TEACHER_ROLES:
        raise HTTPException(403, "该文件仅限教师访问")

    path = await storage.get_path(f.storage_path)
    if not path.exists():
        raise HTTPException(404, "文件内容丢失")
    return FileResponse(path, filename=f.name, media_type=f.mime_type or "application/octet-stream")


@router.patch("/files/{file_id}", tags=[TAG])
async def update_file(
    team_id: int,
    file_id: int,
    data: FileUpdate,
    request: Request,
    member: TeamMember = Depends(require_team_role(*TEACHER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    f = await db.get(FileRecord, file_id)
    if not f or f.team_id != team_id:
        raise HTTPException(404, "文件不存在")
    if data.name:
        f.name = data.name
    if data.folder_id is not None:
        if data.folder_id:
            target = await db.get(Folder, data.folder_id)
            if not target or target.team_id != team_id:
                raise HTTPException(404, "目标文件夹不存在")
        f.folder_id = data.folder_id
    if data.visibility:
        f.visibility = data.visibility
    await db.commit()
    await db.refresh(f)
    await log_audit_action(
        db, team_id=team_id, operator_id=member.user_id,
        operator_name="教师", operator_role=member.role,
        action_type="UPDATE", target_type="file", target_id=file_id,
        target_summary=f"修改文件：{f.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return {"message": "文件已更新", "id": file_id}


@router.delete("/files/{file_id}", tags=[TAG])
async def delete_file(
    team_id: int,
    file_id: int,
    request: Request,
    member: TeamMember = Depends(require_team_role(*TEACHER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    f = await db.get(FileRecord, file_id)
    if not f or f.team_id != team_id:
        raise HTTPException(404, "文件不存在")
    await storage.delete(f.storage_path)
    db.delete(f)
    await db.commit()
    await log_audit_action(
        db, team_id=team_id, operator_id=member.user_id,
        operator_name="教师", operator_role=member.role,
        action_type="DELETE", target_type="file", target_id=file_id,
        target_summary=f"删除文件：{f.name}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return {"message": "文件已删除"}
