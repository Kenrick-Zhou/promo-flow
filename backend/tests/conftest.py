from pathlib import Path

import pytest_asyncio
from dotenv import dotenv_values
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.db.base import Base  # noqa: F401 — imports all models so metadata is complete
from app.db.session import get_session
from app.main import app

# ---------------------------------------------------------------------------
# Load test database URL from .env.test (project root), falling back to .env.
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[2]  # promo-flow/
_test_env = dotenv_values(_ROOT / ".env.test") or dotenv_values(_ROOT / ".env")

_TEST_DB_URL = _test_env.get("DATABASE_URL")
if not _TEST_DB_URL:
    raise RuntimeError(
        "DATABASE_URL not found. Create .env.test at the project root "
        "(copy .env.test.example and fill in your test database credentials)."
    )

# Unique prefix for all test data — makes bulk-cleanup safe and deterministic
TEST_PREFIX = "__pytest__"


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncEngine:
    """Session-scoped engine (NullPool to avoid cross-loop connection reuse)."""
    e = create_async_engine(_TEST_DB_URL, poolclass=NullPool)
    yield e
    await e.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_schema(engine: AsyncEngine) -> None:
    """Create pgvector extension + all tables at session start."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(scope="session", autouse=True)
async def cleanup_test_data(engine: AsyncEngine, setup_schema) -> None:
    """Delete all rows whose names start with TEST_PREFIX after the session."""
    yield
    async with AsyncSession(engine) as session:
        await session.execute(
            text(
                "DELETE FROM content_tags WHERE tag_id IN "
                "(SELECT id FROM tags WHERE name LIKE :prefix)"
            ),
            {"prefix": f"{TEST_PREFIX}%"},
        )
        await session.execute(
            text("DELETE FROM tags WHERE name LIKE :prefix"),
            {"prefix": f"{TEST_PREFIX}%"},
        )
        await session.execute(
            text("DELETE FROM categories WHERE name LIKE :prefix"),
            {"prefix": f"{TEST_PREFIX}%"},
        )
        await session.execute(
            text("DELETE FROM users WHERE feishu_open_id LIKE :prefix"),
            {"prefix": f"{TEST_PREFIX}%"},
        )
        await session.commit()


@pytest_asyncio.fixture
async def db(engine: AsyncEngine) -> AsyncSession:
    """Regular AsyncSession per test (for direct DB assertions)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture
async def client(engine: AsyncEngine) -> AsyncClient:
    """HTTP client wired to the FastAPI app. Overrides get_session so every
    request goes to the *test* database instead of the development database."""
    test_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
