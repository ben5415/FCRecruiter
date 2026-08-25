from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated
import hmac

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.modules.auth.models import User, UserSession
from app.modules.auth.security import hash_token
from app.shared.database import get_db_session


@dataclass
class AuthContext:
    user: User
    session: UserSession


async def get_auth_context(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
) -> AuthContext:
    raw_token = request.cookies.get(get_settings().session_cookie_name)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    auth_session = db.scalar(
        select(UserSession)
        .options(joinedload(UserSession.user))
        .where(
            UserSession.token_hash == hash_token(raw_token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
    )
    if auth_session is None or not auth_session.user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    return AuthContext(user=auth_session.user, session=auth_session)


async def get_current_user(context: Annotated[AuthContext, Depends(get_auth_context)]) -> User:
    return context.user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


async def require_csrf(
    request: Request,
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> AuthContext:
    supplied = request.headers.get("X-CSRF-Token", "")
    if not hmac.compare_digest(supplied, context.session.csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") not in get_settings().allowed_frontend_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid request origin")
    return context
