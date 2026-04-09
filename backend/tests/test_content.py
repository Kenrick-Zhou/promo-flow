import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import app.routers.content as content_router
import app.services.infrastructure.ai as ai_service
from app.core.deps import get_current_user
from app.domains.content import ContentType, CreateContentCommand, UserRole
from app.main import app
from app.models.category import Category
from app.models.content import Content
from app.models.user import User
from app.services.content import create_content
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
) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_current_user] = lambda: employee_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def primary_category(db: AsyncSession) -> Category:
    category = Category(
        name=_n(f"一级类目_{uuid.uuid4().hex[:4]}"),
        description="测试一级类目",
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@pytest_asyncio.fixture
async def secondary_category(db: AsyncSession, primary_category: Category) -> Category:
    category = Category(
        name=_n(f"二级类目_{uuid.uuid4().hex[:4]}"),
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
async def test_get_presigned_upload_url_includes_signed_headers(
    employee_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_generate_presigned_upload_url(
        file_key: str,
        expires: int = 300,
        headers: dict[str, str] | None = None,
    ) -> str:
        assert file_key == "uploads/fixed/demo.jpg"
        assert expires == 300
        assert headers == {"Content-Type": "image/jpeg"}
        return "https://example.com/upload"

    monkeypatch.setattr(
        content_router,
        "generate_file_key",
        lambda filename: "uploads/fixed/demo.jpg",
    )
    monkeypatch.setattr(
        content_router,
        "generate_presigned_upload_url",
        fake_generate_presigned_upload_url,
    )

    resp = await employee_client.get(
        "/api/v1/contents/presigned-upload",
        params={"filename": "demo.jpg", "content_type": "image/jpeg"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data == {
        "upload_url": "https://example.com/upload",
        "file_key": "uploads/fixed/demo.jpg",
        "upload_headers": {"Content-Type": "image/jpeg"},
    }


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
    assert data["title"] == "待AI生成"
    assert data["ai_status"] == "pending"
    assert data["description"] == "测试描述"
    assert data["category_id"] == secondary_category.id
    assert data["tags"] == [_n("标签一")]

    result = await db.execute(select(Content).where(Content.id == data["id"]))
    content = result.scalar_one()
    assert content.title == "待AI生成"


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


@pytest.mark.asyncio
async def test_run_ai_analysis_uses_context_and_generates_title_after_analysis(
    db: AsyncSession,
    engine: AsyncEngine,
    employee_user: User,
    secondary_category: Category,
    monkeypatch: pytest.MonkeyPatch,
):
    output = await create_content(
        db,
        command=CreateContentCommand(
            title=None,
            description="适合女性营养场景的宣传图",
            tag_names=[_n("胶原蛋白"), _n("焕亮")],
            content_type=ContentType.image,
            file_key=_n("analysis-sequence.png"),
            uploaded_by=employee_user.id,
            category_id=secondary_category.id,
        ),
    )
    assert secondary_category.parent is not None
    primary_category_name = secondary_category.parent.name
    events: list[str] = []
    captured_analysis: dict[str, object] = {}
    captured_title: dict[str, object] = {}

    async def fake_analyze_content(
        file_url: str,
        content_type: str,
        **kwargs: object,
    ) -> dict[str, object]:
        events.append("analyze")
        captured_analysis.update(
            {
                "file_url": file_url,
                "content_type": content_type,
                **kwargs,
            }
        )
        return {
            "summary": "强调胶原蛋白产品卖点与目标人群。",
            "keywords": ["胶原蛋白", "焕亮", "女性营养"],
        }

    async def fake_generate_content_title(
        content_type: str,
        **kwargs: object,
    ) -> str:
        events.append("title")
        captured_title.update({"content_type": content_type, **kwargs})
        return "胶原蛋白焕亮海报"

    async def fake_generate_embedding(text: str) -> list[float]:
        events.append("embedding")
        expected_text = (
            "胶原蛋白焕亮海报 "
            "强调胶原蛋白产品卖点与目标人群。 "
            "胶原蛋白 焕亮 女性营养"
        )
        assert text == expected_text
        return [0.0] * 1024

    test_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    monkeypatch.setattr(
        content_router,
        "get_public_url",
        lambda file_key: f"https://example.com/{file_key}",
    )
    monkeypatch.setattr(ai_service, "analyze_content", fake_analyze_content)
    monkeypatch.setattr(
        ai_service, "generate_content_title", fake_generate_content_title
    )
    monkeypatch.setattr(ai_service, "generate_embedding", fake_generate_embedding)
    monkeypatch.setattr("app.db.session.AsyncSessionLocal", test_session_maker)

    await content_router._run_ai_analysis(
        output.id,
        output.file_key,
        output.content_type.value,
    )

    assert events == ["analyze", "title", "embedding"]
    assert captured_analysis == {
        "file_url": f"https://example.com/{output.file_key}",
        "content_type": "image",
        "primary_category_name": primary_category_name,
        "category_name": secondary_category.name,
        "tags": [_n("胶原蛋白"), _n("焕亮")],
        "description": "适合女性营养场景的宣传图",
    }
    assert captured_title == {
        "content_type": "image",
        "primary_category_name": primary_category_name,
        "category_name": secondary_category.name,
        "tags": [_n("胶原蛋白"), _n("焕亮")],
        "description": "适合女性营养场景的宣传图",
        "summary": "强调胶原蛋白产品卖点与目标人群。",
        "keywords": ["胶原蛋白", "焕亮", "女性营养"],
    }

    result = await db.execute(select(Content).where(Content.id == output.id))
    content = result.scalar_one()
    assert content.title == "胶原蛋白焕亮海报"
    assert content.ai_summary == "强调胶原蛋白产品卖点与目标人群。"
    assert content.ai_keywords == ["胶原蛋白", "焕亮", "女性营养"]
    assert content.ai_status.value == "completed"
