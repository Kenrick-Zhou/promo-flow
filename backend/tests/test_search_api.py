from collections.abc import Callable

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.content import ContentStatus, ContentType
from app.models.category import Category
from app.models.content import Content
from app.models.user import User
from app.services.infrastructure.storage import get_public_url


@pytest.mark.asyncio
async def test_search_route_returns_results(
    employee_client: AsyncClient,
    db: AsyncSession,
    employee_user: User,
    category: Category,
    make_search_name: Callable[[str], str],
    monkeypatch: pytest.MonkeyPatch,
):
    content = Content(
        title=make_search_name("促销海报"),
        description="夏季促销活动海报",
        content_type=ContentType.image,
        status=ContentStatus.approved,
        file_key=make_search_name("search.png"),
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
        "app.services.search.core.generate_embedding",
        fake_generate_embedding,
    )

    resp = await employee_client.post(
        "/api/v1/search",
        json={"query": "夏季促销", "limit": 10},
    )

    assert resp.status_code == 200
    data = resp.json()
    results = data["results"]
    assert len(results) >= 1
    ids = [r["content"]["id"] for r in results]
    assert content.id in ids
    matched = next(
        result for result in results if result["content"]["id"] == content.id
    )
    assert matched["content"]["file_url"] == get_public_url(content.file_key)


@pytest.mark.asyncio
async def test_search_route_orders_by_vector_similarity(
    employee_client: AsyncClient,
    db: AsyncSession,
    employee_user: User,
    category: Category,
    make_search_name: Callable[[str], str],
    monkeypatch: pytest.MonkeyPatch,
):
    """Different query embeddings should produce different result orderings."""
    emb_a = [1.0] + [0.0] * 1023
    emb_b = [0.0] + [1.0] + [0.0] * 1022

    content_a = Content(
        title=make_search_name("素材A"),
        description="A",
        content_type=ContentType.image,
        status=ContentStatus.approved,
        file_key=make_search_name("a.png"),
        uploaded_by=employee_user.id,
        category_id=category.id,
        embedding=emb_a,
        ai_keywords=[],
    )
    content_b = Content(
        title=make_search_name("素材B"),
        description="B",
        content_type=ContentType.image,
        status=ContentStatus.approved,
        file_key=make_search_name("b.png"),
        uploaded_by=employee_user.id,
        category_id=category.id,
        embedding=emb_b,
        ai_keywords=[],
    )
    db.add_all([content_a, content_b])
    await db.commit()

    async def fake_embedding_close_to_a(query: str) -> list[float]:
        return [0.9] + [0.1] + [0.0] * 1022

    monkeypatch.setattr(
        "app.services.search.core.generate_embedding",
        fake_embedding_close_to_a,
    )
    resp1 = await employee_client.post(
        "/api/v1/search", json={"query": "查询A", "limit": 10}
    )
    assert resp1.status_code == 200
    ids_1 = [r["content"]["id"] for r in resp1.json()["results"]]

    async def fake_embedding_close_to_b(query: str) -> list[float]:
        return [0.1] + [0.9] + [0.0] * 1022

    monkeypatch.setattr(
        "app.services.search.core.generate_embedding",
        fake_embedding_close_to_b,
    )
    resp2 = await employee_client.post(
        "/api/v1/search", json={"query": "查询B", "limit": 10}
    )
    assert resp2.status_code == 200
    ids_2 = [r["content"]["id"] for r in resp2.json()["results"]]

    assert ids_1 != ids_2
    assert ids_1[0] == content_a.id
    assert ids_2[0] == content_b.id
