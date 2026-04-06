from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# Mono-repo: .env lives at project root (one level above backend/)
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # .env 文件优先级高于 shell 环境变量
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )

    APP_ENV: Literal["development", "production", "test"] = "development"
    APP_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    DATABASE_URL: str

    # Aliyun OSS
    OSS_ACCESS_KEY_ID: str
    OSS_ACCESS_KEY_SECRET: str
    OSS_BUCKET_NAME: str
    OSS_ENDPOINT: str
    OSS_BUCKET_DOMAIN: str = ""

    # Feishu
    FEISHU_APP_ID: str
    FEISHU_APP_SECRET: str
    FEISHU_VERIFICATION_TOKEN: str
    FEISHU_ENCRYPT_KEY: str
    FEISHU_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"

    # AI
    DASHSCOPE_API_KEY: str
    DASHSCOPE_VISION_MODEL: str = "qwen-vl-plus"
    DASHSCOPE_EMBEDDING_MODEL: str = "text-embedding-v3"
    DASHSCOPE_RAG_MODEL: str = "qwen3.5-flash"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
