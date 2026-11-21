from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.tactics.models import Formation, PlayingStyle


class TacticEditorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None


class CurrentTacticResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    formation: Formation | None
    playing_style: PlayingStyle | None
    notes: str | None
    updated_by: TacticEditorResponse | None
    updated_at: datetime | None


class UpdateCurrentTacticRequest(BaseModel):
    formation: Formation
    playing_style: PlayingStyle
    notes: str | None = Field(default=None, max_length=2000)
