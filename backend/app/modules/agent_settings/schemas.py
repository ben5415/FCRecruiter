from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel

class AgentDefinitionView(BaseModel):
    id: UUID
    agent_key: str
    version: int
    name: str
    description: str
    tool_names: list[str]
    status: Literal["draft", "active", "disabled"]
    created_at: datetime
    updated_at: datetime

class AgentDefinitionList(BaseModel):
    items: list[AgentDefinitionView]

class RegistrationResult(BaseModel):
    definition: AgentDefinitionView
    created: bool
