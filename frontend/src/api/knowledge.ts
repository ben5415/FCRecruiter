import { getApiError } from "./errors";

export interface KnowledgeDocument {
  document_id: string;
  title: string;
  source_uri: string;
  chunk_count: number;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface KnowledgeSearchHit {
  chunk_id: string;
  document_id: string;
  title: string;
  source_uri: string;
  content: string;
  similarity: number;
  chunk_index: number;
  metadata: Record<string, unknown>;
  evidence_source_id: string;
}

export interface KnowledgeSearchResult {
  query: string;
  hits: KnowledgeSearchHit[];
  retrieval_ms: number;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...init, credentials: "include" });
  if (!response.ok) throw new Error(await getApiError(response));
  return response.json();
}

export async function listKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  const result = await request<{ items: KnowledgeDocument[] }>("/api/knowledge/documents");
  return result.items;
}

export function uploadKnowledgeDocument(
  payload: { title: string; source_uri: string; content: string; metadata: Record<string, unknown> },
  csrfToken: string,
): Promise<{ document_id: string; chunk_count: number; created: boolean }> {
  return request("/api/knowledge/documents", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function deleteKnowledgeDocument(documentId: string, csrfToken: string): Promise<{ message: string }> {
  return request(`/api/knowledge/documents/${documentId}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export function searchKnowledge(
  payload: { query: string; limit: number; min_similarity: number },
  csrfToken: string,
): Promise<KnowledgeSearchResult> {
  return request("/api/knowledge/search", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}
