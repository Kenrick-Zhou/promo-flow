"""Auth routes: Feishu OAuth login."""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.domains.auth import FeishuLoginCommand
from app.schemas.user import TokenOut
from app.services.auth import FeishuOAuthError, login_with_code, raise_auth_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def feishu_login_url(request: Request):
    """Return the Feishu OAuth authorization URL for the frontend to redirect to."""
    params = urlencode(
        {
            "client_id": settings.FEISHU_APP_ID,
            "redirect_uri": settings.FEISHU_REDIRECT_URI,
            "response_type": "code",
            "scope": "contact:user.base:readonly",
        }
    )
    url = f"https://accounts.feishu.cn/open-apis/authen/v1/authorize?{params}"
    logger.info(
        "[auth/login] 生成 OAuth URL | client_id=%s | redirect_uri=%s | url=%s",
        settings.FEISHU_APP_ID,
        settings.FEISHU_REDIRECT_URI,
        url,
    )
    return {"authorization_url": url}


@router.get("/callback", response_model=TokenOut)
async def feishu_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> TokenOut:
    """Handle Feishu OAuth callback and return JWT."""
    logger.info(
        "[auth/callback] 收到 OAuth 回调 | code=%s...",
        code[:10] if len(code) > 10 else code,
    )
    try:
        session = await login_with_code(
            db,
            command=FeishuLoginCommand(code=code),
        )
    except FeishuOAuthError as exc:
        logger.error("[auth/callback] 飞书 OAuth 失败 | error=%s", exc)
        raise_auth_error(exc)

    return TokenOut.from_domain(session)
