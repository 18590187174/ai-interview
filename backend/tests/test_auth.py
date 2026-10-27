"""认证流程：注册、登录、刷新轮换与重用检测、登出、获取当前用户。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.errors import ErrorCode
from app.models.refresh_token import RefreshToken
from app.services.token import hash_token

PASSWORD = "Passw0rd1"


def unique_email(prefix: str = "user") -> str:
    import os

    return f"{prefix}-{os.urandom(4).hex()}@example.com"


class TestRegister:
    def test_register_success(self, client):
        email = unique_email()
        response = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": PASSWORD},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == email
        assert body["email_verified"] is False
        assert "password" not in body and "password_hash" not in body

    def test_register_duplicate_email(self, client, registered_user):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": registered_user["email"], "password": PASSWORD},
        )
        assert response.status_code == 409
        assert response.json()["code"] == ErrorCode.EMAIL_ALREADY_REGISTERED

    def test_register_weak_password(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": unique_email(), "password": "short1"},
        )
        assert response.status_code == 422
        assert response.json()["code"] == ErrorCode.VALIDATION_ERROR

    def test_register_invalid_email(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": PASSWORD},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_returns_token_pair(self, client, registered_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["access_token"] and body["refresh_token"]
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0 and body["refresh_expires_in"] > 0

    def test_login_sets_http_only_cookie(self, client, registered_user):
        client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        )
        cookie_header = "; ".join(
            value for key, value in client.cookies.items() if key == "refresh_token"
        )
        assert cookie_header, "登录应下发 refresh_token Cookie"

    def test_login_wrong_password(self, client, registered_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": "WrongPass1"},
        )
        assert response.status_code == 401
        assert response.json()["code"] == ErrorCode.INVALID_CREDENTIALS

    def test_login_unknown_account_matches_wrong_password_response(self, client, registered_user):
        wrong_password = client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": "WrongPass1"},
        )
        unknown = client.post(
            "/api/v1/auth/login",
            json={"email": unique_email("ghost"), "password": "WrongPass1"},
        )
        assert unknown.status_code == wrong_password.status_code == 401
        assert unknown.json()["code"] == wrong_password.json()["code"]
        assert unknown.json()["message"] == wrong_password.json()["message"]


class TestRefreshRotation:
    def _login(self, client, user) -> str:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": user["email"], "password": user["password"]},
        )
        assert response.status_code == 200
        return response.json()

    def test_refresh_returns_new_pair(self, client, registered_user):
        tokens = self._login(client, registered_user)
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 200
        new_tokens = response.json()
        assert new_tokens["refresh_token"] != tokens["refresh_token"]
        assert new_tokens["access_token"]

    def test_reused_refresh_token_is_rejected_and_revokes_sessions(
        self, client, registered_user, db_session
    ):
        tokens = self._login(client, registered_user)
        first = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        rotated = first.json()["refresh_token"]

        reuse = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert reuse.status_code == 401
        assert reuse.json()["code"] == ErrorCode.REFRESH_TOKEN_REUSED

        # 重用触发该用户全部会话吊销
        after_revoke = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": rotated},
        )
        assert after_revoke.status_code == 401

        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(rotated)
        )
        assert db_session.scalar(stmt).revoked_at is not None

    def test_expired_refresh_token_is_rejected(self, client, registered_user, db_session):
        tokens = self._login(client, registered_user)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(tokens["refresh_token"])
        )
        token = db_session.scalar(stmt)
        token.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 401
        assert response.json()["code"] == ErrorCode.TOKEN_EXPIRED

    def test_refresh_without_token(self, client):
        response = client.post("/api/v1/auth/refresh", json={})
        assert response.status_code == 401
        assert response.json()["code"] == ErrorCode.TOKEN_INVALID


class TestLogout:
    def test_logout_revokes_token(self, client, registered_user):
        tokens = client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        ).json()
        refresh_token = tokens["refresh_token"]

        logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert logout.status_code == 204

        reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert reuse.status_code == 401

    def test_repeated_logout_still_succeeds(self, client, registered_user):
        tokens = client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        ).json()
        refresh_token = tokens["refresh_token"]

        first_logout = client.post(
            "/api/v1/auth/logout", json={"refresh_token": refresh_token}
        )
        second_logout = client.post(
            "/api/v1/auth/logout", json={"refresh_token": refresh_token}
        )
        assert first_logout.status_code == 204
        assert second_logout.status_code == 204


class TestCurrentUser:
    def test_me_with_valid_token(self, client, registered_user):
        access_token = client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        ).json()["access_token"]

        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == registered_user["email"]

    def test_me_without_token_returns_no_user_data(self, client):
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401
        assert "email" not in response.json()
