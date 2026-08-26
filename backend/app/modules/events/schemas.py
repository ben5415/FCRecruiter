from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.events.models import TeamEventType


class TeamEventWrite(BaseModel):
    player_id: int | None = None
    injury_date: date | None = None
    event_date: date | None = None
    description: str | None = Field(default=None, max_length=4000)
    recovery_days: int | None = Field(default=None, ge=0)
    training_project: str | None = Field(default=None, max_length=200)
    training_effect: int | None = Field(default=None, ge=0, le=10)


class CreateTeamEventRequest(TeamEventWrite):
    event_type: TeamEventType


class UpdateTeamEventRequest(TeamEventWrite):
    pass


class EventPlayerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: int
    short_name: str | None


class EventCreatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None


class TeamEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: TeamEventType
    player: EventPlayerResponse | None
    created_by: EventCreatorResponse | None
    injury_date: date | None
    event_date: date | None
    description: str | None
    recovery_days: int | None
    expected_return_date: date | None
    training_project: str | None
    training_effect: int | None
    created_at: datetime
    updated_at: datetime


class TeamEventListResponse(BaseModel):
    items: list[TeamEventResponse]
    total: int
