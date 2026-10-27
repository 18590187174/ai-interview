"""知识库文档端点测试与检索服务测试。"""

from __future__ import annotations

import uuid

import pytest

from app.api.deps import get_storage
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.user import User
from app.services.knowledge import extract_terms, retrieve_chunks, split_chunks
from app.services.storage import LocalStorage

MD_MIME = "text/markdown"


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


class TestSplitChunks:
    def test_short_text_single_chunk(self) -> None:
        assert split_chunks("短文本") == ["短文本"]

    def test_long_text_overlapping_chunks(self) -> None:
        text = "".join(str(i % 10) for i in range(1000))
        chunks = split_chunks(text, size=100, overlap=20)
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)
        # 相邻片段有重叠
        assert chunks[0][-20:] == chunks[1][:20]

    def test_extract_terms_mixed_language(self) -> None:
        terms = extract_terms("招聘 Python 后端工程师，熟悉 FastAPI")
        assert "python" in terms
        assert "后端" in terms
        assert "fastapi" in terms


class TestUploadDocument:
    def test_upload_md_creates_chunks(
        self, client, registered_user, uploads_dir, db_session
    ) -> None:
        _login(client, registered_user)
        long_text = "人工智能面试要点。" * 60  # 足够多分片
        response = client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("notes.md", long_text.encode("utf-8"), MD_MIME)},
            data={"is_public": "true"},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["retrievable"] is True
        assert body["is_public"] is True
        assert body["parse_error_code"] is None
        assert KnowledgeChunk.document_id  # 模型可引用

    def test_upload_empty_document_marked_not_retrievable(
        self, client, registered_user, uploads_dir
    ) -> None:
        _login(client, registered_user)
        import io

        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        buffer = io.BytesIO()
        writer.write(buffer)

        response = client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("blank.pdf", buffer.getvalue(), "application/pdf")},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["retrievable"] is False
        assert body["parse_error_code"] == "PARSE_FAILED"
        assert body["parse_error"]

    def test_upload_rejects_unsupported(self, client, registered_user, uploads_dir) -> None:
        _login(client, registered_user)
        response = client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("evil.exe", b"binary", "application/octet-stream")},
        )
        assert response.status_code == 415
        assert response.json()["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_upload_rejects_oversize(self, client, registered_user, uploads_dir) -> None:
        _login(client, registered_user)
        response = client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("big.md", b"x" * (10 * 1024 * 1024 + 1), MD_MIME)},
        )
        assert response.status_code == 413
        assert response.json()["code"] == "FILE_TOO_LARGE"


class TestVisibility:
    def test_list_shows_public_and_own_only(
        self, client, db_session, registered_user, uploads_dir
    ) -> None:
        _login(client, registered_user)
        client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("mine.md", "我的文档".encode(), MD_MIME)},
        )
        other = User(email="kb-owner@example.com", password_hash="x", email_verified=False)
        db_session.add(other)
        db_session.commit()
        db_session.add(
            KnowledgeDocument(
                owner_id=other.id,
                name="private.md",
                stored_path=f"knowledge/{other.id}/x.md",
                size_bytes=1,
                content_type=MD_MIME,
                is_public=False,
                retrievable=True,
            )
        )
        db_session.add(
            KnowledgeDocument(
                owner_id=other.id,
                name="shared.md",
                stored_path=f"knowledge/{other.id}/y.md",
                size_bytes=1,
                content_type=MD_MIME,
                is_public=True,
                retrievable=True,
            )
        )
        db_session.commit()

        names = [item["name"] for item in client.get("/api/v1/knowledge/documents").json()]
        assert set(names) == {"mine.md", "shared.md"}

    def test_read_other_private_document_returns_404(
        self, client, db_session, registered_user, uploads_dir
    ) -> None:
        _login(client, registered_user)
        other = User(email="kb-private@example.com", password_hash="x", email_verified=False)
        db_session.add(other)
        db_session.commit()
        private = KnowledgeDocument(
            owner_id=other.id,
            name="secret.md",
            stored_path=f"knowledge/{other.id}/s.md",
            size_bytes=1,
            content_type=MD_MIME,
            is_public=False,
            retrievable=True,
        )
        db_session.add(private)
        db_session.commit()

        response = client.get(f"/api/v1/knowledge/documents/{private.id}")
        assert response.status_code == 404


