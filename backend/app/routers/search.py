"""Search routes: semantic search + RAG."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.audit import SearchQueryIn, SearchResultOut
from app.services.infrastructure.ai import generate_embedding
from app.services.search import semantic_search

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=list[SearchResultOut])
async def semantic_search_route(
    body: SearchQueryIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Semantic search over approved content using pgvector cosine similarity."""
    command = body.to_domain()
    embedding = await generate_embedding(command.query)
    results = await semantic_search(db, query_embedding=embedding, command=command)
    return [SearchResultOut.from_domain(r) for r in results]
