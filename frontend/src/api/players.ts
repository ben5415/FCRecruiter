export type PlayerListItem = {
  player_id: number;
  short_name: string | null;
  long_name: string | null;
  player_positions: string | null;
  overall: number | null;
  potential: number | null;
  value_eur: number | null;
  wage_eur: number | null;
  age: number | null;
  preferred_foot: string | null;
  player_face_url: string | null;
  club: { club_team_id: number; club_name: string | null } | null;
  country: { nationality_id: number; nationality_name: string | null } | null;
};

export type PlayerPage = {
  items: PlayerListItem[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

type GetPlayersOptions = {
  page: number;
  pageSize?: number;
  search?: string;
  position?: string;
  signal?: AbortSignal;
};

export async function getPlayers({
  page,
  pageSize = 24,
  search,
  position,
  signal,
}: GetPlayersOptions): Promise<PlayerPage> {
  const parameters = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (search?.trim()) parameters.set("search", search.trim());
  if (position?.trim()) parameters.set("position", position.trim());

  const response = await fetch(`/api/players?${parameters}`, {
    credentials: "include",
    signal,
  });
  if (!response.ok) {
    throw new Error(`Player request failed with status ${response.status}`);
  }
  return (await response.json()) as PlayerPage;
}
