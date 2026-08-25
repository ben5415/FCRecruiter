from pydantic import BaseModel, ConfigDict, Field, SecretStr


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)
    password: SecretStr = Field(min_length=1, max_length=1024)


class AccountClubResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_team_id: int
    club_name: str | None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None
    email: str | None
    role: str
    is_active: bool
    managed_club_team_id: int
    managed_club: AccountClubResponse


class AuthResponse(BaseModel):
    user: UserResponse
    csrf_token: str


class MessageResponse(BaseModel):
    message: str
