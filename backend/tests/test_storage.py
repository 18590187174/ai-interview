"""存储接口与本地实现测试。"""

from __future__ import annotations

import pytest

from app.core.errors import AppError, ErrorCode
from app.services.storage import LocalStorage


@pytest.fixture
def storage(tmp_path) -> LocalStorage:
    return LocalStorage(tmp_path / "uploads")


def test_save_read_roundtrip(storage: LocalStorage) -> None:
    path = storage.save("resumes", "owner-1", "张三.pdf", b"pdf-bytes")
    assert path.startswith("resumes/owner-1/")
    assert path.endswith(".pdf")
    assert storage.read(path) == b"pdf-bytes"


def test_save_keeps_extension_and_generates_unique_names(storage: LocalStorage) -> None:
    first = storage.save("resumes", "owner-1", "a.docx", b"1")
    second = storage.save("resumes", "owner-1", "b.docx", b"2")
    assert first != second
    assert first.endswith(".docx")


def test_read_missing_file(storage: LocalStorage) -> None:
    with pytest.raises(AppError) as exc:
        storage.read("resumes/owner-1/not-exists.pdf")
    assert exc.value.status_code == 404


def test_delete_removes_file_and_is_idempotent(storage: LocalStorage) -> None:
    path = storage.save("resumes", "owner-1", "a.pdf", b"x")
    storage.delete(path)
    with pytest.raises(AppError):
        storage.read(path)
    storage.delete(path)  # 不存在时静默成功


def test_path_traversal_is_rejected(storage: LocalStorage) -> None:
    with pytest.raises(AppError) as exc:
        storage.read("../outside-secret.txt")
    assert exc.value.code == ErrorCode.FILE_PATH_INVALID

    with pytest.raises(AppError) as exc:
        storage.read("resumes/..\\..\\escape.pdf")
    assert exc.value.code == ErrorCode.FILE_PATH_INVALID
