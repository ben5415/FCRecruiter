import json
from uuid import uuid4

from agent_service.app.observability.evaluation import evaluate_recruitment_run
from agent_service.app.observability.models import AgentRun, AgentTraceRecord


def test_rules_accept_grounded_candidate_from_deterministic_search() -> None:
    run = AgentRun(
        id=uuid4(), tenant_id=1, user_id=2, agent_key="recruitment", agent_version=3,
        model_name="fake", question="Recommend a winger", degraded=False,
        step_count=3, tool_call_count=2, input_tokens=10, output_tokens=5,
        total_tokens=15, latency_ms=50,
        output={
            "status": "completed", "summary": "A winger is needed.",
            "needs": [{
                "position": "RW", "priority": "high", "reason": "Depth is limited.",
                "evidence": [{"source_type": "squad", "source_id": "squad:current",
                              "description": "Current squad"}],
            }],
            "candidates": [{
                "player_id": 7, "player_name": "Candidate", "fit_grade": "A",
                "reasons": ["Fits role"], "risks": ["Needs scouting"],
                "evidence": [{"source_type": "player", "source_id": "player:7",
                              "description": "Search result"}],
            }],
            "assumptions": [], "uncertainty": "medium",
        },
    )
    run.events = [
        AgentTraceRecord(sequence=1, step=1, event_type="tool", name="get_squad",
                         success=True, latency_ms=2, details={}),
        AgentTraceRecord(sequence=2, step=1, event_type="tool", name="get_current_tactic",
                         success=True, latency_ms=2, details={}),
        AgentTraceRecord(sequence=3, step=2, event_type="tool", name="search_players",
                         success=True, latency_ms=3, details={"result": {"value": {
                             "items": [{"player_id": 7}]
                         }}}),
    ]

    result = evaluate_recruitment_run(run)

    assert result.passed is True
    assert result.score == 1


def test_rules_reject_candidate_not_returned_by_search() -> None:
    run = AgentRun(
        id=uuid4(), tenant_id=1, user_id=2, agent_key="recruitment", agent_version=1,
        model_name="fake", question="Recommend", degraded=False, step_count=1,
        tool_call_count=1, input_tokens=0, output_tokens=0, total_tokens=0, latency_ms=1,
        output=json.loads(json.dumps({
            "status": "completed", "summary": "Recommendation", "needs": [],
            "candidates": [{"player_id": 99, "player_name": "Invented", "fit_grade": "B",
                            "reasons": ["Unknown"], "risks": [],
                            "evidence": [{"source_type": "player", "source_id": "player:99",
                                          "description": "Claim"}]}],
            "assumptions": [], "uncertainty": "high",
        })),
    )
    run.events = [
        AgentTraceRecord(sequence=1, step=1, event_type="tool", name="get_squad",
                         success=True, latency_ms=1, details={}),
        AgentTraceRecord(sequence=2, step=1, event_type="tool", name="get_current_tactic",
                         success=True, latency_ms=1, details={}),
        AgentTraceRecord(sequence=3, step=1, event_type="tool", name="search_players",
                         success=True, latency_ms=1,
                         details={"result": {"value": {"items": [{"player_id": 7}]}}}),
    ]

    result = evaluate_recruitment_run(run)

    assert result.passed is False
    assert next(c for c in result.checks if c.name == "candidate_legality").passed is False
