import { type FormEvent, useEffect, useState } from "react";

import { getPlayers, type PlayerPage } from "../api/players";
import { PlayerCard } from "../components/PlayerCard";


type PageState =
  | { kind: "loading" }
  | { kind: "success"; data: PlayerPage }
  | { kind: "error"; message: string };

type PaginationItem = number | "ellipsis-left" | "ellipsis-right";

function pageSizeForWidth(width: number): number {
  if (width <= 520) return 8;
  if (width <= 800) return 12;
  if (width <= 1100) return 18;
  return 24;
}

function paginationItems(currentPage: number, totalPages: number): PaginationItem[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }
  if (currentPage <= 4) {
    return [1, 2, 3, 4, 5, "ellipsis-right", totalPages];
  }
  if (currentPage >= totalPages - 3) {
    return [
      1,
      "ellipsis-left",
      totalPages - 4,
      totalPages - 3,
      totalPages - 2,
      totalPages - 1,
      totalPages,
    ];
  }
  return [
    1,
    "ellipsis-left",
    currentPage - 1,
    currentPage,
    currentPage + 1,
    "ellipsis-right",
    totalPages,
  ];
}

export function PlayersPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(() => pageSizeForWidth(window.innerWidth));
  const [searchDraft, setSearchDraft] = useState("");
  const [positionDraft, setPositionDraft] = useState("");
  const [search, setSearch] = useState("");
  const [position, setPosition] = useState("");
  const [state, setState] = useState<PageState>({ kind: "loading" });

  useEffect(() => {
    function updatePageSize() {
      const nextPageSize = pageSizeForWidth(window.innerWidth);
      setPageSize(nextPageSize);
    }

    window.addEventListener("resize", updatePageSize);
    return () => window.removeEventListener("resize", updatePageSize);
  }, []);

  useEffect(() => {
    setPage(1);
  }, [pageSize]);

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    getPlayers({ page, pageSize, search, position, signal: controller.signal })
      .then((data) => setState({ kind: "success", data }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        const message = error instanceof Error ? error.message : "Unknown error";
        setState({ kind: "error", message });
      });
    return () => controller.abort();
  }, [page, pageSize, position, search]);

  function submitFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setSearch(searchDraft);
    setPosition(positionDraft);
  }

  function clearFilters() {
    setSearchDraft("");
    setPositionDraft("");
    setSearch("");
    setPosition("");
    setPage(1);
  }

  return (
    <main className="marketplace">
      <header className="marketplace__header">
        <div>
          <p className="eyebrow">Recruitment database</p>
          <h1>Player Marketplace</h1>
        </div>
        <p>Browse the FC26 player pool. Recruitment analysis will be added later.</p>
      </header>

      <form className="filters" onSubmit={submitFilters}>
        <label>Player name
          <input value={searchDraft} onChange={(e) => setSearchDraft(e.target.value)} placeholder="e.g. Bellingham" />
        </label>
        <label>Position
          <input value={positionDraft} onChange={(e) => setPositionDraft(e.target.value)} placeholder="e.g. CM" maxLength={10} />
        </label>
        <button type="submit">Search</button>
        <button className="button--secondary" type="button" onClick={clearFilters}>Clear</button>
      </form>

      {state.kind === "loading" && <section className="page-message">Loading players…</section>}
      {state.kind === "error" && (
        <section className="page-message page-message--error">
          <h2>Could not load players</h2><p>{state.message}</p>
        </section>
      )}
      {state.kind === "success" && state.data.items.length === 0 && (
        <section className="page-message"><h2>No matching players</h2><p>Try removing a filter.</p></section>
      )}
      {state.kind === "success" && state.data.items.length > 0 && (
        <>
          <div className="results-summary">
            <span>{state.data.total.toLocaleString()} players</span>
            <span>{state.data.page_size} per page · Page {state.data.page} of {state.data.pages}</span>
          </div>
          <section className="player-grid" aria-label="Players">
            {state.data.items.map((player) => <PlayerCard key={player.player_id} player={player} />)}
          </section>
          <nav className="pagination" aria-label="Player pagination">
            <button className="button--secondary" type="button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button>
            <div className="pagination__pages">
              {paginationItems(page, state.data.pages).map((item) =>
                typeof item === "number" ? (
                  <button
                    className={item === page ? "pagination__number pagination__number--current" : "pagination__number"}
                    type="button"
                    key={item}
                    aria-current={item === page ? "page" : undefined}
                    onClick={() => setPage(item)}
                  >
                    {item}
                  </button>
                ) : (
                  <span className="pagination__ellipsis" key={item} aria-hidden="true">…</span>
                ),
              )}
            </div>
            <button className="button--secondary" type="button" disabled={page >= state.data.pages} onClick={() => setPage((value) => value + 1)}>Next</button>
          </nav>
        </>
      )}
    </main>
  );
}
