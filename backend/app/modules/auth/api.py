from datetime import datetime, timedelta, timezone
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.modules.auth.dependencies import AuthContext, get_auth_context, require_csrf
from app.modules.auth.models import User, UserSession
from app.modules.auth.schemas import AuthResponse, LoginRequest, MessageResponse, UserResponse
from app.modules.auth.security import (
    DUMMY_PASSWORD_HASH,
    generate_token,
    hash_token,
    normalize_identifier,
    verify_password,
)
from app.shared.database import get_db_session


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
) -> AuthResponse:
    identifier = normalize_identifier(payload.identifier)
    user = db.scalar(
        select(User).where(
            or_(User.username_normalized == identifier, User.email_normalized == identifier)
        )
    )
    encoded = user.password_hash if user else DUMMY_PASSWORD_HASH
    valid = verify_password(payload.password.get_secret_value(), encoded)
    if user is None or not valid or not user.is_active or not user.tenant.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    settings = get_settings()
    raw_token = generate_token()
    csrf_token = generate_token()
    now = datetime.now(timezone.utc)
    db.add(
        UserSession(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(raw_token),
            csrf_token=csrf_token,
            expires_at=now + timedelta(hours=settings.session_lifetime_hours),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    )
    user.last_login_at = now
    db.commit()
    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        max_age=settings.session_lifetime_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return AuthResponse(user=UserResponse.model_validate(user), csrf_token=csrf_token)


@router.get("/me", response_model=AuthResponse)
async def me(context: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthResponse:
    return AuthResponse(
        user=UserResponse.model_validate(context.user),
        csrf_token=context.session.csrf_token,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    context: Annotated[AuthContext, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db_session)],
) -> MessageResponse:
    context.session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/", samesite="lax")
    return MessageResponse(message="Logged out")
