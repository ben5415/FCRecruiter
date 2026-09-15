"""Recruitment Agent 可见的类型化 Tool 输入与 Backend 响应。"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


RatingGrade = Literal["D", "C", "B", "A", "A+"]


class StrictToolInput(BaseModel):
    """拒绝模型生成的未声明参数，例如 tenant_id 或 sql。"""

    model_config = ConfigDict(extra="forbid")


class EmptyToolInput(StrictToolInput):
    pass


class CandidatePlayerInput(StrictToolInput):
    player_id: int = Field(gt=0)


class InjuryQueryInput(StrictToolInput):
    from_date: date | None = None
    to_date: date | None = None
    limit: int = Field(default=30, ge=1, le=50)

    @model_validator(mode="after")
    def validate_range(self) -> "InjuryQueryInput":
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValueError("from_date cannot be later than to_date")
        return self


class PlayerSearchInput(StrictToolInput):
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
    def validate_age_range(self) -> "PlayerSearchInput":
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age cannot be greater than max_age")
        return self


class KnowledgeSearchInput(StrictToolInput):
    query: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)
    min_similarity: float = Field(default=0.25, ge=-1, le=1)


class ToolPlayer(BaseModel):
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

    @computed_field
    @property
    def evidence_source_id(self) -> str:
        return f"player:{self.player_id}"


class SquadToolResult(BaseModel):
    club_name: str | None
    players: list[ToolPlayer]
    total: int

    @computed_field
    @property
    def evidence_source_id(self) -> str:
        return "squad:current"


class TacticToolResult(BaseModel):
    formation: str | None
    playing_style: str | None
    notes: str | None
    updated_at: datetime | None

    @computed_field
    @property
    def evidence_source_id(self) -> str:
        return "tactic:current"


class InjuryToolItem(BaseModel):
    event_id: int
    player_id: int | None
    player_name: str | None
    injury_date: date | None
    description: str | None
    recovery_days: int | None
    expected_return_date: date | None

    @computed_field
    @property
    def evidence_source_id(self) -> str:
        return f"event:{self.event_id}"


class InjuryToolResult(BaseModel):
    items: list[InjuryToolItem]
    total: int


class PlayerSearchToolResult(BaseModel):
    items: list[ToolPlayer]
    total_matched: int
    returned: int
