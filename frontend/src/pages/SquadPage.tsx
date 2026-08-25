import { useEffect, useState } from "react";

import { getSquad, type SquadResponse } from "../api/team";
import { PlayerCard } from "../components/PlayerCard";


type SquadState =
  | { kind: "loading" }
  | { kind: "success"; data: SquadResponse }
  | { kind: "error"; message: string };

export function SquadPage() {
  const [state, setState] = useState<SquadState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    getSquad(controller.signal)
      .then((data) => setState({ kind: "success", data }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        const message = error instanceof Error ? error.message : "Unknown error";
        setState({ kind: "error", message });
      });
    return () => controller.abort();
  }, []);

  return (
    <main className="marketplace squad-page">
      <header className="marketplace__header">
        <div>
          <p className="eyebrow">First team</p>
          <h1>{state.kind === "success" ? state.data.club.club_name : "Squad"}</h1>
        </div>
        <p>Review every player currently registered in the managed club.</p>
      </header>

      {state.kind === "loading" && <section className="page-message">Loading squad…</section>}
      {state.kind === "error" && (
        <section className="page-message page-message--error">
          <h2>Could not load squad</h2><p>{state.message}</p>
        </section>
      )}
      {state.kind === "success" && (
        <>
          <div className="results-summary squad-summary">
            <span>{state.data.total} first-team players</span>
            <span>Ordered by overall rating</span>
          </div>
          <section className="player-grid" aria-label="Manchester United squad">
            {state.data.players.map((player) => (
              <PlayerCard key={player.player_id} player={player} />
            ))}
          </section>
        </>
      )}
    </main>
  );
}