class TestDeleteDocument:
    def test_delete_own_document_removes_chunks(
        self, client, db_session, registered_user, uploads_dir
    ) -> None:
        _login(client, registered_user)
        created = client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("delete-me.md", ("段落一。" * 100).encode(), MD_MIME)},
        ).json()
        document_id = uuid.UUID(created["id"])
        assert db_session.query(KnowledgeChunk).filter_by(document_id=document_id).count() > 0

        response = client.delete(f"/api/v1/knowledge/documents/{created['id']}")
        assert response.status_code == 204
        assert db_session.query(KnowledgeChunk).filter_by(document_id=document_id).count() == 0
        assert db_session.query(KnowledgeDocument).filter_by(id=document_id).first() is None

    def test_delete_others_public_document_returns_403(
        self, client, db_session, registered_user, uploads_dir
    ) -> None:
        _login(client, registered_user)
        other = User(email="kb-pub@example.com", password_hash="x", email_verified=False)
        db_session.add(other)
        db_session.commit()
        shared = KnowledgeDocument(
            owner_id=other.id,
            name="public.md",
            stored_path=f"knowledge/{other.id}/p.md",
            size_bytes=1,
            content_type=MD_MIME,
            is_public=True,
            retrievable=True,
        )
        db_session.add(shared)
        db_session.commit()

        response = client.delete(f"/api/v1/knowledge/documents/{shared.id}")
        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"
        assert db_session.query(KnowledgeDocument).filter_by(id=shared.id).first() is not None


class TestRetrieval:
    def test_related_chunks_rank_first(
        self, client, db_session, registered_user, uploads_dir
    ) -> None:
        _login(client, registered_user)
        client.post(
            "/api/v1/knowledge/documents",
            files={
                "file": (
                    "tech.md",
                    "后端工程师需要深入理解 Python 语言特性，"
                    "熟悉 FastAPI 框架与数据库设计。".encode(),
                    MD_MIME,
                )
            },
            data={"is_public": "true"},
        )
        client.post(
            "/api/v1/knowledge/documents",
            files={
                "file": (
                    "finance.md",
                    "会计师需要掌握企业会计准则与财务报表编制规范。".encode(),
                    MD_MIME,
                )
            },
            data={"is_public": "true"},
        )

        results = retrieve_chunks(
            db_session,
            user=db_session.query(User).filter_by(email=registered_user["email"]).first(),
            target_role="Python 后端工程师",
            job_description="负责后端服务开发，使用 Python 与 FastAPI，熟悉数据库。",
        )
        assert results, "应检索到相关片段"
        contents = [chunk.content for chunk, _ in results]
        assert any("Python" in content for content in contents)
        assert not any("会计" in content for content in results[0][0].content)

    def test_private_documents_are_not_retrieved(
        self, client, db_session, registered_user, uploads_dir
    ) -> None:
        other = User(email="kb-rank@example.com", password_hash="x", email_verified=False)
        db_session.add(other)
        db_session.commit()
        private_doc = KnowledgeDocument(
            owner_id=other.id,
            name="private-tech.md",
            stored_path=f"knowledge/{other.id}/t.md",
            size_bytes=10,
            content_type=MD_MIME,
            is_public=False,
            retrievable=True,
        )
        db_session.add(private_doc)
        db_session.commit()
        db_session.add(
            KnowledgeChunk(
                document_id=private_doc.id,
                chunk_index=0,
                content="Python 后端工程师面试要点：FastAPI 与数据库。",
            )
        )
        db_session.commit()

        user = db_session.query(User).filter_by(email=registered_user["email"]).first()
        results = retrieve_chunks(
            db_session, user=user, target_role="Python 后端", job_description="Python 开发"
        )
        assert results == []
