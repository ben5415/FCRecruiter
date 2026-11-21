from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.players.ratings import RatingGrade, rating_grade


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
    overall: RatingGrade | None
    potential: RatingGrade | None
    value_eur: int | None
    wage_eur: int | None
    age: int | None
    preferred_foot: str | None
    player_face_url: str | None
    club: ClubSummary | None
    country: CountrySummary | None

    @field_validator("overall", "potential", mode="before")
    @classmethod
    def hide_numeric_rating(cls, value: object) -> object:
        if isinstance(value, (int, float)):
            return rating_grade(value)
        return value


class PlayerPage(BaseModel):
    items: list[PlayerListItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class PlayerDetail(BaseModel):
    player_id: int
    short_name: str | None
    long_name: str | None
    player_positions: str | None
    overall: RatingGrade | None
    potential: RatingGrade | None
    value_eur: int | None
    wage_eur: int | None
    release_clause_eur: float | None
    age: int | None
    dob: str | None
    height_cm: int | None
    weight_kg: int | None
    preferred_foot: str | None
    weak_foot: int | None
    skill_moves: int | None
    international_reputation: int | None
    body_type: str | None
    player_tags: str | None
    player_traits: str | None
    player_face_url: str | None
    club_name: str | None
    league_name: str | None
    nationality_name: str | None
    club_position: str | None
    club_jersey_number: float | None
    club_loaned_from: str | None
    club_joined_date: str | None
    club_contract_valid_until_year: float | None
    attributes: dict[str, dict[str, RatingGrade | None]]
    position_ratings: dict[str, RatingGrade | None]

    @field_validator("overall", "potential", mode="before")
    @classmethod
    def hide_numeric_rating(cls, value: object) -> object:
        if isinstance(value, (int, float)):
            return rating_grade(value)
        return value
