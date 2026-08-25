import type { PlayerListItem } from "./players";


export type SquadResponse = {
  club: {
    club_team_id: number;
    club_name: string | null;
  };
  players: PlayerListItem[];
  total: number;
};

export async function getSquad(signal?: AbortSignal): Promise<SquadResponse> {
  const response = await fetch("/api/team/squad", {
    credentials: "include",
    signal,
  });
  if (!response.ok) {
    throw new Error(`Squad request failed with status ${response.status}`);
  }
  return (await response.json()) as SquadResponse;
}
