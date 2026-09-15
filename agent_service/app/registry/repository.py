from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from agent_service.app.registry.models import AgentDefinition, AgentDefinitionStatus


class AgentDefinitionNotFoundError(LookupError):
    pass


class ActiveAgentDefinitionNotFoundError(LookupError):
    pass


class AgentDefinitionRepository:
    def __init__(self, session: Session):
        self._session = session

    def list_versions(self, agent_key: str) -> list[AgentDefinition]:
        return list(self._session.scalars(
            select(AgentDefinition).where(AgentDefinition.agent_key == agent_key)
            .order_by(AgentDefinition.version.desc())
        ))

    def discover_active(self, agent_key: str) -> AgentDefinition:
        definition = self._session.scalar(select(AgentDefinition).where(
            AgentDefinition.agent_key == agent_key,
            AgentDefinition.status == AgentDefinitionStatus.ACTIVE,
        ))
        if definition is None:
            raise ActiveAgentDefinitionNotFoundError(f"No active definition for {agent_key}")
        return definition

    def register_current(self, *, agent_key: str, name: str, description: str,
                         system_prompt: str, tool_names: list[str], output_schema: dict) -> tuple[AgentDefinition, bool]:
        latest = self._session.scalar(select(AgentDefinition).where(
            AgentDefinition.agent_key == agent_key
        ).order_by(AgentDefinition.version.desc()).limit(1))
        if latest and latest.system_prompt == system_prompt and latest.tool_names == tool_names and latest.output_schema == output_schema:
            return latest, False
        next_version = (self._session.scalar(select(func.max(AgentDefinition.version)).where(
            AgentDefinition.agent_key == agent_key
        )) or 0) + 1
        definition = AgentDefinition(
            agent_key=agent_key, version=next_version, name=name, description=description,
            system_prompt=system_prompt, tool_names=tool_names, output_schema=output_schema,
            status=AgentDefinitionStatus.DRAFT,
        )
        self._session.add(definition)
        self._session.commit()
        self._session.refresh(definition)
        return definition, True

    def set_status(self, agent_key: str, version: int, status: AgentDefinitionStatus) -> AgentDefinition:
        definition = self._session.scalar(select(AgentDefinition).where(
            AgentDefinition.agent_key == agent_key, AgentDefinition.version == version
        ))
        if definition is None:
            raise AgentDefinitionNotFoundError(f"Definition {agent_key} v{version} not found")
        if status == AgentDefinitionStatus.ACTIVE:
            self._session.execute(update(AgentDefinition).where(
                AgentDefinition.agent_key == agent_key,
                AgentDefinition.status == AgentDefinitionStatus.ACTIVE,
            ).values(status=AgentDefinitionStatus.DISABLED))
        definition.status = status
        self._session.commit()
        self._session.refresh(definition)
        return definition

