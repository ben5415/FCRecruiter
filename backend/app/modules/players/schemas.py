from pydantic import BaseModel, ConfigDict, Field


class ClubSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    club_team_id: int
    club_name: str | None


class CountrySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nationality_id: int
    nationality_name: str | None


class PlayerListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    player_id: int
    short_name: str | None
    long_name: str | None
    player_positions: str | None
    overall: int | None
    potential: int | None
    value_eur: int | None
    wage_eur: int | None
    age: int | None
    preferred_foot: str | None
    player_face_url: str | None
    club: ClubSummary | None
    country: CountrySummary | None


class PlayerPage(BaseModel):
    items: list[PlayerListItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)
