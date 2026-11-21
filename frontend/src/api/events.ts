import { getApiError } from "./errors";

export type TeamEventType = "medical" | "training" | "dressing_room";

export interface TeamEvent {
  id: number;
  event_type: TeamEventType;
  player: { player_id: number; short_name: string | null } | null;
  created_by: { id: number; username: string; display_name: string | null } | null;
  injury_date: string | null;
  event_date: string | null;
  description: string | null;
  recovery_days: number | null;
  expected_return_date: string | null;
  training_project: string | null;
  training_effect: number | null;
  created_at: string;
  updated_at: string;
}

export interface EventWrite {
  player_id?: number;
  injury_date?: string;
  event_date?: string;
  description?: string;
  recovery_days?: number;
  training_project?: string;
  training_effect?: number;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...init, credentials: "include" });
  if (!response.ok) throw new Error(await getApiError(response));
  return response.json();
}

export async function listEvents(type?: TeamEventType): Promise<{ items: TeamEvent[]; total: number }> {
  const query = type ? `?event_type=${type}` : "";
  return request(`/api/events${query}`);
}

export function createEvent(eventType: TeamEventType, payload: EventWrite, csrf: string): Promise<TeamEvent> {
  return request("/api/events", {
    method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ event_type: eventType, ...payload }),
  });
}

export function updateEvent(id: number, payload: EventWrite, csrf: string): Promise<TeamEvent> {
  return request(`/api/events/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(payload),
  });
}

export function deleteEvent(id: number, csrf: string): Promise<{ message: string }> {
  return request(`/api/events/${id}`, { method: "DELETE", headers: { "X-CSRF-Token": csrf } });
}
