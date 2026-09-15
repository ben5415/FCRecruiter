import { Link } from "react-router-dom";
import type { RecruitmentAnalysisResult } from "../api/recruitment";

const money = new Intl.NumberFormat("en", { style: "currency", currency: "EUR", notation: "compact" });

export function RecruitmentReportPanel({ result, onApplyFilters }: {
  result: RecruitmentAnalysisResult;
  onApplyFilters?: (position: string) => void;
}) {
  const report = result.output;
  const filters = report.suggested_filters;
  return <section className="agent-report" aria-live="polite">
    <div className="agent-report__heading"><div><p className="eyebrow">Agent analysis</p><h2>{report.status === "degraded" ? "Limited analysis" : "Recruitment brief"}</h2></div><span className={`uncertainty uncertainty--${report.uncertainty}`}>{report.uncertainty} uncertainty</span></div>
    <p className="agent-report__summary">{report.summary}</p>
    {report.needs.length > 0 && <div className="agent-report__section"><h3>Squad needs</h3><div className="agent-needs">{report.needs.map((need, index) => <article key={`${need.position}-${index}`}><strong>{need.position} · {need.priority}</strong><p>{need.reason}</p></article>)}</div></div>}
    {filters && <div className="agent-report__section"><h3>Suggested initial filters</h3><div className="filter-chips">
      {filters.positions.map((position) => <button type="button" key={position} onClick={() => onApplyFilters?.(position)}>{position}</button>)}
      {filters.min_age != null && <span>Age ≥ {filters.min_age}</span>}{filters.max_age != null && <span>Age ≤ {filters.max_age}</span>}
      {filters.max_value_eur != null && <span>Value ≤ {money.format(filters.max_value_eur)}</span>}
      {filters.max_wage_eur != null && <span>Wage ≤ {money.format(filters.max_wage_eur)}</span>}
      {filters.preferred_foot && <span>{filters.preferred_foot} foot</span>}{filters.minimum_overall && <span>OVR ≥ {filters.minimum_overall}</span>}
    </div></div>}
    {report.candidates.length > 0 && <div className="agent-report__section"><h3>Candidate assessment</h3>{report.candidates.map((candidate) => <article className="agent-candidate" key={candidate.player_id}><div><strong>{candidate.player_name}</strong><span>Fit {candidate.fit_grade}</span></div><ul>{candidate.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>{candidate.risks.length > 0 && <p><b>Risks:</b> {candidate.risks.join("; ")}</p>}<Link to={`/players/${candidate.player_id}`}>View player</Link></article>)}</div>}
    {report.assumptions.length > 0 && <details><summary>Assumptions and evidence boundary</summary><ul>{report.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></details>}
    <footer>{result.step_count} model steps · {result.tool_call_count} tool calls</footer>
  </section>;
}
