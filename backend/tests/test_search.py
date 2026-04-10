import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.domains.content import ContentStatus, ContentType, UserRole
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
async def employee_client(
    client: AsyncClient,
    employee_user: User,
) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: employee_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def category(db: AsyncSession) -> Category:
    category = Category(
        name=_n(f"类目_{uuid.uuid4().hex[:4]}"),
        description="测试类目",
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@pytest.mark.asyncio
async def test_semantic_search_route_returns_results(
    employee_client: AsyncClient,
    db: AsyncSession,
    employee_user: User,
    category: Category,
    monkeypatch: pytest.MonkeyPatch,
):
    content = Content(
        title=_n("促销海报"),
        description="夏季促销活动海报",
        content_type=ContentType.image,
        status=ContentStatus.approved,
        file_key=_n("search.png"),
        uploaded_by=employee_user.id,
        category_id=category.id,
        embedding=[0.1] * 1024,
        ai_keywords=[],
    )
    db.add(content)
    await db.commit()

    async def fake_generate_embedding(query: str) -> list[float]:
        return [0.1] * 1024

    monkeypatch.setattr(
        "app.routers.search.generate_embedding", fake_generate_embedding
    )

    resp = await employee_client.post(
        "/api/v1/search",
        json={"query": "夏季促销", "limit": 10},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["content"]["id"] == content.id
    assert data[0]["content"]["title"] == content.title


@pytest.mark.asyncio
async def test_semantic_search_orders_by_similarity(
    employee_client: AsyncClient,
    db: AsyncSession,
    employee_user: User,
    category: Category,
    monkeypatch: pytest.MonkeyPatch,
):
    """Different query embeddings should produce different result orderings."""
    # Create two contents with distinct embeddings
    emb_a = [1.0] + [0.0] * 1023
    emb_b = [0.0] + [1.0] + [0.0] * 1022

    content_a = Content(
        title=_n("素材A"),
        description="A",
        content_type=ContentType.image,
        status=ContentStatus.approved,
        file_key=_n("a.png"),
        uploaded_by=employee_user.id,
        category_id=category.id,
        embedding=emb_a,
        ai_keywords=[],
    )
    content_b = Content(
        title=_n("素材B"),
        description="B",
        content_type=ContentType.image,
        status=ContentStatus.approved,
        file_key=_n("b.png"),
        uploaded_by=employee_user.id,
        category_id=category.id,
        embedding=emb_b,
        ai_keywords=[],
    )
    db.add_all([content_a, content_b])
    await db.commit()

    # Query with embedding close to A → A should rank first
    async def fake_embedding_close_to_a(query: str) -> list[float]:
        return [0.9] + [0.1] + [0.0] * 1022

    monkeypatch.setattr(
        "app.routers.search.generate_embedding", fake_embedding_close_to_a
    )
    resp1 = await employee_client.post(
        "/api/v1/search", json={"query": "查询A", "limit": 10}
    )
    assert resp1.status_code == 200
    ids_1 = [r["content"]["id"] for r in resp1.json()]

    # Query with embedding close to B → B should rank first
    async def fake_embedding_close_to_b(query: str) -> list[float]:
        return [0.1] + [0.9] + [0.0] * 1022

    monkeypatch.setattr(
        "app.routers.search.generate_embedding", fake_embedding_close_to_b
    )
    resp2 = await employee_client.post(
        "/api/v1/search", json={"query": "查询B", "limit": 10}
    )
    assert resp2.status_code == 200
    ids_2 = [r["content"]["id"] for r in resp2.json()]

    # The two queries must produce different orderings
    assert ids_1 != ids_2
    assert ids_1[0] == content_a.id
    assert ids_2[0] == content_b.id
