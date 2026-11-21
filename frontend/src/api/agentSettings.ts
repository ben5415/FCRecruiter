import { getApiError } from "./errors";

export interface AgentDefinition { id: string; agent_key: string; version: number; name: string; description: string; tool_names: string[]; status: "draft" | "active" | "disabled"; created_at: string; updated_at: string; }
async function request<T>(path: string, init: RequestInit = {}): Promise<T> { const response = await fetch(path, { ...init, credentials: "include" }); if (!response.ok) throw new Error(await getApiError(response)); return response.json(); }
export async function listAgentVersions(): Promise<AgentDefinition[]> { return (await request<{ items: AgentDefinition[] }>("/api/agent-settings/versions")).items; }
function mutate<T>(path: string, csrfToken: string): Promise<T> { return request(path, { method: "POST", headers: { "X-CSRF-Token": csrfToken } }); }
export function registerCurrentAgent(csrfToken: string) { return mutate<{ definition: AgentDefinition; created: boolean }>("/api/agent-settings/register-current", csrfToken); }
export function enableAgentVersion(version: number, csrfToken: string) { return mutate<AgentDefinition>(`/api/agent-settings/versions/${version}/enable`, csrfToken); }
export function disableAgentVersion(version: number, csrfToken: string) { return mutate<AgentDefinition>(`/api/agent-settings/versions/${version}/disable`, csrfToken); }
