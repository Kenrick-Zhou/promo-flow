from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bot.router import router as bot_router
from app.core.config import settings
from app.core.middleware import RequestIdMiddleware, register_exception_handlers
from app.routers.router import router as api_router

app = FastAPI(
    title="PromoFlow API",
    version="0.1.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
)

# Middleware (order matters: outermost first)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
register_exception_handlers(app)

app.include_router(api_router)
app.include_router(bot_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
