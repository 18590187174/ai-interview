"""应用配置：全部来自环境变量，仓库中不存放任何密钥。"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

REQUIRED_SETTINGS_ZH = {
    "jwt_secret_key": "JWT_SECRET_KEY（令牌签名密钥）",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "AI 模拟面试平台"
    environment: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    # 数据库
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/ai_interview",
        alias="DATABASE_URL",
    )
    database_echo: bool = False

    # 认证与令牌
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 1800
    refresh_token_ttl_seconds: int = 2592000

    # Cookie（承载 Refresh Token）
    cookie_secure: bool = False
    cookie_samesite: Literal["strict", "lax", "none"] = "strict"
    cookie_domain: str | None = None

    # 跨域
    cors_origins: str = "http://localhost:5173"

    # 密码哈希（Argon2id）
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 4

    # 大模型（OpenAI 兼容接口，默认 DeepSeek；不配置 Key 时押题功能不可用，其余不受影响）
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: int = 120
    llm_temperature: float = 0.3
    llm_max_output_tokens: int = 4096
    prompt_version: str = "prediction-v1"
    prediction_question_count: int = 8

    # 文件上传
    upload_root: str = "var/uploads"
    upload_max_size_mb: int = 10
    resume_quota_per_user: int = 10
    resume_max_chars: int = 12000

    @property
    def upload_max_size_bytes(self) -> int:
        return self.upload_max_size_mb * 1024 * 1024

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        missing = []
        for error in exc.errors():
            field = ".".join(str(part) for part in error.get("loc", ()))
            missing.append(REQUIRED_SETTINGS_ZH.get(field, field))
        raise RuntimeError(f"缺少必需的配置项：{', '.join(missing)}") from exc


def clear_settings_cache() -> None:
    get_settings.cache_clear()
