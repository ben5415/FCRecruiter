from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.admin.schemas import CreateUserRequest, PasswordUpdateRequest, UpdateUserRequest, UserListResponse
from app.modules.auth.dependencies import AuthContext, require_csrf, require_manager
from app.modules.auth.models import User, UserSession
from app.modules.auth.schemas import MessageResponse, UserResponse
from app.modules.auth.security import hash_password, normalize_identifier
from app.shared.database import get_db_session


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
async def list_users(
    manager: Annotated[User, Depends(require_manager)],
    db: Annotated[Session, Depends(get_db_session)],
) -> UserListResponse:
    users = db.scalars(
        select(User).where(User.tenant_id == manager.tenant_id).order_by(User.created_at, User.id)
    ).all()
    return UserListResponse(items=[UserResponse.model_validate(user) for user in users])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    _: Annotated[AuthContext, Depends(require_csrf)],
    manager: Annotated[User, Depends(require_manager)],
    db: Annotated[Session, Depends(get_db_session)],
) -> UserResponse:
    username_normalized = normalize_identifier(payload.username)
    email_normalized = normalize_identifier(str(payload.email)) if payload.email else None
    duplicate = db.scalar(
        select(User).where(
            or_(
                User.username_normalized == username_normalized,
                User.email_normalized == email_normalized if email_normalized else False,
            )
        )
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")
    user = User(
        username=payload.username.strip(),
        username_normalized=username_normalized,
        email=str(payload.email) if payload.email else None,
        email_normalized=email_normalized,
        display_name=payload.display_name.strip() if payload.display_name else None,
        password_hash=hash_password(payload.password.get_secret_value()),
        role=payload.role,
        is_active=True,
        tenant_id=manager.tenant_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    context: Annotated[AuthContext, Depends(require_csrf)],
    manager: Annotated[User, Depends(require_manager)],
    db: Annotated[Session, Depends(get_db_session)],
) -> UserResponse:
    user = db.scalar(select(User).where(User.id == user_id, User.tenant_id == manager.tenant_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.is_active is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes supplied")
    if user.id == manager.id and payload.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot disable your own account")
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_active is False:
        for auth_session in db.scalars(
            select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        ):
            from datetime import datetime, timezone
            auth_session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    _: Annotated[AuthContext, Depends(require_csrf)],
    manager: Annotated[User, Depends(require_manager)],
    db: Annotated[Session, Depends(get_db_session)],
) -> MessageResponse:
    user = db.scalar(select(User).where(User.id == user_id, User.tenant_id == manager.tenant_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == manager.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )
    db.delete(user)
    db.commit()
    return MessageResponse(message="User deleted")


@router.patch("/users/{user_id}/password", response_model=MessageResponse)
async def update_password(
    user_id: int,
    payload: PasswordUpdateRequest,
    context: Annotated[AuthContext, Depends(require_csrf)],
    manager: Annotated[User, Depends(require_manager)],
    db: Annotated[Session, Depends(get_db_session)],
) -> MessageResponse:
    user = db.scalar(select(User).where(User.id == user_id, User.tenant_id == manager.tenant_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.password_hash = hash_password(payload.password.get_secret_value())
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for auth_session in db.scalars(
        select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    ):
        if auth_session.id != context.session.id:
            auth_session.revoked_at = now
    db.commit()
    return MessageResponse(message="Password updated")
