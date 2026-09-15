from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RecruitmentAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=3, max_length=4000)
    player_id: int | None = Field(default=None, gt=0)


class Evidence(BaseModel):
    source_type: Literal["squad", "tactic", "event", "player", "knowledge"]
    source_id: str
    description: str


class RecruitmentNeed(BaseModel):
    position: str
    priority: Literal["low", "medium", "high"]
    reason: str
    evidence: list[Evidence]


class CandidateRecommendation(BaseModel):
    player_id: int
    player_name: str
    fit_grade: Literal["D", "C", "B", "A", "A+"]
    reasons: list[str]
    risks: list[str]
    evidence: list[Evidence]


class SuggestedPlayerFilters(BaseModel):
    positions: list[str] = Field(default_factory=list)
    min_age: int | None = None
    max_age: int | None = None
    max_value_eur: int | None = None
    max_wage_eur: int | None = None
    preferred_foot: Literal["Left", "Right"] | None = None
    minimum_overall: Literal["D", "C", "B", "A", "A+"] | None = None


class RecruitmentReport(BaseModel):
    status: Literal["completed", "degraded"]
    summary: str
    needs: list[RecruitmentNeed]
    candidates: list[CandidateRecommendation]
    suggested_filters: SuggestedPlayerFilters | None = None
    assumptions: list[str]
    uncertainty: Literal["low", "medium", "high"]


class RecruitmentAnalysisResponse(BaseModel):
    output: RecruitmentReport
    degraded: bool
    error_code: str | None
    step_count: int
    tool_call_count: int
    trace: list[dict]
