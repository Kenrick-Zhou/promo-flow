from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_session
from app.domains.content import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer()


async def get_db(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error_code": "invalid_token",
            "message": "Invalid or expired token.",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_access_token(credentials.credentials)
    except JWTError as err:
        raise credentials_exception from err

    user = await db.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    return user


def require_role(*roles: UserRole):
    """Dependency factory: restrict endpoint to specific roles."""

    async def _check(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "insufficient_permission",
                    "message": "Insufficient permissions.",
                },
            )
        return current_user

    return _check
