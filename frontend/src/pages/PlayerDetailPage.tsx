import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getPlayerDetail, type PlayerDetail } from "../api/players";
import { analyseRecruitment, type RecruitmentAnalysisResult } from "../api/recruitment";
import { useAuth } from "../auth/AuthContext";
import { RecruitmentReportPanel } from "../components/RecruitmentReportPanel";

const money = new Intl.NumberFormat("en", { style: "currency", currency: "EUR", notation: "compact", maximumFractionDigits: 1 });
const label = (value: string) => value.split("_").map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");

export function PlayerDetailPage() {
  const { csrfToken } = useAuth();
  const { playerId } = useParams();
  const navigate = useNavigate();
  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [error, setError] = useState("");
  const [analysis, setAnalysis] = useState<RecruitmentAnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState("");
  const [analysing, setAnalysing] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getPlayerDetail(Number(playerId), controller.signal).then(setPlayer).catch((reason) => {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(reason instanceof Error ? reason.message : "Could not load player");
    });
    return () => controller.abort();
  }, [playerId]);

  if (error) return <main className="marketplace"><button className="button--secondary" onClick={() => navigate(-1)}>Back</button><div className="page-message page-message--error">{error}</div></main>;
  if (!player) return <main className="marketplace"><div className="page-message">Loading player details…</div></main>;
  const name = player.long_name || player.short_name || `Player ${player.player_id}`;

  async function analysePlayer() {
    if (!csrfToken) return;
    setAnalysing(true); setAnalysisError("");
    try {
      setAnalysis(await analyseRecruitment({
        player_id: player!.player_id,
        question: `Assess whether ${name} should be recruited. Compare the player's profile with our positional strength, squad depth and the coach's current tactical requirements. Explain fit, overlap and risks using available evidence.`,
      }, csrfToken));
    } catch (reason) {
      setAnalysisError(reason instanceof Error ? reason.message : "Could not analyse this player");
    } finally { setAnalysing(false); }
  }

  return <main className="marketplace player-detail-page">
    <button className="button--secondary player-detail__back" onClick={() => navigate(-1)}>← Back</button>
    <header className="player-detail__hero">
      <div className="player-detail__portrait">{player.player_face_url ? <img src={player.player_face_url} alt="" /> : <span>{player.short_name?.slice(0, 2)}</span>}</div>
      <div><p className="eyebrow">{player.player_positions || "Player profile"}</p><h1>{name}</h1><p>{player.club_name || "Free agent"} · {player.league_name || "No league"} · {player.nationality_name || "Unknown nationality"}</p></div>
      <dl className="player-detail__headline"><div><dt>OVR</dt><dd>{player.overall ?? "—"}</dd></div><div><dt>POT</dt><dd>{player.potential ?? "—"}</dd></div></dl>
    </header>

    <section className="player-agent-entry"><div><p className="eyebrow">Recruitment Agent</p><h2>Fit for this club</h2><p>Compare this player with the current squad and tactical approach.</p></div><button type="button" disabled={analysing} onClick={() => void analysePlayer()}>{analysing ? "Analysing…" : "Analyse recruitment fit"}</button></section>
    {analysisError && <p className="form-error" role="alert">{analysisError}</p>}
    {analysis && <RecruitmentReportPanel result={analysis} />}

    <section className="detail-panel"><h2>Profile</h2><dl className="detail-grid">
      <div><dt>Age / DOB</dt><dd>{player.age ?? "—"} · {player.dob || "—"}</dd></div><div><dt>Height / Weight</dt><dd>{player.height_cm ?? "—"} cm · {player.weight_kg ?? "—"} kg</dd></div>
      <div><dt>Preferred foot</dt><dd>{player.preferred_foot || "—"}</dd></div><div><dt>Weak foot</dt><dd>{player.weak_foot ?? "—"} / 5</dd></div><div><dt>Skill moves</dt><dd>{player.skill_moves ?? "—"} / 5</dd></div><div><dt>International reputation</dt><dd>{player.international_reputation ?? "—"} / 5</dd></div>
      <div><dt>Club role</dt><dd>{player.club_position || "—"} · #{player.club_jersey_number ?? "—"}</dd></div><div><dt>Contract</dt><dd>{player.club_joined_date || "—"} – {player.club_contract_valid_until_year ?? "—"}</dd></div>
      <div><dt>Value</dt><dd>{player.value_eur == null ? "—" : money.format(player.value_eur)}</dd></div><div><dt>Wage</dt><dd>{player.wage_eur == null ? "—" : money.format(player.wage_eur)}</dd></div><div><dt>Release clause</dt><dd>{player.release_clause_eur == null ? "—" : money.format(player.release_clause_eur)}</dd></div><div><dt>Body type</dt><dd>{player.body_type || "—"}</dd></div>
    </dl></section>

    <div className="attribute-sections">{Object.entries(player.attributes).map(([group, attributes]) => <section className="detail-panel" key={group}><h2>{group}</h2><dl className="attribute-grid">{Object.entries(attributes).map(([name, value]) => <div key={name}><dt>{label(name.replace(`${group.toLowerCase()}_`, ""))}</dt><dd>{value ?? "—"}</dd></div>)}</dl></section>)}</div>

    <section className="detail-panel"><h2>Position ratings</h2><dl className="position-rating-grid">{Object.entries(player.position_ratings).map(([position, rating]) => <div key={position}><dt>{position.toUpperCase()}</dt><dd>{rating || "—"}</dd></div>)}</dl></section>
    {(player.player_tags || player.player_traits) && <section className="detail-panel"><h2>Tags & traits</h2>{player.player_tags && <p><strong>Tags:</strong> {player.player_tags}</p>}{player.player_traits && <p><strong>Traits:</strong> {player.player_traits}</p>}</section>}
  </main>;
}
