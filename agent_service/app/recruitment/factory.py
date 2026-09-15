"""真实招募 Agent 的模型、Tool 与 Runner 装配。"""

from collections.abc import Sequence

from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr

from agent_service.app.config import get_agent_settings
from agent_service.app.recruitment.schemas import RecruitmentReport, recruitment_fallback
from agent_service.app.recruitment.tools import (
    RECRUITMENT_TOOL_NAMES,
    build_recruitment_tools_from_settings,
)
from agent_service.app.runtime.model_adapter import LangChainModelAdapter
from agent_service.app.runtime.runner import AgentRunner
from agent_service.app.runtime.schemas import AgentLimits


def build_recruitment_runner(
    allowed_tools: Sequence[str] = RECRUITMENT_TOOL_NAMES,
) -> AgentRunner[RecruitmentReport]:
    settings = get_agent_settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required for recruitment analysis")
    model = ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=SecretStr(settings.deepseek_api_key),
        base_url=settings.deepseek_base_url,
        temperature=0,
        timeout=30,
        max_retries=1,
    )
    return AgentRunner(
        model=LangChainModelAdapter(model),
        tools=build_recruitment_tools_from_settings(),
        output_model=RecruitmentReport,
        fallback_factory=recruitment_fallback,
        limits=AgentLimits(max_steps=6, max_tool_calls=8),
        allowed_tools=allowed_tools,
    )
