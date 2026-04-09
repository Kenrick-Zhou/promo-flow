"""Integration tests for system management routes (categories and tags)."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.domains.content import UserRole
from app.main import app
from app.models.user import User
from tests.conftest import TEST_PREFIX

# Per-run unique suffix to avoid conflicts between test runs on shared DB
_RUN = uuid.uuid4().hex[:8]


def _n(name: str) -> str:
    """Build a test-unique name: __pytest__{run_id}_{name}"""
    return f"{TEST_PREFIX}{_RUN}_{name}"


# ============================================================
# Auth fixtures
# ============================================================


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    user = User(
        feishu_open_id=_n(f"admin_{uuid.uuid4().hex[:4]}"),
        feishu_union_id=_n(f"union_a_{uuid.uuid4().hex[:4]}"),
        name="测试管理员",
        role=UserRole.admin,
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def employee_user(db: AsyncSession) -> User:
    user = User(
        feishu_open_id=_n(f"emp_{uuid.uuid4().hex[:4]}"),
        feishu_union_id=_n(f"union_e_{uuid.uuid4().hex[:4]}"),
        name="测试员工",
        role=UserRole.employee,
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, admin_user: User) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: admin_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def employee_client(client: AsyncClient, employee_user: User) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: employee_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


# ============================================================
# Category Tests
# ============================================================


@pytest.mark.asyncio
async def test_list_categories_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_categories_authenticated(employee_client: AsyncClient):
    resp = await employee_client.get("/api/v1/categories")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_category_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/admin/categories", json={"name": _n("unauth")})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_category_as_employee_forbidden(employee_client: AsyncClient):
    resp = await employee_client.post(
        "/api/v1/admin/categories", json={"name": _n("emp_forbidden")}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_primary_category(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/admin/categories",
        json={"name": _n("健康资讯"), "description": "健康相关资讯类目"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert _n("健康资讯") in data["name"]
    assert data["description"] == "健康相关资讯类目"
    assert data["parent_id"] is None
    assert "id" in data


@pytest.mark.asyncio
async def test_create_secondary_category(admin_client: AsyncClient):
    primary = await admin_client.post(
        "/api/v1/admin/categories",
        json={"name": _n("产品介绍"), "description": "产品介绍类目"},
    )
    assert primary.status_code == 201
    parent_id = primary.json()["id"]

    resp = await admin_client.post(
        "/api/v1/admin/categories",
        json={
            "name": _n("营养补充剂"),
            "description": "营养补充剂子类",
            "parent_id": parent_id,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["parent_id"] == parent_id


@pytest.mark.asyncio
async def test_create_category_duplicate_name(admin_client: AsyncClient):
    await admin_client.post(
        "/api/v1/admin/categories",
        json={"name": _n("重复类目"), "description": "重复测试"},
    )
    resp = await admin_client.post(
        "/api/v1/admin/categories",
        json={"name": _n("重复类目"), "description": "重复测试"},
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "duplicate_category"


@pytest.mark.asyncio
async def test_update_category(admin_client: AsyncClient):
    created = await admin_client.post(
        "/api/v1/admin/categories",
        json={"name": _n("旧名称"), "description": "原始说明"},
    )
    cat_id = created.json()["id"]

    resp = await admin_client.patch(
        f"/api/v1/admin/categories/{cat_id}",
        json={"name": _n("新名称"), "description": "更新后说明"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == _n("新名称")
    assert resp.json()["description"] == "更新后说明"


@pytest.mark.asyncio
async def test_update_category_not_found(admin_client: AsyncClient):
    resp = await admin_client.patch(
        "/api/v1/admin/categories/2147483647", json={"name": _n("不存在")}
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "category_not_found"


@pytest.mark.asyncio
async def test_delete_category(admin_client: AsyncClient):
    created = await admin_client.post(
        "/api/v1/admin/categories",
        json={"name": _n("待删除类目"), "description": "待删除说明"},
    )
    cat_id = created.json()["id"]
    resp = await admin_client.delete(f"/api/v1/admin/categories/{cat_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_category_with_children(admin_client: AsyncClient):
    parent = await admin_client.post(
        "/api/v1/admin/categories",
        json={"name": _n("父类目"), "description": "父类目说明"},
    )
    parent_id = parent.json()["id"]
    await admin_client.post(
        "/api/v1/admin/categories",
        json={
            "name": _n("子类目"),
            "description": "子类目说明",
            "parent_id": parent_id,
        },
    )
    resp = await admin_client.delete(f"/api/v1/admin/categories/{parent_id}")
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "category_has_children"


@pytest.mark.asyncio
async def test_list_categories_returns_tree(admin_client: AsyncClient):
    primary = await admin_client.post(
        "/api/v1/admin/categories",
        json={"name": _n("类目树根"), "description": "树根说明"},
    )
    parent_id = primary.json()["id"]
    await admin_client.post(
        "/api/v1/admin/categories",
        json={
            "name": _n("类目树叶"),
            "description": "树叶说明",
            "parent_id": parent_id,
        },
    )

    resp = await admin_client.get("/api/v1/categories")
    assert resp.status_code == 200
    roots = [c for c in resp.json() if c["id"] == parent_id]
    assert len(roots) == 1
    assert len(roots[0]["children"]) == 1
    assert roots[0]["children"][0]["name"] == _n("类目树叶")


# ============================================================
# Tag Tests
# ============================================================


@pytest.mark.asyncio
async def test_list_tags_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/tags")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_tags_authenticated(employee_client: AsyncClient):
    resp = await employee_client.get("/api/v1/tags")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_tag(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/v1/admin/tags", json={"name": _n("健康"), "is_system": True}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == _n("健康")
    assert data["is_system"] is True


@pytest.mark.asyncio
async def test_create_tag_duplicate(admin_client: AsyncClient):
    await admin_client.post("/api/v1/admin/tags", json={"name": _n("重复标签")})
    resp = await admin_client.post("/api/v1/admin/tags", json={"name": _n("重复标签")})
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "duplicate_tag"


@pytest.mark.asyncio
async def test_update_tag(admin_client: AsyncClient):
    created = await admin_client.post("/api/v1/admin/tags", json={"name": _n("旧标签")})
    tag_id = created.json()["id"]

    resp = await admin_client.patch(
        f"/api/v1/admin/tags/{tag_id}", json={"name": _n("新标签")}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == _n("新标签")


@pytest.mark.asyncio
async def test_update_tag_not_found(admin_client: AsyncClient):
    resp = await admin_client.patch(
        "/api/v1/admin/tags/2147483647", json={"name": _n("不存在")}
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "tag_not_found"


@pytest.mark.asyncio
async def test_delete_tag(admin_client: AsyncClient):
    created = await admin_client.post(
        "/api/v1/admin/tags", json={"name": _n("待删除标签")}
    )
    tag_id = created.json()["id"]
    resp = await admin_client.delete(f"/api/v1/admin/tags/{tag_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_create_tag_as_employee_forbidden(employee_client: AsyncClient):
    resp = await employee_client.post(
        "/api/v1/admin/tags", json={"name": _n("员工标签")}
    )
    assert resp.status_code == 403
