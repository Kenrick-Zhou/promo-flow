from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"


def create_access_token(
    subject: str | int, expires_delta: timedelta | None = None
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(subject), "exp": expire}
    return str(jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=ALGORITHM))


def decode_access_token(token: str) -> str:
    """Decode JWT and return the subject (user_id). Raises JWTError on failure."""
    payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[ALGORITHM])
    sub: str | None = payload.get("sub")
    if sub is None:
        raise JWTError("Missing subject")
    return sub
