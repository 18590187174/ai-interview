"""字典端点测试。"""

from __future__ import annotations


def _login(client, user: dict) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"


class TestCreateDictItem:
    def test_requires_auth(self, client) -> None:
        response = client.post(
            "/api/v1/dictionaries", json={"type": "target_role", "label": "后端工程师"}
        )
        assert response.status_code == 401

    def test_write_requires_admin(self, client, registered_user) -> None:
        _login(client, registered_user)
        response = client.post(
            "/api/v1/dictionaries", json={"type": "target_role", "label": "后端工程师"}
        )
        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"

    def test_delete_requires_admin(self, client, registered_user) -> None:
        _login(client, registered_user)
        response = client.delete("/api/v1/dictionaries/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 403

    def test_create_success(self, client, admin_user) -> None:
        _login(client, admin_user)
        response = client.post(
            "/api/v1/dictionaries", json={"type": "target_role", "label": "后端工程师"}
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["type"] == "target_role"
        assert body["label"] == "后端工程师"
        assert body["value"] == "后端工程师"
        assert body["enabled"] is True

    def test_create_with_explicit_value(self, client, admin_user) -> None:
        _login(client, admin_user)
        response = client.post(
            "/api/v1/dictionaries",
            json={"type": "programming_language", "label": "JS/TS", "value": "javascript"},
        )
        assert response.status_code == 201
        assert response.json()["value"] == "javascript"

    def test_rejects_unknown_type(self, client, admin_user) -> None:
        _login(client, admin_user)
        response = client.post(
            "/api/v1/dictionaries", json={"type": "unknown_type", "label": "x"}
        )
        assert response.status_code == 422

    def test_rejects_blank_label(self, client, admin_user) -> None:
        _login(client, admin_user)
        response = client.post(
            "/api/v1/dictionaries", json={"type": "target_role", "label": "  "}
        )
        assert response.status_code == 422

    def test_duplicate_type_value_rejected(self, client, admin_user) -> None:
        _login(client, admin_user)
        payload = {"type": "target_role", "label": "测试工程师"}
        assert client.post("/api/v1/dictionaries", json=payload).status_code == 201
        assert client.post("/api/v1/dictionaries", json=payload).status_code == 409


class TestListDictItems:
    def test_list_by_type_only_enabled(self, client, admin_user, registered_user) -> None:
        _login(client, admin_user)
        client.post("/api/v1/dictionaries", json={"type": "target_role", "label": "后端工程师"})
        client.post(
            "/api/v1/dictionaries", json={"type": "programming_language", "label": "Python"}
        )

        # 普通用户可读取（押题向导依赖），但列表中只有启用项
        client.headers["Authorization"] = ""
        _login(client, registered_user)
        roles = client.get("/api/v1/dictionaries/target_role").json()
        langs = client.get("/api/v1/dictionaries/programming_language").json()
        assert [item["label"] for item in roles] == ["后端工程师"]
        assert [item["label"] for item in langs] == ["Python"]

    def test_list_rejects_unknown_type(self, client, registered_user) -> None:
        _login(client, registered_user)
        assert client.get("/api/v1/dictionaries/whatever").status_code == 422

    def test_list_all_groups(self, client, admin_user) -> None:
        _login(client, admin_user)
        client.post("/api/v1/dictionaries", json={"type": "target_role", "label": "后端工程师"})
        client.post("/api/v1/dictionaries", json={"type": "programming_language", "label": "Go"})
        items = client.get("/api/v1/dictionaries").json()
        assert {item["type"] for item in items} == {"target_role", "programming_language"}


class TestDeleteDictItem:
    def test_delete_success(self, client, admin_user) -> None:
        _login(client, admin_user)
        created = client.post(
            "/api/v1/dictionaries", json={"type": "target_role", "label": "待删除"}
        ).json()
        assert client.delete(f"/api/v1/dictionaries/{created['id']}").status_code == 204
        assert client.get("/api/v1/dictionaries/target_role").json() == []

    def test_delete_missing_returns_404(self, client, admin_user) -> None:
        _login(client, admin_user)
        response = client.delete("/api/v1/dictionaries/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
