"""Agent Tool API 的输入输出边界。

这些 Schema 有意小于浏览器 API 的数据模型，只把分析所需字段暴露给模型。
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.players.ratings import RatingGrade
from app.modules.tactics.models import Formation, PlayingStyle


class AgentPlayer(BaseModel):
    player_id: int
    name: str | None
    positions: str | None
    overall: RatingGrade | None
    potential: RatingGrade | None
    age: int | None
    value_eur: int | None
    wage_eur: int | None
    preferred_foot: str | None
    club_name: str | None
    nationality_name: str | None


class AgentSquadResponse(BaseModel):
    club_name: str | None
    players: list[AgentPlayer]
    total: int = Field(ge=0)


class AgentTacticResponse(BaseModel):
    formation: Formation | None
    playing_style: PlayingStyle | None
    notes: str | None
    updated_at: datetime | None


class InjuryEvent(BaseModel):
    event_id: int
    player_id: int | None
    player_name: str | None
    injury_date: date | None
    description: str | None
    recovery_days: int | None
    expected_return_date: date | None


class InjuryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_date: date | None = None
    to_date: date | None = None
    limit: int = Field(default=30, ge=1, le=50)

    @model_validator(mode="after")
    def validate_range(self) -> "InjuryQuery":
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValueError("from_date cannot be later than to_date")
        return self


class InjuryListResponse(BaseModel):
    items: list[InjuryEvent]
    total: int = Field(ge=0)


class PlayerSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search: str | None = Field(default=None, max_length=100)
    positions: list[str] = Field(default_factory=list, max_length=5)
    min_age: int | None = Field(default=None, ge=15, le=50)
    max_age: int | None = Field(default=None, ge=15, le=50)
    max_value_eur: int | None = Field(default=None, ge=0)
    max_wage_eur: int | None = Field(default=None, ge=0)
    preferred_foot: Literal["Left", "Right"] | None = None
    minimum_overall: RatingGrade | None = None
    limit: int = Field(default=10, ge=1, le=25)

    @model_validator(mode="after")
    def validate_filters(self) -> "PlayerSearchRequest":
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age cannot be greater than max_age")
        allowed_positions = {
            "GK", "RB", "RWB", "CB", "LB", "LWB", "CDM", "CM", "CAM",
            "RM", "RW", "LM", "LW", "CF", "ST",
        }
        normalized = [position.strip().upper() for position in self.positions]
        if any(position not in allowed_positions for position in normalized):
            raise ValueError("positions contains an unsupported football position")
        self.positions = normalized
        self.search = self.search.strip() if self.search else None
        return self


class PlayerSearchResponse(BaseModel):
    items: list[AgentPlayer]
    total_matched: int = Field(ge=0)
    returned: int = Field(ge=0)
