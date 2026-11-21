export type RatingGrade = "D" | "C" | "B" | "A" | "A+";

export type PlayerListItem = {
  player_id: number;
  short_name: string | null;
  long_name: string | null;
  player_positions: string | null;
  overall: RatingGrade | null;
  potential: RatingGrade | null;
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

export interface PlayerDetail {
  player_id: number; short_name: string | null; long_name: string | null;
  player_positions: string | null; overall: RatingGrade | null; potential: RatingGrade | null;
  value_eur: number | null; wage_eur: number | null; release_clause_eur: number | null;
  age: number | null; dob: string | null; height_cm: number | null; weight_kg: number | null;
  preferred_foot: string | null; weak_foot: number | null; skill_moves: number | null;
  international_reputation: number | null; body_type: string | null;
  player_tags: string | null; player_traits: string | null; player_face_url: string | null;
  club_name: string | null; league_name: string | null; nationality_name: string | null;
  club_position: string | null; club_jersey_number: number | null; club_loaned_from: string | null;
  club_joined_date: string | null; club_contract_valid_until_year: number | null;
  attributes: Record<string, Record<string, RatingGrade | null>>;
  position_ratings: Record<string, RatingGrade | null>;
}

export async function getPlayerDetail(playerId: number, signal?: AbortSignal): Promise<PlayerDetail> {
  const response = await fetch(`/api/players/${playerId}`, { credentials: "include", signal });
  if (!response.ok) throw new Error(`Player detail request failed with status ${response.status}`);
  return response.json();
}

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
