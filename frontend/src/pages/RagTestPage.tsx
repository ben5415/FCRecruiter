import { useState, type FormEvent } from "react";

import {
  searchKnowledge,
  type KnowledgeSearchResult,
} from "../api/knowledge";
import { useAuth } from "../auth/AuthContext";


export function RagTestPage() {
  const { user, csrfToken } = useAuth();
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(5);
  const [minSimilarity, setMinSimilarity] = useState(0.25);
  const [result, setResult] = useState<KnowledgeSearchResult | null>(null);
  const [roundTripMs, setRoundTripMs] = useState<number | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!csrfToken || !query.trim()) return;
    setSearching(true);
    setError("");
    setResult(null);
    setRoundTripMs(null);
    const started = performance.now();
    try {
      const next = await searchKnowledge({
        query: query.trim(),
        limit,
        min_similarity: minSimilarity,
      }, csrfToken);
      setRoundTripMs(performance.now() - started);
      setResult(next);
    } catch (reason) {
      setRoundTripMs(performance.now() - started);
      setError(reason instanceof Error ? reason.message : "Could not run knowledge retrieval");
    } finally {
      setSearching(false);
    }
  }

  return <main className="marketplace rag-test-page">
    <div className="marketplace__header">
      <div>
        <p className="eyebrow">{user?.tenant.name} · Internal evaluation</p>
        <h1>RAG Test</h1>
      </div>
      <p>Test BGE-M3 and pgvector retrieval directly. This page does not call the chat model.</p>
    </div>

    <form className="rag-test-form" onSubmit={submit}>
      <label className="rag-test-form__query">Query
        <textarea
          autoFocus
          maxLength={2000}
          placeholder="Example: What qualities should a centre-back have in a high pressing system?"
          required
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      <label>Top K
        <input
          max={20}
          min={1}
          type="number"
          value={limit}
          onChange={(event) => setLimit(Number(event.target.value))}
        />
      </label>
      <label>Minimum similarity
        <input
          max={1}
          min={-1}
          step={0.05}
          type="number"
          value={minSimilarity}
          onChange={(event) => setMinSimilarity(Number(event.target.value))}
        />
      </label>
      <button disabled={searching || !csrfToken}>{searching ? "Retrieving…" : "Run retrieval"}</button>
    </form>

    <p className="knowledge-hint">
      Results are limited to global knowledge and the signed-in tenant. Change the threshold to inspect false positives and missed results.
    </p>
    {error && <p className="form-error" role="alert">{error}</p>}

    {result && <section className="rag-test-results" aria-live="polite">
      <div className="rag-test-metrics">
        <div><span>Hits</span><strong>{result.hits.length}</strong></div>
        <div><span>Agent retrieval</span><strong>{result.retrieval_ms.toFixed(1)} ms</strong></div>
        <div><span>Browser round trip</span><strong>{roundTripMs?.toFixed(1)} ms</strong></div>
        <div><span>Threshold</span><strong>{minSimilarity.toFixed(2)}</strong></div>
      </div>

      {result.hits.length === 0
        ? <div className="empty-state"><h2>No passage passed the threshold</h2><p>Try a lower threshold, or confirm that this tenant has indexed knowledge.</p></div>
        : <div className="rag-hit-list">{result.hits.map((hit, index) => <article className="rag-hit" key={hit.chunk_id}>
          <header>
            <div><p className="eyebrow">Rank {index + 1} · Chunk {hit.chunk_index}</p><h2>{hit.title}</h2></div>
            <strong>{hit.similarity.toFixed(3)}</strong>
          </header>
          <p className="rag-hit__source">{hit.source_uri}</p>
          <p className="rag-hit__content">{hit.content}</p>
          <code>{hit.evidence_source_id}</code>
        </article>)}</div>}
    </section>}
  </main>;
}
