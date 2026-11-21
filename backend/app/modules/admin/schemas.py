from pydantic import BaseModel, EmailStr, Field, SecretStr

from app.modules.auth.models import UserRole
from app.modules.auth.schemas import UserResponse


class UserListResponse(BaseModel):
    items: list[UserResponse]


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: SecretStr = Field(min_length=8, max_length=1024)
    display_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    role: UserRole = UserRole.PLAYER


class UpdateUserRequest(BaseModel):
    is_active: bool | None = None


class PasswordUpdateRequest(BaseModel):
    password: SecretStr = Field(min_length=8, max_length=1024)
