"""Recruitment Agent 对外输出的严格业务契约。

这些类不是模型的内部思考过程，而是最终允许返回 Backend/Frontend 的字段。
extra='forbid' 会拒绝模型擅自添加的未知字段，避免前端逐渐依赖未定义输出。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_service.app.runtime.schemas import AgentRunContext


class Evidence(BaseModel):
    """一条分析依据，未来用于跳转到球员、战术、事件或知识片段。"""

    model_config = ConfigDict(extra="forbid")

    source_type: Literal["squad", "tactic", "event", "player", "knowledge"]
    source_id: str
    description: str


class RecruitmentNeed(BaseModel):
    """Agent 识别出的一个位置补强需求。"""

    model_config = ConfigDict(extra="forbid")

    position: str
    priority: Literal["low", "medium", "high"]
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)


class CandidateRecommendation(BaseModel):
    """一个候选球员及其适配理由、风险和证据。"""

    model_config = ConfigDict(extra="forbid")

    player_id: int
    player_name: str
    fit_grade: Literal["D", "C", "B", "A", "A+"]
    reasons: list[str]
    risks: list[str]
    evidence: list[Evidence] = Field(default_factory=list)


class RecruitmentReport(BaseModel):
    """前端最终渲染的完整报告，同时也是 Runner 的 output_model。"""

    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "degraded"] = "completed"
    summary: str
    needs: list[RecruitmentNeed] = Field(default_factory=list)
    candidates: list[CandidateRecommendation] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    uncertainty: Literal["low", "medium", "high"]


def recruitment_fallback(
    error_code: str,
    _message: str,
    _context: AgentRunContext,
) -> RecruitmentReport:
    """当模型或 Tool 链路失败时生成安全、可预测的报告。

    降级结果不伪造阵容结论或球员推荐，只声明当前不可用并提高不确定性。
    """

    return RecruitmentReport(
        status="degraded",
        summary="The recruitment analysis is temporarily unavailable.",
        assumptions=[f"Runtime fallback: {error_code}"],
        uncertainty="high",
    )
