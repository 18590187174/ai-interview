"""系统设置端点测试：LLM 凭据的查询、更新与运行时生效。"""

from __future__ import annotations

from app.services.system_settings import effective_llm_config


def _login(client, user: dict) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"


class TestGetLLMSettings:
    def test_requires_auth(self, client) -> None:
        assert client.get("/api/v1/settings/llm").status_code == 401

    def test_read_requires_admin(self, client, registered_user) -> None:
        _login(client, registered_user)
        response = client.get("/api/v1/settings/llm")
        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"

    def test_update_requires_admin(self, client, registered_user) -> None:
        _login(client, registered_user)
        response = client.put("/api/v1/settings/llm", json={"model": "deepseek-chat"})
        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"

    def test_me_returns_is_admin_flag(self, client, registered_user, admin_user) -> None:
        _login(client, registered_user)
        assert client.get("/api/v1/users/me").json()["is_admin"] is False

        _login(client, admin_user)
        assert client.get("/api/v1/users/me").json()["is_admin"] is True

    def test_none_source_when_unconfigured(self, client, admin_user) -> None:
        _login(client, admin_user)
        body = client.get("/api/v1/settings/llm").json()
        assert body["has_api_key"] is False
        assert body["source"] == "none"

    def test_mask_never_returns_full_key(self, client, admin_user) -> None:
        _login(client, admin_user)
        client.put("/api/v1/settings/llm", json={"api_key": "sk-test-1234567890abcd"})
        body = client.get("/api/v1/settings/llm").json()

        assert body["has_api_key"] is True
        assert body["source"] == "database"
        assert body["api_key_masked"].startswith("***")
        assert body["api_key_masked"].endswith("abcd")
        assert "sk-test-1234567890abcd" not in __import__("json").dumps(body)


class TestUpdateLLMSettings:
    def test_update_key_keeps_when_absent(self, client, admin_user) -> None:
        _login(client, admin_user)
        client.put("/api/v1/settings/llm", json={"api_key": "sk-key-first"})

        response = client.put("/api/v1/settings/llm", json={"model": "deepseek-reasoner"})
        assert response.status_code == 200, response.text
        assert response.json()["has_api_key"] is True

        body = client.get("/api/v1/settings/llm").json()
        assert body["model"] == "deepseek-reasoner"
        assert body["api_key_masked"].endswith("irst")

    def test_clear_key_falls_back(self, client, admin_user) -> None:
        _login(client, admin_user)
        client.put("/api/v1/settings/llm", json={"api_key": "sk-to-be-cleared"})
        response = client.put("/api/v1/settings/llm", json={"api_key": ""})
        assert response.status_code == 200

        body = client.get("/api/v1/settings/llm").json()
        assert body["has_api_key"] is False
        assert body["source"] == "none"

    def test_invalid_base_url_rejected(self, client, admin_user) -> None:
        _login(client, admin_user)
        response = client.put(
            "/api/v1/settings/llm", json={"base_url": "ftp://not-http"}
        )
        assert response.status_code == 422

    def test_runtime_config_prefers_database(self, client, db_session, admin_user) -> None:
        _login(client, admin_user)
        client.put(
            "/api/v1/settings/llm",
            json={
                "api_key": "sk-from-database",
                "base_url": "https://api.example.com/v1",
                "model": "my-model",
            },
        )

        from app.core.config import get_settings

        config = effective_llm_config(db_session, get_settings())
        assert config.api_key == "sk-from-database"
        assert config.base_url == "https://api.example.com/v1"
        assert config.model == "my-model"
        assert config.source == "database"
