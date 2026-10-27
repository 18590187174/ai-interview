"""简历管理端点测试。"""

from __future__ import annotations

import io
import uuid

import docx
import pytest

from app.api.deps import get_storage
from app.models.resume import Resume
from app.models.user import User
from app.services.storage import LocalStorage


def _docx_bytes(paragraphs: list[str] | None = None) -> bytes:
    document = docx.Document()
    for text in paragraphs or ["张三", "五年 Python 后端经验"]:
        document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def uploads_dir(tmp_path) -> LocalStorage:
    local = LocalStorage(tmp_path / "uploads")
    from app.main import app

    app.dependency_overrides[get_storage] = lambda: local
    yield local
    from app.main import app

    app.dependency_overrides.pop(get_storage, None)


def _login(client, user: dict) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class TestUploadResume:
    def test_requires_auth(self, client) -> None:
        response = client.post(
            "/api/v1/resumes", files={"file": ("resume.docx", _docx_bytes(), DOCX_MIME)}
        )
        assert response.status_code == 401
        assert response.json()["code"] == "UNAUTHORIZED"

    def test_upload_success(self, client, registered_user, uploads_dir) -> None:
        _login(client, registered_user)
        response = client.post(
            "/api/v1/resumes", files={"file": ("我的简历.docx", _docx_bytes(), DOCX_MIME)}
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["parse_status"] == "succeeded"
        assert body["original_name"] == "我的简历.docx"
        assert body["parse_error_code"] is None
        # 响应不泄露内部存储路径
        assert "stored_path" not in body
        assert len(list(uploads_dir.root.rglob("*我的简历*"))) == 0  # 文件按 uuid 命名

    def test_upload_rejects_oversize(self, client, registered_user, uploads_dir) -> None:
        _login(client, registered_user)
        big = b"x" * (10 * 1024 * 1024 + 1)
        response = client.post(
            "/api/v1/resumes", files={"file": ("big.pdf", big, "application/pdf")}
        )
        assert response.status_code == 413
        assert response.json()["code"] == "FILE_TOO_LARGE"
        # 磁盘上不残留文件
        assert list(uploads_dir.root.rglob("*big*")) == []

    def test_upload_rejects_unsupported_type(self, client, registered_user, uploads_dir) -> None:
        _login(client, registered_user)
        response = client.post(
            "/api/v1/resumes", files={"file": ("virus.exe", b"binary", "application/octet-stream")}
        )
        assert response.status_code == 415
        assert response.json()["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_upload_quota_exceeded(self, client, db_session, registered_user, uploads_dir) -> None:
        _login(client, registered_user)
        owner_id = uuid.UUID(registered_user["id"])
        for index in range(10):
            db_session.add(
                Resume(
                    owner_id=owner_id,
                    original_name=f"resume-{index}.pdf",
                    stored_path=f"resumes/{registered_user['id']}/{uuid.uuid4().hex}.pdf",
                    size_bytes=10,
                    content_type="application/pdf",
                    parse_status="succeeded",
                )
            )
        db_session.commit()

        response = client.post(
            "/api/v1/resumes", files={"file": ("one-more.docx", _docx_bytes(), DOCX_MIME)}
        )
        assert response.status_code == 409
        assert response.json()["code"] == "RESUME_QUOTA_EXCEEDED"

    def test_upload_parse_failure_is_reported(self, client, registered_user, uploads_dir) -> None:
        _login(client, registered_user)
        response = client.post(
            "/api/v1/resumes",
            files={"file": ("empty.pdf", _blank_pdf(), "application/pdf")},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["parse_status"] == "failed"
        assert body["parse_error_code"] == "PARSE_FAILED"
        assert body["parse_error"]


def _blank_pdf() -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class TestListResumes:
    def test_lists_only_own_resumes(self, client, db_session, registered_user, uploads_dir) -> None:
        _login(client, registered_user)
        for index in range(2):
            client.post(
                "/api/v1/resumes",
                files={"file": (f"resume-{index}.docx", _docx_bytes(), DOCX_MIME)},
            )

        other = User(email="other-user@example.com", password_hash="x", email_verified=False)
        db_session.add(other)
        db_session.commit()
        db_session.add(
            Resume(
                owner_id=other.id,
                original_name="hidden.docx",
                stored_path=f"resumes/{other.id}/x.docx",
                size_bytes=1,
                content_type=DOCX_MIME,
                parse_status="succeeded",
            )
        )
        db_session.commit()

        response = client.get("/api/v1/resumes")
        assert response.status_code == 200
        names = [item["original_name"] for item in response.json()]
        assert names == ["resume-0.docx", "resume-1.docx"]


class TestDeleteResume:
    def test_delete_removes_record_and_file(
        self, client, registered_user, uploads_dir
    ) -> None:
        _login(client, registered_user)
        created = client.post(
            "/api/v1/resumes", files={"file": ("to-delete.docx", _docx_bytes(), DOCX_MIME)}
        ).json()

        # 找到落盘文件
        files = [p for p in uploads_dir.root.rglob("*") if p.is_file()]
        assert len(files) == 1
        stored_relative = files[0].relative_to(uploads_dir.root).as_posix()

        response = client.delete(f"/api/v1/resumes/{created['id']}")
        assert response.status_code == 204
        assert client.get("/api/v1/resumes").json() == []
        assert list(uploads_dir.root.rglob("*to-delete*")) == []
        # 二次删除按不存在处理
        assert client.delete(f"/api/v1/resumes/{created['id']}").status_code == 404
        assert stored_relative

class TestPreviewResume:
    def test_preview_parsed_resume(self, client, registered_user, uploads_dir) -> None:
        _login(client, registered_user)
        created = client.post(
            "/api/v1/resumes",
            files={"file": ("预览简历.docx", _docx_bytes(["李四", "五年 Python 经验"]), DOCX_MIME)},
        ).json()

        response = client.get(f"/api/v1/resumes/{created['id']}/preview")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["original_name"] == "预览简历.docx"
        assert "李四" in body["parsed_text"]
        assert "五年 Python 经验" in body["parsed_text"]

    def test_preview_unparsed_resume_returns_409(
        self, client, registered_user, uploads_dir
    ) -> None:
        _login(client, registered_user)
        blank = client.post(
            "/api/v1/resumes",
            files={"file": ("blank.pdf", _blank_pdf(), "application/pdf")},
        ).json()

        response = client.get(f"/api/v1/resumes/{blank['id']}/preview")
        assert response.status_code == 409
        assert response.json()["code"] == "RESUME_NOT_PARSED"
        assert response.json()["message"]

    def test_preview_other_users_resume_returns_404(
        self, client, db_session, registered_user, uploads_dir
    ) -> None:
        _login(client, registered_user)
        other = User(email="preview-owner@example.com", password_hash="x", email_verified=False)
        db_session.add(other)
        db_session.commit()
        resume = Resume(
            owner_id=other.id,
            original_name="secret.docx",
            stored_path=f"resumes/{other.id}/p.docx",
            size_bytes=1,
            content_type=DOCX_MIME,
            parse_status="succeeded",
            parsed_text="秘密",
        )
        db_session.add(resume)
        db_session.commit()

        response = client.get(f"/api/v1/resumes/{resume.id}/preview")
        assert response.status_code == 404

    def test_delete_other_users_resume_returns_404(
        self, client, db_session, registered_user, uploads_dir
    ) -> None:
        _login(client, registered_user)
        other = User(email="owner-2@example.com", password_hash="x", email_verified=False)
        db_session.add(other)
        db_session.commit()
        resume = Resume(
            owner_id=other.id,
            original_name="secret.docx",
            stored_path=f"resumes/{other.id}/x.docx",
            size_bytes=1,
            content_type=DOCX_MIME,
            parse_status="succeeded",
        )
        db_session.add(resume)
        db_session.commit()

        response = client.delete(f"/api/v1/resumes/{resume.id}")
        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"
        # 他人简历仍在
        assert db_session.query(Resume).filter(Resume.id == resume.id).first() is not None
