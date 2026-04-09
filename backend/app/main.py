from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.bot.router import router as bot_router
from app.core.config import settings
from app.core.middleware import RequestIdMiddleware, register_exception_handlers
from app.db.session import engine
from app.routers.router import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时预热连接池，避免第一批请求承担 TCP+TLS+PG 握手延迟
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    # 优雅关闭：归还所有连接，避免云 RDS 侧留悬挂连接
    await engine.dispose()


app = FastAPI(
    title="PromoFlow API",
    version="0.1.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    lifespan=lifespan,
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
