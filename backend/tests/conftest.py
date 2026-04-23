import uuid
from collections.abc import Callable
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

from app.core.deps import get_current_user
from app.db.base import Base  # noqa: F401 — imports all models so metadata is complete
from app.db.session import get_session
from app.domains.content import UserRole
from app.main import app
from app.models.category import Category
from app.models.user import User

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

# Each worker process gets its own unique suffix so parallel workers don't
# delete each other's in-flight data during session-scoped cleanup.
_WORKER_ID = uuid.uuid4().hex[:8]
TEST_PREFIX = f"__pytest__{_WORKER_ID}_"


@pytest_asyncio.fixture
def make_search_name() -> Callable[[str], str]:
    """Return a per-test helper for generating cleanup-friendly names."""

    run_id = uuid.uuid4().hex[:8]

    def _make(name: str) -> str:
        return f"{TEST_PREFIX}{run_id}_{name}"

    return _make


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
                "DELETE FROM audit_logs WHERE content_id IN "
                "(SELECT id FROM contents WHERE file_key LIKE :prefix)"
            ),
            {"prefix": f"{TEST_PREFIX}%"},
        )
        await session.execute(
            text("DELETE FROM contents WHERE file_key LIKE :prefix"),
            {"prefix": f"{TEST_PREFIX}%"},
        )
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


@pytest_asyncio.fixture
async def employee_user(
    db: AsyncSession,
    make_search_name: Callable[[str], str],
) -> User:
    user = User(
        feishu_open_id=make_search_name(f"emp_{uuid.uuid4().hex[:4]}"),
        feishu_union_id=make_search_name(f"union_{uuid.uuid4().hex[:4]}"),
        name="测试员工",
        role=UserRole.employee,
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def employee_client(
    client: AsyncClient,
    employee_user: User,
) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: employee_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def category(
    db: AsyncSession,
    make_search_name: Callable[[str], str],
) -> Category:
    category = Category(
        name=make_search_name(f"类目_{uuid.uuid4().hex[:4]}"),
        description="测试类目",
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category
