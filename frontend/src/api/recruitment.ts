import { getApiError } from "./errors";

export interface Evidence { source_type: string; source_id: string; description: string }
export interface SuggestedFilters {
  positions: string[]; min_age: number | null; max_age: number | null;
  max_value_eur: number | null; max_wage_eur: number | null;
  preferred_foot: "Left" | "Right" | null; minimum_overall: string | null;
}
export interface RecruitmentReport {
  status: "completed" | "degraded";
  summary: string;
  needs: Array<{ position: string; priority: string; reason: string; evidence: Evidence[] }>;
  candidates: Array<{ player_id: number; player_name: string; fit_grade: string; reasons: string[]; risks: string[]; evidence: Evidence[] }>;
  suggested_filters: SuggestedFilters | null;
  assumptions: string[];
  uncertainty: "low" | "medium" | "high";
}
export interface RecruitmentAnalysisResult {
  output: RecruitmentReport; degraded: boolean; error_code: string | null;
  step_count: number; tool_call_count: number;
}

export async function analyseRecruitment(
  payload: { question: string; player_id?: number }, csrfToken: string,
): Promise<RecruitmentAnalysisResult> {
  const response = await fetch("/api/recruitment/analyse", {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await getApiError(response));
  return response.json();
}
