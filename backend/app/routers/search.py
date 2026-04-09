"""Search routes: semantic search + RAG."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.audit import SearchQueryIn, SearchResultOut
from app.schemas.content import ContentOut
from app.services.infrastructure.ai import generate_embedding, generate_rag_response
from app.services.search import semantic_search

router = APIRouter(prefix="/search", tags=["search"])


def _build_context_title(title: str | None) -> str:
    return title or "未命名素材"


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


@router.post("/rag", response_model=dict)
async def rag_search_route(
    body: SearchQueryIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """RAG: retrieve relevant content and generate a natural language answer."""
    command = body.to_domain()
    embedding = await generate_embedding(command.query)
    results = await semantic_search(db, query_embedding=embedding, command=command)
    context_docs = [
        (
            f"{_build_context_title(r.content.title)}: "
            f"{r.content.ai_summary or r.content.description or ''}"
        )
        for r in results
    ]
    answer = await generate_rag_response(command.query, context_docs)
    return {
        "answer": answer,
        "sources": [ContentOut.from_domain(r.content) for r in results],
    }
