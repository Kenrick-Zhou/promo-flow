"""Search routes: unified hybrid search."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.audit import SearchQueryIn, SearchResultsOut
from app.services.search import raise_search_error, search_contents

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResultsOut)
async def search_route(
    body: SearchQueryIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Unified hybrid search over approved content."""
    command = body.to_domain()
    try:
        result = await search_contents(db, command=command)
    except Exception as exc:
        raise_search_error(exc)
    return SearchResultsOut.from_domain(result)
