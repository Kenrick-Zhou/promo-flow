import uuid
from collections.abc import AsyncGenerator
from types import SimpleNamespace

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import app.routers.content as content_router
import app.services.content.core as content_core
import app.services.infrastructure.ai as ai_service
from app.core.deps import get_current_user
from app.domains.content import (
    AiStatus,
    ContentOutput,
    ContentStatus,
    ContentType,
    CreateContentCommand,
    UserRole,
)
from app.main import app
from app.models.category import Category
from app.models.content import Content
from app.models.user import User
from app.services.content import create_content
from app.services.content.core import (
    _render_download_intro_markdown,
    send_file_to_chat,
    send_file_to_user,
)
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
async def test_create_content_rejects_document_content_type(
    employee_client: AsyncClient,
    secondary_category: Category,
):
    resp = await employee_client.post(
        "/api/v1/contents",
        json={
            "description": "测试描述",
            "tag_names": [],
            "content_type": "document",
            "file_key": _n("invalid-document.bin"),
            "category_id": secondary_category.id,
        },
    )

    assert resp.status_code == 422
    data = resp.json()
    assert data["error_code"] == "validation_error"
    assert data["message"] == "Validation failed"
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
        # New format: build_embedding_text includes title, description, tags,
        # ai_keywords, ai_summary, primary_category, category, type_label
        assert "胶原蛋白焕亮海报" in text
        assert "强调胶原蛋白产品卖点与目标人群。" in text
        assert "图片 图像" in text
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
    assert content.search_document is not None
    assert content.embedding_text is not None


def test_render_download_intro_markdown_includes_key_fields():
    markdown = _render_download_intro_markdown(
        ContentOutput(
            id=1,
            title="春季焕新主视觉",
            description=None,
            tags=["海报", "春季上新"],
            content_type=ContentType.image,
            status=ContentStatus.approved,
            file_key="uploads/demo.png",
            file_url="https://example.com/demo.png",
            file_size=None,
            media_width=None,
            media_height=None,
            view_count=128,
            download_count=32,
            ai_summary="画面以清新绿色为主，突出春日促销氛围。",
            ai_keywords=["春季营销", "清新", "促销海报"],
            ai_status=AiStatus.completed,
            ai_error=None,
            ai_processed_at=None,
            uploaded_by=7,
            uploaded_by_name="市场设计组",
            category_id=11,
            category_name="活动海报",
            primary_category_name="电商设计",
            created_at="2026-04-13T00:00:00+00:00",
            updated_at="2026-04-13T00:00:00+00:00",
        )
    )

    assert "春季焕新主视觉" in markdown
    assert "电商设计 / 活动海报" in markdown
    assert "海报、春季上新" in markdown
    assert "春季营销、清新、促销海报" in markdown
    assert "市场设计组" in markdown
    assert "浏览 128 次，下载 32 次" in markdown


def _build_download_output(*, content_type: ContentType) -> ContentOutput:
    return ContentOutput(
        id=1,
        title="春季焕新主视觉",
        description=None,
        tags=["海报", "春季上新"],
        content_type=content_type,
        status=ContentStatus.approved,
        file_key=(
            "uploads/demo.png"
            if content_type == ContentType.image
            else "uploads/demo.mp4"
        ),
        file_url=(
            "https://example.com/demo.png"
            if content_type == ContentType.image
            else "https://example.com/demo.mp4"
        ),
        file_size=None,
        media_width=None,
        media_height=None,
        view_count=128,
        download_count=32,
        ai_summary="画面以清新绿色为主，突出春日促销氛围。",
        ai_keywords=["春季营销", "清新", "促销海报"],
        ai_status=AiStatus.completed,
        ai_error=None,
        ai_processed_at=None,
        uploaded_by=7,
        uploaded_by_name="市场设计组",
        category_id=11,
        category_name="活动海报",
        primary_category_name="电商设计",
        created_at="2026-04-13T00:00:00+00:00",
        updated_at="2026-04-13T00:00:00+00:00",
    )


