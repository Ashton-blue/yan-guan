"""Storage 适配器接口 + 本地持久卷实现。

设计原则：
- 接口化，业务代码只依赖 StorageAdapter，不直接操作文件路径。
- 后续替换为 S3 / Supabase Storage 时，只需实现同名接口，不改业务代码。
- 密钥/路径零硬编码，全部从环境变量读取。
"""
import os
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path


class StorageAdapter(ABC):
    """文件存储抽象接口"""

    @abstractmethod
    async def save(self, team_id: int, name: str, content: bytes, mime_type: str = "") -> str:
        """写入文件，返回 storage_path（相对路径）"""

    @abstractmethod
    async def get(self, storage_path: str) -> bytes:
        """读取文件内容"""

    @abstractmethod
    async def get_path(self, storage_path: str) -> Path:
        """返回本地绝对路径（用于 FileResponse 流式下载/预览）"""

    @abstractmethod
    async def delete(self, storage_path: str) -> None:
        """删除文件"""

    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """判断文件是否存在"""


class LocalStorageAdapter(StorageAdapter):
    """基于持久卷的本地存储（Zeabur 挂载可写目录）"""

    def __init__(self):
        base = os.getenv("STORAGE_DIR", "/data/yan-guan-files")
        self.base_dir = Path(base)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, storage_path: str) -> Path:
        p = self.base_dir / storage_path
        # 防路径穿越
        if not p.resolve().is_relative_to(self.base_dir.resolve()):
            raise ValueError("Invalid storage path")
        return p

    async def save(self, team_id: int, name: str, content: bytes, mime_type: str = "") -> str:
        safe_name = f"{uuid.uuid4().hex}_{name}"
        rel = f"team_{team_id}/{safe_name}"
        p = self._resolve(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        return rel

    async def get(self, storage_path: str) -> bytes:
        p = self._resolve(storage_path)
        return p.read_bytes()

    async def get_path(self, storage_path: str) -> Path:
        return self._resolve(storage_path)

    async def delete(self, storage_path: str) -> None:
        p = self._resolve(storage_path)
        if p.exists():
            p.unlink()

    async def exists(self, storage_path: str) -> bool:
        return self._resolve(storage_path).exists()


# 全局单例
storage: StorageAdapter = LocalStorageAdapter()
