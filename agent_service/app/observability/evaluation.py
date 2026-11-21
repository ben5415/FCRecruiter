"""无需调用 LLM 的确定性离线评测规则。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agent_service.app.observability.models import AgentRun
from agent_service.app.recruitment.schemas import RecruitmentReport


class RuleCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class RuleEvaluation(BaseModel):
    score: float = Field(ge=0, le=1)
    passed: bool
    checks: list[RuleCheck]


class JudgeEvaluation(BaseModel):
    """LLM Judge 必须返回的紧凑结构，避免自由文本不可比较。"""

    model_config = ConfigDict(extra="forbid")
    relevance: int = Field(ge=1, le=5)
    evidence_use: int = Field(ge=1, le=5)
    actionability: int = Field(ge=1, le=5)
    verdict: Literal["pass", "fail"]
    reason: str = Field(max_length=500)


def evaluate_recruitment_run(run: AgentRun) -> RuleEvaluation:
    checks: list[RuleCheck] = []
    try:
        report = RecruitmentReport.model_validate(run.output)
        checks.append(RuleCheck(name="pydantic_schema", passed=True, detail="Valid RecruitmentReport"))
    except ValidationError as error:
        return RuleEvaluation(score=0, passed=False, checks=[
            RuleCheck(name="pydantic_schema", passed=False, detail=str(error))
        ])

    successful_tools = {e.name for e in run.events if e.event_type == "tool" and e.success}
    required_tools = {"get_squad", "get_current_tactic"}
    missing_tools = sorted(required_tools - successful_tools)
    if report.candidates and not ({"search_players", "get_candidate_player"} & successful_tools):
        missing_tools.append("search_players|get_candidate_player")
    checks.append(RuleCheck(
        name="tool_selection", passed=not missing_tools,
        detail="Required tools used" if not missing_tools else f"Missing: {', '.join(missing_tools)}",
    ))

    eligible_ids = _eligible_player_ids(run)
    recommended_ids = {candidate.player_id for candidate in report.candidates}
    illegal_ids = sorted(recommended_ids - eligible_ids)
    candidate_check = not recommended_ids or (bool(eligible_ids) and not illegal_ids)
    checks.append(RuleCheck(
        name="candidate_legality", passed=candidate_check,
        detail="All candidates came from deterministic search" if candidate_check
        else f"Candidates outside search results: {illegal_ids}",
    ))

    incomplete = [f"need:{need.position}" for need in report.needs if not need.evidence]
    incomplete += [f"player:{candidate.player_id}" for candidate in report.candidates
                   if not candidate.evidence]
    checks.append(RuleCheck(
        name="evidence_completeness", passed=not incomplete,
        detail="All claims contain evidence" if not incomplete else f"Missing: {', '.join(incomplete)}",
    ))
    score = sum(check.passed for check in checks) / len(checks)
    return RuleEvaluation(score=score, passed=all(check.passed for check in checks), checks=checks)


def _eligible_player_ids(run: AgentRun) -> set[int]:
    ids: set[int] = set()
    for event in run.events:
        if event.event_type != "tool" or not event.success:
            continue
        value: Any = event.details.get("result", {}).get("value", {})
        players = value.get("items", []) if event.name == "search_players" else (
            [value] if event.name == "get_candidate_player" else []
        )
        for player in players:
            if isinstance(player, dict) and isinstance(player.get("player_id"), int):
                ids.add(player["player_id"])
    return ids