def _install_download_test_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    content_type: ContentType,
    fail_markdown: bool = False,
    target_kind: str = "user",
) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []
    output = _build_download_output(content_type=content_type)
    content = SimpleNamespace(
        file_url=output.file_url,
        file_key=output.file_key,
        content_type=output.content_type,
    )

    class _AsyncSessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeResponse:
        status_code = 200
        headers = {"content-length": "3"}

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self, chunk_size: int):
            assert chunk_size == 65536
            yield b"abc"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeHttpClient:
        def __init__(self, *, timeout: float):
            assert timeout == 120.0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def stream(self, method: str, url: str):
            assert method == "GET"
            assert url == output.file_url
            return _FakeResponse()

    async def fake_get_content_orm(db: object, content_id: int):
        assert content_id == 1
        return content

    async def fake_send_markdown(open_id: str, title: str, markdown: str) -> None:
        events.append(("markdown", markdown))
        assert open_id == "ou_test"
        assert title == "素材已开始准备"
        if fail_markdown:
            raise RuntimeError("markdown failed")

    async def fake_send_card(chat_id: str, title: str, markdown: str) -> None:
        events.append(("card", markdown))
        assert chat_id == "oc_test_chat"
        assert title == "素材已开始准备"
        if fail_markdown:
            raise RuntimeError("card failed")

    def fake_send_image(open_id: str, file_stream, file_name: str) -> None:
        events.append(("image", file_name))
        assert open_id == "ou_test"
        assert file_stream.read() == b"abc"

    def fake_send_file(open_id: str, file_stream, file_name: str) -> None:
        events.append(("file", file_name))
        assert open_id == "ou_test"
        assert file_stream.read() == b"abc"

    def fake_send_image_to_chat(chat_id: str, file_stream, file_name: str) -> None:
        events.append(("chat_image", file_name))
        assert chat_id == "oc_test_chat"
        assert file_stream.read() == b"abc"

    def fake_send_file_to_chat(chat_id: str, file_stream, file_name: str) -> None:
        events.append(("chat_file", file_name))
        assert chat_id == "oc_test_chat"
        assert file_stream.read() == b"abc"

    async def fake_to_thread(func, *args):
        func(*args)

    monkeypatch.setattr(content_core, "get_content_orm", fake_get_content_orm)
    monkeypatch.setattr(content_core, "_content_to_output", lambda _: output)
    monkeypatch.setattr(
        content_core, "_render_download_intro_markdown", lambda _: "介绍文案"
    )
    monkeypatch.setattr(
        "app.db.session.AsyncSessionLocal", lambda: _AsyncSessionContext()
    )
    monkeypatch.setattr(
        "app.services.infrastructure.feishu.send_markdown_to_user",
        fake_send_markdown,
    )
    monkeypatch.setattr(
        "app.services.infrastructure.feishu.send_interactive_card_to_chat",
        fake_send_card,
    )
    monkeypatch.setattr(
        "app.services.infrastructure.feishu.send_image_to_user_sync", fake_send_image
    )
    monkeypatch.setattr(
        "app.services.infrastructure.feishu.send_file_to_user_sync", fake_send_file
    )
    monkeypatch.setattr(
        "app.services.infrastructure.feishu.send_image_to_chat_sync",
        fake_send_image_to_chat,
    )
    monkeypatch.setattr(
        "app.services.infrastructure.feishu.send_file_to_chat_sync",
        fake_send_file_to_chat,
    )
    monkeypatch.setattr("httpx.Client", _FakeHttpClient)
    monkeypatch.setattr("asyncio.to_thread", fake_to_thread)
    return events


@pytest.mark.asyncio
async def test_send_file_to_user_sends_markdown_before_image(
    monkeypatch: pytest.MonkeyPatch,
):
    events = _install_download_test_stubs(monkeypatch, content_type=ContentType.image)

    await send_file_to_user(1, feishu_open_id="ou_test")

    assert events == [
        ("markdown", "介绍文案"),
        ("image", "demo.png"),
    ]


@pytest.mark.asyncio
async def test_send_file_to_user_continues_when_markdown_send_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    events = _install_download_test_stubs(
        monkeypatch,
        content_type=ContentType.video,
        fail_markdown=True,
    )

    await send_file_to_user(1, feishu_open_id="ou_test")

    assert events == [
        ("markdown", "介绍文案"),
        ("file", "demo.mp4"),
    ]


@pytest.mark.asyncio
async def test_send_file_to_chat_sends_card_before_image(
    monkeypatch: pytest.MonkeyPatch,
):
    events = _install_download_test_stubs(monkeypatch, content_type=ContentType.image)

    await send_file_to_chat(1, chat_id="oc_test_chat")

    assert events == [
        ("card", "介绍文案"),
        ("chat_image", "demo.png"),
    ]


@pytest.mark.asyncio
async def test_send_file_to_chat_continues_when_card_send_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    events = _install_download_test_stubs(
        monkeypatch,
        content_type=ContentType.video,
        fail_markdown=True,
    )

    await send_file_to_chat(1, chat_id="oc_test_chat")

    assert events == [
        ("card", "介绍文案"),
        ("chat_file", "demo.mp4"),
    ]
