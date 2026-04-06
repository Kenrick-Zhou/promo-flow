"""Auth service package."""

from app.services.auth.core import (
    get_feishu_app_token,
    get_user_by_id,
    list_users,
    login_with_code,
    update_user_role,
)
from app.services.auth.errors import (
    FeishuOAuthError,
    InsufficientPermissionError,
    InvalidTokenError,
    UserNotFoundError,
    raise_auth_error,
)

__all__ = [
    "get_feishu_app_token",
    "get_user_by_id",
    "list_users",
    "login_with_code",
    "update_user_role",
    "FeishuOAuthError",
    "InsufficientPermissionError",
    "InvalidTokenError",
    "UserNotFoundError",
    "raise_auth_error",
]
