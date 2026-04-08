"""API router aggregation."""

from fastapi import APIRouter

from app.routers import admin, audit, auth, content, search, system

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(content.router)
router.include_router(audit.router)
router.include_router(search.router)
router.include_router(admin.router)
router.include_router(system.router)
