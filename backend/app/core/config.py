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

    # ── Search: Query Understanding ──────────────────────────
    SEARCH_ENABLE_LLM_QUERY_PARSE: bool = False
    SEARCH_LLM_QUERY_PARSE_MODEL: str = "qwen-turbo"
    SEARCH_LLM_QUERY_PARSE_TIMEOUT_S: int = 3

    # ── Search: Multi-path Recall ────────────────────────────
    SEARCH_VECTOR_RECALL_LIMIT: int = 50
    SEARCH_FTS_RECALL_LIMIT: int = 50
    SEARCH_TAG_RECALL_LIMIT: int = 30
    SEARCH_RRF_K: int = 60
    SEARCH_FTS_BACKEND: str = "ilike"  # "zhparser" | "ilike"
    SEARCH_FTS_ZH_TSCONFIG: str = "zhparser"  # e.g. zhcfg

    # ── Search: Business Scoring ─────────────────────────────
    SEARCH_SCORE_CONTENT_TYPE_MATCH: float = 80
    SEARCH_SCORE_TAG_EXACT: float = 100
    SEARCH_SCORE_TAG_PHRASE: float = 85
    SEARCH_SCORE_AI_KEYWORD_EXACT: float = 70
    SEARCH_SCORE_AI_KEYWORD_PHRASE: float = 55
    SEARCH_SCORE_TITLE_EXACT: float = 60
    SEARCH_SCORE_TITLE_PHRASE: float = 45
    SEARCH_SCORE_CATEGORY_EXACT: float = 40
    SEARCH_SCORE_CATEGORY_PHRASE: float = 30
    SEARCH_SCORE_MUST_TERM_DESC: float = 20
    SEARCH_SCORE_MUST_TERM_SUMMARY: float = 15
    SEARCH_SCORE_FTS_MAX: float = 30
    SEARCH_SCORE_VECTOR_MAX: float = 25
    SEARCH_SCORE_FRESHNESS_MAX: float = 5

    # ── Search: LLM Rerank ───────────────────────────────────
    SEARCH_ENABLE_LLM_RERANK: bool = False
    SEARCH_LLM_RERANK_MODEL: str = "qwen-turbo"
    SEARCH_LLM_RERANK_TOP_K: int = 10
    SEARCH_LLM_RERANK_CANDIDATE_LIMIT: int = 30
    SEARCH_LLM_RERANK_TIMEOUT_S: int = 8

    # ── Search: Observability ────────────────────────────────
    SEARCH_DEBUG_TIMING: bool = False

    # ── Hot Score ────────────────────────────────────────────
    HOT_SCORE_VIEW_WEIGHT: float = 1.0
    HOT_SCORE_DOWNLOAD_WEIGHT: float = 5.0
    HOT_SCORE_FRESHNESS_HALF_LIFE_DAYS: float = 10.0
    HOT_SCORE_TIME_DECAY_LAMBDA: float = 0.05


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
