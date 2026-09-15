import { type FormEvent, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { getPlayers, type PlayerPage } from "../api/players";
import { PlayerCard } from "../components/PlayerCard";
import { analyseRecruitment, type RecruitmentAnalysisResult } from "../api/recruitment";
import { useAuth } from "../auth/AuthContext";
import { RecruitmentReportPanel } from "../components/RecruitmentReportPanel";


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
  const { csrfToken } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const parsedPage = Number(searchParams.get("page"));
  const page = Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;
  const search = searchParams.get("search") ?? "";
  const position = searchParams.get("position") ?? "";
  const [pageSize, setPageSize] = useState(() => pageSizeForWidth(window.innerWidth));
  const previousPageSize = useRef(pageSize);
  const [searchDraft, setSearchDraft] = useState(search);
  const [positionDraft, setPositionDraft] = useState(position);
  const [pageDraft, setPageDraft] = useState(String(page));
  const [state, setState] = useState<PageState>({ kind: "loading" });
  const [analysis, setAnalysis] = useState<RecruitmentAnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState("");
  const [analysing, setAnalysing] = useState(false);

  function updateQuery(nextPage: number, nextSearch = search, nextPosition = position) {
    const parameters = new URLSearchParams();
    if (nextPage > 1) parameters.set("page", String(nextPage));
    if (nextSearch.trim()) parameters.set("search", nextSearch.trim());
    if (nextPosition.trim()) parameters.set("position", nextPosition.trim());
    setSearchParams(parameters);
  }

  useEffect(() => {
    function updatePageSize() {
      const nextPageSize = pageSizeForWidth(window.innerWidth);
      setPageSize(nextPageSize);
    }

    window.addEventListener("resize", updatePageSize);
    return () => window.removeEventListener("resize", updatePageSize);
  }, []);

  useEffect(() => {
    if (previousPageSize.current !== pageSize) {
      previousPageSize.current = pageSize;
      updateQuery(1);
    }
  }, [pageSize]);

  useEffect(() => {
    setSearchDraft(search);
    setPositionDraft(position);
    setPageDraft(String(page));
  }, [page, position, search]);

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
    updateQuery(1, searchDraft, positionDraft);
  }

  function clearFilters() {
    setSearchDraft("");
    setPositionDraft("");
    updateQuery(1, "", "");
  }

  function jumpToPage(event: FormEvent<HTMLFormElement>, totalPages: number) {
    event.preventDefault();
    const requestedPage = Number(pageDraft);
    if (!Number.isInteger(requestedPage)) {
      setPageDraft(String(page));
      return;
    }
    updateQuery(Math.min(Math.max(requestedPage, 1), totalPages));
  }

  async function analyseSquad() {
    if (!csrfToken) return;
    setAnalysing(true); setAnalysisError("");
    try {
      setAnalysis(await analyseRecruitment({ question: "Analyse our squad strength and depth by position, consider the current coach's formation and playing style, then produce the most important recruitment need and practical initial marketplace filters." }, csrfToken));
    } catch (reason) {
      setAnalysisError(reason instanceof Error ? reason.message : "Could not run recruitment analysis");
    } finally { setAnalysing(false); }
  }

  return (
    <main className="marketplace">
      <header className="marketplace__header">
        <div>
          <p className="eyebrow">Recruitment database</p>
          <h1>Player Marketplace</h1>
        </div>
        <div className="marketplace-agent-action"><p>Analyse squad gaps before filtering the market.</p><button type="button" onClick={() => void analyseSquad()} disabled={analysing}>{analysing ? "Analysing…" : "Generate recruitment brief"}</button></div>
      </header>

      {analysisError && <p className="form-error" role="alert">{analysisError}</p>}
      {analysis && <RecruitmentReportPanel result={analysis} onApplyFilters={(nextPosition) => { setPositionDraft(nextPosition); updateQuery(1, "", nextPosition); }} />}

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
            <button className="button--secondary" type="button" disabled={page <= 1} onClick={() => updateQuery(page - 1)}>Previous</button>
            <div className="pagination__pages">
              {paginationItems(page, state.data.pages).map((item) =>
                typeof item === "number" ? (
                  <button
                    className={item === page ? "pagination__number pagination__number--current" : "pagination__number"}
                    type="button"
                    key={item}
                    aria-current={item === page ? "page" : undefined}
                    onClick={() => updateQuery(item)}
                  >
                    {item}
                  </button>
                ) : (
                  <span className="pagination__ellipsis" key={item} aria-hidden="true">…</span>
                ),
              )}
            </div>
            <button className="button--secondary" type="button" disabled={page >= state.data.pages} onClick={() => updateQuery(page + 1)}>Next</button>
            <form className="pagination__jump" onSubmit={(event) => jumpToPage(event, state.data.pages)}>
              <label>Page <input aria-label="Page number" type="number" min="1" max={state.data.pages} value={pageDraft} onChange={(event) => setPageDraft(event.target.value)} /></label>
              <button className="button--secondary" type="submit">Go</button>
            </form>
          </nav>
        </>
      )}
    </main>
  );
}
