import { useEffect, useState, type FormEvent } from "react";

import {
  deleteKnowledgeDocument,
  listKnowledgeDocuments,
  uploadKnowledgeDocument,
  type KnowledgeDocument,
} from "../api/knowledge";
import { useAuth } from "../auth/AuthContext";


export function KnowledgePage() {
  const { user, csrfToken } = useAuth();
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [sourceUri, setSourceUri] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    try {
      setDocuments(await listKnowledgeDocuments());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load knowledge documents");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  function selectFile(selected: File | null) {
    setFile(selected);
    if (selected && !title) {
      setTitle(selected.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " "));
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || !csrfToken) return;
    setError("");
    setSubmitting(true);
    try {
      if (file.size > 2_000_000) throw new Error("The knowledge file must be smaller than 2 MB");
      const content = await file.text();
      await uploadKnowledgeDocument({
        title: title.trim(),
        source_uri: sourceUri.trim() || `upload://${file.name}`,
        content,
        metadata: { filename: file.name },
      }, csrfToken);
      setFile(null);
      setTitle("");
      setSourceUri("");
      const input = document.getElementById("knowledge-file") as HTMLInputElement | null;
      if (input) input.value = "";
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not upload knowledge document");
    } finally {
      setSubmitting(false);
    }
  }

  async function remove(document: KnowledgeDocument) {
    if (!csrfToken || !window.confirm(`Delete knowledge document “${document.title}”?`)) return;
    setError("");
    try {
      await deleteKnowledgeDocument(document.document_id, csrfToken);
      setDocuments((current) => current.filter((item) => item.document_id !== document.document_id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete knowledge document");
    }
  }

  return <main className="marketplace knowledge-page">
    <div className="marketplace__header">
      <div><p className="eyebrow">{user?.tenant.name} · Private knowledge</p><h1>Knowledge Base</h1></div>
      <p>Maintain football and club-specific material available to this tenant&apos;s recruitment agent.</p>
    </div>

    <form className="knowledge-form" onSubmit={submit}>
      <label><span>Document <span className="required-mark">*</span></span>
        <input id="knowledge-file" required type="file" accept=".md,.txt,text/plain,text/markdown" onChange={(event) => selectFile(event.target.files?.[0] || null)} />
      </label>
      <label><span>Title <span className="required-mark">*</span></span>
        <input required maxLength={300} value={title} onChange={(event) => setTitle(event.target.value)} />
      </label>
      <label>Original source URL
        <input maxLength={1000} placeholder="Optional" value={sourceUri} onChange={(event) => setSourceUri(event.target.value)} />
      </label>
      <button disabled={submitting}>{submitting ? "Processing…" : "Upload and index"}</button>
    </form>
    <p className="knowledge-hint">UTF-8 Markdown or text, maximum 2 MB. Uploading generates embeddings locally through Ollama.</p>
    {error && <p className="form-error" role="alert">{error}</p>}

    <div className="knowledge-list">
      {loading && <p>Loading knowledge documents…</p>}
      {!loading && documents.length === 0 && <div className="empty-state"><h2>No private knowledge yet</h2><p>Upload the first document for this club.</p></div>}
      {documents.map((document) => <article className="knowledge-row" key={document.document_id}>
        <div><strong>{document.title}</strong><p>{document.source_uri}</p></div>
        <div className="knowledge-row__meta"><span>{document.chunk_count} chunks</span><time>{new Date(document.created_at).toLocaleDateString()}</time></div>
        <button className="button--danger" type="button" onClick={() => void remove(document)}>Delete</button>
      </article>)}
    </div>
  </main>;
}
