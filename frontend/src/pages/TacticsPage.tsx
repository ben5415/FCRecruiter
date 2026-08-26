import { useEffect, useState, type FormEvent } from "react";

import { getCurrentTactic, updateCurrentTactic, type CurrentTactic, type Formation, type PlayingStyle } from "../api/tactics";
import { useAuth } from "../auth/AuthContext";


const FORMATIONS: Formation[] = ["4-3-3", "4-2-3-1", "4-4-2", "3-4-3", "3-5-2", "5-3-2"];
const STYLES: { value: PlayingStyle; label: string }[] = [
  { value: "balanced", label: "Balanced" },
  { value: "possession", label: "Possession" },
  { value: "counter_attack", label: "Counter attack" },
  { value: "high_press", label: "High press" },
  { value: "low_block", label: "Low block" },
  { value: "wing_play", label: "Wing play" },
  { value: "direct", label: "Direct" },
];

function styleLabel(style: PlayingStyle | null): string {
  return STYLES.find((option) => option.value === style)?.label ?? "Not configured";
}

function FormationPreview({ formation }: { formation: Formation }) {
  const lines = formation.split("-").map(Number).reverse();
  return <div className="tactic-pitch" aria-label={`${formation} formation preview`}>
    <div className="tactic-pitch__box" />
    {lines.map((count, lineIndex) => <div className="tactic-pitch__line" key={`${lineIndex}-${count}`}>
      {Array.from({ length: count }, (_, playerIndex) => <span className="tactic-pitch__player" key={playerIndex} />)}
    </div>)}
    <div className="tactic-pitch__line tactic-pitch__goalkeeper"><span className="tactic-pitch__player">GK</span></div>
  </div>;
}

export function TacticsPage() {
  const { user, csrfToken } = useAuth();
  const canEdit = user?.role === "manager" || user?.role === "coach";
  const [current, setCurrent] = useState<CurrentTactic | null>(null);
  const [formation, setFormation] = useState<Formation>("4-3-3");
  const [playingStyle, setPlayingStyle] = useState<PlayingStyle>("balanced");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getCurrentTactic(controller.signal).then((tactic) => {
      setCurrent(tactic);
      if (tactic.formation) setFormation(tactic.formation);
      if (tactic.playing_style) setPlayingStyle(tactic.playing_style);
      setNotes(tactic.notes ?? "");
    }).catch((reason) => {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(reason instanceof Error ? reason.message : "Could not load tactics");
    }).finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!csrfToken) return;
    setSaving(true); setError("");
    try {
      const tactic = await updateCurrentTactic({ formation, playing_style: playingStyle, notes: notes.trim() || null }, csrfToken);
      setCurrent(tactic); setNotes(tactic.notes ?? "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save tactics");
    } finally { setSaving(false); }
  }

  return <main className="marketplace tactics-page">
    <header className="marketplace__header"><div><p className="eyebrow">Match strategy</p><h1>Tactics</h1></div><p>Set the current formation and playing style for {user?.tenant.name}.</p></header>
    {loading ? <section className="page-message">Loading tactics…</section> : <div className="tactics-layout">
      <section className="tactic-panel tactic-panel--pitch">
        <div className="tactic-summary"><div><p className="eyebrow">Current setup</p><h2>{current?.formation ?? "Not configured"}</h2></div><strong>{styleLabel(current?.playing_style ?? null)}</strong></div>
        <FormationPreview formation={formation} />
        {current?.updated_at && <small>Last updated by {current.updated_by?.display_name || current.updated_by?.username || "Deleted user"} · {new Date(current.updated_at).toLocaleString()}</small>}
      </section>
      <section className="tactic-panel"><h2>{canEdit ? "Edit current tactics" : "Current tactical notes"}</h2>
        {canEdit ? <form className="tactic-form" onSubmit={submit}>
          <label>Formation *<select required value={formation} onChange={(event) => setFormation(event.target.value as Formation)}>{FORMATIONS.map((option) => <option key={option}>{option}</option>)}</select></label>
          <label>Playing style *<select required value={playingStyle} onChange={(event) => setPlayingStyle(event.target.value as PlayingStyle)}>{STYLES.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}</select></label>
          <label>Notes<textarea maxLength={2000} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Optional tactical instructions or context" /></label>
          <button disabled={saving} type="submit">{saving ? "Saving…" : "Save tactics"}</button>
        </form> : <p className="tactic-notes">{current?.notes || "No tactical notes have been added."}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
      </section>
    </div>}
  </main>;
}
