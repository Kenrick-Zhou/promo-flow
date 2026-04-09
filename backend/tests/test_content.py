import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.routers.content as content_router
from app.core.deps import get_current_user
from app.domains.content import UserRole
from app.main import app
from app.models.category import Category
from app.models.content import Content
from app.models.user import User
from tests.conftest import TEST_PREFIX

_RUN = uuid.uuid4().hex[:8]


def _n(name: str) -> str:
    return f"{TEST_PREFIX}{_RUN}_{name}"


@pytest_asyncio.fixture
async def employee_user(db: AsyncSession) -> User:
    user = User(
        feishu_open_id=_n(f"emp_{uuid.uuid4().hex[:4]}"),
        feishu_union_id=_n(f"union_{uuid.uuid4().hex[:4]}"),
        name="测试员工",
        role=UserRole.employee,
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def employee_client(client: AsyncClient, employee_user: User) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: employee_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def primary_category(db: AsyncSession) -> Category:
    category = Category(
        name=_n("一级类目"),
        description="测试一级类目",
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@pytest_asyncio.fixture
async def secondary_category(db: AsyncSession, primary_category: Category) -> Category:
    category = Category(
        name=_n("二级类目"),
        description="测试二级类目",
        parent_id=primary_category.id,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_list_contents_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/contents")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_content_without_title(
    employee_client: AsyncClient,
    db: AsyncSession,
    secondary_category: Category,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_run_ai_analysis(
        content_id: int, file_key: str, content_type: str
    ) -> None:
        return None

    monkeypatch.setattr(content_router, "_run_ai_analysis", fake_run_ai_analysis)

    resp = await employee_client.post(
        "/api/v1/contents",
        json={
            "description": "测试描述",
            "tag_names": [_n("标签一")],
            "content_type": "image",
            "file_key": _n("content-without-title.png"),
            "category_id": secondary_category.id,
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] is None
    assert data["description"] == "测试描述"
    assert data["category_id"] == secondary_category.id
    assert data["tags"] == [_n("标签一")]

    result = await db.execute(select(Content).where(Content.id == data["id"]))
    content = result.scalar_one()
    assert content.title is None


@pytest.mark.asyncio
async def test_create_content_with_primary_category_rejected(
    employee_client: AsyncClient,
    primary_category: Category,
):
    resp = await employee_client.post(
        "/api/v1/contents",
        json={
            "description": "测试描述",
            "tag_names": [],
            "content_type": "image",
            "file_key": _n("invalid-category.png"),
            "category_id": primary_category.id,
        },
    )

    assert resp.status_code == 400
    data = resp.json()
    assert data["error_code"] == "invalid_category"
    assert "二级类目" in data["message"]
    assert data["request_id"]
    assert resp.headers["X-Request-ID"] == data["request_id"]
