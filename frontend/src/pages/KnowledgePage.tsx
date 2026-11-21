import { useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";

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
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

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

  function addFiles(selectedFiles: FileList | File[]) {
    const selected = Array.from(selectedFiles);
    const accepted: File[] = [];
    const rejected: string[] = [];
    for (const file of selected) {
      if (!/\.(md|txt)$/i.test(file.name)) {
        rejected.push(`${file.name}: only .md and .txt files are supported`);
      } else if (file.size > 2_000_000) {
        rejected.push(`${file.name}: file is larger than 2 MB`);
      } else {
        accepted.push(file);
      }
    }
    setFiles((current) => {
      const merged = new Map(current.map((file) => [`${file.name}:${file.size}:${file.lastModified}`, file]));
      accepted.forEach((file) => merged.set(`${file.name}:${file.size}:${file.lastModified}`, file));
      return [...merged.values()];
    });
    setSuccess("");
    setError(rejected.join("; "));
    if (fileInput.current) fileInput.current.value = "";
  }

  function dropFiles(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (!submitting) addFiles(event.dataTransfer.files);
  }

  function removeSelectedFile(target: File) {
    setFiles((current) => current.filter((file) => file !== target));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (files.length === 0 || !csrfToken) return;
    setError("");
    setSuccess("");
    setSubmitting(true);
    const failed: Array<{ file: File; message: string }> = [];
    let uploaded = 0;
    for (const [index, file] of files.entries()) {
      setUploadProgress(`Indexing ${index + 1} of ${files.length}: ${file.name}`);
      try {
        const content = await file.text();
        await uploadKnowledgeDocument({
          title: file.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").trim(),
          source_uri: `upload://${file.name}`,
          content,
          metadata: {
            filename: file.name,
            size_bytes: file.size,
            last_modified: file.lastModified,
          },
        }, csrfToken);
        uploaded += 1;
      } catch (reason) {
        failed.push({
          file,
          message: reason instanceof Error ? reason.message : "Upload failed",
        });
      }
    }
    setFiles(failed.map((item) => item.file));
    setUploadProgress("");
    setSubmitting(false);
    if (uploaded > 0) setSuccess(`${uploaded} document${uploaded === 1 ? "" : "s"} processed successfully.`);
    if (failed.length > 0) setError(failed.map((item) => `${item.file.name}: ${item.message}`).join("; "));
    if (uploaded > 0) await load();
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

    <form className="knowledge-upload-form" onSubmit={submit}>
      <input
        ref={fileInput}
        className="knowledge-file-input"
        id="knowledge-files"
        multiple
        type="file"
        accept=".md,.txt,text/plain,text/markdown"
        onChange={(event) => event.target.files && addFiles(event.target.files)}
      />
      <div
        className={dragging ? "knowledge-file-picker knowledge-file-picker--dragging" : "knowledge-file-picker"}
        onDragEnter={(event) => { event.preventDefault(); if (!submitting) setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false);
        }}
        onDrop={dropFiles}
      >
        <button
          className="knowledge-file-picker__button"
          disabled={submitting}
          type="button"
          onClick={() => fileInput.current?.click()}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4" />
          </svg>
          Choose files
        </button>
        <div>
          <strong>{files.length > 0 ? `${files.length} file${files.length === 1 ? "" : "s"} selected` : "Select knowledge documents"}</strong>
          <p>Choose multiple files or drag them here. Markdown and text, up to 2 MB each.</p>
        </div>
      </div>

      {files.length > 0 && <div className="knowledge-selected-files">
        {files.map((file) => <div className="knowledge-selected-file" key={`${file.name}:${file.size}:${file.lastModified}`}>
          <div><strong>{file.name}</strong><span>{Math.max(1, Math.ceil(file.size / 1024))} KB</span></div>
          <button
            aria-label={`Remove ${file.name}`}
            disabled={submitting}
            type="button"
            onClick={() => removeSelectedFile(file)}
          >×</button>
        </div>)}
      </div>}

      <div className="knowledge-upload-actions">
        <p>{uploadProgress || "Files are indexed sequentially to avoid overloading the local embedding model."}</p>
        <button disabled={submitting || files.length === 0}>
          {submitting ? "Processing…" : `Upload and index${files.length > 0 ? ` (${files.length})` : ""}`}
        </button>
      </div>
    </form>
    {success && <p className="form-success" role="status">{success}</p>}
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
