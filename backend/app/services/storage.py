"""文件存储接口与本地文件系统实现。

业务层只依赖 Storage 抽象，未来可替换为对象存储而不改动业务代码。
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath

from app.core.errors import AppError, ErrorCode


class Storage(ABC):
    """文件存储抽象。"""

    @abstractmethod
    def save(self, scope: str, owner_id: str, filename: str, content: bytes) -> str:
        """保存文件，返回相对于存储根目录的路径。"""

    @abstractmethod
    def read(self, stored_path: str) -> bytes:
        """按相对存储路径读取文件内容。"""

    @abstractmethod
    def delete(self, stored_path: str) -> None:
        """删除文件；文件不存在时静默成功。"""


class LocalStorage(Storage):
    """本地文件系统实现：{root}/{scope}/{owner_id}/{uuid}{ext}。"""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, stored_path: str) -> Path:
        normalized = PurePosixPath(stored_path.replace("\\", "/"))
        candidate = (self.root / normalized).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise AppError(400, ErrorCode.FILE_PATH_INVALID, "非法的文件路径")
        return candidate

    def save(self, scope: str, owner_id: str, filename: str, content: bytes) -> str:
        suffix = PurePosixPath(filename.replace("\\", "/")).suffix
        relative = f"{scope}/{owner_id}/{uuid.uuid4().hex}{suffix}"
        target = self._resolve(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return relative

    def read(self, stored_path: str) -> bytes:
        path = self._resolve(stored_path)
        if not path.is_file():
            raise AppError(404, ErrorCode.NOT_FOUND, "文件不存在")
        return path.read_bytes()

    def delete(self, stored_path: str) -> None:
        path = self._resolve(stored_path)
        path.unlink(missing_ok=True)
