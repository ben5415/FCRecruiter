import { useEffect, useMemo, useState, type FormEvent } from "react";

import { createEvent, deleteEvent, listEvents, updateEvent, type EventWrite, type TeamEvent, type TeamEventType } from "../api/events";
import { getSquad } from "../api/team";
import type { PlayerListItem } from "../api/players";
import type { Role } from "../api/auth";
import { useAuth } from "../auth/AuthContext";

const LABELS: Record<TeamEventType, string> = { medical: "Medical", training: "Training", dressing_room: "Dressing room" };
const WRITE_TYPES: Record<Role, TeamEventType[]> = {
  manager: ["medical", "training", "dressing_room"], doctor: ["medical"],
  coach: ["training", "dressing_room"], player: ["dressing_room"],
};

interface EventFormState {
  playerId: string; injuryDate: string; eventDate: string; description: string;
  recoveryDays: string; trainingProject: string; trainingEffect: string;
}
const EMPTY_FORM: EventFormState = { playerId: "", injuryDate: "", eventDate: "", description: "", recoveryDays: "", trainingProject: "", trainingEffect: "" };

export function EventsPage() {
  const { user, csrfToken } = useAuth();
  const writableTypes = WRITE_TYPES[user!.role];
  const [events, setEvents] = useState<TeamEvent[]>([]);
  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [filter, setFilter] = useState<TeamEventType | "all">("all");
  const [eventType, setEventType] = useState<TeamEventType>(writableTypes[0]);
  const [form, setForm] = useState<EventFormState>(EMPTY_FORM);
  const [editing, setEditing] = useState<TeamEvent | null>(null);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [eventResult, squad] = await Promise.all([listEvents(filter === "all" ? undefined : filter), getSquad()]);
      setEvents(eventResult.items); setPlayers(squad.players);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load events"); }
  };
  useEffect(() => { void load(); }, [filter]);

  const canEdit = (event: TeamEvent) => writableTypes.includes(event.event_type);
  const payload = useMemo<EventWrite>(() => {
    if (eventType === "medical") return { player_id: Number(form.playerId), injury_date: form.injuryDate, description: form.description, recovery_days: Number(form.recoveryDays) };
    if (eventType === "training") return { player_id: Number(form.playerId), event_date: form.eventDate, training_project: form.trainingProject, training_effect: Number(form.trainingEffect) };
    return { event_date: form.eventDate, description: form.description };
  }, [eventType, form]);

  function resetForm(type = writableTypes[0]) { setEditing(null); setEventType(type); setForm(EMPTY_FORM); }
  function startEdit(event: TeamEvent) {
    setEditing(event); setEventType(event.event_type);
    setForm({ playerId: String(event.player?.player_id ?? ""), injuryDate: event.injury_date ?? "", eventDate: event.event_date ?? "", description: event.description ?? "", recoveryDays: String(event.recovery_days ?? ""), trainingProject: event.training_project ?? "", trainingEffect: String(event.training_effect ?? "") });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      if (editing) await updateEvent(editing.id, payload, csrfToken!);
      else await createEvent(eventType, payload, csrfToken!);
      resetForm(); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save event"); }
  }

  async function remove(event: TeamEvent) {
    if (!window.confirm("Delete this team event?")) return;
    try { await deleteEvent(event.id, csrfToken!); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not delete event"); }
  }

  return <main className="marketplace events-page">
    <div className="marketplace__header"><div><p className="eyebrow">Club timeline</p><h1>Team events</h1></div><p>Shared medical, training and dressing-room context for {user?.tenant.name}.</p></div>
    <section className="event-composer">
      <div className="event-composer__header"><h2>{editing ? `Edit ${LABELS[eventType]} event` : "Add event"}</h2>{editing && <button className="button--secondary" onClick={() => resetForm()}>Cancel edit</button>}</div>
      {!editing && <div className="event-type-picker">{writableTypes.map((type) => <button className={eventType === type ? "event-type-picker__active" : "button--secondary"} key={type} onClick={() => resetForm(type)}>{LABELS[type]}</button>)}</div>}
      <form className="event-form" onSubmit={submit}>
        {(eventType === "medical" || eventType === "training") && <label>Player *<select required value={form.playerId} onChange={(e) => setForm({ ...form, playerId: e.target.value })}><option value="">Select a squad player</option>{players.map((player) => <option key={player.player_id} value={player.player_id}>{player.short_name}</option>)}</select></label>}
        {eventType === "medical" && <><label>Injury date *<input required type="date" value={form.injuryDate} onChange={(e) => setForm({ ...form, injuryDate: e.target.value })} /></label><label>Recovery days *<input required min="0" type="number" value={form.recoveryDays} onChange={(e) => setForm({ ...form, recoveryDays: e.target.value })} /></label></>}
        {(eventType === "training" || eventType === "dressing_room") && <label>Event date *<input required type="date" value={form.eventDate} onChange={(e) => setForm({ ...form, eventDate: e.target.value })} /></label>}
        {eventType === "training" && <><label>Training project *<input required value={form.trainingProject} onChange={(e) => setForm({ ...form, trainingProject: e.target.value })} /></label><label>Effect score *<input required type="number" value={form.trainingEffect} onChange={(e) => setForm({ ...form, trainingEffect: e.target.value })} /></label></>}
        {(eventType === "medical" || eventType === "dressing_room") && <label className="event-form__description">Description *<textarea required maxLength={4000} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>}
        <button type="submit">{editing ? "Save changes" : "Add event"}</button>
      </form>
    </section>
    {error && <p className="form-error">{error}</p>}
    <div className="event-filters"><button className={filter === "all" ? "event-type-picker__active" : "button--secondary"} onClick={() => setFilter("all")}>All</button>{Object.entries(LABELS).map(([type, label]) => <button className={filter === type ? "event-type-picker__active" : "button--secondary"} key={type} onClick={() => setFilter(type as TeamEventType)}>{label}</button>)}</div>
    <div className="event-list">{events.map((event) => <article className={`event-card event-card--${event.event_type}`} key={event.id}>
      <div><p className="event-card__type">{LABELS[event.event_type]}</p><h2>{event.player?.short_name || LABELS[event.event_type]}</h2></div>
      <div className="event-card__body">{event.event_type === "medical" && <p>{event.description}<br/><strong>{event.injury_date}</strong> · {event.recovery_days} days · return {event.expected_return_date}</p>}{event.event_type === "training" && <p><strong>{event.event_date}</strong> · {event.training_project} · effect <strong>{event.training_effect}</strong></p>}{event.event_type === "dressing_room" && <p><strong>{event.event_date}</strong><br/>{event.description}</p>}<small>Added by {event.created_by?.display_name || event.created_by?.username || "Deleted user"} · {new Date(event.created_at).toLocaleString()}</small></div>
      <div className="event-card__actions">{canEdit(event) && <button className="button--secondary" onClick={() => startEdit(event)}>Edit</button>}{user?.role === "manager" && <button className="button--danger" onClick={() => void remove(event)}>Delete</button>}</div>
    </article>)}{events.length === 0 && <div className="page-message">No team events yet.</div>}</div>
  </main>;
}
