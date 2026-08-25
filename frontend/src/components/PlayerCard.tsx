import { useState } from "react";

import type { PlayerListItem } from "../api/players";


const euroFormatter = new Intl.NumberFormat("en", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 1,
  notation: "compact",
});

function formatMoney(value: number | null): string {
  return value === null ? "Unknown" : euroFormatter.format(value);
}

function positionGroup(positions: string | null): string {
  const primaryPosition = positions?.split(",")[0]?.trim().toUpperCase();
  if (primaryPosition === "GK") return "goalkeeper";
  if (["CB", "LB", "RB", "LWB", "RWB"].includes(primaryPosition ?? "")) {
    return "defender";
  }
  if (["CDM", "CM", "CAM", "LM", "RM"].includes(primaryPosition ?? "")) {
    return "midfielder";
  }
  if (["LW", "RW", "CF", "ST"].includes(primaryPosition ?? "")) {
    return "attacker";
  }
  return "unknown";
}

export function PlayerCard({ player }: { player: PlayerListItem }) {
  const [imageFailed, setImageFailed] = useState(false);
  const name = player.short_name ?? player.long_name ?? `Player ${player.player_id}`;
  const initials = name.split(" ").map((part) => part[0]).join("").slice(0, 2);
  const group = positionGroup(player.player_positions);

  return (
    <article className="player-card">
      <div className="player-card__identity">
        <div className={`player-card__portrait player-card__portrait--${group}`}>
          {player.player_face_url && !imageFailed ? (
            <img src={player.player_face_url} alt="" onError={() => setImageFailed(true)} />
          ) : (
            <span>{initials}</span>
          )}
        </div>
        <div className="player-card__name">
          <p className="player-card__position">{player.player_positions ?? "Unknown"}</p>
          <h2>{name}</h2>
          <p>{player.club?.club_name ?? "Free agent"}</p>
        </div>
      </div>

      <dl className="player-card__ratings">
        <div><dt>OVR</dt><dd>{player.overall ?? "—"}</dd></div>
        <div><dt>POT</dt><dd>{player.potential ?? "—"}</dd></div>
      </dl>

      <dl className="player-card__details">
        <div><dt>Age</dt><dd>{player.age ?? "Unknown"}</dd></div>
        <div><dt>Nation</dt><dd>{player.country?.nationality_name ?? "Unknown"}</dd></div>
        <div><dt>Value</dt><dd>{formatMoney(player.value_eur)}</dd></div>
        <div><dt>Wage</dt><dd>{formatMoney(player.wage_eur)}</dd></div>
      </dl>
    </article>
  );
}
