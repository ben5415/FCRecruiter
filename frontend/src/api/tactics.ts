import { getApiError } from "./errors";


export type Formation = "4-3-3" | "4-2-3-1" | "4-4-2" | "3-4-3" | "3-5-2" | "5-3-2";
export type PlayingStyle = "possession" | "counter_attack" | "high_press" | "low_block" | "wing_play" | "direct" | "balanced";

export interface CurrentTactic {
  formation: Formation | null;
  playing_style: PlayingStyle | null;
  notes: string | null;
  updated_by: { id: number; username: string; display_name: string | null } | null;
  updated_at: string | null;
}

export interface TacticWrite {
  formation: Formation;
  playing_style: PlayingStyle;
  notes: string | null;
}

export async function getCurrentTactic(signal?: AbortSignal): Promise<CurrentTactic> {
  const response = await fetch("/api/tactics/current", { credentials: "include", signal });
  if (!response.ok) throw new Error(await getApiError(response));
  return response.json();
}

export async function updateCurrentTactic(payload: TacticWrite, csrf: string): Promise<CurrentTactic> {
  const response = await fetch("/api/tactics/current", {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await getApiError(response));
  return response.json();
}
