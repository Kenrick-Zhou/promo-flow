import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_pending_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/audit/pending")
    assert resp.status_code == 401
