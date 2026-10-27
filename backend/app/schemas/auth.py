"""认证相关请求与响应结构。"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not PASSWORD_PATTERN.match(value):
            raise ValueError("密码至少 8 位，且需同时包含字母与数字")
        return value


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOi...",
            "refresh_token": "Zm9vYmFy",
            "token_type": "bearer",
            "expires_in": 1800,
            "refresh_expires_in": 2592000,
        }
    })

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class RefreshRequest(BaseModel):
    """刷新令牌优先来自 httpOnly Cookie，body 仅作为非浏览器客户端的备选。"""

    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
