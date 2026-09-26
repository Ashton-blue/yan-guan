"""文件管理 API：文件夹 + 文件上传/下载/列表/重命名/移动/删除"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select, func, and_, or_, not_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.middleware.permission import get_team_member, require_team_role, TEACHER_ROLES
from app.models.file_management import Folder, FileRecord, Message
from app.models.user import User
from app.models.team_member import TeamMember
from app.schemas.file_management import FolderCreate, FolderOut, FileOut, FileUpdate, FileSearchResult, FolderSearchResult
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
@router.post("/folders", response_model=FolderOut, status_code=201, tags=[TAG])
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

    await db.delete(folder)
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
@router.post("/files/upload", status_code=201, tags=[TAG])
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
    await db.delete(f)
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


# ============ 搜索 ============
TYPE_CATEGORIES = {
    "document": (
        "application/pdf", "application/msword", "application/vnd.openxmlformats",
        "application/vnd.ms-excel", "application/vnd.ms-powerpoint",
        "text/", "application/rtf",
    ),
    "image": ("image/",),
    "video": ("video/",),
    "audio": ("audio/",),
    "archive": (
        "application/zip", "application/x-rar-compressed",
        "application/x-7z-compressed", "application/x-tar", "application/gzip",
    ),
}


def _type_conditions(column, category: str):
    """根据类型分类返回 SQLAlchemy 过滤条件。"""
    if category == "other":
        all_prefixes = [p for prefixes in TYPE_CATEGORIES.values() for p in prefixes]
        conds = [column.startswith(p) for p in all_prefixes]
        return not_(or_(*conds, column.is_(None)))
    prefixes = TYPE_CATEGORIES.get(category, ())
    if not prefixes:
        return None
    return or_(*[column.startswith(p) for p in prefixes])


async def _get_descendant_folder_ids(db: AsyncSession, team_id: int, root_id: Optional[int]):
    """递归查询 root_id 下所有后代文件夹 ID（含 root_id 自身）。
    root_id=None 时返回该团队所有文件夹 ID。
    """
    # 基础：起点文件夹
    base = select(Folder.id, Folder.parent_id).where(Folder.team_id == team_id)
    if root_id is not None:
        base = base.where(Folder.id == root_id)
    else:
        base = base  # 全团队所有文件夹
    base = base.cte("desc_folders", recursive=True)

    # 递归：子文件夹
    recursive = select(Folder.id, Folder.parent_id).join(
        base, Folder.parent_id == base.c.id
    )
    cte = base.union_all(recursive)
    result = await db.execute(select(cte.c.id))
    return {row[0] for row in result.all()}


async def _build_folder_path(db: AsyncSession, team_id: int, folder_id: Optional[int]) -> Optional[str]:
    """向上追溯构建文件夹路径（不含自身名字 → 给文件用：parent_id 开始）。
    传入 folder_id 为 None 时返回 None。
    """
    if not folder_id:
        return None
    parts = []
    current_id = folder_id
    visited = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        fobj = await db.get(Folder, current_id)
        if not fobj or fobj.team_id != team_id:
            break
        parts.insert(0, fobj.name)
        current_id = fobj.parent_id
    return "/".join(parts) if parts else None


@router.get("/search", tags=[TAG])
async def search_files(
    team_id: int,
    q: str = Query("", min_length=0, max_length=100),
    file_type: Optional[str] = Query(None, pattern="^(document|image|video|audio|archive|other)$"),
    sort_by: str = Query("newest", pattern="^(newest|oldest|name)$"),
    recursive: bool = Query(True),
    folder_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    member: TeamMember = Depends(get_team_member),
    db: AsyncSession = Depends(get_db),
):
    """搜索文件（默认递归含子目录），同时返回匹配的文件夹。
    - q: 关键词模糊匹配名称（空关键词=不筛选，可当类型筛选用）
    - file_type: 按类型筛选（document/image/video/audio/archive/other）
    - sort_by: newest / oldest / name
    - recursive: 是否递归子目录
    - folder_id: 限定搜索根目录（None=团队全部）
    """
    keyword = q.strip()
    like = f"%{keyword}%"

    # 1. 确定文件夹范围
    if recursive and (folder_id is not None):
        # 指定 folder + 递归 → 取该文件夹及其所有后代
        descendant_ids = await _get_descendant_folder_ids(db, team_id, folder_id)
        file_folder_ids = list(descendant_ids)
        folder_scope_ids = list(descendant_ids)
    elif (not recursive) and (folder_id is not None):
        # 指定 folder + 不递归 → 仅直接子级
        file_folder_ids = [folder_id]
        folder_scope_ids = [folder_id] if folder_id else []
    elif recursive and folder_id is None:
        # 全团队 + 递归 → 不加 folder_id 过滤（全团队文件）
        file_folder_ids = None  # None 表示不过滤
        folder_scope_ids = None
    else:
        # folder_id=None + 不递归 → 根目录（folder_id IS NULL）
        file_folder_ids = []  # 用特殊值表示根目录

    # 2. 文件查询
    file_q = select(FileRecord).where(FileRecord.team_id == team_id)
    file_total_q = select(func.count()).select_from(FileRecord.__table__).where(
        FileRecord.team_id == team_id
    )

    # folder 范围过滤
    if file_folder_ids is None:
        # 全团队，不过滤
        pass
    elif len(file_folder_ids) == 0:
        # 根目录
        file_q = file_q.where(FileRecord.folder_id.is_(None))
        file_total_q = file_total_q.where(FileRecord.folder_id.is_(None))
    else:
        file_q = file_q.where(FileRecord.folder_id.in_(file_folder_ids))
        file_total_q = file_total_q.where(FileRecord.folder_id.in_(file_folder_ids))

    # 关键词
    if keyword:
        file_q = file_q.where(FileRecord.name.ilike(like))
        file_total_q = file_total_q.where(FileRecord.name.ilike(like))

    # 类型
    if file_type:
        cond = _type_conditions(FileRecord.mime_type, file_type)
        if cond is not None:
            file_q = file_q.where(cond)
            file_total_q = file_total_q.where(cond)

    # 排序
    if sort_by == "newest":
        file_q = file_q.order_by(FileRecord.created_at.desc())
    elif sort_by == "oldest":
        file_q = file_q.order_by(FileRecord.created_at.asc())
    else:  # name
        file_q = file_q.order_by(FileRecord.name.asc())

    file_total = await db.scalar(file_total_q) or 0
    file_result = await db.execute(
        file_q.offset((page - 1) * page_size).limit(page_size)
    )
    files = file_result.scalars().all()

    # 3. 路径 & 上传者
    folder_path_map: dict = {}
    folder_ids_in_files = list({f.folder_id for f in files if f.folder_id})
    for fid in folder_ids_in_files:
        folder_path_map[fid] = await _build_folder_path(db, team_id, fid)

    up_ids = list({f.uploaded_by for f in files if f.uploaded_by})
    names: dict = {}
    if up_ids:
        ur = await db.execute(select(User.id, User.name).where(User.id.in_(up_ids)))
        names = {row[0]: row[1] for row in ur.all()}

    file_out = []
    for f in files:
        d = {c.name: getattr(f, c.name) for c in f.__table__.columns}
        d["uploaded_by_name"] = names.get(f.uploaded_by)
        d["folder_path"] = folder_path_map.get(f.folder_id)
        file_out.append(d)

    # 4. 文件夹搜索（前 20 条匹配）
    folder_q = select(Folder).where(Folder.team_id == team_id)
    if folder_scope_ids is not None:
        if len(folder_scope_ids) == 0:
            # 根目录下的直接子文件夹
            folder_q = folder_q.where(Folder.parent_id == folder_id) if folder_id else \
                folder_q.where(Folder.parent_id.is_(None))
        else:
            # 后代范围内（排除起点自身，只看子/孙级匹配；但为了简单包含自身也可）
            folder_q = folder_q.where(Folder.id.in_(folder_scope_ids))
    if keyword:
        folder_q = folder_q.where(Folder.name.ilike(like))
    folder_q = folder_q.order_by(Folder.name).limit(20)
    folder_result = await db.execute(folder_q)
    folders = folder_result.scalars().all()

    folder_out = []
    for fo in folders:
        d = {c.name: getattr(fo, c.name) for c in fo.__table__.columns}
        # 路径 = 父级链（不含自己）
        d["folder_path"] = await _build_folder_path(db, team_id, fo.parent_id)
        folder_out.append(d)

    return {
        "files": {
            "items": file_out,
            "total": file_total,
            "page": page,
            "page_size": page_size,
        },
        "folders": {
            "items": folder_out,
            "total": len(folder_out),
        },
        "keyword": keyword,
    }
