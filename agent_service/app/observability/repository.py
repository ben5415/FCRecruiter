"""轨迹和评测结果的最小持久化仓储。"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from agent_service.app.observability.models import AgentRun, AgentTraceRecord, EvaluationResult
from agent_service.app.runtime.schemas import AgentRunContext, AgentRunResult


class ObservabilityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_run(self, *, context: AgentRunContext, agent_key: str, agent_version: int,
                 model_name: str, question: str, result: AgentRunResult, latency_ms: int) -> AgentRun:
        model_events = [event for event in result.trace if event.event_type == "model"]
        run = AgentRun(
            id=context.run_id, tenant_id=context.tenant_id, user_id=context.user_id,
            agent_key=agent_key, agent_version=agent_version, model_name=model_name,
            question=question, output=result.output.model_dump(mode="json"),
            degraded=result.degraded, error_code=result.error_code,
            step_count=result.step_count, tool_call_count=result.tool_call_count,
            input_tokens=sum(int(e.details.get("input_tokens", 0)) for e in model_events),
            output_tokens=sum(int(e.details.get("output_tokens", 0)) for e in model_events),
            total_tokens=sum(int(e.details.get("total_tokens", 0)) for e in model_events),
            latency_ms=latency_ms,
        )
        run.events = [AgentTraceRecord(
            sequence=index, step=event.step, event_type=event.event_type, name=event.name,
            success=event.success, latency_ms=event.latency_ms, details=event.details,
        ) for index, event in enumerate(result.trace, start=1)]
        self._session.add(run)
        self._session.commit()
        return run

    def list_runs(self, *, limit: int = 100) -> list[AgentRun]:
        return list(self._session.scalars(
            select(AgentRun).options(selectinload(AgentRun.events))
            .order_by(AgentRun.created_at.desc()).limit(limit)
        ))

    def save_evaluation(self, result: EvaluationResult) -> None:
        self._session.add(result)
        self._session.commit()
