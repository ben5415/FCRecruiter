const PRESET_CLUB_IDS = new Set([
  1, 2, 5, 9, 10, 11, 13, 18, // Premier League
  21, 22,                       // Bundesliga
  240, 241, 243,                // La Liga
  73,                            // Ligue 1
  44, 45, 47,                   // Serie A
  111768, 112540, 110955,        // Chinese Super League
]);

export function getTeamTheme(clubId: number | undefined): string {
  return clubId && PRESET_CLUB_IDS.has(clubId) ? `club-${clubId}` : "neutral";
}
