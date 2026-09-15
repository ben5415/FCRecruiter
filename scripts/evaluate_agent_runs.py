"""离线评测已保存的 Recruitment Agent Runs；LLM Judge 默认不启用。"""

import argparse
import asyncio
from statistics import mean

from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import SecretStr

from agent_service.app.config import get_agent_settings
from agent_service.app.observability.evaluation import JudgeEvaluation, evaluate_recruitment_run
from agent_service.app.observability.models import EvaluationResult
from agent_service.app.observability.repository import ObservabilityRepository
from agent_service.app.shared.database import get_agent_session_factory


JUDGE_PROMPT = """You evaluate football recruitment reports. Judge only relevance,
evidence use and actionability. Do not introduce new football facts. Return the required schema."""


async def judge_run(run) -> JudgeEvaluation:
    settings = get_agent_settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required when --judge is enabled")
    model = ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=SecretStr(settings.deepseek_api_key),
        base_url=settings.deepseek_base_url,
        temperature=0,
        max_retries=1,
    ).with_structured_output(JudgeEvaluation)
    return await model.ainvoke([
        SystemMessage(content=JUDGE_PROMPT),
        HumanMessage(content=f"Question:\n{run.question}\n\nReport:\n{run.output}"),
    ])


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--judge", action="store_true", help="Judge at most --judge-limit runs")
    parser.add_argument("--judge-limit", type=int, default=3)
    args = parser.parse_args()
    if args.limit < 1 or not 0 <= args.judge_limit <= 10:
        parser.error("--limit must be positive and --judge-limit must be between 0 and 10")

    with get_agent_session_factory()() as session:
        repository = ObservabilityRepository(session)
        runs = repository.list_runs(limit=args.limit)
        scores = []
        for index, run in enumerate(runs):
            rules = evaluate_recruitment_run(run)
            scores.append(rules.score)
            repository.save_evaluation(EvaluationResult(
                run_id=run.id, evaluator="rules-v1", score=rules.score,
                passed=rules.passed, details=rules.model_dump(mode="json"),
            ))
            print(f"{run.id} rules={rules.score:.2f} passed={rules.passed}")
            if args.judge and index < args.judge_limit:
                judged = await judge_run(run)
                judge_score = mean([judged.relevance, judged.evidence_use, judged.actionability]) / 5
                repository.save_evaluation(EvaluationResult(
                    run_id=run.id, evaluator=f"llm-judge:{get_agent_settings().deepseek_model}",
                    score=judge_score, passed=judged.verdict == "pass",
                    details=judged.model_dump(mode="json"),
                ))
                print(f"  judge={judge_score:.2f} verdict={judged.verdict}")
        print(f"evaluated={len(runs)} average_rule_score={mean(scores) if scores else 0:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
